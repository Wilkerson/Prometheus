"""
Configurações para testes.
Uso: DJANGO_SETTINGS_MODULE=prometheus.settings.test
"""

from .dev import *  # noqa: F401, F403

# Desabilita password hashers pesados para testes mais rápidos
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Celery síncrono nos testes
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
