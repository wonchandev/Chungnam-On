"""AI 챗봇 LLM 호출. 테스트에서는 `stream_answer` 를 mock 한다."""
from collections.abc import Iterator

from django.conf import settings

REFUSAL_TEXT = "죄송합니다. 이 질문에는 답변드릴 수 없습니다. 다른 방식으로 질문해 주세요."


def llm_available() -> bool:
    return bool(settings.ANTHROPIC_API_KEY)


def stream_answer(system: str, messages: list[dict]) -> Iterator[str]:
    """Claude 로 답변을 스트리밍 (텍스트 조각 yield). 안전 분류기 거절 시 서버측 fallback 을 켜 둔다."""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=60.0)
    with client.beta.messages.stream(
        model=settings.ASSISTANT_MODEL,
        max_tokens=2048,
        system=system,
        messages=messages,
        output_config={"effort": "low"},  # 단순 안내성 질의응답이라 낮은 effort 로 충분
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    ) as stream:
        for text in stream.text_stream:
            yield text
        final = stream.get_final_message()
        if final.stop_reason == "refusal":
            yield REFUSAL_TEXT
