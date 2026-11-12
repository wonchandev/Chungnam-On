from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """근로자 / 사업주를 구분하는 커스텀 유저. 프로젝트 초기에 확정해야 하므로 미리 생성."""

    class Role(models.TextChoices):
        WORKER = "worker", "근로자"
        EMPLOYER = "employer", "사업주"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.WORKER)
    preferred_language = models.CharField(max_length=10, default="ko")

    def __str__(self):
        return self.username
