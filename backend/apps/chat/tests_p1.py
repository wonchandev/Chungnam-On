import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from apps.chat import presence
from apps.chat.models import ChatRoom
from apps.core.models import Notification
from apps.core.testing import client_for, make_employer, make_job, make_worker
from apps.jobs.models import Application


def png(name="a.png"):
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


class ChatP1Test(TestCase):
    def setUp(self):
        self.boss, self.w = make_employer(), make_worker(lang="th", phone="010-1111-2222")
        self.job = make_job(self.boss.company)
        self.cw, self.cb = client_for(self.w), client_for(self.boss)
        self.rid = self.cw.post("/api/chat/rooms/", {"job_id": self.job.id}, format="json").json()["id"]

    def test_quick_replies_translated(self):
        res = self.cw.get("/api/chat/quick-replies/").json()  # th → echo 번역
        self.assertEqual(len(res), 4)
        self.assertTrue(res[0]["text"].startswith("[th]"))
        self.assertEqual(res[0]["text_ko"], "위치는 어디인가요?")
        self.assertEqual(self.cw.get("/api/chat/quick-replies/", HTTP_ACCEPT_LANGUAGE="ko").json()[0]["text"], "위치는 어디인가요?")

    def test_image_attachment(self):
        res = self.cw.post(f"/api/chat/rooms/{self.rid}/messages/", {"image": png()}, format="multipart")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertTrue(res.json()["image"])
        self.assertEqual(res.json()["text"], "")
        self.assertEqual(res.json()["source_lang"], "th")
        self.assertEqual(res.json()["translations"], {})
        self.assertEqual(self.cw.post(f"/api/chat/rooms/{self.rid}/messages/", {}, format="json").status_code, 400)
        # 이미지+텍스트
        res = self.cw.post(
            f"/api/chat/rooms/{self.rid}/messages/", {"image": png("b.png"), "text": "รูปภาพ"}, format="multipart",
        )
        self.assertEqual(res.json()["source_lang"], "th")
        self.assertEqual(res.json()["translations"], {"ko": "[ko] รูปภาพ"})

    def test_leave_and_revive(self):
        self.assertEqual(self.cw.delete(f"/api/chat/rooms/{self.rid}/").status_code, 204)
        self.assertEqual(self.cw.get("/api/chat/rooms/").json()["count"], 0)
        self.assertEqual(self.cb.get("/api/chat/rooms/").json()["count"], 1)  # 상대 목록에는 남아 있음
        self.cb.post(f"/api/chat/rooms/{self.rid}/messages/", {"text": "안녕하세요"}, format="json")  # 상대가 보내면 복원
        self.assertEqual(self.cw.get("/api/chat/rooms/").json()["count"], 1)
        # 다시 문의하기를 눌러도 같은 방
        self.cw.delete(f"/api/chat/rooms/{self.rid}/")
        res = self.cw.post("/api/chat/rooms/", {"job_id": self.job.id}, format="json")
        self.assertEqual((res.status_code, res.json()["id"]), (200, self.rid))
        self.assertEqual(self.cw.get("/api/chat/rooms/").json()["count"], 1)

    def test_call_policy(self):
        self.assertEqual(self.cw.get(f"/api/chat/rooms/{self.rid}/call/").json()["code"], "call_not_allowed")
        Application.objects.create(job=self.job, applicant=self.w, status="approved")
        self.assertEqual(self.cb.get(f"/api/chat/rooms/{self.rid}/call/").json(), {"phone": self.w.phone})  # 사업주 → 근로자 번호
        self.assertEqual(self.cw.get(f"/api/chat/rooms/{self.rid}/call/").json()["code"], "no_phone")  # 사업주는 번호 미등록
        self.assertEqual(client_for(make_worker("x")).get(f"/api/chat/rooms/{self.rid}/call/").status_code, 404)

    def test_offline_notification_collapsed_per_room(self):
        self.cw.post(f"/api/chat/rooms/{self.rid}/messages/", {"text": "하나"}, format="json")
        self.cw.post(f"/api/chat/rooms/{self.rid}/messages/", {"text": "둘"}, format="json")
        ns = Notification.objects.filter(user=self.boss, type="chat")
        self.assertEqual(ns.count(), 1)
        self.assertEqual(ns[0].body, "둘")
        self.assertEqual(ns[0].data["room_id"], self.rid)

    def test_no_notification_when_online(self):
        presence.mark_connected(self.boss.id)
        try:
            self.cw.post(f"/api/chat/rooms/{self.rid}/messages/", {"text": "하나"}, format="json")
        finally:
            presence.mark_disconnected(self.boss.id)
        self.assertFalse(Notification.objects.filter(user=self.boss, type="chat").exists())

    def test_blocked(self):
        self.cb.post(f"/api/blocks/{self.w.id}/")
        res = self.cw.post(f"/api/chat/rooms/{self.rid}/messages/", {"text": "x"}, format="json")
        self.assertEqual((res.status_code, res.json()["code"]), (403, "blocked"))
        # 새 방도 못 만듦
        other_job = make_job(self.boss.company)
        self.assertEqual(self.cw.post("/api/chat/rooms/", {"job_id": other_job.id}, format="json").status_code, 403)
        self.cb.delete(f"/api/blocks/{self.w.id}/")
        self.assertEqual(self.cw.post(f"/api/chat/rooms/{self.rid}/messages/", {"text": "x"}, format="json").status_code, 201)
