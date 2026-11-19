from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.testing import PW, client_for, make_employer, make_worker


class HealthDocsTest(TestCase):
    def test_health(self):
        res = self.client.get("/api/health/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

    def test_docs(self):
        self.assertEqual(self.client.get("/docs").status_code, 200)
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)


class AuthFlowTest(TestCase):
    def test_register_login_me_refresh_logout(self):
        c = APIClient()
        res = c.post("/api/auth/register/", {
            "username": "worker1", "password": PW, "role": "worker", "name": "소미차이", "nationality": "TH",
            "preferred_language": "th", "visa_type": "E-9", "region": "44130",
        }, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertNotIn("password", res.json())

        tokens = c.post("/api/auth/login/", {"username": "worker1", "password": PW}, format="json").json()
        self.assertEqual(c.get("/api/auth/me/").status_code, 401)
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        me = c.get("/api/auth/me/").json()
        self.assertEqual(me["nationality"], "TH")
        self.assertEqual(me["temperature"], 36.5)
        self.assertEqual(c.patch("/api/auth/me/", {"preferred_language": "vi"}, format="json").status_code, 200)

        new = APIClient().post("/api/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(new.status_code, 200)
        rotated = new.json()["refresh"]

        self.assertEqual(c.post("/api/auth/logout/", {"refresh": rotated}, format="json").status_code, 204)
        # 로그아웃된 refresh 는 재사용 불가
        self.assertEqual(APIClient().post("/api/auth/refresh/", {"refresh": rotated}, format="json").status_code, 401)

    def test_employer_requires_company(self):
        c = APIClient()
        res = c.post("/api/auth/register/", {"username": "boss", "password": PW, "role": "employer"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "validation_error")
        res = c.post("/api/auth/register/", {
            "username": "boss", "password": PW, "role": "employer",
            "company": {"name": "충남 건설", "business_number": "123-45-67890", "representative": "홍", "address": "천안"},
        }, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["company"]["business_number"], "1234567890")

    def test_password_change(self):
        w = make_worker()
        c = client_for(w)
        self.assertEqual(c.patch("/api/auth/password/", {"old_password": "x", "new_password": "Another-Pass!9"}, format="json").status_code, 400)
        self.assertEqual(c.patch("/api/auth/password/", {"old_password": PW, "new_password": "Another-Pass!9"}, format="json").status_code, 204)
        w.refresh_from_db()
        self.assertTrue(w.check_password("Another-Pass!9"))

    def test_me_summary(self):
        w, b = make_worker(), make_employer()
        self.assertIn("applications", client_for(w).get("/api/me/summary/").json())
        self.assertIn("jobs", client_for(b).get("/api/me/summary/").json())

    def test_unsupported_language_rejected(self):
        res = APIClient().post("/api/auth/register/", {"username": "a", "password": PW, "preferred_language": "xx"}, format="json")
        self.assertEqual(res.status_code, 400)


class RegionTest(TestCase):
    def test_regions_seeded_and_search(self):
        res = APIClient().get("/api/regions/", {"level": "sigungu"})
        self.assertEqual(len(res.json()), 15)
        res = APIClient().get("/api/regions/search/", {"q": "천안"})
        self.assertEqual(res.json()[0]["code"], "44130")
        self.assertEqual(APIClient().get("/api/regions/search/", {"q": ""}).json(), [])
