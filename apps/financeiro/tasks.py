"""Tasks Celery do modulo Financeiro."""

from celery import shared_task


@shared_task(name="financeiro.gerar_recorrentes")
def gerar_recorrentes():
    """Gera despesas recorrentes para o proximo periodo.
    Agendado via Celery Beat para rodar no dia 1 de cada mes.
    """
    from django.core.management import call_command
    call_command("gerar_recorrentes")


@shared_task(name="financeiro.gerar_folha_mensal")
def gerar_folha_mensal():
    """Gera folha de pagamento automatica para o mes corrente.
    Agendado via Celery Beat para rodar no dia 1 de cada mes.
    """
    from django.core.management import call_command
    call_command("gerar_folha_mensal")
