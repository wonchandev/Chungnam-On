from django.conf import settings
from django.db import models


class Region(models.Model):
    """행정구역. level: sido(시도) → sigungu(시군구) → eupmyeondong(읍면동)"""

    class Level(models.TextChoices):
        SIDO = "sido", "시도"
        SIGUNGU = "sigungu", "시군구"
        EUPMYEONDONG = "eupmyeondong", "읍면동"

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)
    name_en = models.CharField(max_length=80, blank=True)
    level = models.CharField(max_length=15, choices=Level.choices)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.name


class Notification(models.Model):
    """앱 내 알림 (푸시 발송은 별도). type 예: application, decision, chat, comment, companion, complaint"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=30)
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500, blank=True)
    data = models.JSONField(default=dict, blank=True, help_text="화면 이동용 {job_id, room_id, ...}")
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Report(models.Model):
    """신고: 공고/유저/게시글/댓글/채팅방/메시지"""

    class Target(models.TextChoices):
        JOB = "job", "공고"
        USER = "user", "유저"
        POST = "post", "게시글"
        COMMENT = "comment", "댓글"
        ROOM = "room", "채팅방"
        MESSAGE = "message", "메시지"

    class Reason(models.TextChoices):
        SPAM = "spam", "스팸/광고"
        ABUSE = "abuse", "욕설/비하"
        FRAUD = "fraud", "사기/임금 체불 의심"
        ILLEGAL = "illegal", "불법/위험"
        OTHER = "other", "기타"

    class Status(models.TextChoices):
        OPEN = "open", "접수"
        RESOLVED = "resolved", "처리 완료(블라인드)"
        REJECTED = "rejected", "반려"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports")
    target_type = models.CharField(max_length=10, choices=Target.choices)
    target_id = models.PositiveIntegerField()
    reason = models.CharField(max_length=10, choices=Reason.choices, default=Reason.OTHER)
    detail = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("reporter", "target_type", "target_id")
        ordering = ["-created_at"]


class Block(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocking")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocked_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("blocker", "blocked")
