"""AI 챗봇 LLM 호출 (OpenAI Chat Completions). 테스트에서는 `stream_answer` 를 mock 한다."""
from collections.abc import Iterator

from django.conf import settings

REFUSAL_TEXT = "죄송합니다. 이 질문에는 답변드릴 수 없습니다. 다른 방식으로 질문해 주세요."


def llm_available() -> bool:
    return bool(settings.OPENAI_API_KEY)


def stream_answer(system: str, messages: list[dict]) -> Iterator[str]:
    """OpenAI 로 답변을 스트리밍 (텍스트 조각 yield)."""
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=60.0)
    stream = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "system", "content": system}, *messages],
        max_completion_tokens=2048,
        stream=True,
    )
    refused = False
    for chunk in stream:
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        if choice.delta.content:
            yield choice.delta.content
        if getattr(choice.delta, "refusal", None):
            refused = True
        if choice.finish_reason == "content_filter":
            refused = True
    if refused:
        yield REFUSAL_TEXT
