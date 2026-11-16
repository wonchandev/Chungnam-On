"""Google Cloud 음성 인식·합성 및 Vision REST 호출 (GOOGLE_TRANSLATE_API_KEY 사용).
키가 없거나 호출 실패 시 ServiceError. 테스트는 이 모듈의 함수를 mock 한다."""
import base64
import json
import urllib.parse
import urllib.request

from django.conf import settings

from apps.core.exceptions import ServiceError

SPEECH_LANG = {
    "ko": "ko-KR", "en": "en-US", "vi": "vi-VN", "th": "th-TH", "zh": "cmn-Hans-CN",
    "uz": "uz-UZ", "km": "km-KH", "ne": "ne-NP", "id": "id-ID", "mn": "mn-MN",
}
TTS_LANG = {"ko": "ko-KR", "en": "en-US", "vi": "vi-VN", "th": "th-TH", "zh": "cmn-CN", "id": "id-ID"}
MAX_TTS_BYTES = 5000
TTS_ENDPOINT = "https://texttospeech.googleapis.com/v1/text:synthesize"
MAX_INLINE_AUDIO = 10 * 1024 * 1024  # 동기 인식에 그대로 실어 보낼 수 있는 크기
ENCODINGS = {"WEBM_OPUS": 48000, "OGG_OPUS": 48000, "LINEAR16": 16000, "FLAC": 16000, "MP3": 16000}


def _post(url: str, payload: dict, *, api_key: str | None = None) -> dict:
    key = settings.GOOGLE_TRANSLATE_API_KEY if api_key is None else api_key
    if not key:
        raise ServiceError("google_key_missing", "GOOGLE_TRANSLATE_API_KEY 가 설정되지 않아 사용할 수 없습니다.", 503)
    req = urllib.request.Request(
        f"{url}?key={urllib.parse.quote(key)}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return json.load(res)
    except Exception as e:
        raise ServiceError("google_api_error", "외부 번역 서비스 호출에 실패했습니다.", 502) from e


def speech_to_text(audio: bytes, lang: str, encoding: str = "WEBM_OPUS") -> str:
    """음성(동기, 약 1분/10MB 이내) → 텍스트"""
    data = _post("https://speech.googleapis.com/v1/speech:recognize", {
        "config": {"encoding": encoding, "sampleRateHertz": ENCODINGS.get(encoding, 48000),
                   "languageCode": SPEECH_LANG.get(lang, lang), "enableAutomaticPunctuation": True},
        "audio": {"content": base64.b64encode(audio).decode()},
    })
    return " ".join(r["alternatives"][0]["transcript"].strip() for r in data.get("results", []) if r.get("alternatives"))


def text_to_speech(text: str, language: str) -> bytes:
    """번역문을 Google Cloud Text-to-Speech로 합성해 MP3 바이트를 반환한다."""
    payload = {
        "input": {"text": text},
        "voice": {"languageCode": TTS_LANG[language]},
        "audioConfig": {"audioEncoding": "MP3"},
    }
    if settings.GOOGLE_TTS_USE_ADC:
        data = _synthesize_with_adc(payload)
    else:
        key = settings.GOOGLE_TTS_API_KEY or settings.GOOGLE_TRANSLATE_API_KEY
        if not key:
            raise ServiceError("tts_key_missing", "음성 합성용 Google API 키를 설정해주세요.", 503)
        data = _post(TTS_ENDPOINT, payload, api_key=key)
    try:
        audio = base64.b64decode(data["audioContent"], validate=True)
    except (KeyError, TypeError, ValueError) as error:
        raise ServiceError("tts_invalid_response", "음성 합성 서비스에서 유효한 응답을 받지 못했습니다.", 502) from error
    if not audio:
        raise ServiceError("tts_invalid_response", "음성 합성 서비스에서 빈 음성을 받았습니다.", 502)
    return audio


def _synthesize_with_adc(payload: dict) -> dict:
    from google.auth import default
    from google.auth.exceptions import DefaultCredentialsError, GoogleAuthError
    from google.auth.transport.requests import AuthorizedSession
    from requests.exceptions import RequestException

    try:
        credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        with AuthorizedSession(credentials) as session:
            response = session.post(TTS_ENDPOINT, json=payload, timeout=20)
            response.raise_for_status()
            return response.json()
    except DefaultCredentialsError as error:
        raise ServiceError("tts_credentials_missing", "Google 음성 합성용 기본 인증 정보를 설정해주세요.", 503) from error
    except (GoogleAuthError, RequestException, ValueError) as error:
        raise ServiceError("google_api_error", "Google 음성 합성 서비스 호출에 실패했습니다.", 502) from error


def annotate_image(image: bytes) -> dict:
    """사진 OCR 원본 응답(responses[0]). 글자 영역·좌표가 필요하면 apps.translation.ocr 로 정리한다."""
    data = _post("https://vision.googleapis.com/v1/images:annotate", {
        "requests": [{"image": {"content": base64.b64encode(image).decode()}, "features": [{"type": "TEXT_DETECTION"}]}],
    })
    resp = (data.get("responses") or [{}])[0]
    if resp.get("error"):
        raise ServiceError("google_api_error", "사진 글자 인식에 실패했습니다.", 502)
    return resp


def image_to_text(image: bytes) -> str:
    """사진 속 글자(OCR) 추출"""
    return (annotate_image(image).get("fullTextAnnotation") or {}).get("text", "").strip()
