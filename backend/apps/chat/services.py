from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import ServiceError
from apps.core.models import Notification
from apps.core.services import is_blocked_between, notify
from apps.translation.services import detect_source_language, translate_many

from . import presence

from .models import ChatParticipant, ChatRoom, Message, MessageTranslation


def room_group(room_id) -> str:
    return f"chat_{room_id}"


def serialize_message(msg: Message) -> dict:
    return {
        "id": msg.id,
        "room": msg.room_id,
        "sender": msg.sender_id,
        "text": msg.text,
        "image": msg.image.url if msg.image else None,
        "source_lang": msg.source_lang,
        "translations": {t.lang: t.text for t in msg.translations.all()},
        "created_at": msg.created_at.isoformat(),
    }


def get_or_create_room(user, other, job=None) -> ChatRoom:
    """user 와 other 사이의 (같은 공고) 채팅방을 반환, 없으면 생성. 차단 관계면 ServiceError."""
    if is_blocked_between(user, other):
        raise ServiceError("blocked", "차단 관계에서는 채팅할 수 없습니다.", 403)
    rooms = ChatRoom.objects.filter(job=job, participants__user=user).filter(participants__user=other)
    room = rooms.first()
    if room:
        ChatParticipant.objects.filter(room=room, user=user).update(left_at=None)  # 나갔던 방을 다시 열면 복원
        return room
    with transaction.atomic():
        room = ChatRoom.objects.create(job=job)
        for u in (user, other):
            lang = u.preferred_language if u.preferred_language in settings.SUPPORTED_LANGUAGES else settings.DEFAULT_LANGUAGE
            ChatParticipant.objects.create(room=room, user=u, language=lang)
    return room


def send_message(room: ChatRoom, sender, text: str = "", image=None) -> Message:
    """메시지 저장 → 상대방 언어로 자동 번역 → 방 그룹에 브로드캐스트 → 오프라인 상대에게 알림.
    차단 관계면 ServiceError. 나갔던 방은 보낸 쪽도 다시 보이게, 상대가 나간 방은 상대에게 다시 보이게 한다."""
    others = list(room.participants.exclude(user=sender).select_related("user"))
    if any(is_blocked_between(sender, p.user) for p in others):
        raise ServiceError("blocked", "차단 관계에서는 메시지를 보낼 수 없습니다.", 403)
    me = room.participants.get(user=sender)
    source_lang = detect_source_language(text, fallback=me.language)
    msg = Message.objects.create(room=room, sender=sender, text=text, image=image, source_lang=source_lang)
    if text:
        translated = translate_many(text, source_lang, [p.language for p in others], chat=True)
        for lang, t in translated.items():
            MessageTranslation.objects.create(message=msg, lang=lang, text=t)
    now = timezone.now()
    ChatRoom.objects.filter(pk=room.pk).update(last_message_at=now)
    ChatParticipant.objects.filter(room=room, user=sender).update(last_read_at=now, left_at=None)
    ChatParticipant.objects.filter(room=room).exclude(user=sender).update(left_at=None)
    msg = Message.objects.prefetch_related("translations").get(pk=msg.pk)
    broadcast(room.id, {"type": "chat.message", "message": serialize_message(msg)})
    for p in others:
        if not presence.is_online(p.user_id):  # 접속 중이면 실시간으로 받으므로 알림 생략
            _notify_new_message(p.user, room, sender, text or "사진을 보냈어요")
    return msg


def _notify_new_message(user, room, sender, preview):
    """방 단위로 안 읽은 알림 1개만 유지(내용 갱신)"""
    existing = [n for n in Notification.objects.filter(user=user, type="chat", is_read=False)[:20] if n.data.get("room_id") == room.id]
    if existing:
        n = existing[0]
        n.title, n.body = f"{sender.display_name}님의 새 메시지", preview[:500]
        n.save(update_fields=["title", "body"])
    else:
        notify(user, "chat", f"{sender.display_name}님의 새 메시지", preview, room_id=room.id)


def broadcast(room_id, event: dict) -> None:
    layer = get_channel_layer()
    if layer is not None:
        async_to_sync(layer.group_send)(room_group(room_id), event)
