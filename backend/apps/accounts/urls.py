from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import extra
from .views import LogoutView, MeSummaryView, MeView, PasswordChangeView, RegisterView, SafeTokenRefreshView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", TokenObtainPairView.as_view(), name="auth-login"),
    path("refresh/", SafeTokenRefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("password/", PasswordChangeView.as_view(), name="auth-password"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("withdraw/", extra.WithdrawView.as_view(), name="auth-withdraw"),
    path("verify/request/", extra.VerifyRequestView.as_view(), name="auth-verify-request"),
    path("verify/confirm/", extra.VerifyConfirmView.as_view(), name="auth-verify-confirm"),
    path("password-reset/request/", extra.PasswordResetRequestView.as_view(), name="auth-reset-request"),
    path("password-reset/confirm/", extra.PasswordResetConfirmView.as_view(), name="auth-reset-confirm"),
    path("social/<str:provider>/", extra.SocialLoginView.as_view(), name="auth-social"),
]

# /api/me/summary/ 는 config.urls 에서 연결
me_urlpatterns = [
    path("me/summary/", MeSummaryView.as_view(), name="me-summary"),
    path("me/worker-profile/", extra.WorkerProfileView.as_view(), name="me-worker-profile"),
]
