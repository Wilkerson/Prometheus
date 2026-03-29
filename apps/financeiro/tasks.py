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


@shared_task(name="financeiro.processar_webhook_asaas")
def processar_webhook_asaas(evento_id):
    """Processa evento do webhook Asaas de forma assincrona."""
    from apps.financeiro.services.asaas_webhook import processar_evento
    processar_evento(evento_id)
