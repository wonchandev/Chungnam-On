"""충남온 Django settings. 환경별 값은 .env 로 관리합니다 (.env.example 참고)."""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-only-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "daphne",  # runserver 를 ASGI(WebSocket 지원)로 실행
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "corsheaders",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",
    "channels",
    "rest_framework_simplejwt.token_blacklist",
    # local apps
    "apps.core",
    "apps.chat",
    "apps.accounts",
    "apps.jobs",
    "apps.community",
    "apps.assistant",
    "apps.translation",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "config" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Redis 가 있으면(REDIS_URL) 채널 레이어/캐시를 Redis 로, 없으면 메모리(로컬 개발용)
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# DB: 기본은 SQLite(로컬), DATABASE_URL 이 있으면 PostgreSQL 등으로 전환
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS (프론트엔드 개발 서버 주소를 .env 에 지정)
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "PAGE_SIZE": 20,
}

# 다국어: 서비스가 지원하는 언어 (UI/번역 대상). 기준 언어는 ko.
SUPPORTED_LANGUAGES = ["ko", "en", "vi", "th", "zh", "uz", "km", "ne", "id", "mn"]
DEFAULT_LANGUAGE = "ko"

# 번역 엔진 (apps/translation/backends.py): Google Cloud Translation.
# API 키가 없으면 개발용 EchoTranslator('[언어] 원문')로 동작합니다.
GOOGLE_TRANSLATE_API_KEY = env("GOOGLE_TRANSLATE_API_KEY", default="")
GOOGLE_TTS_API_KEY = env("GOOGLE_TTS_API_KEY", default="")
GOOGLE_TTS_USE_ADC = env.bool("GOOGLE_TTS_USE_ADC", default=False)
TRANSLATION_BACKEND = env(
    "TRANSLATION_BACKEND",
    default="apps.translation.backends.GoogleTranslator"
    if GOOGLE_TRANSLATE_API_KEY
    else "apps.translation.backends.EchoTranslator",
)
TRANSLATION_CACHE_TTL_DAYS = env.int("TRANSLATION_CACHE_TTL_DAYS", default=30)

# AI 행정·생활 챗봇 (OpenAI). 키가 없으면 행정 가이드 검색 기반 간이 답변으로 동작.
# 모델명은 계정에서 사용 가능한 값으로 .env 에서 바꿀 수 있다.
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o-mini")
OPENAI_TRANSLATE_MODEL = env("OPENAI_TRANSLATE_MODEL", default="gpt-4o-mini")

# 실시간 음성 번역의 Claude 문맥 보정
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
ANTHROPIC_VOICE_MODEL = env("ANTHROPIC_VOICE_MODEL", default="claude-haiku-5-5")
ANTHROPIC_WORKSPACE_ID = env("ANTHROPIC_WORKSPACE_ID", default="")

# 이메일(인증번호/비밀번호 재설정): 기본은 콘솔 출력(개발용)
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@chungnamon.local")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=30)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "충남온 API",
    "DESCRIPTION": "충청남도 외국인 일용직 근로자를 위한 구인·구직 및 생활 지원 플랫폼",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "ApplicationStatusEnum": "apps.jobs.models.Application.Status",
        "JobStatusEnum": "apps.jobs.models.JobPost.Status",
        "PayTypeEnum": "apps.jobs.models.JobPost.PayType",
        "LanguageEnum": "apps.translation.serializers.LANGUAGE_CHOICES",
        "SourceLanguageEnum": "apps.translation.serializers.SOURCE_LANGUAGE_CHOICES",
        "ComplaintCategoryEnum": "apps.assistant.models.Complaint.Category",
        "PostCategoryEnum": "apps.community.models.Post.Category",
        "PhraseCategoryEnum": "apps.translation.models.Phrase.Category",
        "GuideCategoryEnum": "apps.assistant.models.AdminGuide.Category",
    },
}
