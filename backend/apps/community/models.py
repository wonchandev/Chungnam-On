from django.conf import settings
from django.db import models


class Post(models.Model):
    class Category(models.TextChoices):
        LIFE = "life", "생활정보"
        REVIEW = "review", "근무후기"
        JOB_INFO = "job_info", "일자리정보"
        FREE = "free", "자유"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    region = models.ForeignKey("core.Region", null=True, blank=True, on_delete=models.SET_NULL, related_name="posts",
                               help_text="지역 커뮤니티(시군구). 비우면 충남 전체")
    category = models.CharField(max_length=10, choices=Category.choices, default=Category.FREE, db_index=True)
    title = models.CharField(max_length=200)
    body = models.TextField()
    image = models.ImageField(upload_to="community/", null=True, blank=True)
    source_lang = models.CharField(max_length=10, default="ko")
    job = models.ForeignKey("jobs.JobPost", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
                            help_text="근무 후기/일자리 정보가 가리키는 공고")
    is_hidden = models.BooleanField(default=False, help_text="신고 처리 등으로 블라인드")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")

    class Meta:
        unique_together = ("post", "user")


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField(max_length=1000)
    source_lang = models.CharField(max_length=10, default="ko")
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class CompanionPost(models.Model):
    """함께 일하러 갈 동료 모집 (동행)"""

    class Status(models.TextChoices):
        OPEN = "open", "모집중"
        CLOSED = "closed", "마감"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="companion_posts")
    job = models.ForeignKey("jobs.JobPost", null=True, blank=True, on_delete=models.SET_NULL, related_name="companion_posts")
    region = models.ForeignKey("core.Region", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    title = models.CharField(max_length=150)
    body = models.TextField(blank=True)
    source_lang = models.CharField(max_length=10, default="ko")
    meet_place = models.CharField(max_length=150, blank=True)
    meet_at = models.DateTimeField(null=True, blank=True)
    capacity = models.PositiveSmallIntegerField(default=2, help_text="작성자를 제외한 모집 인원")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class CompanionParticipant(models.Model):
    post = models.ForeignKey(CompanionPost, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")
