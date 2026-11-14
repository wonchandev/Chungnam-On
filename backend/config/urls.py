from django.contrib import admin
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
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
