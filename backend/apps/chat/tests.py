from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import TestCase, TransactionTestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.chat.middleware import JWTAuthMiddleware
from apps.chat.models import ChatRoom
from apps.chat.routing import websocket_urlpatterns
from apps.core.testing import client_for, make_employer, make_job, make_worker


class ChatRestTest(TestCase):
    def setUp(self):
        self.boss = make_employer()
        self.worker = make_worker(lang="th")
        self.job = make_job(self.boss.company)
        self.cw, self.cb = client_for(self.worker), client_for(self.boss)

    def open_room(self):
        return self.cw.post("/api/chat/rooms/", {"job_id": self.job.id}, format="json")

    def test_create_room_idempotent(self):
        res = self.open_room()
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["counterpart"]["name"], "충남 건설")
        self.assertEqual(res.json()["my_language"], "th")
        self.assertEqual(res.json()["counterpart_language"], "ko")
        self.assertEqual(self.open_room().status_code, 200)
        self.assertEqual(ChatRoom.objects.count(), 1)
        self.assertEqual(self.cw.post("/api/chat/rooms/", {}, format="json").status_code, 400)
        self.assertEqual(self.cw.post("/api/chat/rooms/", {"user_id": self.worker.id}, format="json").status_code, 400)

    def test_direct_room(self):
        friend = make_worker("friend", lang="vi")
        res = self.cw.post("/api/chat/rooms/", {"user_id": friend.id}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertIsNone(res.json()["job"])

    def test_messages_translated_unread_and_read(self):
        rid = self.open_room().json()["id"]
        res = self.cw.post(f"/api/chat/rooms/{rid}/messages/", {"text": "สวัสดีครับ"}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["source_lang"], "th")
        self.assertEqual(res.json()["translations"], {"ko": "[ko] สวัสดีครับ"})

        rooms = self.cb.get("/api/chat/rooms/").json()["results"]
        self.assertEqual(rooms[0]["unread_count"], 1)
        self.assertEqual(rooms[0]["last_message"]["text"], "สวัสดีครับ")
        self.assertEqual(self.cw.get("/api/chat/rooms/").json()["results"][0]["unread_count"], 0)  # 내가 보낸 건 안읽음 아님

        self.assertEqual(self.cb.post(f"/api/chat/rooms/{rid}/read/").status_code, 204)
        self.assertEqual(self.cb.get("/api/chat/rooms/").json()["results"][0]["unread_count"], 0)

        msgs = self.cb.get(f"/api/chat/rooms/{rid}/messages/").json()
        self.assertEqual(len(msgs["results"]), 1)

    def test_translation_language_setting(self):
        rid = self.open_room().json()["id"]
        res = self.cw.patch(f"/api/chat/rooms/{rid}/translation/", {"language": "vi"}, format="json")
        self.assertEqual(res.json()["my_language"], "vi")
        self.cb.post(f"/api/chat/rooms/{rid}/messages/", {"text": "안녕하세요"}, format="json")
        msg = self.cw.get(f"/api/chat/rooms/{rid}/messages/").json()["results"][0]
        self.assertEqual(msg["translations"], {"vi": "[vi] 안녕하세요"})
        self.assertEqual(self.cw.patch(f"/api/chat/rooms/{rid}/translation/", {"language": "zz"}, format="json").status_code, 400)

    def test_outsider_cannot_access(self):
        rid = self.open_room().json()["id"]
        out = client_for(make_worker("outsider"))
        self.assertEqual(out.get(f"/api/chat/rooms/{rid}/messages/").status_code, 404)
        self.assertEqual(out.post(f"/api/chat/rooms/{rid}/messages/", {"text": "x"}, format="json").status_code, 404)
        self.assertEqual(out.get("/api/chat/rooms/").json()["count"], 0)

    def test_message_pagination_cursor(self):
        rid = self.open_room().json()["id"]
        for i in range(35):
            self.cw.post(f"/api/chat/rooms/{rid}/messages/", {"text": f"m{i}"}, format="json")
        page1 = self.cw.get(f"/api/chat/rooms/{rid}/messages/").json()
        self.assertEqual(len(page1["results"]), 30)
        self.assertEqual(page1["results"][0]["text"], "m34")  # 최신순
        self.assertIsNotNone(page1["next"])


class ChatWebSocketTest(TransactionTestCase):
    serialized_rollback = True  # 마이그레이션 시드(지역·업종)를 flush 후 복원
    def setUp(self):
        from apps.chat.services import get_or_create_room

        self.boss, self.worker = make_employer(), make_worker(lang="th")
        self.room = get_or_create_room(self.worker, self.boss.company.owner, make_job(self.boss.company))
        self.app = JWTAuthMiddleware(URLRouter(websocket_urlpatterns))

    def comm(self, user=None, token=None):
        token = token or (str(AccessToken.for_user(user)) if user else "")
        return WebsocketCommunicator(self.app, f"/ws/chat/{self.room.id}/?token={token}")

    async def test_unauthenticated_rejected(self):
        ok, code = await self.comm().connect()
        self.assertFalse(ok)

    async def test_outsider_rejected(self):
        from channels.db import database_sync_to_async

        out = await database_sync_to_async(make_worker)("out")
        ok, _ = await self.comm(out).connect()
        self.assertFalse(ok)

    async def test_realtime_message_translation_presence_read(self):
        a, b = self.comm(self.worker), self.comm(self.boss)
        self.assertTrue((await a.connect())[0])
        self.assertTrue((await b.connect())[0])

        # 접속 알림(presence) 소비
        seen = []
        for comm in (a, b):
            while not await comm.receive_nothing(timeout=0.2):
                seen.append(await comm.receive_json_from())
        self.assertTrue(any(m["type"] == "presence" and m["online"] for m in seen))

        await a.send_json_to({"type": "message", "text": "สวัสดี"})
        for comm in (a, b):
            ev = await comm.receive_json_from(timeout=3)
            self.assertEqual(ev["type"], "message")
            self.assertEqual(ev["message"]["text"], "สวัสดี")
            self.assertEqual(ev["message"]["translations"], {"ko": "[ko] สวัสดี"})

        await b.send_json_to({"type": "read"})
        ev = await a.receive_json_from(timeout=3)
        self.assertEqual(ev["type"], "read")

        await a.send_json_to({"type": "message", "text": "  "})
        self.assertEqual((await a.receive_json_from(timeout=3))["type"], "error")

        await a.disconnect()
        await b.disconnect()
