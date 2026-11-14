from datetime import date, timedelta
from io import BytesIO

from django.test import TestCase
from PIL import Image

from apps.accounts.models import WorkerProfile
from apps.core.models import Notification, Region
from apps.core.testing import client_for, make_employer, make_job, make_worker
from apps.jobs.models import Application, JobCategory, JobPost


class JobDuplicateTicker(TestCase):
    def setUp(self):
        self.boss = make_employer()
        self.job = make_job(self.boss.company, start_date=date.today() + timedelta(days=5), end_date=date.today() + timedelta(days=9),
                            deadline=date.today() + timedelta(days=3), title="원본")

    def test_duplicate_keeps_length_and_clears_deadline(self):
        c = client_for(self.boss)
        res = c.post(f"/api/jobs/{self.job.id}/duplicate/", {"start_date": str(date.today() + timedelta(days=20))}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        new = JobPost.objects.get(pk=res.json()["id"])
        self.assertEqual((new.end_date - new.start_date).days, 4)
        self.assertIsNone(new.deadline)
        self.assertEqual(new.title, "원본")
        self.assertEqual(new.status, "open")
        self.assertEqual(client_for(make_employer("b2", number="2234567890")).post(f"/api/jobs/{self.job.id}/duplicate/").status_code, 404)

    def test_ticker(self):
        res = client_for().get("/api/jobs/ticker/").json()
        self.assertEqual(res[0]["label"], "[일급 300,000] 천안시 건설현장")


class RecentAndSearch(TestCase):
    def setUp(self):
        self.boss = make_employer()
        self.a, self.b = make_job(self.boss.company, title="천안 건설 A"), make_job(self.boss.company, title="천안 물류 B")
        self.w = make_worker()

    def test_recent_views(self):
        c = client_for(self.w)
        c.get(f"/api/jobs/{self.a.id}/")
        c.get(f"/api/jobs/{self.b.id}/")
        c.get(f"/api/jobs/{self.a.id}/")  # 다시 보면 맨 앞으로
        self.assertEqual([j["id"] for j in c.get("/api/jobs/recent/").json()], [self.a.id, self.b.id])
        self.assertEqual(client_for().get("/api/jobs/recent/").status_code, 401)

    def test_popular_searches(self):
        for q in ["천안", "천안", "천안", "물류", "a"]:
            client_for().get("/api/jobs/", {"q": q})
        res = client_for().get("/api/jobs/popular-searches/").json()
        self.assertEqual(res[0], {"keyword": "천안", "count": 3})
        self.assertNotIn("a", [r["keyword"] for r in res])  # 1글자는 제외


class Recommendation(TestCase):
    def test_profile_based_ranking(self):
        boss = make_employer()
        near = make_job(boss.company, title="가까운 건설", region=Region.objects.get(code="44130"))
        far = make_job(boss.company, title="먼 물류", region=Region.objects.get(code="44270"),
                       category=JobCategory.objects.get(code="logistics"))
        w = make_worker()
        c = client_for(w)
        res = c.put("/api/me/worker-profile/", {"desired_regions": ["44270"], "available_categories": ["logistics"],
                                                "experience_years": 2}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        rec = c.get("/api/jobs/recommended/").json()
        self.assertEqual(rec[0]["id"], far.id)
        self.assertIn("가능한 업종", rec[0]["match_reasons"])
        self.assertGreater(rec[0]["match_score"], rec[1]["match_score"])
        # 비로그인은 최신순
        self.assertEqual(len(client_for().get("/api/jobs/recommended/").json()), 2)
        self.assertEqual(client_for(boss).get("/api/me/worker-profile/").status_code, 403)

    def test_night_shift_penalty(self):
        boss = make_employer()
        make_job(boss.company, title="야간", night_shift=True)
        make_job(boss.company, title="주간")
        w = make_worker()
        WorkerProfile.objects.create(user=w, can_night_shift=False)
        rec = client_for(w).get("/api/jobs/recommended/").json()
        self.assertEqual(rec[0]["title"], "주간")


class ApplyNotifyChat(TestCase):
    def setUp(self):
        self.boss, self.w = make_employer(), make_worker(phone="010-1")
        self.job = make_job(self.boss.company, start_date=date.today(), headcount=2)

    def test_apply_creates_room_and_notifications(self):
        res = client_for(self.w).post(f"/api/jobs/{self.job.id}/apply/", format="json")
        self.assertEqual(res.status_code, 201)
        self.assertIsNotNone(res.json()["chat_room_id"])
        n = Notification.objects.get(user=self.boss)
        self.assertEqual((n.type, n.data["job_id"]), ("application", self.job.id))
        app_id = res.json()["id"]
        client_for(self.boss).patch(f"/api/applications/{app_id}/", {"status": "approved"}, format="json")
        self.assertEqual(Notification.objects.filter(user=self.w, type="decision").count(), 1)

    def test_notifications_off_and_blocked(self):
        self.boss.notifications_enabled = False
        self.boss.save()
        client_for(self.w).post(f"/api/jobs/{self.job.id}/apply/")
        self.assertFalse(Notification.objects.filter(user=self.boss).exists())

    def test_blocked_applicant_gets_no_room(self):
        other = make_worker("w2")
        client_for(self.boss).post(f"/api/blocks/{other.id}/")
        res = client_for(other).post(f"/api/jobs/{self.job.id}/apply/")
        self.assertEqual(res.status_code, 201)
        self.assertIsNone(res.json()["chat_room_id"])


class AttendanceFlow(TestCase):
    def setUp(self):
        self.boss, self.w = make_employer(), make_worker()
        self.job = make_job(self.boss.company, start_date=date.today())
        self.app = Application.objects.create(job=self.job, applicant=self.w, status="approved")
        self.cb = client_for(self.boss)

    def test_check_in_complete_then_review(self):
        # 완료 전 후기 불가, 출근 확인 없이 완료 불가
        self.assertEqual(client_for(self.w).post(f"/api/jobs/{self.job.id}/reviews/", {"score": 5}, format="json").status_code, 403)
        self.assertEqual(self.cb.post(f"/api/applications/{self.app.id}/complete/").status_code, 409)
        r = self.cb.post(f"/api/applications/{self.app.id}/check-in/")
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(r.json()["checked_in_at"])
        self.assertEqual(self.cb.post(f"/api/applications/{self.app.id}/check-in/").status_code, 200)  # 멱등
        self.assertIsNotNone(self.cb.post(f"/api/applications/{self.app.id}/complete/").json()["completed_at"])
        self.assertTrue(Notification.objects.filter(user=self.w, type="completed").exists())
        self.assertEqual(client_for(self.w).post(f"/api/jobs/{self.job.id}/reviews/", {"score": 5}, format="json").status_code, 201)
        # 내 구직활동에도 표시
        self.assertIsNotNone(client_for(self.w).get("/api/applications/mine/").json()["results"][0]["completed_at"])

    def test_check_in_rules(self):
        future = make_job(self.boss.company, start_date=date.today() + timedelta(days=3))
        a = Application.objects.create(job=future, applicant=self.w, status="approved")
        self.assertEqual(self.cb.post(f"/api/applications/{a.id}/check-in/").status_code, 409)
        pending = Application.objects.create(job=self.job, applicant=make_worker("w2"), status="pending")
        self.assertEqual(self.cb.post(f"/api/applications/{pending.id}/check-in/").status_code, 409)
        self.assertEqual(client_for(self.w).post(f"/api/applications/{self.app.id}/check-in/").status_code, 403)


class AgencyTest(TestCase):
    def test_agency_list_detail(self):
        a = make_employer("agency", name="천안 인력사무소", number="3234567890")
        a.company.is_agency = True; a.company.save()
        a.temperature = 40; a.save()
        make_employer("plain", number="4234567890")
        make_job(a.company)
        c = client_for()
        res = c.get("/api/agencies/").json()
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["results"][0]["open_job_count"], 1)
        self.assertEqual(c.get("/api/agencies/", {"q": "없는"}).json()["count"], 0)
        d = c.get(f"/api/agencies/{a.company.id}/").json()
        self.assertEqual(d["name"], "천안 인력사무소")
        self.assertEqual(len(d["jobs"]), 1)
        self.assertEqual(c.get(f"/api/agencies/{make_employer('p2', number='5234567890').company.id}/").status_code, 404)


class BboxListFilter(TestCase):
    def test_bbox(self):
        boss = make_employer()
        make_job(boss.company, title="in", lat=36.82, lng=127.15)
        make_job(boss.company, title="out", lat=36.0, lng=126.0)
        res = client_for().get("/api/jobs/", {"bbox": "36.7,127.0,36.9,127.3"}).json()
        self.assertEqual([r["title"] for r in res["results"]], ["in"])
        self.assertEqual(client_for().get("/api/jobs/", {"bbox": "x"}).json()["count"], 0)


class HiddenJob(TestCase):
    def test_hidden_excluded(self):
        boss = make_employer()
        j = make_job(boss.company)
        JobPost.objects.filter(pk=j.pk).update(is_hidden=True)
        self.assertEqual(client_for().get("/api/jobs/").json()["count"], 0)
        self.assertEqual(client_for().get(f"/api/jobs/{j.id}/").status_code, 404)
