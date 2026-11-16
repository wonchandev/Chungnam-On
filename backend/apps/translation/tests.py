import io
import json
from datetime import timedelta
from unittest import mock
from urllib.error import HTTPError
from urllib.parse import parse_qs

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.core.testing import client_for, make_worker
from apps.translation.glossary import TERMS
from apps.translation.models import TranslationCache
from apps.translation.services import detect_source_language, translate_batch, translate_many, translate_text


class TranslationServiceTest(TestCase):
    def test_same_language_and_empty_passthrough(self):
        self.assertEqual(translate_text("안녕", "ko", "ko"), "안녕")
        self.assertEqual(translate_text("", "ko", "th"), "")

    def test_cached(self):
        self.assertEqual(translate_text("안녕하세요", "ko", "th"), "[th] 안녕하세요")
        self.assertEqual(TranslationCache.objects.count(), 1)
        translate_text("안녕하세요", "ko", "th")
        self.assertEqual(TranslationCache.objects.count(), 1)

    def test_cache_normalizes_unicode_and_line_endings(self):
        with mock.patch("apps.translation.backends.EchoTranslator.translate", return_value="translated") as translate:
            self.assertEqual(translate_text("Cafe\u0301\r\nmenu", "en", "ko"), "translated")
            self.assertEqual(translate_text("Café\nmenu", "en", "ko"), "translated")
        translate.assert_called_once_with("Café\nmenu", "en", "ko")

    @override_settings(TRANSLATION_CACHE_TTL_DAYS=1)
    def test_expired_cache_is_refreshed_in_place(self):
        translate_text("hello", "en", "ko")
        expired = timezone.now() - timedelta(days=2)
        TranslationCache.objects.update(created_at=expired)
        with mock.patch("apps.translation.backends.EchoTranslator.translate", return_value="새 번역") as translate:
            self.assertEqual(translate_text("hello", "en", "ko"), "새 번역")
            self.assertEqual(translate_text("hello", "en", "ko"), "새 번역")
        translate.assert_called_once()
        self.assertGreater(TranslationCache.objects.get().created_at, expired)

    @override_settings(TRANSLATION_CACHE_TTL_DAYS=0)
    def test_cache_can_be_disabled(self):
        with mock.patch("apps.translation.backends.EchoTranslator.translate", side_effect=["first", "second"]):
            self.assertEqual(translate_text("안녕", "ko", "en"), "first")
            self.assertEqual(translate_text("안녕", "ko", "en"), "second")
        self.assertFalse(TranslationCache.objects.exists())

    @override_settings(TRANSLATION_BACKEND="apps.translation.backends.OpenAITranslator", OPENAI_API_KEY="test-key")
    def test_cache_is_scoped_to_openai_model(self):
        with mock.patch("apps.translation.backends.OpenAITranslator._complete", side_effect=["first", "second"]) as complete:
            with override_settings(OPENAI_TRANSLATE_MODEL="model-one"):
                self.assertEqual(translate_text("안녕", "ko", "en"), "first")
            with override_settings(OPENAI_TRANSLATE_MODEL="model-two"):
                self.assertEqual(translate_text("안녕", "ko", "en"), "second")
        self.assertEqual(complete.call_count, 2)

    def test_translate_many_skips_source_and_survives_failures(self):
        self.assertEqual(set(translate_many("a", "ko", ["ko", "en", "th"])), {"en", "th"})
        with mock.patch("apps.translation.services.translate_text", side_effect=RuntimeError("api down")):
            self.assertEqual(translate_many("a", "ko", ["en"]), {})

    @override_settings(TRANSLATION_BACKEND="apps.translation.backends.GoogleTranslator", GOOGLE_TRANSLATE_API_KEY="test-key")
    def test_batch_applies_glossary_and_reuses_cached_entries(self):
        texts = ["일당 120000원", "안전모와 4대 보험", "휴게 시간 30분", "", "일당 120000원"]
        response = {"data": {"translations": [
            {"translatedText": "CHUNGNAMTERM0X 120000 won"},
            {"translatedText": "CHUNGNAMTERM0X and CHUNGNAMTERM1X"},
            {"translatedText": "CHUNGNAMTERM0X 30 minutes"},
        ]}}
        with mock.patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(response).encode())) as request:
            results = translate_batch(texts, "ko", "en")
            self.assertEqual(translate_text(texts[0], "ko", "en"), results[0])
            self.assertEqual(translate_batch(texts, "ko", "en"), results)
        request.assert_called_once()
        self.assertEqual(parse_qs(request.call_args.args[0].data.decode())["q"], [
            "CHUNGNAMTERM0X 120000원", "CHUNGNAMTERM0X와 CHUNGNAMTERM1X", "CHUNGNAMTERM0X 30분",
        ])
        self.assertEqual(results, [
            "daily pay 120000 won", "hard hat and four major social insurance programs",
            "break time 30 minutes", "", "daily pay 120000 won",
        ])
        self.assertEqual(TranslationCache.objects.count(), 3)

    @override_settings(TRANSLATION_BACKEND="apps.translation.backends.GoogleTranslator", GOOGLE_TRANSLATE_API_KEY="test-key")
    def test_existing_cache_without_glossary_does_not_hide_terms(self):
        with override_settings(TRANSLATION_BACKEND="apps.translation.backends.EchoTranslator"):
            self.assertEqual(translate_text("일당", "ko", "en"), "[en] 일당")
        response = io.BytesIO(b'{"data":{"translations":[{"translatedText":"CHUNGNAMTERM0X"}]}}')
        with mock.patch("urllib.request.urlopen", return_value=response):
            self.assertEqual(translate_text("일당", "ko", "en"), "daily pay")

    @override_settings(TRANSLATION_BACKEND="apps.translation.backends.GoogleTranslator", GOOGLE_TRANSLATE_API_KEY="test-key")
    def test_changing_a_glossary_entry_invalidates_the_previous_translation(self):
        with mock.patch("apps.translation.backends.GoogleTranslator.translate_batch", return_value=["CHUNGNAMTERM0X"]) as translate:
            self.assertEqual(translate_text("안전모", "ko", "en"), "hard hat")
            with mock.patch.dict(TERMS["안전모"], {"en": "safety helmet"}):
                self.assertEqual(translate_text("안전모", "ko", "en"), "safety helmet")
        self.assertEqual(translate.call_count, 2)

    @override_settings(TRANSLATION_BACKEND="apps.translation.backends.GoogleTranslator", GOOGLE_TRANSLATE_API_KEY="test-key")
    def test_detect_normalizes_supported_languages_and_falls_back(self):
        response = io.BytesIO(b'{"data":{"detections":[[{"language":"zh-CN"}]]}}')
        with mock.patch("urllib.request.urlopen", return_value=response) as request:
            self.assertEqual(detect_source_language("午休三十分钟", fallback="ko"), "zh")
        self.assertIn("/detect?", request.call_args.args[0].full_url)
        self.assertEqual(parse_qs(request.call_args.args[0].data.decode())["q"], ["午休三十分钟"])
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError), self.assertLogs("apps.translation.services"):
            self.assertEqual(detect_source_language("bonjour", fallback="ko"), "ko")


class TranslateApiTest(TestCase):
    def test_endpoint(self):
        self.assertEqual(client_for().post("/api/translate/text/", {"text": "hi", "target": "ko", "source": "en"}, format="json").status_code, 401)
        c = client_for(make_worker())
        res = c.post("/api/translate/text/", {"text": "안녕", "target": "th"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["translated_text"], "[th] 안녕")
        self.assertEqual(c.post("/api/translate/text/", {"text": "안녕", "target": "xx"}, format="json").status_code, 400)

    def test_auto_source_is_reported(self):
        res = client_for(make_worker()).post(
            "/api/translate/text/", {"text": "안녕", "source": "auto", "target": "th"}, format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["source"], "ko")

    @override_settings(TRANSLATION_BACKEND="apps.translation.backends.GoogleTranslator", GOOGLE_TRANSLATE_API_KEY="test-key")
    def test_provider_timeout_returns_gateway_timeout(self):
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError):
            response = client_for(make_worker()).post(
                "/api/translate/text/", {"text": "안녕", "source": "ko", "target": "en"}, format="json",
            )
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json()["code"], "translation_timeout")

    @override_settings(TRANSLATION_BACKEND="apps.translation.backends.GoogleTranslator", GOOGLE_TRANSLATE_API_KEY="test-key")
    def test_google_daily_quota_and_temporary_limit_return_different_codes(self):
        client = client_for(make_worker())
        for reason, code, retry_after in [
            ("dailyLimitExceeded", "translation_quota_exhausted", None),
            ("userRateLimitExceeded", "translation_rate_limited", "90"),
        ]:
            with self.subTest(reason=reason):
                body = io.BytesIO(json.dumps({"error": {"errors": [{"reason": reason}]}}).encode())
                error = HTTPError("https://translation.googleapis.com/", 403, "limit", {"Retry-After": "90"}, body)
                with mock.patch("urllib.request.urlopen", side_effect=error):
                    response = client.post("/api/translate/text/", {"text": "안녕", "target": "en"}, format="json")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["code"], code)
                self.assertEqual(response.headers.get("Retry-After"), retry_after)

    @override_settings(TRANSLATION_BACKEND="apps.translation.backends.OpenAITranslator", OPENAI_API_KEY="test-key")
    def test_openai_429_distinguishes_temporary_rate_limits_and_billing_quota(self):
        from openai import RateLimitError

        client = client_for(make_worker())
        for reason, code, retry_after in [
            ("organization_spend_limit_exceeded", "translation_quota_exhausted", None),
            ("rate_limit_exceeded", "translation_rate_limited", "45"),
        ]:
            with self.subTest(reason=reason):
                upstream = mock.Mock(status_code=429, headers={"Retry-After": "45"})
                error = RateLimitError("limit", response=upstream, body={"code": reason})
                with mock.patch("openai.OpenAI") as sdk:
                    sdk.return_value.chat.completions.create.side_effect = error
                    response = client.post("/api/translate/text/", {"text": "안녕", "target": "en"}, format="json")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["code"], code)
                self.assertEqual(response.headers.get("Retry-After"), retry_after)
                self.assertEqual(sdk.call_args.kwargs["max_retries"], 0)


class GoogleTranslatorTest(TestCase):
    def test_request_and_language_mapping(self):
        from apps.translation.backends import GoogleTranslator

        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"], captured["body"] = req.full_url, parse_qs(req.data.decode())
            return io.BytesIO(json.dumps({"data": {"translations": [{"translatedText": "你好"}]}}).encode())

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            out = GoogleTranslator(api_key="KEY").translate("안녕하세요", "ko", "zh")
        self.assertEqual(out, "你好")
        self.assertIn("key=KEY", captured["url"])
        self.assertEqual(captured["body"]["target"], ["zh-CN"])
        self.assertEqual(captured["body"]["format"], ["text"])

    def test_missing_key_raises(self):
        from django.test import override_settings

        from apps.translation.backends import GoogleTranslator

        with override_settings(GOOGLE_TRANSLATE_API_KEY=""):
            with self.assertRaises(RuntimeError):
                GoogleTranslator()
