"""
Processamento de eventos do webhook Asaas.
Cada evento atualiza CobrancaAsaas + Lancamento no modulo principal.
"""

import logging
from decimal import Decimal

from django.utils import timezone

from apps.financeiro.models import (
    CategoriaFinanceira, CobrancaAsaas, ContaBancaria, EventoWebhookAsaas,
    Lancamento,
)

logger = logging.getLogger(__name__)


def processar_evento(evento_id):
    """Processa um evento do webhook Asaas (chamado via Celery)."""
    try:
        evento = EventoWebhookAsaas.objects.get(pk=evento_id)
    except EventoWebhookAsaas.DoesNotExist:
        logger.error(f"Evento {evento_id} nao encontrado")
        return

    if evento.processado:
        return

    try:
        payload = evento.payload
        event_type = evento.evento
        payment = payload.get("payment", {})

        if event_type in ("PAYMENT_CREATED",):
            _processar_payment_created(payment)

        elif event_type in ("PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"):
            _processar_payment_received(payment)

        elif event_type == "PAYMENT_OVERDUE":
            _processar_payment_overdue(payment)

        elif event_type in ("PAYMENT_REFUNDED", "PAYMENT_DELETED"):
            _processar_payment_cancelled(payment)

        evento.processado = True
        evento.save(update_fields=["processado"])

    except Exception as e:
        logger.error(f"Erro ao processar evento {evento_id}: {e}")
        evento.erro = str(e)
        evento.save(update_fields=["erro"])


def _get_or_create_cobranca(payment):
    """Busca ou cria CobrancaAsaas a partir do payload."""
    asaas_id = payment.get("id", "")
    cobranca, created = CobrancaAsaas.objects.get_or_create(
        asaas_id=asaas_id,
        defaults={
            "cliente_id": _resolve_cliente(payment),
            "tipo": "mensalidade" if payment.get("subscription") else "avulsa",
            "valor": Decimal(str(payment.get("value", 0))),
            "valor_liquido": Decimal(str(payment.get("netValue", 0) or 0)),
            "vencimento": payment.get("dueDate", ""),
            "status": payment.get("status", ""),
            "billing_type": payment.get("billingType", ""),
            "invoice_url": payment.get("invoiceUrl", ""),
            "bank_slip_url": payment.get("bankSlipUrl", ""),
        },
    )
    if not created:
        cobranca.status = payment.get("status", cobranca.status)
        cobranca.valor_liquido = Decimal(str(payment.get("netValue", 0) or 0))
        cobranca.billing_type = payment.get("billingType", cobranca.billing_type)
        cobranca.invoice_url = payment.get("invoiceUrl", cobranca.invoice_url)
        cobranca.bank_slip_url = payment.get("bankSlipUrl", cobranca.bank_slip_url)
        cobranca.save()
    return cobranca


def _resolve_cliente(payment):
    """Resolve o ID do cliente do CRM a partir do payload Asaas."""
    from apps.financeiro.models import ClienteAsaas
    customer_id = payment.get("customer", "")
    try:
        return ClienteAsaas.objects.get(asaas_id=customer_id).cliente_id
    except ClienteAsaas.DoesNotExist:
        return None


def _get_conta_asaas():
    """Retorna a ContaBancaria do Asaas."""
    return ContaBancaria.objects.filter(nome__icontains="asaas").first()


def _get_categoria_receita():
    """Retorna categoria de receita de servicos."""
    return CategoriaFinanceira.objects.filter(
        tipo="receita", pai__isnull=False
    ).first()


def _processar_payment_created(payment):
    """PAYMENT_CREATED — cria cobranca + lancamento pendente."""
    cobranca = _get_or_create_cobranca(payment)

    if not cobranca.lancamento:
        conta = _get_conta_asaas()
        cat = _get_categoria_receita()
        if conta and cat:
            lanc = Lancamento.objects.create(
                tipo="receita",
                descricao=f"Asaas: {payment.get('description', cobranca.asaas_id)}",
                valor=cobranca.valor,
                valor_liquido=cobranca.valor_liquido,
                categoria=cat,
                conta=conta,
                canal="gateway",
                data_vencimento=cobranca.vencimento,
                data_competencia=cobranca.vencimento,
                status="pendente",
                cliente_id=cobranca.cliente_id,
                id_externo=cobranca.asaas_id,
            )
            cobranca.lancamento = lanc
            cobranca.save(update_fields=["lancamento"])


def _processar_payment_received(payment):
    """PAYMENT_RECEIVED / PAYMENT_CONFIRMED — confirma pagamento."""
    cobranca = _get_or_create_cobranca(payment)

    pago_em = payment.get("paymentDate") or payment.get("confirmedDate")
    cobranca.pago_em = pago_em
    cobranca.status = payment.get("status", "RECEIVED")
    cobranca.valor_liquido = Decimal(str(payment.get("netValue", 0) or cobranca.valor))
    cobranca.save()

    if cobranca.lancamento:
        cobranca.lancamento.status = "confirmado"
        cobranca.lancamento.data_pagamento = pago_em
        cobranca.lancamento.valor_liquido = cobranca.valor_liquido
        cobranca.lancamento.save(update_fields=["status", "data_pagamento", "valor_liquido"])
    else:
        _processar_payment_created(payment)
        cobranca.refresh_from_db()
        if cobranca.lancamento:
            cobranca.lancamento.status = "confirmado"
            cobranca.lancamento.data_pagamento = pago_em
            cobranca.lancamento.save(update_fields=["status", "data_pagamento"])


def _processar_payment_overdue(payment):
    """PAYMENT_OVERDUE — marca como vencido."""
    cobranca = _get_or_create_cobranca(payment)
    cobranca.status = "OVERDUE"
    cobranca.save(update_fields=["status"])


def _processar_payment_cancelled(payment):
    """PAYMENT_REFUNDED / PAYMENT_DELETED — cancela."""
    cobranca = _get_or_create_cobranca(payment)
    cobranca.status = payment.get("status", "REFUNDED")
    cobranca.save(update_fields=["status"])

    if cobranca.lancamento:
        cobranca.lancamento.status = "cancelado"
        cobranca.lancamento.save(update_fields=["status"])
