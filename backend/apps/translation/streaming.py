"""Google Speech-to-Text에 실시간 PCM 프레임을 보내 인식 결과를 받는다."""

from collections.abc import AsyncIterator

from django.conf import settings
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import speech_v1

from apps.core.exceptions import ServiceError

from .audio import SAMPLE_RATE
from .errors import classify_http_error
from .google import SPEECH_LANG


async def recognize_stream(
    frames: AsyncIterator[bytes], source: str, *, timeout: int,
) -> AsyncIterator[tuple[str, bool]]:
    key = settings.GOOGLE_TRANSLATE_API_KEY
    if not key:
        raise ServiceError("google_key_missing", "음성 인식용 Google API 키를 설정해주세요.", 503)
    config = speech_v1.StreamingRecognitionConfig(
        config=speech_v1.RecognitionConfig(
            encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SAMPLE_RATE,
            language_code=SPEECH_LANG[source],
            enable_automatic_punctuation=True,
        ),
        interim_results=True,
    )

    async def requests():
        yield speech_v1.StreamingRecognizeRequest(streaming_config=config)
        async for frame in frames:
            yield speech_v1.StreamingRecognizeRequest(audio_content=frame)

    try:
        async with speech_v1.SpeechAsyncClient(client_options=ClientOptions(api_key=key)) as client:
            responses = await client.streaming_recognize(requests=requests(), retry=None, timeout=timeout)
            async for response in responses:
                if response.error.code:
                    raise ServiceError("speech_stream_error", "실시간 음성 인식에 실패했습니다.", 502)
                for result in response.results:
                    if result.alternatives:
                        text = result.alternatives[0].transcript.strip()
                        if text:
                            yield text, result.is_final
    except GoogleAPICallError as error:
        raise classify_http_error(error.code or 502, (error.reason,), None) from error
