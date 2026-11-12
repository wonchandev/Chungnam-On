from django.test import TestCase
from rest_framework.test import APIClient


class HealthCheckTest(TestCase):
    def test_health(self):
        res = self.client.get("/api/health/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

    def test_docs(self):
        self.assertEqual(self.client.get("/docs").status_code, 200)
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)


class AuthFlowTest(TestCase):
    def test_register_login_me(self):
        c = APIClient()
        res = c.post(
            "/api/auth/register/",
            {"username": "worker1", "password": "Str0ng-pass!23", "role": "worker"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertNotIn("password", res.json())

        res = c.post(
            "/api/auth/login/",
            {"username": "worker1", "password": "Str0ng-pass!23"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        tokens = res.json()

        self.assertEqual(c.get("/api/auth/me/").status_code, 401)
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        res = c.get("/api/auth/me/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["username"], "worker1")

        res = APIClient().post("/api/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(res.status_code, 200)
