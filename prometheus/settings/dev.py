"""
Configurações de desenvolvimento.
Uso: DJANGO_SETTINGS_MODULE=prometheus.settings.dev
"""

from .base import *  # noqa: F401, F403

DEBUG = True

# Em dev, aceita qualquer host
ALLOWED_HOSTS = ["*"]

# CORS permissivo em dev
CORS_ALLOW_ALL_ORIGINS = True

# Email no console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Logging mais detalhado
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
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
        "django.db.backends": {
            "level": "WARNING",
            "handlers": ["console"],
        },
    },
}
