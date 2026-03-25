"""
Configurações para testes.
Uso: DJANGO_SETTINGS_MODULE=prometheus.settings.test
"""

from .dev import *  # noqa: F401, F403

# SQLite em memória para testes rápidos sem depender de PostgreSQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Desabilita password hashers pesados para testes mais rápidos
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Celery síncrono nos testes
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
