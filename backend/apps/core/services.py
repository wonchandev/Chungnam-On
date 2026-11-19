from django.db.models import Q

from .models import Block, Notification


def notify(user, type: str, title: str, body: str = "", **data) -> Notification | None:
    """알림 저장. 사용자가 알림을 끈 경우 저장하지 않음. (푸시 발송은 여기에 연결)"""
    if not user.notifications_enabled:
        return None
    return Notification.objects.create(user=user, type=type, title=title, body=body[:500], data=data)


def blocked_user_ids(user) -> set:
    """나와 차단 관계(내가 차단했거나 나를 차단한)인 유저 id"""
    if not user or not user.is_authenticated:
        return set()
    ids = set()
    for a, b in Block.objects.filter(Q(blocker=user) | Q(blocked=user)).values_list("blocker_id", "blocked_id"):
        ids.add(b if a == user.id else a)
    return ids


def is_blocked_between(u1, u2) -> bool:
    return Block.objects.filter(Q(blocker=u1, blocked=u2) | Q(blocker=u2, blocked=u1)).exists()
