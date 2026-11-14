"""행정·생활 AI 챗봇: 행정 가이드 검색(RAG) + Claude 답변 + 대화 저장"""
import json
import logging
import re
from collections.abc import Iterator

from django.db.models import Q

from apps.translation.services import translate_text

from . import llm
from .models import AdminGuide, ChatTurn, Conversation

logger = logging.getLogger(__name__)

HISTORY_TURNS = 10
TOP_K = 4

SYSTEM_PROMPT = """You are the assistant of "충남온 (Chungnam-On)", a service for foreign day laborers working in Chungcheongnam-do, Korea.
You help with administrative and daily-life questions: visa and stay, health insurance, labor and wages, and life in Korea.

Rules:
- Answer in the user's language: {language}. Keep answers short, plain and practical, with steps when helpful.
- Base your answer on the "Reference guides" below when they are relevant. If they do not cover the question, say so honestly instead of guessing.
- Never invent laws, fees, deadlines, office names or phone numbers. Rules change, so tell the user to confirm with an official source for anything legal or time-sensitive.
- For visa/stay matters, point to HiKorea (https://www.hikorea.go.kr) and the Korea Immigration Contact Center (1345). For urgent danger or injury, tell them to call 119; for crime, 112.
- You are not a lawyer. Do not give a definitive legal judgment.

Reference guides:
{context}
"""


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[\w가-힣]+", text.lower()) if len(t) >= 2]


def search_guides(query_ko: str, k: int = TOP_K) -> list[AdminGuide]:
    """키워드 점수 기반 간이 검색 (제목 가중치 3, 요약 2, 본문 1)."""
    toks = tokens(query_ko)
    if not toks:
        return []
    q = Q()
    for t in toks:
        q |= Q(title__icontains=t) | Q(summary__icontains=t) | Q(body__icontains=t)
    scored = []
    for g in AdminGuide.objects.filter(is_published=True).filter(q)[:50]:
        score = sum(3 * g.title.lower().count(t) + 2 * g.summary.lower().count(t) + g.body.lower().count(t) for t in toks)
        scored.append((score, g))
    scored.sort(key=lambda x: -x[0])
    return [g for _, g in scored[:k]]


def build_system(language: str, guides: list[AdminGuide]) -> str:
    ctx = "\n\n".join(f"[{g.id}] {g.title}\n{g.body[:1500]}" + (f"\n(source: {g.source_url})" if g.source_url else "") for g in guides)
    return SYSTEM_PROMPT.format(language=language, context=ctx or "(no matching guide found)")


def fallback_answer(guides: list[AdminGuide]) -> str:
    """LLM 키가 없을 때: 검색된 가이드를 그대로 안내"""
    if not guides:
        return "관련 안내를 찾지 못했습니다. 하이코리아(https://www.hikorea.go.kr) 또는 외국인종합안내센터 1345 에 문의해 주세요."
    lines = ["관련 안내를 찾았습니다:"] + [f"• {g.title}: {g.summary or g.body[:100]}" for g in guides]
    return "\n".join(lines)


def prepare(user, message: str, language: str, conversation: Conversation | None):
    """대화 생성/이어가기 + 사용자 메시지 저장 + 검색. (conversation, guides, history) 반환"""
    if conversation is None:
        conversation = Conversation.objects.create(user=user, title=message[:50], language=language)
    history = list(conversation.turns.order_by("-id")[:HISTORY_TURNS])[::-1]
    ChatTurn.objects.create(conversation=conversation, role=ChatTurn.Role.USER, text=message)
    query_ko = message
    if language != "ko":
        try:
            query_ko = translate_text(message, language, "ko")  # 가이드가 한국어이므로 검색용으로 번역
        except Exception:
            logger.warning("query translation failed", exc_info=True)
    guides = search_guides(query_ko)
    msgs = [{"role": t.role, "content": t.text} for t in history] + [{"role": "user", "content": message}]
    return conversation, guides, msgs


def run(user, message: str, language: str, conversation: Conversation | None) -> Iterator[dict]:
    """이벤트 스트림: {"type":"delta","text"} ... {"type":"done", conversation_id, message_id, sources}"""
    conversation, guides, msgs = prepare(user, message, language, conversation)
    sources = [{"id": g.id, "title": g.title} for g in guides]
    parts: list[str] = []
    try:
        if llm.llm_available():
            for piece in llm.stream_answer(build_system(language, guides), msgs):
                parts.append(piece)
                yield {"type": "delta", "text": piece}
        else:
            text = fallback_answer(guides)
            parts.append(text)
            yield {"type": "delta", "text": text}
    except Exception:
        logger.exception("assistant LLM failed")
        err = "죄송합니다. 지금은 답변을 만들 수 없습니다. 잠시 후 다시 시도해 주세요."
        if not parts:
            parts.append(err)
        yield {"type": "error", "message": err}
    answer = "".join(parts)
    turn = ChatTurn.objects.create(conversation=conversation, role=ChatTurn.Role.ASSISTANT, text=answer, sources=sources)
    conversation.save(update_fields=["updated_at"])
    yield {"type": "done", "conversation_id": conversation.id, "message_id": turn.id, "sources": sources}


def sse(events: Iterator[dict]) -> Iterator[str]:
    for e in events:
        yield f"data: {json.dumps(e, ensure_ascii=False)}\n\n"
