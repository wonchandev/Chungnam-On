from django.test import TestCase

from apps.core.testing import client_for, make_worker
from apps.translation.models import TranslationCache
from apps.translation.services import translate_many, translate_text


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
        from unittest import mock

        with mock.patch("apps.translation.services.translate_text", side_effect=RuntimeError("api down")):
            self.assertEqual(translate_many("a", "ko", ["en"]), {})


class TranslateApiTest(TestCase):
    def test_endpoint(self):
        self.assertEqual(client_for().post("/api/translate/text/", {"text": "hi", "target": "ko", "source": "en"}, format="json").status_code, 401)
        c = client_for(make_worker())
        res = c.post("/api/translate/text/", {"text": "안녕", "target": "th"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["translated_text"], "[th] 안녕")
        self.assertEqual(c.post("/api/translate/text/", {"text": "안녕", "target": "xx"}, format="json").status_code, 400)


class GoogleTranslatorTest(TestCase):
    def test_request_and_language_mapping(self):
        import io
        import json
        from unittest import mock
        from urllib.parse import parse_qs

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
