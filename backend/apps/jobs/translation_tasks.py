import logging
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from apps.translation.errors import TranslationProviderError
from apps.translation.services import translate_batch

from .models import JobPost, JobPostTranslation, JobTranslationTask

logger = logging.getLogger(__name__)
TRANSLATED_FIELDS = ("title", "description", "work_type")
LEASE_DURATION = timedelta(minutes=20)
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 30
PENDING_TASK_FIELDS = {
    "claim_id": None, "lease_until": None, "failed": False,
    "retry_count": 0, "available_at": None, "retry_languages": None,
}


def queue_job_translation(job: JobPost) -> None:
    """공고를 저장하는 트랜잭션에서 호출해 이전 번역과 진행 중인 작업을 무효화한다."""
    JobTranslationTask.objects.update_or_create(job=job, defaults=PENDING_TASK_FIELDS)
    JobPostTranslation.objects.filter(job=job).delete()


def requeue_failed_translations() -> int:
    """실패한 작업을 다시 등록한다. 이미 번역된 언어는 유지한다."""
    return JobTranslationTask.objects.filter(failed=True).update(queued_at=timezone.now(), **PENDING_TASK_FIELDS)


def translate_next_job() -> bool:
    """번역 작업 한 건을 처리한다. 처리할 작업이 없을 때만 False 를 반환한다."""
    now = timezone.now()
    available = JobTranslationTask.objects.filter(failed=False).filter(
        Q(lease_until__isnull=True) | Q(lease_until__lte=now),
        Q(available_at__isnull=True) | Q(available_at__lte=now),
    )
    task_id = available.order_by("queued_at", "pk").values_list("pk", flat=True).first()
    if task_id is None:
        return False

    claim_id = uuid4()
    claimed = available.filter(pk=task_id).update(claim_id=claim_id, lease_until=now + LEASE_DURATION)
    if not claimed:
        return True

    owned = JobTranslationTask.objects.filter(pk=task_id, claim_id=claim_id)
    task = owned.select_related("job").first()
    if task is None:
        return True

    texts = [getattr(task.job, field) for field in TRANSLATED_FIELDS]
    targets = [language for language in settings.SUPPORTED_LANGUAGES if language != "ko"]
    completed = set(task.job.translations.values_list("lang", flat=True))
    languages = [language for language in targets if language not in completed]
    if task.retry_languages is not None:
        languages = [language for language in languages if language in task.retry_languages]

    rows = []
    retry_languages = []
    retry_after = 0
    for index, language in enumerate(languages):
        try:
            values = translate_batch(texts, "ko", language)
        except TranslationProviderError as error:
            code = error.get_codes()
            logger.warning("Job %s translation to %s failed (%s)", task.job_id, language, code)
            if code == "translation_quota_exhausted":
                retry_languages.clear()
                break
            if error.retryable:
                retry_after = max(retry_after, error.wait or 0)
                if code == "translation_rate_limited" or error.wait:
                    retry_languages.extend(languages[index:])
                    break
                retry_languages.append(language)
            continue
        except Exception as error:
            logger.warning("Job %s translation to %s failed (%s)", task.job_id, language, type(error).__name__)
            continue
        title, description, work_type = values
        completed.add(language)
        rows.append(JobPostTranslation(
            job_id=task.job_id, lang=language, title=title[:300], description=description, work_type=work_type[:200],
        ))

    with transaction.atomic():
        # PostgreSQL 에서 공고를 먼저 잠가 공고 수정과 같은 순서로 잠금을 획득한다.
        # SQLite 는 첫 UPDATE/DELETE 에서 쓰기 잠금을 획득한다.
        if connection.features.has_select_for_update:
            JobPost.objects.select_for_update().filter(pk=task.job_id).first()
        if retry_languages and task.retry_count < MAX_RETRIES:
            delay = max(retry_after, RETRY_DELAY_SECONDS * 2 ** task.retry_count)
            owns_current_task = owned.update(
                claim_id=None, lease_until=None, retry_count=task.retry_count + 1,
                available_at=timezone.now() + timedelta(seconds=delay), retry_languages=retry_languages,
            )
        elif set(targets) - completed:
            owns_current_task = owned.update(
                failed=True, claim_id=None, lease_until=None, available_at=None, retry_languages=None,
            )
        else:
            owns_current_task, _ = owned.delete()
        if owns_current_task:
            JobPostTranslation.objects.bulk_create(
                rows, update_conflicts=True, unique_fields=["job", "lang"], update_fields=TRANSLATED_FIELDS,
            )
    return True
