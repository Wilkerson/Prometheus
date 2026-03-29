"""
Envio de emails do modulo CRM/Comercial.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _get_emails_admins():
    """Retorna emails dos admins."""
    from apps.accounts.models import Usuario
    return list(
        Usuario.objects.filter(is_superuser=True, is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )


def enviar_cliente_novo(cliente):
    """Email quando novo cliente e cadastrado."""
    try:
        html = render_to_string("crm/emails/cliente_novo.html", {"cliente": cliente})
        send_mail(
            subject=f"Novo cliente cadastrado — {cliente.nome}",
            message="",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=_get_emails_admins(),
            html_message=html,
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Erro ao enviar email cliente novo: {e}")
