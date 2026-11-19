"""AI 챗봇 LLM 호출 (OpenAI). 테스트에서는 이 모듈의 함수를 mock 한다."""
import json
from collections.abc import Callable, Iterator

from django.conf import settings

REFUSAL_TEXT = "죄송합니다. 이 질문에는 답변드릴 수 없습니다. 다른 방식으로 질문해 주세요."
MAX_TOOL_ROUNDS = 3


def llm_available() -> bool:
    return bool(settings.OPENAI_API_KEY)


def _client():
    from openai import OpenAI

    return OpenAI(api_key=settings.OPENAI_API_KEY, timeout=60.0)


def stream_answer(system: str, messages: list[dict], tools: list[dict] | None = None,
                  run_tool: Callable[[str, dict], dict] | None = None) -> Iterator[str]:
    """답변을 스트리밍 (텍스트 조각 yield). tools 가 있으면 함수 호출(최대 3회)을 처리한다."""
    client = _client()
    msgs = [{"role": "system", "content": system}, *messages]
    refused = False
    for _ in range(MAX_TOOL_ROUNDS + 1):
        kw = {"tools": tools} if tools else {}
        stream = client.chat.completions.create(
            model=settings.OPENAI_MODEL, messages=msgs, max_completion_tokens=2048, stream=True, **kw
        )
        calls: dict[int, dict] = {}
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
            if tools:
                for tc in choice.delta.tool_calls or []:
                    c = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                    c["id"] = tc.id or c["id"]
                    if tc.function:
                        c["name"] = tc.function.name or c["name"]
                        c["args"] += tc.function.arguments or ""
        if not calls or not run_tool:
            break
        msgs.append({"role": "assistant", "tool_calls": [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["args"] or "{}"}}
            for c in calls.values()]})
        for c in calls.values():
            try:
                args = json.loads(c["args"] or "{}")
            except ValueError:
                args = {}
            msgs.append({"role": "tool", "tool_call_id": c["id"],
                         "content": json.dumps(run_tool(c["name"], args), ensure_ascii=False, default=str)})
    if refused:
        yield REFUSAL_TEXT


def complete_json(system: str, user: str) -> dict:
    """짧은 JSON 응답 (대화 제목·후속 질문 생성용)"""
    res = _client().chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        max_completion_tokens=300,
        timeout=20.0,
    )
    return json.loads(res.choices[0].message.content or "{}")


def embed(texts: list[str]) -> list[list[float]]:
    res = _client().embeddings.create(model=settings.OPENAI_EMBEDDING_MODEL, input=texts)
    return [d.embedding for d in res.data]
