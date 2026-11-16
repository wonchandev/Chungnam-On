import io
import json
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.core.exceptions import ServiceError
from apps.core.testing import client_for, make_worker
from apps.translation import google
from apps.translation.models import LanguageCourse


def png():
    buf = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buf, "PNG")
    return SimpleUploadedFile("a.png", buf.getvalue(), content_type="image/png")


class LanguagesPhrasesTest(TestCase):
    def test_languages(self):
        res = client_for().get("/api/languages/").json()
        self.assertEqual(len(res), 10)
        self.assertEqual(res[0], {"code": "ko", "native_name": "한국어", "name": "Korean"})

    def test_phrases(self):
        c = client_for()
        res = c.get("/api/phrases/", {"category": "safety"}, HTTP_ACCEPT_LANGUAGE="th").json()
        self.assertEqual(len(res), 4)
        self.assertTrue(res[0]["text"].startswith("[th]"))
        self.assertEqual(res[0]["category_label"], "안전")
        ko = c.get("/api/phrases/", {"q": "안전모"}).json()
        self.assertEqual([p["text_ko"] for p in ko], ["안전모를 착용하세요"])
        self.assertEqual(ko[0]["text"], "안전모를 착용하세요")  # ko 는 번역 없이 원문


class VoiceImageTest(TestCase):
    def setUp(self):
        self.c = client_for(make_worker())

    def test_voice(self):
        audio = SimpleUploadedFile("a.webm", b"\x00\x01", content_type="audio/webm")
        with mock.patch.object(google, "speech_to_text", return_value="안녕하세요") as m:
            res = self.c.post("/api/translate/voice/", {"audio": audio, "source": "ko", "target": "th"}, format="multipart")
        self.assertEqual(res.status_code, 200, res.content)
        # 서버가 해석할 수 없는 파일은 클라이언트가 알려준 encoding 으로 그대로 보낸다 (길이 정보 없음)
        self.assertEqual(res.json(), {"transcript": "안녕하세요", "source": "ko", "target": "th", "translated_text": "[th] 안녕하세요",
                                      "duration_seconds": None})
        self.assertEqual(m.call_args.args[1:], ("ko", "WEBM_OPUS"))

    def test_voice_empty_transcript(self):
        with mock.patch.object(google, "speech_to_text", return_value=""):
            res = self.c.post("/api/translate/voice/", {"audio": SimpleUploadedFile("a.webm", b"x"), "source": "ko", "target": "th"}, format="multipart")
        self.assertEqual(res.json()["translated_text"], "")

    def test_image_auto_source(self):
        with mock.patch.object(google, "annotate_image", return_value={"fullTextAnnotation": {"text": "DANGER\n"}}):
            res = self.c.post("/api/translate/image/", {"image": png(), "target": "ko"}, format="multipart")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((res.json()["detected_text"], res.json()["source"], res.json()["translated_text"]), ("DANGER", "auto", "[ko] DANGER"))

    def test_requires_auth_and_valid_input(self):
        self.assertEqual(client_for().post("/api/translate/image/", {}, format="multipart").status_code, 401)
        self.assertEqual(self.c.post("/api/translate/image/", {"target": "ko"}, format="multipart").status_code, 400)

    @override_settings(GOOGLE_TRANSLATE_API_KEY="")
    def test_google_key_missing(self):
        with self.assertRaises(ServiceError):
            google.image_to_text(b"x")

    def test_google_request_shape(self):
        captured = {}

        def fake(req, timeout=None):
            import json
            captured["url"], captured["body"] = req.full_url, json.loads(req.data)
            return io.BytesIO(b'{"results":[{"alternatives":[{"transcript":" hello "}]}]}')

        with override_settings(GOOGLE_TRANSLATE_API_KEY="K"), mock.patch("urllib.request.urlopen", fake):
            out = google.speech_to_text(b"abc", "zh", "OGG_OPUS")
        self.assertEqual(out, "hello")
        self.assertIn("speech.googleapis.com", captured["url"])
        self.assertEqual(captured["body"]["config"]["languageCode"], "cmn-Hans-CN")
        self.assertEqual(captured["body"]["config"]["encoding"], "OGG_OPUS")


class CourseTest(TestCase):
    def test_enroll_flow(self):
        c = client_for(make_worker())
        res = c.get("/api/courses/").json()
        self.assertEqual(len(res), 3)
        cid = res[0]["id"]
        r = c.post(f"/api/courses/{cid}/enroll/")
        self.assertEqual((r.status_code, r.json()["is_enrolled"], r.json()["enrolled_count"]), (201, True, 1))
        self.assertEqual(c.post(f"/api/courses/{cid}/enroll/").json()["code"], "already_enrolled")
        self.assertEqual([x["id"] for x in c.get("/api/courses/mine/").json()["results"]], [cid])
        self.assertFalse(c.delete(f"/api/courses/{cid}/enroll/").json()["is_enrolled"])
        self.assertEqual(client_for().post(f"/api/courses/{cid}/enroll/").status_code, 401)

    def test_capacity(self):
        LanguageCourse.objects.update(capacity=1)
        cid = LanguageCourse.objects.first().id
        client_for(make_worker("a")).post(f"/api/courses/{cid}/enroll/")
        res = client_for(make_worker("b")).post(f"/api/courses/{cid}/enroll/")
        self.assertEqual((res.status_code, res.json()["code"]), (409, "course_full"))


class OpenAITranslatorTest(TestCase):
    def test_batch_returns_ordered_translations_in_one_request(self):
        from apps.translation.backends import OpenAITranslator

        with mock.patch("openai.OpenAI") as cls:
            create = cls.return_value.chat.completions.create
            create.return_value = mock.Mock(choices=[mock.Mock(message=mock.Mock(
                content='{"translations":["Hard hats", "Break time"]}',
            ))])
            result = OpenAITranslator(api_key="K", model="m").translate_batch(["안전모", "휴게시간"], "ko", "en")
        self.assertEqual(result, ["Hard hats", "Break time"])
        create.assert_called_once()
        self.assertEqual(create.call_args.kwargs["response_format"], {"type": "json_object"})
        self.assertEqual(json.loads(create.call_args.kwargs["messages"][1]["content"]), ["안전모", "휴게시간"])

    def test_translate_request(self):
        from apps.translation.backends import OpenAITranslator

        with mock.patch("openai.OpenAI") as cls:
            cls.return_value.chat.completions.create.return_value = mock.Mock(
                choices=[mock.Mock(message=mock.Mock(content="  สวัสดี \n"))]
            )
            out = OpenAITranslator(api_key="K", model="m").translate("안녕하세요", "ko", "th")
        self.assertEqual(out, "สวัสดี")
        kw = cls.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual((kw["model"], kw["temperature"]), ("m", 0))
        self.assertIn("Thai", kw["messages"][0]["content"])
        self.assertIn("Korean", kw["messages"][0]["content"])
        self.assertEqual(kw["messages"][1], {"role": "user", "content": "안녕하세요"})

    def test_auto_source_and_missing_key(self):
        from apps.translation.backends import OpenAITranslator

        with mock.patch("openai.OpenAI") as cls:
            cls.return_value.chat.completions.create.return_value = mock.Mock(choices=[mock.Mock(message=mock.Mock(content="x"))])
            OpenAITranslator(api_key="K").translate("hi", "auto", "ko")
        self.assertNotIn("source language", cls.return_value.chat.completions.create.call_args.kwargs["messages"][0]["content"])
        with override_settings(OPENAI_API_KEY=""):
            with self.assertRaises(RuntimeError):
                OpenAITranslator()
