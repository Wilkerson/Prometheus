"""
Configuracoes de producao.
Uso: DJANGO_SETTINGS_MODULE=prometheus.settings.production
"""

from decouple import Csv, config

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())

# Seguranca
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# Database — conexoes persistentes em producao
DATABASES["default"]["CONN_MAX_AGE"] = config("DB_CONN_MAX_AGE", default=600, cast=int)

# Cache com Redis (sessions + cache geral)
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Static files — servidos pelo Nginx/Easypanel, nao pelo Django
STATIC_ROOT = BASE_DIR / "staticfiles"

# Sentry (monitoramento de erros)
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        send_default_pii=False,
    )

# Logging estruturado
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
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
        "django.security": {
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
