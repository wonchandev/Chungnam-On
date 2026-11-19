"""행정 가이드 검색: 임베딩 의미 검색(문단 단위) → 실패/미설정 시 키워드 검색"""
import logging
import math
import re

from django.conf import settings

from apps.translation.services import translate_text

from . import llm
from .models import AdminGuide, GuideChunk

logger = logging.getLogger(__name__)
TOP_K = 4
CHUNK_CHARS = 500
RELATIVE_MARGIN = 0.05


def split_chunks(guide: AdminGuide) -> list[str]:
    """본문을 문단 단위로 나눠 ~500자로 묶는다. 각 조각 앞에 제목을 붙여 문맥을 유지."""
    chunks, cur = [], ""
    for para in re.split(r"\n\s*\n|\n(?=[-•■●▶])", guide.body):
        para = para.strip()
        if not para:
            continue
        if cur and len(cur) + len(para) > CHUNK_CHARS:
            chunks.append(cur)
            cur = ""
        cur = f"{cur}\n{para}".strip()
    if cur:
        chunks.append(cur)
    return [f"{guide.title}\n{c}" for c in chunks] or [f"{guide.title}\n{guide.summary}"]


def index_guide(guide: AdminGuide) -> int:
    texts = split_chunks(guide)
    vectors = llm.embed(texts)
    guide.chunks.all().delete()
    GuideChunk.objects.bulk_create([GuideChunk(guide=guide, text=t, embedding=v) for t, v in zip(texts, vectors)])
    return len(texts)


def _cos(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def semantic_search(query: str, k: int = TOP_K) -> list[tuple[AdminGuide, str]]:
    """질의를 임베딩해 유사 문단 상위 k개. 최소 유사도 미만은 제외(재순위화). 다국어 질의도 번역 없이 검색."""
    qv = llm.embed([query])[0]
    chunks = GuideChunk.objects.filter(guide__is_published=True).select_related("guide")
    scored = sorted(((_cos(qv, c.embedding), c) for c in chunks), key=lambda x: -x[0])
    if not scored:
        return []
    floor = max(settings.ASSISTANT_MIN_SCORE, scored[0][0] - RELATIVE_MARGIN)  # 1위와 비슷한 점수만 남김
    return [(c.guide, c.text) for s, c in scored[:k] if s >= floor]


def retrieve(query: str, language: str) -> list[tuple[AdminGuide, str]]:
    from .chatbot import search_guides

    if llm.llm_available() and GuideChunk.objects.exists():
        try:
            return semantic_search(query)
        except Exception:
            logger.warning("semantic search failed, fallback to keyword", exc_info=True)
    query_ko = query
    if language != "ko":
        try:
            query_ko = translate_text(query, language, "ko")
        except Exception:
            logger.warning("query translation failed", exc_info=True)
    return [(g, g.body[:1500]) for g in search_guides(query_ko)]
