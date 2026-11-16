import asyncio
import json
import logging
from collections import deque
from contextlib import aclosing, suppress

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from httpx2 import AsyncClient

from apps.core.exceptions import ServiceError

from .audio import BYTES_PER_SECOND
from .claude import translate_voice_segment
from .google import SPEECH_LANG
from .services import translate_text
from .streaming import recognize_stream

logger = logging.getLogger(__name__)
MAX_AUDIO_SECONDS = 280
MAX_SESSION_SECONDS = 290
MAX_FRAME_BYTES = BYTES_PER_SECOND // 2
MAX_QUEUED_FRAMES = 32
MAX_QUEUED_SEGMENTS = 32
translate_segment = database_sync_to_async(translate_text, thread_sensitive=False)


class VoiceTranslationConsumer(AsyncWebsocketConsumer):
    """JWT 인증 후 16kHz 모노 PCM16-LE 프레임을 받고 문장별 인식·번역 이벤트를 보낸다."""

    async def connect(self):
        self.stream_task = None
        if not self.scope["user"].is_authenticated:
            await self.close(code=4401)
            return
        # 마지막 한 자리는 종료 신호에 남겨둔다.
        self.frames = asyncio.Queue(maxsize=MAX_QUEUED_FRAMES + 1)
        self.audio_bytes = 0
        self.input_closed = False
        await self.accept()

    async def disconnect(self, close_code):
        if self.stream_task is not None:
            self.stream_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.stream_task

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data is not None:
            await self.receive_audio(bytes_data)
            return
        try:
            message = json.loads(text_data)
        except (TypeError, ValueError):
            message = None
        if not isinstance(message, dict):
            await self.send_event(type="error", code="invalid_voice_message")
            return
        if message.get("type") == "start":
            await self.start_stream(message.get("source"), message.get("target"))
        elif message.get("type") == "stop" and self.stream_task is not None:
            self.close_audio_input()
        else:
            await self.send_event(type="error", code="invalid_voice_message")

    async def start_stream(self, source, target):
        if self.stream_task is not None:
            await self.send_event(type="error", code="voice_already_started")
        elif (
            source not in settings.SUPPORTED_LANGUAGES
            or source not in SPEECH_LANG
            or target not in settings.SUPPORTED_LANGUAGES
        ):
            await self.send_event(type="error", code="invalid_voice_languages")
        elif not settings.GOOGLE_TRANSLATE_API_KEY:
            await self.send_event(type="error", code="google_key_missing")
            await self.close(code=1011)
        else:
            await self.send_event(type="ready", max_frame_bytes=MAX_FRAME_BYTES, max_audio_seconds=MAX_AUDIO_SECONDS)
            self.stream_task = asyncio.create_task(self.run_stream(source, target))

    async def receive_audio(self, frame):
        if self.stream_task is None or self.input_closed:
            await self.send_event(type="error", code="voice_stream_not_accepting_audio")
        elif not frame or len(frame) > MAX_FRAME_BYTES or len(frame) % 2:
            await self.send_event(type="error", code="invalid_audio_chunk")
        elif self.audio_bytes + len(frame) > MAX_AUDIO_SECONDS * BYTES_PER_SECOND:
            await self.send_event(type="error", code="voice_stream_limit")
            self.close_audio_input()
        elif self.frames.qsize() >= MAX_QUEUED_FRAMES:
            await self.send_event(type="error", code="voice_stream_busy")
            self.close_audio_input()
        else:
            self.audio_bytes += len(frame)
            self.frames.put_nowait(frame)

    def close_audio_input(self):
        if not self.input_closed:
            self.input_closed = True
            self.frames.put_nowait(None)

    async def audio_frames(self, first):
        frame = first
        while frame is not None:
            yield frame
            frame = await self.frames.get()

    async def run_stream(self, source, target):
        try:
            first = await asyncio.wait_for(self.frames.get(), timeout=10)
            if first is not None:
                recognitions = recognize_stream(self.audio_frames(first), source, timeout=MAX_SESSION_SECONDS)
                async with asyncio.timeout(MAX_SESSION_SECONDS), aclosing(recognitions):
                    await self.send_stream_results(recognitions, source, target)
            await self.send_event(type="complete")
        except TimeoutError:
            await self.send_event(type="error", code="voice_stream_timeout")
        except ServiceError as error:
            await self.send_event(type="error", code=error.get_codes())
        except Exception as error:
            logger.error("Voice stream failed (%s)", type(error).__name__)
            await self.send_event(type="error", code="speech_stream_error")
        self.input_closed = True
        await self.close()

    async def send_stream_results(self, recognitions, source, target):
        if not settings.ANTHROPIC_API_KEY or source == target:
            await self.send_transcripts(recognitions, source, target)
            return

        pending = asyncio.Queue(maxsize=MAX_QUEUED_SEGMENTS)
        transcripts = asyncio.create_task(self.send_transcripts(recognitions, source, target, pending))
        translations = asyncio.create_task(self.send_claude_translations(pending, source, target))
        try:
            await asyncio.gather(transcripts, translations)
        finally:
            transcripts.cancel()
            translations.cancel()
            await asyncio.gather(transcripts, translations, return_exceptions=True)

    async def send_transcripts(self, recognitions, source, target, pending=None):
        segment = 0
        async for text, is_final in recognitions:
            await self.send_event(type="transcript", segment=segment, text=text, is_final=is_final)
            if is_final:
                if pending is None:
                    await self.send_translation(segment, text, source, target)
                else:
                    await pending.put((segment, text))
                segment += 1
        if pending is not None:
            await pending.put(None)

    async def send_claude_translations(self, pending, source, target):
        previous = deque(maxlen=2)
        async with AsyncClient() as client:
            while (item := await pending.get()) is not None:
                segment, text = item
                result = await translate_voice_segment(client, text, source, target, tuple(previous))
                previous.append(text)
                await self.send_translation(segment, text, source, target, claude_result=result)

    async def send_translation(self, segment, text, source, target, *, claude_result=None):
        event = {"type": "translation", "segment": segment, "text": text, "source": source, "target": target}
        if claude_result is None:
            try:
                translated = await translate_segment(text, source, target)
            except ServiceError as error:
                await self.send_event(type="error", segment=segment, code=error.get_codes())
                return
        else:
            event["corrected_text"], translated = claude_result
        await self.send_event(**event, translated_text=translated)

    async def send_event(self, **event):
        await self.send(text_data=json.dumps(event, ensure_ascii=False))
