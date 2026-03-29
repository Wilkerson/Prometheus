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


@shared_task(name="financeiro.verificar_webhook_asaas")
def verificar_webhook_asaas():
    """Verifica se o webhook Asaas esta ativo (recebeu eventos nas ultimas 48h).
    Cria notificacao para admins se inativo.
    """
    import logging
    from datetime import timedelta

    from django.utils import timezone

    from apps.financeiro.models import EventoWebhookAsaas

    logger = logging.getLogger(__name__)
    limite = timezone.now() - timedelta(hours=48)
    ultimo = EventoWebhookAsaas.objects.order_by("-recebido_em").first()

    if ultimo and ultimo.recebido_em >= limite:
        return  # tudo ok

    msg = "Nenhum evento de webhook Asaas recebido nas ultimas 48h."
    logger.warning(msg)

    # Criar notificacao para admins
    try:
        from apps.crm.models import Notificacao
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admins = User.objects.filter(is_superuser=True, is_active=True)
        for admin_user in admins:
            Notificacao.objects.create(
                destinatario=admin_user,
                titulo="Webhook Asaas inativo",
                mensagem=msg,
                tipo="sistema",
            )
    except Exception:
        pass  # se modelo de notificacao nao existir, apenas loga
