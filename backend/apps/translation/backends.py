"""번역 엔진 어댑터. 실제 엔진(Papago/Google/DeepL/LLM)이 확정되면 BaseTranslator 를 상속해 추가하고
settings.TRANSLATION_BACKEND (또는 .env 의 TRANSLATION_BACKEND) 에 dotted path 를 지정합니다."""


class BaseTranslator:
    def translate(self, text: str, source: str, target: str) -> str:
        raise NotImplementedError


class EchoTranslator(BaseTranslator):
    """개발/테스트용: 실제로 번역하지 않고 '[대상언어] 원문' 형태로 반환"""

    def translate(self, text: str, source: str, target: str) -> str:
        return f"[{target}] {text}"


class GoogleTranslator(BaseTranslator):
    """Google Cloud Translation API (Basic, v2) — API 키 방식. .env 의 GOOGLE_TRANSLATE_API_KEY 필요."""

    ENDPOINT = "https://translation.googleapis.com/language/translate/v2"
    # 서비스 언어 코드 → 구글 언어 코드 (나머지는 동일)
    CODE_MAP = {"zh": "zh-CN"}
    TIMEOUT = 10

    def __init__(self, api_key: str | None = None):
        from django.conf import settings

        self.api_key = api_key or settings.GOOGLE_TRANSLATE_API_KEY
        if not self.api_key:
            raise RuntimeError("GOOGLE_TRANSLATE_API_KEY 가 설정되지 않았습니다.")

    def translate(self, text: str, source: str, target: str) -> str:
        import json
        import urllib.parse
        import urllib.request

        params = {
            "q": text,
            "target": self.CODE_MAP.get(target, target),
            "format": "text",  # HTML 이스케이프 방지
        }
        if source != "auto":  # auto 는 구글 언어 자동 감지
            params["source"] = self.CODE_MAP.get(source, source)
        body = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(
            f"{self.ENDPOINT}?key={urllib.parse.quote(self.api_key)}", data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=self.TIMEOUT) as res:
            data = json.load(res)
        return data["data"]["translations"][0]["translatedText"]
