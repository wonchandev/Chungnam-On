"""P1 음성·사진 고도화: 사진 글자 영역별 번역, 음성 서버 변환·긴 음성 분할 인식"""
import io
import math
import wave
from array import array
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from apps.core.exceptions import ServiceError
from apps.core.testing import client_for, make_worker
from apps.translation import audio, google, ocr
from apps.translation.tests_p1 import png


def symbols(text, last_break="EOL_SURE_SPACE"):
    """'안전모 착용' → Vision 단어/기호 구조. 단어 사이 SPACE, 마지막에 last_break"""
    words = []
    parts = text.split(" ")
    for i, part in enumerate(parts):
        syms = [{"text": ch} for ch in part]
        syms[-1]["property"] = {"detectedBreak": {"type": "SPACE" if i < len(parts) - 1 else last_break}}
        words.append({"symbols": syms})
    return words


def box(x1, y1, x2, y2):
    return {"vertices": [{"x": x1, "y": y1}, {"x": x2, "y": y1}, {"x": x2, "y": y2}, {"x": x1, "y": y2}]}


VISION = {
    "fullTextAnnotation": {
        "text": "안전모 착용\n작업 중 금연\nEXIT\n",
        "pages": [{
            "width": 800, "height": 600,
            "blocks": [
                {"property": {"detectedLanguages": [{"languageCode": "ko"}]}, "paragraphs": [
                    {"boundingBox": {"vertices": [{}, {"x": 300}, {"x": 300, "y": 50}, {"y": 50}]},  # 0 좌표 생략
                     "words": symbols("안전모 착용")},
                    {"boundingBox": box(0, 60, 320, 110), "words": symbols("작업 중 금연")},
                ]},
                {"paragraphs": [
                    {"boundingBox": box(600, 500, 700, 540), "property": {"detectedLanguages": [{"languageCode": "en-US"}]},
                     "words": symbols("EXIT", last_break="LINE_BREAK")},
                ]},
            ],
        }],
    },
}


class OcrParseTest(SimpleTestCase):
    def test_paragraph_regions(self):
        out = ocr.parse_annotation(VISION)
        self.assertEqual((out["text"], out["image_width"], out["image_height"]), ("안전모 착용\n작업 중 금연\nEXIT", 800, 600))
        self.assertEqual([r["text"] for r in out["regions"]], ["안전모 착용", "작업 중 금연", "EXIT"])
        first = out["regions"][0]
        self.assertEqual(first["box"], {"x": 0, "y": 0, "width": 300, "height": 50})
        self.assertEqual(first["vertices"][0], {"x": 0, "y": 0})
        self.assertEqual([r["language"] for r in out["regions"]], ["ko", "ko", "en"])  # 문단 → 블록 순서로 언어 결정

    def test_multiline_paragraph_and_hyphen(self):
        para = {"words": [{"symbols": [{"text": "안"}, {"text": "전", "property": {"detectedBreak": {"type": "LINE_BREAK"}}}]},
                          {"symbols": [{"text": "first", "property": {"detectedBreak": {"type": "HYPHEN"}}}]},
                          {"symbols": [{"text": "aid"}]}]}
        out = ocr.parse_annotation({"fullTextAnnotation": {"text": "x", "pages": [{"blocks": [{"paragraphs": [para]}]}]}})
        self.assertEqual(out["regions"][0]["text"], "안전\nfirst-\naid")
        self.assertEqual(out["regions"][0]["box"], {"x": 0, "y": 0, "width": 0, "height": 0})

    def test_empty_and_cap(self):
        self.assertEqual(ocr.parse_annotation({}), {"text": "", "image_width": None, "image_height": None, "regions": []})
        paras = [{"words": symbols(f"w{i}")} for i in range(ocr.MAX_REGIONS + 5)]
        out = ocr.parse_annotation({"fullTextAnnotation": {"text": "x", "pages": [{"blocks": [{"paragraphs": paras}]}]}})
        self.assertEqual(len(out["regions"]), ocr.MAX_REGIONS)

    @override_settings(GOOGLE_TRANSLATE_API_KEY="K")
    def test_vision_error_response(self):
        body = b'{"responses":[{"error":{"code":3,"message":"Bad image data."}}]}'
        with mock.patch("urllib.request.urlopen", return_value=io.BytesIO(body)), self.assertRaises(ServiceError):
            google.annotate_image(b"x")


class ImageRegionTranslateTest(TestCase):
    def setUp(self):
        self.c = client_for(make_worker())

    def post(self, vision, **data):
        with mock.patch.object(google, "annotate_image", return_value=vision) as m:
            res = self.c.post("/api/translate/image/", {"image": png(), "target": "vi", **data}, format="multipart")
        self.assertEqual(m.call_count, 1)  # Vision 호출은 한 번
        self.assertEqual(res.status_code, 200, res.content)
        return res.json()

    def test_regions_translated_and_existing_fields_kept(self):
        body = self.post(VISION, source="ko")
        self.assertEqual((body["detected_text"], body["source"], body["target"]), ("안전모 착용\n작업 중 금연\nEXIT", "ko", "vi"))
        self.assertEqual(body["translated_text"], "[vi] 안전모 착용\n작업 중 금연\nEXIT")
        self.assertEqual((body["image_width"], body["image_height"]), (800, 600))
        self.assertEqual([(r["text"], r["translated_text"]) for r in body["regions"]],
                         [("안전모 착용", "[vi] 안전모 착용"), ("작업 중 금연", "[vi] 작업 중 금연"), ("EXIT", "[vi] EXIT")])
        self.assertEqual(body["regions"][2]["box"], {"x": 600, "y": 500, "width": 100, "height": 40})
        self.assertEqual(set(body["regions"][0]), {"text", "translated_text", "vertices", "box", "language"})

    def test_single_backend_call_for_all_regions(self):
        with mock.patch("apps.translation.backends.EchoTranslator.translate_batch",
                        side_effect=lambda texts, s, t: [f"<{x}>" for x in texts]) as m:
            body = self.post(VISION)
        self.assertEqual(m.call_count, 1)
        self.assertEqual(body["regions"][1]["translated_text"], "<작업 중 금연>")

    def test_same_language_returns_original(self):
        body = self.post(VISION, source="ko", target="ko")
        self.assertEqual(body["regions"][0]["translated_text"], "안전모 착용")

    def test_no_text(self):
        body = self.post({})
        self.assertEqual((body["detected_text"], body["translated_text"], body["regions"]), ("", "", []))


def wav_bytes(seconds, rate=44100, channels=2, freq=440):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = array("h")
        for i in range(int(seconds * rate)):
            v = int(8000 * math.sin(2 * math.pi * freq * i / rate))
            frames.extend([v] * channels)
        w.writeframes(frames.tobytes())
    return buf.getvalue()


def pcm(seconds, quiet_at=()):
    """16kHz 톤. quiet_at 의 초 지점 0.3초는 무음"""
    samples = array("h")
    quiet = {int(q * audio.SAMPLE_RATE) for q in quiet_at}
    i = 0
    total = int(seconds * audio.SAMPLE_RATE)
    while i < total:
        if i in quiet:
            samples.extend([0] * int(0.3 * audio.SAMPLE_RATE))
            i += int(0.3 * audio.SAMPLE_RATE)
            continue
        samples.append(5000 if i % 2 else -5000)
        i += 1
    return samples[:total].tobytes()


class AudioConvertTest(SimpleTestCase):
    def test_ffmpeg_available(self):
        self.assertTrue(audio.ffmpeg_path())

    def test_converts_to_16k_mono(self):
        out = audio.to_pcm(wav_bytes(1.5), limit_seconds=10)
        self.assertAlmostEqual(len(out) / audio.BYTES_PER_SECOND, 1.5, delta=0.05)

    def test_too_long(self):
        with self.assertRaises(ServiceError) as cm:
            audio.to_pcm(wav_bytes(3, rate=8000, channels=1), limit_seconds=2)
        self.assertEqual(cm.exception.get_codes(), "audio_too_long")

    def test_garbage_is_decode_error(self):
        with self.assertRaises(audio.AudioDecodeError):
            audio.to_pcm(b"not audio at all", limit_seconds=10)

    @override_settings(FFMPEG_BINARY="C:/nope/ffmpeg-missing.exe")
    def test_missing_binary_is_decode_error(self):
        with self.assertRaises(audio.AudioDecodeError):
            audio.to_pcm(wav_bytes(0.2), limit_seconds=10)

    def test_split_short_is_single_chunk(self):
        data = pcm(10)
        self.assertEqual(audio.split_pcm(data), [data])

    def test_split_long_at_quiet_points(self):
        data = pcm(130, quiet_at=(52, 104))
        chunks = audio.split_pcm(data)
        self.assertEqual(b"".join(chunks), data)  # 잃어버리는 구간 없음
        lengths = [len(c) / audio.BYTES_PER_SECOND for c in chunks]
        self.assertTrue(all(sec <= audio.CHUNK_SECONDS for sec in lengths), lengths)
        self.assertAlmostEqual(lengths[0], 52, delta=0.11)  # 52초 무음 구간에서 잘림
        self.assertAlmostEqual(lengths[0] + lengths[1], 104, delta=0.11)


class VoiceLongTest(TestCase):
    def setUp(self):
        self.c = client_for(make_worker())

    def test_long_voice_split_and_joined_in_order(self):
        data = pcm(70, quiet_at=(54,))
        replies = iter(["첫 번째", "두 번째"])
        with mock.patch.object(audio, "to_pcm", return_value=data), \
                mock.patch.object(audio, "MAX_WORKERS", 1), \
                mock.patch.object(google, "speech_to_text", side_effect=lambda *a: next(replies)) as m:
            res = self.c.post("/api/translate/voice/", {"audio": SimpleUploadedFile("a.m4a", b"x"), "source": "ko", "target": "vi"},
                              format="multipart")
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual((body["transcript"], body["translated_text"], body["duration_seconds"]),
                         ("첫 번째 두 번째", "[vi] 첫 번째 두 번째", 70.0))
        self.assertEqual([c.args[1:] for c in m.call_args_list], [("ko", "LINEAR16")] * 2)

    def test_real_conversion_path(self):
        with mock.patch.object(google, "speech_to_text", return_value="hello") as m:
            res = self.c.post("/api/translate/voice/", {"audio": SimpleUploadedFile("a.wav", wav_bytes(1)), "source": "en", "target": "ko"},
                              format="multipart")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["duration_seconds"], 1.0)
        self.assertEqual(m.call_args.args[1:], ("en", "LINEAR16"))
        self.assertEqual(len(m.call_args.args[0]), audio.BYTES_PER_SECOND)

    @override_settings(VOICE_MAX_SECONDS=1)
    def test_too_long_rejected(self):
        res = self.c.post("/api/translate/voice/", {"audio": SimpleUploadedFile("a.wav", wav_bytes(2, rate=8000, channels=1)),
                                                    "source": "ko", "target": "vi"}, format="multipart")
        self.assertEqual((res.status_code, res.json()["code"]), (413, "audio_too_long"))

    @override_settings(VOICE_MAX_UPLOAD_MB=0)
    def test_upload_limit(self):
        res = self.c.post("/api/translate/voice/", {"audio": SimpleUploadedFile("a.wav", b"xx"), "source": "ko", "target": "vi"},
                          format="multipart")
        self.assertEqual((res.status_code, res.json()["code"]), (413, "file_too_large"))

    def test_undecodable_large_file_rejected(self):
        with mock.patch.object(google, "MAX_INLINE_AUDIO", 1), mock.patch.object(google, "speech_to_text") as m:
            res = self.c.post("/api/translate/voice/", {"audio": SimpleUploadedFile("a.bin", b"garbage"), "source": "ko", "target": "vi"},
                              format="multipart")
        self.assertEqual((res.status_code, res.json()["code"]), (400, "unsupported_audio"))
        m.assert_not_called()
