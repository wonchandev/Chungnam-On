import asyncio
import base64
import io
import json
import re
from unittest import mock

from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from httpx2 import AsyncClient, MockTransport, Response
from rest_framework_simplejwt.tokens import AccessToken

from apps.chat.middleware import JWTAuthMiddleware
from apps.core.testing import client_for, make_worker

from .backends import GoogleTranslator, OpenAITranslator
from .chat_text import expand_abbreviations, mark_emoticons
from .errors import TranslationProviderError
from .glossary import restore_terms
from .management.commands.compare_translation_engines import SAMPLES
from .models import TranslationCache
from .routing import websocket_urlpatterns


class ChatExpressionTest(SimpleTestCase):
    def test_expands_standalone_abbreviations_and_preserves_urls_and_mentions(self):
        self.assertEqual(expand_abbreviations("ㅇㅋ, ㄳ ㅋㅋㅋㅋ", "ko"), "알겠어요, 감사합니다 하하")
        self.assertEqual(
            expand_abbreviations("THX! @asap #lol thx@example.com https://example.com/thx ASAP", "en"),
            "thank you! @asap #lol thx@example.com https://example.com/thx as soon as possible",
        )

    def test_preserves_complete_emoji_sequences_and_ascii_emoticons(self):
        text = "안녕하세요 👷🏽‍♀️ 🇰🇷 1️⃣ :) 👷🏽‍♀️"
        marked, replacements = mark_emoticons(text)
        self.assertEqual(list(replacements.values()), ["👷🏽‍♀️", "🇰🇷", "1️⃣", ":)", "👷🏽‍♀️"])
        self.assertEqual(restore_terms(marked, replacements), text)


@override_settings(TRANSLATION_BACKEND="apps.translation.backends.GoogleTranslator", GOOGLE_TRANSLATE_API_KEY="test-key")
class ChatExpressionEndpointTest(TestCase):
    def setUp(self):
        self.client = client_for(make_worker(lang="ko"))
        peer = make_worker("peer", lang="en")
        room = self.client.post("/api/chat/rooms/", {"user_id": peer.id}, format="json").json()
        self.url = f"/api/chat/rooms/{room['id']}/messages/"

    def test_chat_translation_expands_text_and_keeps_original_and_emoji(self):
        def translated(texts, source, target):
            self.assertEqual((source, target), ("ko", "en"))
            self.assertTrue(texts[0].startswith("알겠어요 "))
            markers = re.findall(r"CHUNGNAMTERMX*\d+X", texts[0])
            self.assertEqual(len(markers), 2)
            return [f"Okay, put on a {markers[0]}. {markers[1]}"]

        with mock.patch.object(GoogleTranslator, "detect_language", return_value="ko"), \
                mock.patch.object(GoogleTranslator, "translate_batch", side_effect=translated):
            response = self.client.post(self.url, {"text": "ㅇㅋ 안전모 착용 👷🏽‍♀️"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["text"], "ㅇㅋ 안전모 착용 👷🏽‍♀️")
        self.assertEqual(response.json()["translations"], {"en": "Okay, put on a hard hat. 👷🏽‍♀️"})

    def test_emoji_only_messages_are_kept_without_calling_the_provider(self):
        with mock.patch("apps.translation.services.get_translator") as get_translator:
            response = self.client.post(self.url, {"text": "👷🏽‍♀️👍"}, format="json")
        get_translator.assert_not_called()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["text"], "👷🏽‍♀️👍")
        self.assertEqual(response.json()["translations"], {})


@override_settings(TRANSLATION_BACKEND="apps.translation.backends.EchoTranslator", TRANSLATION_CACHE_TTL_DAYS=30)
class PhrasePretranslationTest(TestCase):
    def test_pretranslations_are_reused_by_phrase_and_quick_reply_endpoints(self):
        out = io.StringIO()
        call_command("pretranslate_phrases", "--target", "en", stdout=out)
        self.assertIn("en:", out.getvalue())
        self.assertEqual(set(TranslationCache.objects.values_list("target_lang", flat=True)), {"en"})

        user = client_for(make_worker(lang="en"))
        with mock.patch("apps.translation.services.get_translator") as get_translator:
            phrases = user.get("/api/phrases/", HTTP_ACCEPT_LANGUAGE="en").json()
            replies = user.get("/api/chat/quick-replies/", HTTP_ACCEPT_LANGUAGE="en").json()
        get_translator.assert_not_called()
        self.assertTrue(phrases[0]["text"].startswith("[en] "))
        self.assertTrue(replies[0]["text"].startswith("[en] "))


class EngineComparisonTest(SimpleTestCase):
    @override_settings(GOOGLE_TRANSLATE_API_KEY="google-test-key", OPENAI_API_KEY="openai-test-key")
    def test_same_inputs_are_scored_for_both_engines(self):
        reference = [sample["reference"] for sample in SAMPLES]
        alternate = [reference[0].replace("120,000", "100,000"), *reference[1:]]
        out = io.StringIO()
        with mock.patch.object(GoogleTranslator, "translate_batch", return_value=reference) as google, \
                mock.patch.object(OpenAITranslator, "translate_batch", return_value=alternate) as openai:
            call_command("compare_translation_engines", stdout=out)
        self.assertEqual(google.call_args, openai.call_args)
        report = json.loads(out.getvalue())["providers"]
        self.assertTrue(report["google"]["samples"][0]["numbers_preserved"])
        self.assertFalse(report["openai"]["samples"][0]["numbers_preserved"])
        self.assertEqual(report["google"]["samples"][0]["terms_found"], 2)

    @override_settings(GOOGLE_TRANSLATE_API_KEY="", OPENAI_API_KEY="")
    def test_reports_missing_keys_without_using_network(self):
        out = io.StringIO()
        call_command("compare_translation_engines", stdout=out)
        self.assertEqual(json.loads(out.getvalue())["providers"], {
            "google": {"status": "missing_key"}, "openai": {"status": "missing_key"},
        })


class TextToSpeechTest(TestCase):
    @override_settings(GOOGLE_TTS_USE_ADC=False, GOOGLE_TTS_API_KEY="tts-test-key", GOOGLE_TRANSLATE_API_KEY="translation-test-key")
    def test_returns_mp3_and_uses_the_separate_tts_key(self):
        audio = b"ID3-test-audio"
        mocked_body = {"audioContent": base64.b64encode(audio).decode()}
        with mock.patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(mocked_body).encode())) as request:
            response = client_for(make_worker()).post(
                "/api/translate/tts/", {"text": "Wear a hard hat.", "language": "en"},
                format="json", HTTP_ACCEPT="audio/mpeg",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "audio/mpeg")
        self.assertEqual(response.content, audio)
        sent = request.call_args.args[0]
        self.assertIn("?key=tts-test-key", sent.full_url)
        self.assertEqual(json.loads(sent.data), {
            "input": {"text": "Wear a hard hat."}, "voice": {"languageCode": "en-US"},
            "audioConfig": {"audioEncoding": "MP3"},
        })

    def test_requires_auth_and_enforces_byte_limit_and_supported_language(self):
        url = "/api/translate/tts/"
        anonymous = client_for().post(url, {}, format="json", HTTP_ACCEPT="audio/mpeg")
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(anonymous["Content-Type"], "application/json")
        user = client_for(make_worker())
        self.assertEqual(user.post(url, {"text": "한" * 1667, "language": "ko"}, format="json").status_code, 400)
        self.assertEqual(user.post(url, {"text": "Hello", "language": "mn"}, format="json").status_code, 400)

    @override_settings(GOOGLE_TTS_USE_ADC=True)
    def test_explicit_adc_configuration_uses_an_authorized_session(self):
        credentials = object()
        audio = b"ID3-demo"
        upstream = mock.Mock()
        upstream.json.return_value = {"audioContent": base64.b64encode(audio).decode()}
        with mock.patch("google.auth.default", return_value=(credentials, "demo-project")) as authorize, \
                mock.patch("google.auth.transport.requests.AuthorizedSession") as authorized_session:
            session = authorized_session.return_value.__enter__.return_value
            session.post.return_value = upstream
            response = client_for(make_worker()).post(
                "/api/translate/tts/", {"text": "안전모를 착용하세요.", "language": "ko"}, format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, audio)
        authorize.assert_called_once_with(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        authorized_session.assert_called_once_with(credentials)
        self.assertEqual(session.post.call_args.kwargs["json"]["voice"], {"languageCode": "ko-KR"})


@override_settings(GOOGLE_TRANSLATE_API_KEY="test-key", ANTHROPIC_API_KEY="")
class VoiceStreamTest(TransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        self.token = str(AccessToken.for_user(make_worker()))
        self.app = JWTAuthMiddleware(URLRouter(websocket_urlpatterns))

    def connection(self, authenticated=True):
        token = f"?token={self.token}" if authenticated else ""
        return WebsocketCommunicator(self.app, f"/ws/translate/voice/{token}")

    async def test_requires_jwt(self):
        socket = self.connection(authenticated=False)
        self.assertEqual(await socket.connect(), (False, 4401))
        await socket.disconnect()

    async def test_sends_a_translation_before_client_stops(self):
        frame = b"\0" * 6400

        async def recognize(frames, source, *, timeout):
            self.assertEqual(source, "ko")
            self.assertEqual(await anext(frames), frame)
            yield "안전모", False
            yield "안전모를 착용하세요", True
            self.assertEqual([chunk async for chunk in frames], [])

        socket = self.connection()
        self.assertTrue((await socket.connect())[0])
        try:
            with mock.patch("apps.translation.consumers.recognize_stream", recognize), \
                    mock.patch("apps.translation.consumers.translate_segment", new_callable=mock.AsyncMock,
                               return_value="Wear a hard hat.") as translate:
                await socket.send_json_to({"type": "start", "source": "ko", "target": "en"})
                self.assertEqual((await socket.receive_json_from())["type"], "ready")
                await socket.send_to(bytes_data=frame)
                self.assertFalse((await socket.receive_json_from())["is_final"])
                self.assertTrue((await socket.receive_json_from())["is_final"])
                result = await socket.receive_json_from()
                self.assertEqual(result, {
                    "type": "translation", "segment": 0, "text": "안전모를 착용하세요",
                    "translated_text": "Wear a hard hat.", "source": "ko", "target": "en",
                })
                translate.assert_awaited_once_with("안전모를 착용하세요", "ko", "en")
                await socket.send_json_to({"type": "stop"})
                self.assertEqual(await socket.receive_json_from(), {"type": "complete"})
        finally:
            await socket.disconnect()

    async def test_rejects_invalid_audio_and_language_without_opening_a_provider_stream(self):
        socket = self.connection()
        self.assertTrue((await socket.connect())[0])
        try:
            with mock.patch("apps.translation.consumers.recognize_stream") as recognize:
                await socket.send_json_to({"type": "start", "source": "no-such-language", "target": "en"})
                self.assertEqual((await socket.receive_json_from())["code"], "invalid_voice_languages")
                await socket.send_json_to({"type": "start", "source": "ko", "target": "en"})
                self.assertEqual((await socket.receive_json_from())["type"], "ready")
                await socket.send_to(bytes_data=b"\0")
                self.assertEqual((await socket.receive_json_from())["code"], "invalid_audio_chunk")
                await socket.send_json_to({"type": "stop"})
                self.assertEqual(await socket.receive_json_from(), {"type": "complete"})
            recognize.assert_not_called()
        finally:
            await socket.disconnect()

    async def test_keeps_the_stream_open_when_one_translation_fails(self):
        async def recognize(frames, source, *, timeout):
            await anext(frames)
            yield "첫 문장", True
            yield "둘째 문장", True
            self.assertEqual([chunk async for chunk in frames], [])

        socket = self.connection()
        self.assertTrue((await socket.connect())[0])
        try:
            with mock.patch("apps.translation.consumers.recognize_stream", recognize), \
                    mock.patch("apps.translation.consumers.translate_segment", new_callable=mock.AsyncMock,
                               side_effect=[TranslationProviderError("translation_timeout"), "Second sentence."]):
                await socket.send_json_to({"type": "start", "source": "ko", "target": "en"})
                await socket.receive_json_from()
                await socket.send_to(bytes_data=b"\0" * 6400)
                self.assertEqual((await socket.receive_json_from())["segment"], 0)
                self.assertEqual(await socket.receive_json_from(), {
                    "type": "error", "segment": 0, "code": "translation_timeout",
                })
                self.assertEqual((await socket.receive_json_from())["segment"], 1)
                self.assertEqual((await socket.receive_json_from())["translated_text"], "Second sentence.")
                await socket.send_json_to({"type": "stop"})
                self.assertEqual(await socket.receive_json_from(), {"type": "complete"})
        finally:
            await socket.disconnect()

    async def test_continues_transcripts_while_claude_translates_confirmed_sentences(self):
        first = (
            "현장 출입구에 머리 보호구가 있습니다. 지난주에 설치한 보관함 아래에 있어요. "
            "작업을 시작하기 전에 안내판을 읽고 필요한 장비를 챙겨 주세요."
        )
        second = "안전문을 착용하고 들어오세요. 휴게시간은 30분입니다."
        corrected = "안전모를 착용하고 들어오세요. 휴게시간은 30분입니다."
        release_claude = asyncio.Event()
        messages = []

        async def recognize(frames, source, *, timeout):
            await anext(frames)
            yield first, True
            yield "안전문을", False
            yield second, True
            self.assertEqual([chunk async for chunk in frames], [])

        async def respond(request):
            body = json.loads(request.content)
            message = json.loads(body["messages"][0]["content"])
            messages.append(message)
            await release_claude.wait()
            if message["transcript"] == first:
                await asyncio.sleep(0.1)
                return self.claude_response(
                    first, "Head protection is at the site entrance, below the new lockers. "
                    "Read the notice and collect your equipment before starting work.",
                )
            return self.claude_response(corrected, "Wear a hard hat when entering. The break is 30 minutes.")

        socket = self.connection()
        self.assertTrue((await socket.connect())[0])
        try:
            with (
                override_settings(ANTHROPIC_API_KEY="claude-test"),
                mock.patch("apps.translation.claude.CLAUDE_MIN_TIMEOUT_SECONDS", 0.05),
                mock.patch("apps.translation.consumers.recognize_stream", recognize),
                mock.patch("apps.translation.consumers.AsyncClient", return_value=AsyncClient(transport=MockTransport(respond))),
                mock.patch("apps.translation.consumers.translate_segment", new_callable=mock.AsyncMock) as translate,
            ):
                await socket.send_json_to({"type": "start", "source": "ko", "target": "en"})
                self.assertEqual((await socket.receive_json_from())["type"], "ready")
                await socket.send_to(bytes_data=b"\0" * 6400)
                self.assertEqual((await socket.receive_json_from())["text"], first)
                self.assertFalse((await socket.receive_json_from())["is_final"])
                self.assertEqual((await socket.receive_json_from())["text"], second)
                release_claude.set()
                result = await socket.receive_json_from()
                self.assertEqual((result["segment"], result["corrected_text"]), (0, first))
                result = await socket.receive_json_from()
                self.assertEqual((result["segment"], result["text"], result["corrected_text"]), (1, second, corrected))
                self.assertIn("hard hat", result["translated_text"])
                self.assertEqual([message["transcript"] for message in messages], [first, second])
                self.assertEqual(messages[1]["previous_sentences"], [first])
                self.assertEqual(messages[1]["glossary"]["안전모"], "hard hat")
                translate.assert_not_awaited()
                await socket.send_json_to({"type": "stop"})
                self.assertEqual(await socket.receive_json_from(), {"type": "complete"})
        finally:
            await socket.disconnect()

    async def test_uses_default_translation_when_claude_times_out_or_changes_numbers(self):
        sentences = ["첫 문장입니다.", "휴게시간은 30분입니다."]

        async def recognize(frames, source, *, timeout):
            await anext(frames)
            for sentence in sentences:
                yield sentence, True
            self.assertEqual([chunk async for chunk in frames], [])

        async def respond(request):
            body = json.loads(request.content)
            if json.loads(body["messages"][0]["content"])["transcript"] == sentences[0]:
                await asyncio.Event().wait()
            return self.claude_response("휴게시간은 40분입니다.", "The break is 40 minutes.")

        socket = self.connection()
        self.assertTrue((await socket.connect())[0])
        try:
            with (
                override_settings(ANTHROPIC_API_KEY="claude-test"),
                mock.patch("apps.translation.claude.CLAUDE_MIN_TIMEOUT_SECONDS", 0.05),
                mock.patch("apps.translation.consumers.recognize_stream", recognize),
                mock.patch("apps.translation.consumers.AsyncClient", return_value=AsyncClient(transport=MockTransport(respond))),
                mock.patch("apps.translation.consumers.translate_segment", new_callable=mock.AsyncMock,
                           side_effect=["First sentence.", "The break is 30 minutes."]) as translate,
            ):
                await socket.send_json_to({"type": "start", "source": "ko", "target": "en"})
                await socket.receive_json_from()
                await socket.send_to(bytes_data=b"\0" * 6400)
                self.assertEqual((await socket.receive_json_from())["type"], "transcript")
                self.assertEqual((await socket.receive_json_from())["type"], "transcript")
                self.assertEqual((await socket.receive_json_from())["translated_text"], "First sentence.")
                result = await socket.receive_json_from()
                self.assertEqual(result["translated_text"], "The break is 30 minutes.")
                self.assertNotIn("corrected_text", result)
                self.assertEqual(translate.await_args_list, [mock.call(text, "ko", "en") for text in sentences])
                await socket.send_json_to({"type": "stop"})
                self.assertEqual(await socket.receive_json_from(), {"type": "complete"})
        finally:
            await socket.disconnect()

    @staticmethod
    def claude_response(corrected, translated):
        return Response(200, json={
            "stop_reason": "end_turn",
            "content": [{
                "type": "text",
                "text": json.dumps({"corrected_text": corrected, "translated_text": translated}),
            }],
        })
