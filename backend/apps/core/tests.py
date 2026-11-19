from django.test import TestCase

from apps.community.models import Post
from apps.core.models import Block, Notification, Report
from apps.core.testing import client_for, make_employer, make_job, make_worker


class NotificationApiTest(TestCase):
    def setUp(self):
        self.w = make_worker()
        for i in range(3):
            Notification.objects.create(user=self.w, type="x", title=f"n{i}")
        Notification.objects.create(user=make_worker("other"), type="x", title="남의 알림")
        self.c = client_for(self.w)

    def test_list_unread_and_read(self):
        self.assertEqual(self.c.get("/api/notifications/").json()["count"], 3)
        self.assertEqual(self.c.get("/api/notifications/unread-count/").json()["unread_count"], 3)
        first = self.c.get("/api/notifications/").json()["results"][0]["id"]
        self.assertEqual(self.c.post(f"/api/notifications/{first}/read/").status_code, 204)
        self.assertEqual(self.c.get("/api/notifications/unread-count/").json()["unread_count"], 2)
        self.assertEqual(self.c.get("/api/notifications/", {"unread": "true"}).json()["count"], 2)
        self.assertEqual(self.c.post("/api/notifications/read-all/").status_code, 204)
        self.assertEqual(self.c.get("/api/notifications/unread-count/").json()["unread_count"], 0)

    def test_cannot_read_others(self):
        other = Notification.objects.get(title="남의 알림")
        self.assertEqual(self.c.post(f"/api/notifications/{other.id}/read/").status_code, 404)
        self.assertEqual(client_for().get("/api/notifications/").status_code, 401)


class ReportBlockTest(TestCase):
    def test_report_list_is_private_and_status_cannot_be_written(self):
        a, b = make_worker("report-a"), make_worker("report-b")
        c = client_for(a)
        mine = Report.objects.create(reporter=a, target_type="user", target_id=b.id, reason="abuse")
        Report.objects.create(reporter=b, target_type="user", target_id=a.id)
        data = c.get("/api/reports/").json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], mine.id)
        self.assertEqual(data["results"][0]["target_type_label"], "유저")
        self.assertEqual(data["results"][0]["status_label"], "접수")
        self.assertEqual(client_for().get("/api/reports/").status_code, 401)
        response = c.post("/api/reports/", {"target_type": "room", "target_id": 1, "status": "resolved", "reporter": b.id}, format="json")
        self.assertEqual(response.status_code, 201)
        report = Report.objects.get(pk=response.json()["id"])
        self.assertEqual(report.reporter_id, a.id)
        self.assertEqual(report.status, "open")

    def test_report_dedup_and_admin_hide(self):
        boss, w = make_employer(), make_worker()
        job = make_job(boss.company)
        c = client_for(w)
        res = c.post("/api/reports/", {"target_type": "job", "target_id": job.id, "reason": "fraud", "detail": "임금 체불 의심"}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["status"], "open")
        self.assertEqual(c.post("/api/reports/", {"target_type": "job", "target_id": job.id}, format="json").json()["code"], "already_reported")
        self.assertEqual(c.post("/api/reports/", {"target_type": "bogus", "target_id": 1}, format="json").status_code, 400)
        # 관리자 액션: 블라인드 처리
        from django.contrib import admin
        from apps.core.admin import ReportAdmin

        ReportAdmin(Report, admin.site).hide_targets(None, Report.objects.all())
        self.assertEqual(client_for().get("/api/jobs/").json()["count"], 0)
        self.assertEqual(Report.objects.get().status, "resolved")

    def test_block_and_list(self):
        a, b = make_worker("a"), make_worker("b")
        c = client_for(a)
        self.assertEqual(c.post(f"/api/blocks/{a.id}/").status_code, 400)
        self.assertEqual(c.post(f"/api/blocks/{b.id}/").status_code, 204)
        self.assertEqual(c.post(f"/api/blocks/{b.id}/").status_code, 204)  # 멱등
        self.assertEqual(c.get("/api/blocks/").json()["results"][0]["blocked"], b.id)
        self.assertEqual(c.delete(f"/api/blocks/{b.id}/").status_code, 204)
        self.assertEqual(Block.objects.count(), 0)
        self.assertEqual(c.post("/api/blocks/9999/").status_code, 404)
