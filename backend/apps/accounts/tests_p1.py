import io
import json
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.testing import PW, client_for, make_employer, make_worker


@override_settings(DEBUG=True)
class VerificationTest(TestCase):
    def setUp(self):
        self.w = make_worker()
        self.c = client_for(self.w)

    def test_email_verify_flow(self):
        res = self.c.post("/api/auth/verify/request/", {"channel": "email", "target": "a@b.com"}, format="json")
        self.assertEqual(res.status_code, 200)
        code = res.json()["dev_code"]
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(code, mail.outbox[0].body)
        bad = self.c.post("/api/auth/verify/confirm/", {"channel": "email", "target": "a@b.com", "code": "000000" if code != "000000" else "111111"}, format="json")
        self.assertEqual(bad.json()["code"], "code_mismatch")
        ok = self.c.post("/api/auth/verify/confirm/", {"channel": "email", "target": "a@b.com", "code": code}, format="json")
        self.assertEqual(ok.status_code, 200)
        self.w.refresh_from_db()
        self.assertTrue(self.w.email_verified)
        self.assertEqual(self.w.email, "a@b.com")
        # 사용한 코드는 재사용 불가
        again = self.c.post("/api/auth/verify/confirm/", {"channel": "email", "target": "a@b.com", "code": code}, format="json")
        self.assertEqual(again.json()["code"], "code_expired")

    def test_phone_verify_and_attempt_limit(self):
        code = self.c.post("/api/auth/verify/request/", {"channel": "phone", "target": "010-1234-5678"}, format="json").json()["dev_code"]
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.c.post("/api/auth/verify/confirm/", {"channel": "phone", "target": "010-1234-5678", "code": wrong}, format="json")
        res = self.c.post("/api/auth/verify/confirm/", {"channel": "phone", "target": "010-1234-5678", "code": code}, format="json")
        self.assertEqual(res.status_code, 429)

    @override_settings(DEBUG=False)
    def test_dev_code_hidden_in_prod(self):
        res = self.c.post("/api/auth/verify/request/", {"channel": "email", "target": "a@b.com"}, format="json")
        self.assertNotIn("dev_code", res.json())


@override_settings(DEBUG=True)
class PasswordResetTest(TestCase):
    def test_reset_flow(self):
        w = make_worker(email="w@x.com")
        c = APIClient()
        res = c.post("/api/auth/password-reset/request/", {"email": "w@x.com"}, format="json")
        code = res.json()["dev_code"]
        # 존재하지 않는 이메일도 200 (계정 존재 노출 방지)
        self.assertEqual(c.post("/api/auth/password-reset/request/", {"email": "none@x.com"}, format="json").status_code, 200)
        weak = c.post("/api/auth/password-reset/confirm/", {"email": "w@x.com", "code": code, "new_password": "1234"}, format="json")
        self.assertEqual(weak.status_code, 400)
        ok = c.post("/api/auth/password-reset/confirm/", {"email": "w@x.com", "code": code, "new_password": "Brand-New-Pass!9"}, format="json")
        self.assertEqual(ok.status_code, 204, ok.content)
        self.assertEqual(c.post("/api/auth/login/", {"username": "worker1", "password": "Brand-New-Pass!9"}, format="json").status_code, 200)
        self.assertEqual(c.post("/api/auth/login/", {"username": "worker1", "password": PW}, format="json").status_code, 401)


class SocialLoginTest(TestCase):
    def fake(self, payload):
        class R(io.BytesIO):
            def __enter__(s): return s
            def __exit__(s, *a): pass
        return mock.patch("urllib.request.urlopen", lambda req, timeout=None: R(json.dumps(payload).encode()))

    def test_kakao_create_then_login(self):
        c = APIClient()
        with self.fake({"id": 12345, "kakao_account": {"email": "k@k.com"}, "properties": {"nickname": "카카오"}}):
            res = c.post("/api/auth/social/kakao/", {"access_token": "t", "preferred_language": "vi"}, format="json")
            self.assertEqual(res.status_code, 200, res.content)
            self.assertTrue(res.json()["created"])
            again = c.post("/api/auth/social/kakao/", {"access_token": "t"}, format="json")
            self.assertFalse(again.json()["created"])
        u = User.objects.get(username="kakao_12345")
        self.assertEqual((u.role, u.preferred_language, u.name), ("worker", "vi", "카카오"))
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {res.json()['access']}")
        self.assertEqual(c.get("/api/auth/me/").status_code, 200)

    def test_google_and_errors(self):
        with self.fake({"sub": "g1", "email": "g@g.com", "name": "구글"}):
            self.assertEqual(APIClient().post("/api/auth/social/google/", {"access_token": "t"}, format="json").status_code, 200)
        self.assertEqual(APIClient().post("/api/auth/social/facebook/", {"access_token": "t"}, format="json").status_code, 404)
        with mock.patch("urllib.request.urlopen", side_effect=OSError("boom")):
            res = APIClient().post("/api/auth/social/kakao/", {"access_token": "bad"}, format="json")
        self.assertEqual((res.status_code, res.json()["code"]), (401, "social_auth_failed"))


class WithdrawTest(TestCase):
    def test_withdraw(self):
        w = make_worker(email="w@x.com", phone="010")
        c = client_for(w)
        self.assertEqual(c.post("/api/auth/withdraw/", {"password": "wrong"}, format="json").status_code, 403)
        self.assertEqual(c.post("/api/auth/withdraw/", {"password": PW}, format="json").status_code, 204)
        w.refresh_from_db()
        self.assertFalse(w.is_active)
        self.assertEqual((w.email, w.phone, w.name), ("", "", "탈퇴한 사용자"))
        self.assertEqual(APIClient().post("/api/auth/login/", {"username": "worker1", "password": PW}, format="json").status_code, 401)


class SettingsTest(TestCase):
    def test_notification_toggle_and_language(self):
        w = make_worker()
        c = client_for(w)
        res = c.patch("/api/auth/me/", {"notifications_enabled": False, "preferred_language": "vi"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.json()["notifications_enabled"], res.json()["preferred_language"]), (False, "vi"))
        self.assertFalse(res.json()["email_verified"])
        # 인증 여부는 직접 수정 불가
        c.patch("/api/auth/me/", {"email_verified": True}, format="json")
        w.refresh_from_db()
        self.assertFalse(w.email_verified)


class MyPageProfileTest(TestCase):
    def test_worker_profile_roundtrip_and_isolation(self):
        worker = make_worker("profile-worker")
        client = client_for(worker)
        payload = {"experience_years": 3, "experience_note": "현장 보조 경력", "available_categories": ["construction"], "available_weekdays": "0,2,4", "desired_regions": ["44130"], "can_night_shift": True}
        response = client.patch("/api/me/worker-profile/", payload, format="json")
        self.assertEqual(response.status_code, 200)
        saved = client.get("/api/me/worker-profile/").json()
        for name, value in payload.items():
            self.assertEqual(saved[name], value)
        other = client_for(make_worker("profile-other")).get("/api/me/worker-profile/").json()
        self.assertEqual(other["experience_years"], 0)
        self.assertEqual(other["available_categories"], [])

    def test_worker_profile_permissions_and_validation(self):
        self.assertEqual(client_for().get("/api/me/worker-profile/").status_code, 401)
        self.assertEqual(client_for(make_employer()).get("/api/me/worker-profile/").status_code, 403)
        client = client_for(make_worker())
        self.assertEqual(client.patch("/api/me/worker-profile/", {"available_weekdays": "7"}, format="json").status_code, 400)
        self.assertEqual(client.patch("/api/me/worker-profile/", {"desired_regions": ["not-a-region"]}, format="json").status_code, 400)

    def test_profile_cannot_change_role_or_reputation(self):
        worker = make_worker()
        response = client_for(worker).patch("/api/auth/me/", {"name": "새 이름", "username": "changed", "role": "employer", "temperature": 99.9, "review_count": 100}, format="json")
        self.assertEqual(response.status_code, 200)
        worker.refresh_from_db()
        self.assertEqual(worker.name, "새 이름")
        self.assertEqual(worker.username, "worker1")
        self.assertEqual(worker.role, "worker")
        self.assertEqual(worker.temperature, 36.5)
        self.assertEqual(worker.review_count, 0)
