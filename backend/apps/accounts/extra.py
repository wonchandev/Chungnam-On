"""P1 계정 기능: 인증번호(이메일/전화), 비밀번호 재설정, 소셜 로그인, 회원 탈퇴, 근로자 이력 프로필"""
import json
import logging
import random
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.exceptions import ServiceError
from apps.core.models import Region
from apps.jobs.models import JobCategory

from .models import SocialAccount, User, Verification, WorkerProfile

logger = logging.getLogger(__name__)
CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5


# ───────── 인증번호 ─────────
def issue_code(user, channel: str, target: str) -> str:
    """6자리 코드 발급. 이전 미사용 코드는 무효화. 이메일은 발송, 전화는 SMS 사업자 연동 전까지 로그로만 남김."""
    Verification.objects.filter(user=user, channel=channel, used=False).update(used=True)
    code = f"{random.SystemRandom().randint(0, 999999):06d}"
    Verification.objects.create(user=user, channel=channel, target=target, code=code, expires_at=timezone.now() + CODE_TTL)
    if channel in ("email", "reset"):
        send_mail("[충남온] 인증번호", f"인증번호: {code}\n10분 안에 입력해 주세요.", None, [target], fail_silently=True)
    else:
        logger.warning("SMS 발송 미연동 - to=%s code=%s", target, code)  # TODO: SMS 사업자 연동
    return code


def check_code(user, channel: str, target: str, code: str) -> None:
    v = Verification.objects.filter(user=user, channel=channel, target=target, used=False).order_by("-id").first()
    if not v or v.expires_at < timezone.now():
        raise ServiceError("code_expired", "인증번호가 없거나 만료되었습니다. 다시 요청해 주세요.")
    if v.attempts >= MAX_ATTEMPTS:
        raise ServiceError("too_many_attempts", "시도 횟수를 초과했습니다. 인증번호를 다시 요청해 주세요.", 429)
    if v.code != code:
        Verification.objects.filter(pk=v.pk).update(attempts=v.attempts + 1)
        raise ServiceError("code_mismatch", "인증번호가 일치하지 않습니다.")
    Verification.objects.filter(pk=v.pk).update(used=True)


class VerifyRequestSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=["email", "phone"])
    target = serializers.CharField(max_length=100, help_text="이메일 주소 또는 전화번호")


class VerifyConfirmSerializer(VerifyRequestSerializer):
    code = serializers.CharField(max_length=6, min_length=6)


class VerifyRequestView(APIView):
    """인증번호 요청 (로그인 필요). DEBUG 에서는 응답에 `dev_code` 포함."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=VerifyRequestSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        ser = VerifyRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        code = issue_code(request.user, d["channel"], d["target"])
        return Response({"sent": True, "expires_in": int(CODE_TTL.total_seconds()), **({"dev_code": code} if settings.DEBUG else {})})


class VerifyConfirmView(APIView):
    """인증번호 확인 → email_verified / phone_verified 반영"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=VerifyConfirmSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        ser = VerifyConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        check_code(request.user, d["channel"], d["target"], d["code"])
        u = request.user
        if d["channel"] == "email":
            u.email, u.email_verified = d["target"], True
        else:
            u.phone, u.phone_verified = d["target"], True
        u.save(update_fields=["email", "email_verified", "phone", "phone_verified"])
        return Response({"verified": True, "channel": d["channel"]})


# ───────── 비밀번호 재설정 ─────────
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(PasswordResetRequestSerializer):
    code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class PasswordResetRequestView(APIView):
    """비밀번호 재설정 코드 이메일 발송. 계정 존재 여부를 노출하지 않기 위해 항상 200."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(request=PasswordResetRequestSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        ser = PasswordResetRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        out = {"sent": True}
        if user:
            code = issue_code(user, "reset", email)
            if settings.DEBUG:
                out["dev_code"] = code
        return Response(out)


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=PasswordResetConfirmSerializer, responses={204: None})
    def post(self, request):
        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        user = User.objects.filter(email__iexact=d["email"], is_active=True).first()
        if not user:
            raise ServiceError("code_expired", "인증번호가 없거나 만료되었습니다. 다시 요청해 주세요.")
        check_code(user, "reset", d["email"], d["code"])
        user.set_password(d["new_password"])
        user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ───────── 소셜 로그인 ─────────
PROFILE_URLS = {
    "kakao": "https://kapi.kakao.com/v2/user/me",
    "google": "https://www.googleapis.com/oauth2/v3/userinfo",
}


def fetch_social_profile(provider: str, access_token: str) -> dict:
    """provider 액세스 토큰으로 프로필 조회 → {uid, email, name}"""
    req = urllib.request.Request(PROFILE_URLS[provider], headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.load(res)
    except Exception as e:
        raise ServiceError("social_auth_failed", "소셜 로그인 토큰이 올바르지 않습니다.", 401) from e
    if provider == "kakao":
        acc = data.get("kakao_account") or {}
        return {"uid": str(data["id"]), "email": acc.get("email", ""), "name": (data.get("properties") or {}).get("nickname", "")}
    return {"uid": data["sub"], "email": data.get("email", ""), "name": data.get("name", "")}


class SocialLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    preferred_language = serializers.ChoiceField(choices=[(l, l) for l in settings.SUPPORTED_LANGUAGES], required=False)


class SocialLoginView(APIView):
    """소셜 로그인/가입 (근로자 전용). provider: kakao | google. 응답은 일반 로그인과 같은 JWT."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(request=SocialLoginSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request, provider):
        if provider not in PROFILE_URLS:
            raise ServiceError("unsupported_provider", "지원하지 않는 로그인 방식입니다.", 404)
        ser = SocialLoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        prof = fetch_social_profile(provider, ser.validated_data["access_token"])
        acc = SocialAccount.objects.filter(provider=provider, uid=prof["uid"]).select_related("user").first()
        created = False
        if acc:
            user = acc.user
        else:
            user = User(username=f"{provider}_{prof['uid']}", email=prof["email"], name=prof["name"], role=User.Role.WORKER,
                        email_verified=bool(prof["email"]),
                        preferred_language=ser.validated_data.get("preferred_language", "ko"))
            user.set_unusable_password()
            user.save()
            SocialAccount.objects.create(user=user, provider=provider, uid=prof["uid"])
            created = True
        if not user.is_active:
            raise ServiceError("inactive", "탈퇴한 계정입니다.", 403)
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh), "created": created})


# ───────── 회원 탈퇴 ─────────
class WithdrawSerializer(serializers.Serializer):
    password = serializers.CharField(required=False, allow_blank=True, help_text="일반 가입 계정은 필수")


class WithdrawView(APIView):
    """회원 탈퇴: 계정 비활성화 + 개인정보 삭제, 토큰 사용 불가. (작성한 글/공고는 '탈퇴한 사용자'로 남음)"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=WithdrawSerializer, responses={204: None})
    def post(self, request):
        ser = WithdrawSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        u = request.user
        if u.has_usable_password() and not u.check_password(ser.validated_data.get("password", "")):
            raise ServiceError("wrong_password", "비밀번호가 일치하지 않습니다.", 403)
        u.is_active = False
        u.email = u.phone = ""
        u.name = "탈퇴한 사용자"
        u.profile_image = None
        u.set_unusable_password()
        u.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ───────── 근로자 이력 프로필 ─────────
class WorkerProfileSerializer(serializers.ModelSerializer):
    available_categories = serializers.SlugRelatedField(slug_field="code", many=True, queryset=JobCategory.objects.all(), required=False)
    desired_regions = serializers.SlugRelatedField(
        slug_field="code", many=True, queryset=Region.objects.filter(level="sigungu"), required=False
    )

    class Meta:
        model = WorkerProfile
        fields = ("experience_years", "experience_note", "available_categories", "available_weekdays",
                  "desired_regions", "can_night_shift", "updated_at")
        read_only_fields = ("updated_at",)

    def validate_available_weekdays(self, v):
        import re

        if v and not re.fullmatch(r"[0-6](,[0-6])*", v):
            raise serializers.ValidationError("0~6 을 콤마로 구분해 입력하세요. 예: 0,1,2")
        return v


class WorkerProfileView(generics.RetrieveUpdateAPIView):
    """근로자 이력(경력·가능 업종/요일·희망 지역). 일자리 추천에 사용. PUT/PATCH 모두 부분 갱신."""

    serializer_class = WorkerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        if self.request.user.role != User.Role.WORKER:
            raise ServiceError("forbidden", "근로자 계정만 사용할 수 있습니다.", 403)
        return WorkerProfile.objects.get_or_create(user=self.request.user)[0]

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
