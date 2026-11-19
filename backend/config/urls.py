from django.contrib import admin
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from django.views.static import serve as static_serve
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView

from apps.accounts.urls import me_urlpatterns


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include(me_urlpatterns)),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.jobs.urls")),
    path("api/", include("apps.chat.urls")),
    path("api/", include("apps.translation.urls")),
    path("api/", include("apps.assistant.urls")),
    path("api/", include("apps.community.urls")),
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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 업로드 파일(media)은 DEBUG 가 아니어도 제공 (소규모 배포용)
if not settings.DEBUG:
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", static_serve, {"document_root": settings.MEDIA_ROOT})]

# 배포 시 React SPA: API/관리자/문서 외의 경로는 index.html 로 (새로고침·딥링크 대응)
_index = settings.FRONTEND_DIST / "index.html"
if _index.exists():
    from django.http import FileResponse

    def spa(request, *args, **kwargs):
        return FileResponse(open(_index, "rb"), content_type="text/html; charset=utf-8")

    urlpatterns += [re_path(r"^(?!api/|admin/|ws/|media/|static/|docs).*$", spa)]
