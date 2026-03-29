"""
Envio de emails do modulo Financeiro.
"""

import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _get_emails_financeiro():
    """Retorna lista de emails dos usuarios do grupo Financeiro + admins."""
    from apps.accounts.models import Usuario
    emails = set()
    # Admins
    for u in Usuario.objects.filter(is_superuser=True, is_active=True):
        if u.email:
            emails.add(u.email)
    # Grupo Financeiro
    try:
        grupo = Group.objects.get(name="Financeiro")
        for u in grupo.user_set.filter(is_active=True):
            if u.email:
                emails.add(u.email)
    except Group.DoesNotExist:
        pass
    return list(emails)


def enviar_pagamento_recebido(cobranca_asaas):
    """Email quando pagamento e confirmado via Asaas."""
    try:
        html = render_to_string("financeiro/emails/pagamento_recebido.html", {
            "cobranca": cobranca_asaas,
        })
        send_mail(
            subject=f"Pagamento recebido — {cobranca_asaas.cliente.nome} (R$ {cobranca_asaas.valor})",
            message="",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=_get_emails_financeiro(),
            html_message=html,
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Erro ao enviar email pagamento recebido: {e}")


def enviar_cobranca_vencida(cobranca_asaas):
    """Email quando cobranca Asaas vence."""
    try:
        html = render_to_string("financeiro/emails/cobranca_vencida.html", {
            "cobranca": cobranca_asaas,
        })
        send_mail(
            subject=f"Cobranca vencida — {cobranca_asaas.cliente.nome} (R$ {cobranca_asaas.valor})",
            message="",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=_get_emails_financeiro(),
            html_message=html,
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Erro ao enviar email cobranca vencida: {e}")
