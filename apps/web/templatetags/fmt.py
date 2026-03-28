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
