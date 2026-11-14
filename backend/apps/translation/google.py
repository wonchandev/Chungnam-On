"""Google Cloud Speech-to-Text / Vision(OCR) REST 호출 (API 키 방식, 번역과 같은 GOOGLE_TRANSLATE_API_KEY 사용).
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
ENCODINGS = {"WEBM_OPUS": 48000, "OGG_OPUS": 48000, "LINEAR16": 16000, "FLAC": 16000, "MP3": 16000}


def _post(url: str, payload: dict) -> dict:
    key = settings.GOOGLE_TRANSLATE_API_KEY
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


def image_to_text(image: bytes) -> str:
    """사진 속 글자(OCR) 추출"""
    data = _post("https://vision.googleapis.com/v1/images:annotate", {
        "requests": [{"image": {"content": base64.b64encode(image).decode()}, "features": [{"type": "TEXT_DETECTION"}]}],
    })
    resp = (data.get("responses") or [{}])[0]
    return (resp.get("fullTextAnnotation") or {}).get("text", "").strip()
