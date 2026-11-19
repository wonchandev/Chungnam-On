from datetime import date

from django.utils import timezone

from django.conf import settings
from django.db import models
from django.db.models import Q


class JobCategory(models.Model):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=30)
    name_en = models.CharField(max_length=50, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name_plural = "job categories"

    def __str__(self):
        return self.name


class JobPostQuerySet(models.QuerySet):
    def open(self):
        """모집중 + 마감일(없으면 무제한) 미경과"""
        today = timezone.localdate()
        return self.filter(status=JobPost.Status.OPEN, is_hidden=False).filter(Q(deadline__isnull=True) | Q(deadline__gte=today))


class JobPost(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "모집중"
        CLOSED = "closed", "마감"
        CANCELLED = "cancelled", "취소"

    class PayType(models.TextChoices):
        HOURLY = "hourly", "시급"
        DAILY = "daily", "일급"

    company = models.ForeignKey("accounts.Company", on_delete=models.CASCADE, related_name="jobs")
    category = models.ForeignKey(JobCategory, on_delete=models.PROTECT, related_name="jobs")
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    work_type = models.CharField("직무", max_length=100, blank=True, help_text="예: 현장 보조, 자재 운반")
    image = models.ImageField(upload_to="jobs/", null=True, blank=True)

    pay_type = models.CharField(max_length=10, choices=PayType.choices, default=PayType.DAILY)
    pay_amount = models.PositiveIntegerField(help_text="원 단위 정수 (예: 일급 300000)")

    # 근무지
    region = models.ForeignKey("core.Region", on_delete=models.PROTECT, related_name="jobs", help_text="시군구")
    address = models.CharField(max_length=200, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)

    # 근무 일정
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="비우면 start_date 하루만 근무")
    duration_days = models.PositiveIntegerField(default=1, editable=False)
    weekdays = models.CharField(
        max_length=20, blank=True, help_text="근무 요일 콤마구분 (0=월 … 6=일), 비우면 매일. 예: 0,1,2,3,4"
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.PositiveSmallIntegerField(default=60)

    headcount = models.PositiveSmallIntegerField("모집 인원", default=1)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    is_urgent = models.BooleanField("긴급/1일 급구", default=False)
    is_hidden = models.BooleanField(default=False, help_text="신고 처리 등으로 블라인드")

    # 탐색 태그
    beginner_ok = models.BooleanField("초보가능", default=False)
    with_friend = models.BooleanField("친구와 함께", default=False)
    lunch_provided = models.BooleanField("점심 제공", default=False)
    local_preferred = models.BooleanField("인근지역우대", default=False)
    night_shift = models.BooleanField("야간근무", default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = JobPostQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["lat", "lng"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        end = self.end_date or self.start_date
        self.duration_days = (end - self.start_date).days + 1
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        return self.status == self.Status.OPEN and (self.deadline is None or self.deadline >= timezone.localdate())


class JobPostTranslation(models.Model):
    """공고 제목/설명의 자동 번역본 (원문은 ko 로 간주)"""

    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="translations")
    lang = models.CharField(max_length=10)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    work_type = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("job", "lang")


class JobTranslationTask(models.Model):
    job = models.OneToOneField(JobPost, on_delete=models.CASCADE, related_name="translation_task")
    queued_at = models.DateTimeField(auto_now=True, db_index=True)
    claim_id = models.UUIDField(null=True)
    lease_until = models.DateTimeField(null=True)
    failed = models.BooleanField(default=False)
    retry_count = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(null=True, db_index=True)
    retry_languages = models.JSONField(null=True)


class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "대기"
        APPROVED = "approved", "승인"
        REJECTED = "rejected", "거절"

    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    message = models.CharField("지원 메시지", max_length=500, blank=True)
    checked_in_at = models.DateTimeField("출근 확인", null=True, blank=True)
    completed_at = models.DateTimeField("근무 완료", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("job", "applicant")
        ordering = ["-created_at"]


class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks")
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "job")
        ordering = ["-created_at"]


class Review(models.Model):
    """근무 후 상호 평가. 점수로 대상 유저의 '온도'를 갱신한다."""

    TAG_CHOICES = [
        ("punctual", "시간 약속을 잘 지켜요"),
        ("pay_accurate", "급여가 정확해요"),
        ("kind", "친절해요"),
        ("hardworking", "성실해요"),
        ("clear_instructions", "업무 지시가 명확해요"),
        ("safe", "안전하게 일할 수 있어요"),
    ]

    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_written")
    reviewee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_received")
    score = models.PositiveSmallIntegerField(help_text="1~5")
    tags = models.JSONField(default=list, blank=True)
    comment = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("job", "reviewer", "reviewee")
        ordering = ["-created_at"]


class RecentView(models.Model):
    """최근 본 공고 (유저당 공고 1행, 다시 보면 시간 갱신)"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recent_views")
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="+")
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "job")
        ordering = ["-viewed_at"]


class SearchLog(models.Model):
    """공고 검색어 로그 (인기 검색어 집계)"""

    q = models.CharField(max_length=100, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
