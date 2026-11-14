"""WebSocket: ws://<host>/ws/chat/<room_id>/?token=<access>

클라이언트 → 서버:  {"type": "message", "text": "..."} | {"type": "read"}
서버 → 클라이언트:  {"type": "message", "message": {...원문+translations...}}
                    {"type": "read", "user": id, "read_at": iso}
                    {"type": "presence", "user": id, "online": bool}
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from . import presence
from .models import ChatParticipant
from .services import broadcast, room_group, send_message


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.room_id = int(self.scope["url_route"]["kwargs"]["room_id"])
        if not self.user.is_authenticated or not await self._is_participant():
            await self.close(code=4401 if not self.user.is_authenticated else 4403)
            return
        self.group = room_group(self.room_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await database_sync_to_async(presence.mark_connected)(self.user.id)
        await self.channel_layer.group_send(self.group, {"type": "chat.presence", "user": self.user.id, "online": True})

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)
            await database_sync_to_async(presence.mark_disconnected)(self.user.id)
            await self.channel_layer.group_send(
                self.group, {"type": "chat.presence", "user": self.user.id, "online": await database_sync_to_async(presence.is_online)(self.user.id)}
            )

    async def receive_json(self, content, **kwargs):
        kind = content.get("type")
        if kind == "message":
            text = (content.get("text") or "").strip()
            if not text or len(text) > 2000:
                await self.send_json({"type": "error", "message": "메시지는 1~2000자여야 합니다."})
                return
            await self._send(text)
        elif kind == "read":
            await self._mark_read()
        else:
            await self.send_json({"type": "error", "message": "알 수 없는 type 입니다."})

    # ── group event handlers ──
    async def chat_message(self, event):
        await self.send_json({"type": "message", "message": event["message"]})

    async def chat_read(self, event):
        await self.send_json({"type": "read", "user": event["user"], "read_at": event["read_at"]})

    async def chat_presence(self, event):
        await self.send_json({"type": "presence", "user": event["user"], "online": event["online"]})

    # ── db helpers ──
    @database_sync_to_async
    def _is_participant(self):
        return ChatParticipant.objects.filter(room_id=self.room_id, user=self.user).exists()

    @database_sync_to_async
    def _save_and_send(self, text):
        from apps.core.exceptions import ServiceError

        from .models import ChatRoom

        try:
            send_message(ChatRoom.objects.get(pk=self.room_id), self.user, text)
        except ServiceError as e:
            return str(e.detail)

    async def _send(self, text):
        err = await self._save_and_send(text)
        if err:
            await self.send_json({"type": "error", "message": err})

    @database_sync_to_async
    def _mark_read(self):
        now = timezone.now()
        ChatParticipant.objects.filter(room_id=self.room_id, user=self.user).update(last_read_at=now)
        broadcast(self.room_id, {"type": "chat.read", "user": self.user.id, "read_at": now.isoformat()})
