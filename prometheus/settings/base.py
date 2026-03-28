"""
Configuracoes base do projeto Prometheus — RUCH Solutions.
Compartilhadas entre todos os ambientes.
"""

from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# -----------------------------------------------------------------------------
# Core
# -----------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY")
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())

# -----------------------------------------------------------------------------
# Apps
# -----------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
    "storages",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.crm",
    "apps.integracao",
    "apps.rh",
    "apps.financeiro",
    "apps.web",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------
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

ROOT_URLCONF = "prometheus.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.web.context_processors.navigation",
            ],
        },
    },
]

WSGI_APPLICATION = "prometheus.wsgi.application"

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="prometheus"),
        "USER": config("DB_USER", default="prometheus"),
        "PASSWORD": config("DB_PASSWORD", default="prometheus"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
    }
}

# -----------------------------------------------------------------------------
# Auth
# -----------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------------------------------------------
# Internationalization
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Static & Media
# -----------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

# -----------------------------------------------------------------------------
# Login
# -----------------------------------------------------------------------------
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"

# -----------------------------------------------------------------------------
# Email
# -----------------------------------------------------------------------------
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="RUCH Solutions <noreply@ruch.solutions>")

# -----------------------------------------------------------------------------
# Default PK
# -----------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------------------------------------------------------
# Django REST Framework
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# -----------------------------------------------------------------------------
# Simple JWT
# -----------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# -----------------------------------------------------------------------------
# CORS
# -----------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())

# -----------------------------------------------------------------------------
# Celery
# -----------------------------------------------------------------------------
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "rh-alertas-diarios": {
        "task": "rh.alertas_diarios",
        "schedule": 60 * 60 * 24,  # a cada 24 horas
        "options": {"queue": "default"},
    },
}

# -----------------------------------------------------------------------------
# drf-spectacular (Swagger / OpenAPI)
# -----------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Prometheus API — RUCH Solutions",
    "DESCRIPTION": "API de captação e gestão de clientes",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# -----------------------------------------------------------------------------
# Storage (uploads de arquivos)
# -----------------------------------------------------------------------------
# Providers suportados: "s3" (AWS S3 / Cloudflare R2), "gcs" (Google Cloud), "local"
# Para Cloudflare R2: use provider "s3" com STORAGE_S3_ENDPOINT_URL apontando para R2
STORAGE_PROVIDER = config("STORAGE_PROVIDER", default="local")

if STORAGE_PROVIDER == "s3":
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    AWS_ACCESS_KEY_ID = config("STORAGE_S3_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY = config("STORAGE_S3_SECRET_KEY")
    AWS_STORAGE_BUCKET_NAME = config("STORAGE_S3_BUCKET_NAME")
    AWS_S3_REGION_NAME = config("STORAGE_S3_REGION", default="us-east-1")
    AWS_S3_ENDPOINT_URL = config("STORAGE_S3_ENDPOINT_URL", default="")
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 3600

    if not AWS_S3_ENDPOINT_URL:
        AWS_S3_ENDPOINT_URL = None

elif STORAGE_PROVIDER == "gcs":
    STORAGES = {
        "default": {"BACKEND": "storages.backends.gcloud.GoogleCloudStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    GS_BUCKET_NAME = config("STORAGE_GCS_BUCKET_NAME")
    GS_PROJECT_ID = config("STORAGE_GCS_PROJECT_ID", default="")
    GS_CREDENTIALS_FILE = config("STORAGE_GCS_CREDENTIALS_FILE", default="")
    GS_FILE_OVERWRITE = False
    GS_DEFAULT_ACL = None
    GS_QUERYSTRING_AUTH = True

    if GS_CREDENTIALS_FILE:
        from google.oauth2 import service_account
        GS_CREDENTIALS = service_account.Credentials.from_service_account_file(GS_CREDENTIALS_FILE)

# Se STORAGE_PROVIDER == "local", usa o default do Django (MEDIA_ROOT)
