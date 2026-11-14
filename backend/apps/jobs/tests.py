from datetime import date, time, timedelta

from django.core.management import call_command
from django.utils import timezone
from django.test import TestCase

from apps.core.testing import client_for, make_employer, make_job, make_worker
from apps.jobs.models import Application, JobCategory, JobPost
from apps.core.models import Region


def payload(**kw):
    d = dict(
        title="공장 신축 현장 보조 인력 모집", description="자재 운반", work_type="현장 보조", category="construction",
        pay_type="daily", pay_amount=300000, region="44130", address="천안시 서북구", lat=36.82, lng=127.15,
        start_date=str(date.today() + timedelta(days=1)), start_time="08:00", end_time="17:00", headcount=5,
        beginner_ok=True,
    )
    d.update(kw)
    return d


class JobCrudTest(TestCase):
    def setUp(self):
        self.boss, self.worker = make_employer(), make_worker()

    def test_create_requires_employer(self):
        self.assertEqual(client_for().post("/api/jobs/", payload(), format="json").status_code, 401)
        self.assertEqual(client_for(self.worker).post("/api/jobs/", payload(), format="json").status_code, 403)

    def test_create_update_close_delete(self):
        c = client_for(self.boss)
        res = c.post("/api/jobs/", payload(), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        jid = res.json()["id"]
        self.assertEqual(res.json()["company_name"], "충남 건설")
        self.assertTrue(res.json()["tags"]["beginner_ok"])
        self.assertEqual(JobPost.objects.get(pk=jid).translations.count(), 9)  # ko 제외 지원 언어

        res = c.patch(f"/api/jobs/{jid}/", {"pay_amount": 350000}, format="json")
        self.assertEqual(res.json()["pay_amount"], 350000)
        # 다른 사업주는 수정 불가
        other = make_employer("boss2", number="2234567890")
        self.assertEqual(client_for(other).patch(f"/api/jobs/{jid}/", {"title": "x"}, format="json").status_code, 404)

        self.assertEqual(c.post(f"/api/jobs/{jid}/close/").status_code, 204)
        self.assertEqual(client_for().get("/api/jobs/").json()["count"], 0)  # 마감된 공고는 목록 제외
        self.assertEqual(c.delete(f"/api/jobs/{jid}/").status_code, 204)
        self.assertEqual(client_for().get(f"/api/jobs/{jid}/").status_code, 404)

    def test_validation(self):
        c = client_for(self.boss)
        bad = c.post("/api/jobs/", payload(end_date=str(date.today()), start_date=str(date.today() + timedelta(days=3))), format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(c.post("/api/jobs/", payload(lat=10, lng=10), format="json").status_code, 400)
        self.assertEqual(c.post("/api/jobs/", payload(weekdays="9"), format="json").status_code, 400)
        self.assertEqual(c.post("/api/jobs/", payload(region="99999"), format="json").status_code, 400)

    def test_translated_title_by_accept_language(self):
        c = client_for(self.boss)
        jid = c.post("/api/jobs/", payload(), format="json").json()["id"]
        res = client_for().get(f"/api/jobs/{jid}/", HTTP_ACCEPT_LANGUAGE="th")
        self.assertTrue(res.json()["title"].startswith("[th]"))
        self.assertFalse(client_for().get(f"/api/jobs/{jid}/").json()["title"].startswith("["))
        # 로그인 사용자의 preferred_language 로도 결정
        w = make_worker("w_vi", lang="vi")
        self.assertTrue(client_for(w).get(f"/api/jobs/{jid}/").json()["title"].startswith("[vi]"))


class JobListFilterTest(TestCase):
    def setUp(self):
        self.boss = make_employer()
        self.cheonan = make_job(self.boss.company, title="천안 건설", pay_amount=300000, beginner_ok=True)
        self.dangjin = make_job(
            self.boss.company, title="당진 물류", pay_type="hourly", pay_amount=12000,
            category=JobCategory.objects.get(code="logistics"), region=Region.objects.get(code="44270"),
            lat=36.89, lng=126.64, is_urgent=True, duration_days=1, night_shift=True,
            weekdays="0,1", deadline=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=40),
        )
        self.c = client_for()

    def ids(self, **params):
        return {r["id"] for r in self.c.get("/api/jobs/", params).json()["results"]}

    def test_filters(self):
        self.assertEqual(self.ids(), {self.cheonan.id, self.dangjin.id})
        self.assertEqual(self.ids(region="44130"), {self.cheonan.id})
        self.assertEqual(self.ids(region="44130,44270"), {self.cheonan.id, self.dangjin.id})
        self.assertEqual(self.ids(category="logistics"), {self.dangjin.id})
        self.assertEqual(self.ids(pay_type="hourly"), {self.dangjin.id})
        self.assertEqual(self.ids(min_pay=100000), {self.cheonan.id})
        self.assertEqual(self.ids(urgent="true"), {self.dangjin.id})
        self.assertEqual(self.ids(beginner_ok="true"), {self.cheonan.id})
        self.assertEqual(self.ids(night_shift="true"), {self.dangjin.id})
        self.assertEqual(self.ids(q="당진"), {self.dangjin.id})
        self.assertEqual(self.ids(period="long"), {self.dangjin.id})
        self.assertEqual(self.ids(period="one_day"), {self.cheonan.id})
        self.assertEqual(self.ids(weekday=3), {self.cheonan.id})  # dangjin 은 월·화만
        self.assertEqual(self.ids(weekday=0), {self.cheonan.id, self.dangjin.id})

    def test_ordering_and_count(self):
        res = self.c.get("/api/jobs/", {"ordering": "deadline"}).json()
        self.assertEqual(res["count"], 2)
        self.assertEqual(res["results"][0]["id"], self.dangjin.id)  # 마감일 있는 공고가 먼저
        res = self.c.get("/api/jobs/", {"ordering": "-pay_amount"}).json()
        self.assertEqual(res["results"][0]["id"], self.cheonan.id)

    def test_urgent_and_popular(self):
        res = self.c.get("/api/jobs/urgent/").json()
        self.assertEqual([j["id"] for j in res], [self.dangjin.id])
        pop = self.c.get("/api/jobs/popular-categories/").json()
        self.assertEqual({p["code"] for p in pop}, {"construction", "logistics"})
        self.assertEqual(pop[0]["open_count"], 1)

    def test_expired_not_listed_and_command(self):
        JobPost.objects.filter(pk=self.cheonan.pk).update(deadline=date.today() - timedelta(days=1))
        self.assertEqual(self.ids(), {self.dangjin.id})
        call_command("close_expired_jobs")
        self.cheonan.refresh_from_db()
        self.assertEqual(self.cheonan.status, "closed")

    def test_bookmark_flow(self):
        w = make_worker()
        c = client_for(w)
        self.assertEqual(c.post(f"/api/jobs/{self.cheonan.id}/bookmark/").status_code, 204)
        self.assertEqual(c.post(f"/api/jobs/{self.cheonan.id}/bookmark/").status_code, 204)  # 멱등
        res = c.get("/api/jobs/").json()["results"]
        self.assertEqual({r["id"]: r["is_bookmarked"] for r in res}, {self.cheonan.id: True, self.dangjin.id: False})
        self.assertEqual([j["id"] for j in c.get("/api/jobs/bookmarks/").json()["results"]], [self.cheonan.id])
        self.assertEqual(c.delete(f"/api/jobs/{self.cheonan.id}/bookmark/").status_code, 204)
        self.assertEqual(c.get("/api/jobs/bookmarks/").json()["count"], 0)


class ApplicationFlowTest(TestCase):
    def setUp(self):
        self.boss = make_employer()
        self.job = make_job(self.boss.company, headcount=1)
        self.w1, self.w2 = make_worker("w1", phone="010-1111-2222"), make_worker("w2")

    def test_apply_approve_capacity(self):
        c1, c2, cb = client_for(self.w1), client_for(self.w2), client_for(self.boss)
        res = c1.post(f"/api/jobs/{self.job.id}/apply/", {"message": "잘 하겠습니다"}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        app1 = res.json()["id"]
        self.assertEqual(c1.post(f"/api/jobs/{self.job.id}/apply/").status_code, 409)  # 중복
        self.assertEqual(cb.post(f"/api/jobs/{self.job.id}/apply/").status_code, 403)  # 사업주는 지원 불가
        app2 = c2.post(f"/api/jobs/{self.job.id}/apply/").json()["id"]

        applicants = cb.get(f"/api/jobs/{self.job.id}/applications/").json()["results"]
        self.assertEqual(len(applicants), 2)
        self.assertTrue(all(a["phone"] is None for a in applicants))  # 승인 전에는 연락처 숨김
        self.assertEqual(client_for(self.w1).get(f"/api/jobs/{self.job.id}/applications/").status_code, 403)

        self.assertEqual(cb.patch(f"/api/applications/{app1}/", {"status": "approved"}, format="json").json()["phone"], "010-1111-2222")
        # 정원 1명 → 두 번째 승인 불가
        res = cb.patch(f"/api/applications/{app2}/", {"status": "approved"}, format="json")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["code"], "headcount_full")
        self.assertEqual(cb.patch(f"/api/applications/{app2}/", {"status": "rejected"}, format="json").status_code, 200)
        # 다른 사업주는 승인 불가
        other = make_employer("boss2", number="2234567890")
        self.assertEqual(client_for(other).patch(f"/api/applications/{app2}/", {"status": "approved"}, format="json").status_code, 404)

        mine = c1.get("/api/applications/mine/").json()["results"]
        self.assertEqual(mine[0]["status"], "approved")
        self.assertEqual(c1.get("/api/applications/mine/", {"status": "rejected"}).json()["count"], 0)
        detail = c1.get(f"/api/jobs/{self.job.id}/").json()
        self.assertEqual(detail["my_application_status"], "approved")
        self.assertEqual(detail["approved_count"], 1)

    def test_apply_blocked_when_full_or_closed(self):
        Application.objects.create(job=self.job, applicant=self.w1, status="approved")
        self.assertEqual(client_for(self.w2).post(f"/api/jobs/{self.job.id}/apply/").status_code, 409)
        self.job.status = "closed"; self.job.save()
        res = client_for(self.w2).post(f"/api/jobs/{self.job.id}/apply/")
        self.assertEqual(res.json()["code"], "job_closed")

    def test_cancel(self):
        c = client_for(self.w1)
        app = c.post(f"/api/jobs/{self.job.id}/apply/").json()["id"]
        self.assertEqual(client_for(self.w2).delete(f"/api/applications/{app}/").status_code, 404)
        self.assertEqual(c.delete(f"/api/applications/{app}/").status_code, 204)
        self.assertFalse(Application.objects.exists())


class ReviewTest(TestCase):
    def setUp(self):
        self.boss, self.w = make_employer(), make_worker()
        self.job = make_job(self.boss.company, start_date=date.today() - timedelta(days=1))
        Application.objects.create(job=self.job, applicant=self.w, status="approved", completed_at=timezone.now())

    def test_mutual_reviews_update_temperature(self):
        res = client_for(self.w).post(f"/api/jobs/{self.job.id}/reviews/", {"score": 5, "tags": ["punctual", "kind"]}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.boss.refresh_from_db()
        self.assertEqual(self.boss.temperature, 37.5)
        self.assertEqual(self.boss.review_count, 1)
        self.assertEqual(client_for(self.w).post(f"/api/jobs/{self.job.id}/reviews/", {"score": 5}, format="json").status_code, 409)

        cb = client_for(self.boss)
        self.assertEqual(cb.post(f"/api/jobs/{self.job.id}/reviews/", {"score": 1}, format="json").status_code, 400)  # reviewee 필요
        self.assertEqual(cb.post(f"/api/jobs/{self.job.id}/reviews/", {"score": 1, "reviewee": self.w.id}, format="json").status_code, 201)
        self.w.refresh_from_db()
        self.assertEqual(self.w.temperature, 35.5)

        rep = client_for().get(f"/api/users/{self.boss.id}/reputation/").json()
        self.assertEqual(rep["temperature"], 37.5)
        self.assertEqual(rep["tag_counts"], {"punctual": 1, "kind": 1})
        # 공고 카드에 온도 노출
        self.assertEqual(client_for().get("/api/jobs/").json()["results"][0]["company_temperature"], 37.5)

    def test_review_rules(self):
        stranger = make_worker("stranger")
        self.assertEqual(client_for(stranger).post(f"/api/jobs/{self.job.id}/reviews/", {"score": 5}, format="json").status_code, 403)
        notdone = make_job(self.boss.company)  # 근무 완료 처리 전에는 평가 불가
        Application.objects.create(job=notdone, applicant=self.w, status="approved")
        self.assertEqual(client_for(self.w).post(f"/api/jobs/{notdone.id}/reviews/", {"score": 5}, format="json").status_code, 403)
        self.assertEqual(client_for(self.w).post(f"/api/jobs/{self.job.id}/reviews/", {"score": 9}, format="json").status_code, 400)


class MapTest(TestCase):
    def setUp(self):
        boss = make_employer()
        co = boss.company
        # 천안 3건(가까이), 당진 1건, 좌표 없는 1건
        for i in range(3):
            make_job(co, title=f"천안{i}", lat=36.815 + i * 0.001, lng=127.113)
        self.far = make_job(co, title="당진", lat=36.893, lng=126.647, category=JobCategory.objects.get(code="logistics"), is_urgent=True)
        make_job(co, title="좌표없음", lat=None, lng=None)
        self.c = client_for()

    def test_markers_bbox_and_filter(self):
        bbox = dict(sw_lat=36.7, sw_lng=127.0, ne_lat=36.9, ne_lng=127.3)
        res = self.c.get("/api/jobs/map/", bbox).json()
        self.assertEqual(res["total"], 3)
        res = self.c.get("/api/jobs/map/", {"category": "logistics"}).json()
        self.assertEqual([m["title"] for m in res["results"]], ["당진"])
        self.assertEqual(self.c.get("/api/jobs/map/", {"sw_lat": 1}).status_code, 400)
        self.assertEqual(self.c.get("/api/jobs/map/", {"urgent": "true"}).json()["total"], 1)

    def test_clusters(self):
        res = self.c.get("/api/jobs/map/clusters/", {"zoom": 10}).json()
        self.assertEqual(res["total"], 4)
        self.assertEqual(res["clusters"][0]["count"], 3)
        self.assertEqual(len(res["clusters"]), 2)
        res = self.c.get("/api/jobs/map/clusters/", {"zoom": 18}).json()
        self.assertGreaterEqual(len(res["clusters"]), 3)  # 확대하면 분리

    def test_nearby(self):
        res = self.c.get("/api/jobs/nearby/", {"lat": 36.8151, "lng": 127.1139, "radius": 5}).json()
        self.assertEqual(res["count"], 3)
        dists = [r["distance_km"] for r in res["results"]]
        self.assertEqual(dists, sorted(dists))
        self.assertLess(dists[0], 0.5)
        wide = self.c.get("/api/jobs/nearby/", {"lat": 36.8151, "lng": 127.1139, "radius": 50}).json()
        self.assertEqual(wide["count"], 4)
        self.assertEqual(self.c.get("/api/jobs/nearby/").status_code, 400)
