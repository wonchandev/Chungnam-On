from django.db import models


class TranslationCache(models.Model):
    """번역 결과 캐시 (같은 원문·언어쌍은 외부 API 를 다시 호출하지 않음)"""

    key = models.CharField(max_length=64, unique=True, help_text="입력, 언어쌍, 엔진, 모델 및 용어집의 SHA-256")
    source_lang = models.CharField(max_length=10)
    target_lang = models.CharField(max_length=10)
    source_text = models.TextField()
    translated_text = models.TextField()
    backend = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source_lang}->{self.target_lang}: {self.source_text[:20]}"


class Phrase(models.Model):
    """근무 현장 필수 표현 (한국어 원문, 요청 언어로 번역해 제공)"""

    class Category(models.TextChoices):
        GREETING = "greeting", "인사·기본"
        WORK = "work", "작업 지시"
        SAFETY = "safety", "안전"
        PAY = "pay", "급여·근무조건"
        EMERGENCY = "emergency", "긴급·건강"
        TOOLS = "tools", "장비·자재"

    category = models.CharField(max_length=15, choices=Category.choices, db_index=True)
    text_ko = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["category", "order", "id"]

    def __str__(self):
        return self.text_ko


class LanguageCourse(models.Model):
    """무료 언어 교육 (다국어 소통 화면 상단 카드)"""

    class Kind(models.TextChoices):
        CLASS = "class", "강의"
        VIDEO_CALL = "video_call", "화상 수업"

    title = models.CharField(max_length=100)
    description = models.CharField(max_length=300, blank=True)
    taught_language = models.CharField(max_length=10, help_text="배우는 언어 (예: ko, en)")
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.CLASS)
    is_free = models.BooleanField(default=True)
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text="비우면 정원 없음")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title


class CourseEnrollment(models.Model):
    course = models.ForeignKey(LanguageCourse, on_delete=models.CASCADE, related_name="enrollments")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="course_enrollments")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "user")
        ordering = ["-created_at"]
