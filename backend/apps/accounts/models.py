from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

DEFAULT_TEMPERATURE = 36.5


class User(AbstractUser):
    """근로자 / 사업주(인력사무소 포함)를 구분하는 커스텀 유저."""

    class Role(models.TextChoices):
        WORKER = "worker", "근로자"
        EMPLOYER = "employer", "사업주"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.WORKER)
    name = models.CharField("이름", max_length=50, blank=True)
    nationality = models.CharField("국적", max_length=50, blank=True)
    preferred_language = models.CharField("사용 언어", max_length=10, default="ko")
    phone = models.CharField("전화번호", max_length=20, blank=True)
    visa_type = models.CharField("비자 종류", max_length=20, blank=True, help_text="예: E-9, H-2, F-4")
    region = models.ForeignKey(
        "core.Region", null=True, blank=True, on_delete=models.SET_NULL, related_name="residents"
    )
    profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    notifications_enabled = models.BooleanField("알림 수신", default=True)

    # 평판 ("온도"): 기본 36.5, 평가에 따라 가감
    temperature = models.FloatField(default=DEFAULT_TEMPERATURE)
    review_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username

    @property
    def display_name(self):
        if self.role == self.Role.EMPLOYER and hasattr(self, "company"):
            return self.company.name
        return self.name or self.username


class Company(models.Model):
    """사업주 / 인력사무소 정보 (role=employer 인 유저당 1개)"""

    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company")
    name = models.CharField("상호", max_length=100)
    business_number = models.CharField("사업자등록번호", max_length=10, unique=True, help_text="숫자 10자리")
    representative = models.CharField("대표자", max_length=50)
    address = models.CharField("주소", max_length=200)
    is_agency = models.BooleanField("인력사무소 여부", default=False)
    description = models.TextField(blank=True)
    # 사업자 인증 방식은 팀 협의 후 확정 (현재는 관리자가 수동 승인)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class WorkerProfile(models.Model):
    """근로자 이력 프로필 — AI/규칙 기반 일자리 추천의 입력값"""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="worker_profile")
    experience_years = models.PositiveSmallIntegerField(default=0)
    experience_note = models.CharField(max_length=500, blank=True)
    available_categories = models.ManyToManyField("jobs.JobCategory", blank=True, related_name="+")
    available_weekdays = models.CharField(max_length=20, blank=True, help_text="콤마구분 0=월…6=일, 비우면 모든 요일")
    desired_regions = models.ManyToManyField("core.Region", blank=True, related_name="+")
    can_night_shift = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)


class Verification(models.Model):
    """이메일/전화 인증번호, 비밀번호 재설정 코드"""

    class Channel(models.TextChoices):
        EMAIL = "email", "이메일"
        PHONE = "phone", "전화"
        RESET = "reset", "비밀번호 재설정"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verifications")
    channel = models.CharField(max_length=10, choices=Channel.choices)
    target = models.CharField(max_length=100)
    code = models.CharField(max_length=6)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class SocialAccount(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="social_accounts")
    provider = models.CharField(max_length=20)
    uid = models.CharField(max_length=100)

    class Meta:
        unique_together = ("provider", "uid")
