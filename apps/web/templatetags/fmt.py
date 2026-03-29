"""Template filters de formatacao pt-BR."""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def brl(value):
    """Formata valor como moeda brasileira: R$ 1.234,56"""
    if value is None or value == "":
        return "R$ 0,00"
    try:
        num = Decimal(str(value))
    except (InvalidOperation, TypeError):
        return str(value)
    negativo = num < 0
    num = abs(num)
    inteiro = int(num)
    centavos = f"{num % 1:.2f}"[2:]
    inteiro_fmt = f"{inteiro:,}".replace(",", ".")
    resultado = f"R$ {inteiro_fmt},{centavos}"
    if negativo:
        resultado = f"-{resultado}"
    return resultado


@register.filter
def numero_br(value):
    """Formata numero com separadores brasileiros: 1.234,56"""
    if value is None or value == "":
        return "0,00"
    try:
        num = Decimal(str(value))
    except (InvalidOperation, TypeError):
        return str(value)
    inteiro = int(abs(num))
    centavos = f"{abs(num) % 1:.2f}"[2:]
    inteiro_fmt = f"{inteiro:,}".replace(",", ".")
    resultado = f"{inteiro_fmt},{centavos}"
    if num < 0:
        resultado = f"-{resultado}"
    return resultado


# Mapa de status do Asaas para portugues
ASAAS_STATUS_MAP = {
    # Cobrancas
    "PENDING": "Pendente",
    "RECEIVED": "Pago",
    "CONFIRMED": "Confirmado",
    "OVERDUE": "Vencido",
    "REFUNDED": "Estornado",
    "RECEIVED_IN_CASH": "Recebido em dinheiro",
    "REFUND_REQUESTED": "Estorno solicitado",
    "REFUND_IN_PROGRESS": "Estorno em andamento",
    "CHARGEBACK_REQUESTED": "Chargeback solicitado",
    "CHARGEBACK_DISPUTE": "Disputa de chargeback",
    "AWAITING_CHARGEBACK_REVERSAL": "Aguardando reversão",
    "DUNNING_REQUESTED": "Em recuperação",
    "DUNNING_RECEIVED": "Recuperado",
    "AWAITING_RISK_ANALYSIS": "Em análise de risco",
    "DELETED": "Cancelado",
    # Assinaturas
    "ACTIVE": "Ativa",
    "INACTIVE": "Inativa",
    "EXPIRED": "Expirada",
}

ASAAS_STATUS_STYLE = {
    "PENDING": "bg-blue-500/15 text-blue-500",
    "RECEIVED": "bg-emerald-500/15 text-emerald-500",
    "CONFIRMED": "bg-emerald-500/15 text-emerald-500",
    "OVERDUE": "bg-red-500/15 text-red-500",
    "REFUNDED": "bg-amber-500/15 text-amber-500",
    "RECEIVED_IN_CASH": "bg-emerald-500/15 text-emerald-500",
    "REFUND_REQUESTED": "bg-amber-500/15 text-amber-500",
    "REFUND_IN_PROGRESS": "bg-amber-500/15 text-amber-500",
    "CHARGEBACK_REQUESTED": "bg-red-500/15 text-red-500",
    "CHARGEBACK_DISPUTE": "bg-red-500/15 text-red-500",
    "DUNNING_REQUESTED": "bg-amber-500/15 text-amber-500",
    "DUNNING_RECEIVED": "bg-emerald-500/15 text-emerald-500",
    "AWAITING_RISK_ANALYSIS": "bg-blue-500/15 text-blue-500",
    "DELETED": "bg-bg4 text-t3",
    "ACTIVE": "bg-emerald-500/15 text-emerald-500",
    "INACTIVE": "bg-bg4 text-t3",
    "EXPIRED": "bg-red-500/15 text-red-500",
}


@register.filter
def asaas_status(value):
    """Traduz status do Asaas para portugues."""
    return ASAAS_STATUS_MAP.get(value, value)


@register.filter
def asaas_badge(value):
    """Retorna classes CSS do badge para status do Asaas."""
    return ASAAS_STATUS_STYLE.get(value, "bg-bg4 text-t3")
