from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/", include("apps.accounts.urls")),
    # 앱별 API 는 각 앱의 urls.py 를 만들고 여기에 include 합니다.
    # path("api/jobs/", include("apps.jobs.urls")),
    # API 문서 (Scalar)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs",
        TemplateView.as_view(
            template_name="scalar.html", extra_context={"schema_url": "/api/schema/"}
        ),
        name="docs",
    ),
]
