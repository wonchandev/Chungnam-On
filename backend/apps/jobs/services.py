import math
from datetime import date

from django.utils import timezone

from django.conf import settings
from django.db import transaction
from django.db.models import F

from apps.translation.services import translate_many

from .models import JobPost, JobPostTranslation


def sync_job_translations(job: JobPost):
    """공고(ko 원문)를 지원 언어로 번역해 저장. 번역 실패 언어는 건너뜀."""
    targets = [l for l in settings.SUPPORTED_LANGUAGES if l != "ko"]
    titles = translate_many(job.title, "ko", targets)
    descs = translate_many(job.description, "ko", targets) if job.description else {}
    works = translate_many(job.work_type, "ko", targets) if job.work_type else {}
    for lang, title in titles.items():
        JobPostTranslation.objects.update_or_create(
            job=job, lang=lang,
            defaults=dict(title=title, description=descs.get(lang, ""), work_type=works.get(lang, "")),
        )


def close_expired_jobs() -> int:
    """마감일 또는 근무 종료일이 지난 모집중 공고를 마감 처리. (스케줄러/cron 에서 하루 1회 이상 실행)"""
    today = timezone.localdate()
    from django.db.models import Q

    qs = JobPost.objects.filter(status=JobPost.Status.OPEN).filter(
        Q(deadline__lt=today) | Q(end_date__lt=today) | Q(end_date__isnull=True, start_date__lt=today)
    )
    return qs.update(status=JobPost.Status.CLOSED)


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@transaction.atomic
def apply_review_score(user, score: int):
    """평가 점수(1~5)로 온도 갱신: 3점 기준 ±0.5°씩, 0~99.9 범위"""
    from apps.accounts.models import User

    locked = User.objects.select_for_update().get(pk=user.pk)
    locked.temperature = round(min(99.9, max(0.0, locked.temperature + (score - 3) * 0.5)), 1)
    locked.review_count = F("review_count") + 1
    locked.save(update_fields=["temperature", "review_count"])


def score_job_for_worker(job, user, profile) -> tuple[int, list]:
    """규칙 기반 추천 점수와 사유. profile 은 WorkerProfile 또는 None."""
    score, reasons = 0, []
    region_ids = set()
    cat_ids, weekdays = set(), ""
    if profile:
        region_ids = {r.id for r in profile.desired_regions.all()}
        cat_ids = {c.id for c in profile.available_categories.all()}
        weekdays = profile.available_weekdays
    if user.region_id:
        region_ids.add(user.region_id)
    if job.region_id in region_ids:
        score += 3; reasons.append("희망/거주 지역")
    if job.category_id in cat_ids:
        score += 3; reasons.append("가능한 업종")
    if profile and job.weekdays and weekdays:
        if set(job.weekdays.split(",")) <= set(weekdays.split(",")):
            score += 1; reasons.append("가능한 요일")
    if job.beginner_ok and (not profile or profile.experience_years == 0):
        score += 2; reasons.append("초보 가능")
    if job.night_shift and profile and not profile.can_night_shift:
        score -= 3
    if job.is_urgent:
        score += 1; reasons.append("긴급 채용")
    if job.company.owner.temperature >= 40:
        score += 1; reasons.append("평판 좋은 사업주")
    return score, reasons


def recommend_jobs(user, limit=20):
    """로그인 근로자는 프로필 기반 점수순, 그 외는 최신순. 최근 200건 후보 중 선별."""
    from .serializers import annotate_jobs

    cands = list(annotate_jobs(JobPost.objects.open()).prefetch_related("company__owner")[:200])
    profile = None
    if user.is_authenticated and user.role == "worker":
        from apps.accounts.models import WorkerProfile

        profile = WorkerProfile.objects.filter(user=user).prefetch_related("desired_regions", "available_categories").first()
    for j in cands:
        j.match_score, j.match_reasons = score_job_for_worker(j, user, profile) if user.is_authenticated else (0, [])
    cands.sort(key=lambda j: (-j.match_score, -j.created_at.timestamp()))
    return cands[:limit]
