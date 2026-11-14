from django.db import models


class AdminGuide(models.Model):
    """행정 정보 콘텐츠 (비자·체류, 건강보험, 근로계약 등). 원문은 한국어, 다국어 본문은 AdminGuideTranslation."""

    class Category(models.TextChoices):
        VISA = "visa", "비자·체류"
        INSURANCE = "insurance", "건강보험"
        LABOR = "labor", "근로·계약"
        TAX = "tax", "세금·연금"
        LIFE = "life", "생활 정보"
        ETC = "etc", "기타"

    category = models.CharField(max_length=15, choices=Category.choices, default=Category.ETC, db_index=True)
    title = models.CharField(max_length=200)
    summary = models.CharField(max_length=300, blank=True)
    body = models.TextField()
    source_url = models.URLField(blank=True, help_text="공식 출처 (예: 하이코리아)")
    is_published = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class AdminGuideTranslation(models.Model):
    guide = models.ForeignKey(AdminGuide, on_delete=models.CASCADE, related_name="translations")
    lang = models.CharField(max_length=10)
    title = models.CharField(max_length=300)
    summary = models.CharField(max_length=500, blank=True)
    body = models.TextField()

    class Meta:
        unique_together = ("guide", "lang")


class GuideView(models.Model):
    """조회 로그 (최근 인기 집계용)"""

    guide = models.ForeignKey(AdminGuide, on_delete=models.CASCADE, related_name="views")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class Complaint(models.Model):
    """민원 접수. 관리자가 Django admin 에서 답변/상태를 바꾸면 접수자에게 알림이 간다."""

    class Category(models.TextChoices):
        VISA = "visa", "비자·체류"
        LABOR = "labor", "근로·계약"
        WAGE = "wage", "임금 체불·급여"
        INSURANCE = "insurance", "건강보험·산재"
        LIFE = "life", "생활"
        ETC = "etc", "기타"

    class Status(models.TextChoices):
        RECEIVED = "received", "접수"
        IN_PROGRESS = "in_progress", "처리중"
        RESOLVED = "resolved", "답변 완료"

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="complaints")
    category = models.CharField(max_length=15, choices=Category.choices, default=Category.ETC)
    title = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.RECEIVED, db_index=True)
    answer = models.TextField(blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Conversation(models.Model):
    """AI 챗봇 대화"""

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="assistant_conversations")
    title = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=10, default="ko")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class ChatTurn(models.Model):
    class Role(models.TextChoices):
        USER = "user", "사용자"
        ASSISTANT = "assistant", "챗봇"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="turns")
    role = models.CharField(max_length=10, choices=Role.choices)
    text = models.TextField()
    sources = models.JSONField(default=list, blank=True, help_text="참고한 행정 가이드 [{id,title}]")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
