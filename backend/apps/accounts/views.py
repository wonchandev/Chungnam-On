from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.exceptions import ServiceError

from .models import User
from .serializers import LogoutSerializer, PasswordChangeSerializer, RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """회원가입 (근로자 / 사업주·인력사무소). role=employer 면 `company` 필수."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """내 정보 조회 / 수정 (프로필 이미지는 multipart 로 업로드)"""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    """로그아웃: refresh 토큰을 블랙리스트에 등록"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=LogoutSerializer, responses={204: None})
    def post(self, request):
        ser = LogoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            RefreshToken(ser.validated_data["refresh"]).blacklist()
        except TokenError:
            raise ServiceError("invalid_token", "유효하지 않은 토큰입니다.")
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordChangeView(APIView):
    """비밀번호 변경"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=PasswordChangeSerializer, responses={204: None})
    def patch(self, request):
        ser = PasswordChangeSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        request.user.set_password(ser.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeSummaryView(APIView):
    """마이 화면 요약: 프로필, 온도, 지원/관심/공고 건수"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        from apps.jobs.models import Application, Bookmark, JobPost

        u = request.user
        data = {"profile": UserSerializer(u, context={"request": request}).data,
                "bookmark_count": Bookmark.objects.filter(user=u).count()}
        if u.role == "employer" and hasattr(u, "company"):
            jobs = JobPost.objects.filter(company=u.company)
            data["jobs"] = {
                "open": jobs.open().count(),
                "total": jobs.exclude(status="cancelled").count(),
                "pending_applicants": Application.objects.filter(job__company=u.company, status="pending").count(),
            }
        else:
            apps_ = Application.objects.filter(applicant=u)
            data["applications"] = {s: apps_.filter(status=s).count() for s in ("pending", "approved", "rejected")}
        return Response(data)


class SafeTokenRefreshView(TokenRefreshView):
    """삭제·초기화된 사용자의 refresh 토큰이 오면 500 대신 401 을 반환 (프론트가 토큰을 버리고 재로그인하도록)"""

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except User.DoesNotExist:
            raise InvalidToken("사용자를 찾을 수 없습니다. 다시 로그인해 주세요.")
