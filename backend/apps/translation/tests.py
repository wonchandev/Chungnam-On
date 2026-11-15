import io
import json
from unittest import mock
from urllib.parse import parse_qs

from django.test import TestCase, override_settings

from apps.core.testing import client_for, make_worker
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
