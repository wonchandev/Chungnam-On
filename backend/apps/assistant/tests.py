from django.test import TestCase

from apps.assistant.models import AdminGuide, AdminGuideTranslation
from apps.core.testing import client_for, make_employer, make_job, make_worker


class AdminInfoTest(TestCase):
    def setUp(self):
        AdminGuide.objects.all().delete()  # 마이그레이션 시드 가이드 제외
        self.visa = AdminGuide.objects.create(category="visa", title="비자 연장 방법", summary="체류기간 연장", body="출입국사무소 방문")
        AdminGuideTranslation.objects.create(guide=self.visa, lang="en", title="How to extend your visa", body="Visit the office")
        self.ins = AdminGuide.objects.create(category="insurance", title="건강보험 가입", body="직장가입자 안내")
        AdminGuide.objects.create(category="etc", title="비공개", body="x", is_published=False)
        self.c = client_for()

    def test_dashboard(self):
        make_worker(); make_worker("w2"); b = make_employer(); make_job(b.company)
        d = self.c.get("/api/admin-info/dashboard/").json()
        self.assertEqual((d["total_workers"], d["total_employers"], d["open_jobs"], d["guides_total"]), (2, 1, 1, 2))

    def test_list_filter_search_language(self):
        self.assertEqual(self.c.get("/api/admin-info/guides/").json()["count"], 2)  # 비공개 제외
        self.assertEqual(self.c.get("/api/admin-info/guides/", {"category": "visa"}).json()["count"], 1)
        self.assertEqual(self.c.get("/api/admin-info/guides/", {"search": "건강"}).json()["count"], 1)
        res = self.c.get("/api/admin-info/guides/", HTTP_ACCEPT_LANGUAGE="en").json()["results"]
        self.assertIn("How to extend your visa", [g["title"] for g in res])

    def test_detail_translation_fallback_and_views(self):
        en = self.c.get(f"/api/admin-info/guides/{self.visa.id}/", HTTP_ACCEPT_LANGUAGE="en").json()
        self.assertEqual((en["title"], en["language"]), ("How to extend your visa", "en"))
        th = self.c.get(f"/api/admin-info/guides/{self.visa.id}/", HTTP_ACCEPT_LANGUAGE="th").json()
        self.assertEqual((th["title"], th["language"]), ("비자 연장 방법", "ko"))  # 번역 없으면 한국어
        self.visa.refresh_from_db()
        self.assertEqual(self.visa.view_count, 2)

    def test_frequent_and_popular(self):
        for _ in range(3):
            self.c.get(f"/api/admin-info/guides/{self.ins.id}/")
        self.c.get(f"/api/admin-info/guides/{self.visa.id}/")
        self.assertEqual(self.c.get("/api/admin-info/frequent/").json()[0]["id"], self.ins.id)
        self.assertEqual(self.c.get("/api/admin-info/popular/").json()[0]["id"], self.ins.id)
        self.assertEqual(self.c.get("/api/admin-info/guides/99999/").status_code, 404)
