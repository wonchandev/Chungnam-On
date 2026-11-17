import io
import json
from unittest import mock

from django.test import SimpleTestCase

from apps.translation.backends import MyMemoryTranslator
from apps.translation.errors import TranslationProviderError


def fake_response(text="번역", status=200, quota=False):
    body = json.dumps({"responseData": {"translatedText": text}, "responseStatus": status, "quotaFinished": quota}).encode()
    res = mock.MagicMock()
    res.__enter__.return_value = io.BytesIO(body)
    return res


class MyMemoryTest(SimpleTestCase):
    def test_request_shape_and_code_map(self):
        with mock.patch("urllib.request.urlopen", return_value=fake_response("Xin chào")) as op:
            out = MyMemoryTranslator().translate("안녕하세요", "ko", "zh")
        self.assertEqual(out, "Xin chào")
        url = op.call_args.args[0].full_url
        self.assertIn("langpair=ko%7Czh-CN", url)

    def test_long_text_is_chunked_under_limit_and_newlines_kept(self):
        calls = []

        def fake(req, timeout):
            calls.append(req.full_url)
            return fake_response("T")

        text = ("가나다라마바사. " * 80).strip() + "\n\n둘째 줄"
        with mock.patch("urllib.request.urlopen", fake):
            out = MyMemoryTranslator().translate(text, "ko", "en")
        self.assertGreater(len(calls), 1)
        self.assertEqual(out.count("\n"), 2)
        for chunk in MyMemoryTranslator()._chunks(text.split("\n")[0]):
            self.assertLessEqual(len(chunk.encode()), 450)

    def test_quota_and_bad_status(self):
        with mock.patch("urllib.request.urlopen", return_value=fake_response("x", 429)):
            with self.assertRaises(TranslationProviderError) as cm:
                MyMemoryTranslator().translate("안녕", "ko", "en")
        self.assertEqual(cm.exception.detail.code, "translation_quota_exhausted")
        with mock.patch("urllib.request.urlopen", return_value=fake_response("x", 403)):
            with self.assertRaises(TranslationProviderError):
                MyMemoryTranslator().translate("안녕", "ko", "en")
        with mock.patch("urllib.request.urlopen", side_effect=OSError("down")):
            with self.assertRaises(TranslationProviderError):
                MyMemoryTranslator().translate("안녕", "ko", "en")


from django.test import TestCase, override_settings  # noqa: E402


class FeaturesTest(TestCase):
    @override_settings(GOOGLE_TRANSLATE_API_KEY="", GOOGLE_TTS_API_KEY="", GOOGLE_TTS_USE_ADC=False, OPENAI_API_KEY="")
    def test_all_off_without_keys(self):
        d = self.client.get("/api/features/").json()
        self.assertEqual(set(d.values()), {False})

    @override_settings(GOOGLE_TRANSLATE_API_KEY="k", OPENAI_API_KEY="o")
    def test_on_with_keys(self):
        d = self.client.get("/api/features/").json()
        self.assertTrue(all(d[k] for k in ("voice_translate", "image_translate", "live_voice", "tts", "ai_chat")))
