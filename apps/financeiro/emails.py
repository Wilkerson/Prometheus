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


def enviar_cobranca_cancelada(cobranca_asaas):
    """Email quando cobranca e cancelada/estornada."""
    try:
        html = render_to_string("financeiro/emails/cobranca_cancelada.html", {
            "cobranca": cobranca_asaas,
        })
        send_mail(
            subject=f"Cobranca cancelada — {cobranca_asaas.cliente.nome} (R$ {cobranca_asaas.valor})",
            message="",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=_get_emails_financeiro(),
            html_message=html,
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Erro ao enviar email cobranca cancelada: {e}")


def enviar_folha_gerada(competencia, total):
    """Email quando folha e gerada automaticamente."""
    try:
        html = render_to_string("financeiro/emails/folha_pronta.html", {
            "titulo": "Folha de pagamento gerada",
            "mensagem": f"A folha de pagamento foi gerada automaticamente pelo sistema.",
            "competencia": competencia.strftime("%m/%Y"),
            "total": total,
        })
        send_mail(
            subject=f"Folha gerada — {competencia:%m/%Y} ({total} registros)",
            message="",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=_get_emails_financeiro(),
            html_message=html,
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Erro ao enviar email folha gerada: {e}")


def enviar_folha_aprovada(competencia):
    """Email quando todas as folhas sao aprovadas."""
    try:
        html = render_to_string("financeiro/emails/folha_pronta.html", {
            "titulo": "Folha aprovada",
            "mensagem": "Todas as folhas foram aprovadas e estao prontas para exportacao.",
            "competencia": competencia.strftime("%m/%Y"),
        })
        send_mail(
            subject=f"Folha aprovada — {competencia:%m/%Y}",
            message="",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=_get_emails_financeiro(),
            html_message=html,
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Erro ao enviar email folha aprovada: {e}")
