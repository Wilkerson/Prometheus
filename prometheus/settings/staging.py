"""
Configuracoes de staging — deploy na nuvem com dados de teste.
Uso: DJANGO_SETTINGS_MODULE=prometheus.settings.staging

Staging simula producao mas com:
- Fixtures carregadas (reset_dev)
- Asaas sandbox
- Email no console (ou SMTP de teste)
- Dominio: staging.ruch.solutions
- Debug=False (testa como producao)
"""

from decouple import Csv, config

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="staging.ruch.solutions,localhost", cast=Csv())

# Seguranca — mesma de producao
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://staging.ruch.solutions",
    cast=Csv(),
)

# Database — banco separado (prometheus_staging)
DATABASES["default"]["CONN_MAX_AGE"] = config("DB_CONN_MAX_AGE", default=60, cast=int)

# Cache com Redis
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Static files
STATIC_ROOT = BASE_DIR / "staticfiles"

# Email — console em staging (troca pra SMTP de teste se quiser)
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

# Asaas — sempre sandbox em staging
ASAAS_BASE_URL = config("ASAAS_BASE_URL", default="https://api-sandbox.asaas.com/v3")

# Banner de staging — pra ninguem confundir com producao
STAGING = True

# Sentry (opcional pra staging)
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        environment="staging",
    )

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
        "apps": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}
