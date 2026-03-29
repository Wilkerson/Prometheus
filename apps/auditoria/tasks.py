"""Tasks Celery do modulo de Auditoria."""

from celery import shared_task


@shared_task(name="auditoria.limpar_logs_antigos")
def limpar_logs_antigos():
    """Remove registros de auditoria com mais de 1 ano (periodo fiscal).
    Agendado via Celery Beat para rodar mensalmente.
    """
    import logging
    from datetime import timedelta

    from django.utils import timezone

    from apps.auditoria.models import AuditLog
    from apps.financeiro.models import (
        AuditoriaLancamento, EventoWebhookAsaas, LogExportacaoFolha,
    )

    logger = logging.getLogger(__name__)
    limite = timezone.now() - timedelta(days=365)

    # AuditLog canonico
    count_audit = AuditLog.objects.filter(criado_em__lt=limite).delete()[0]

    # Legados
    count_lanc = AuditoriaLancamento.objects.filter(criado_em__lt=limite).delete()[0]
    count_wh = EventoWebhookAsaas.objects.filter(recebido_em__lt=limite).delete()[0]
    count_exp = LogExportacaoFolha.objects.filter(criado_em__lt=limite).delete()[0]

    total = count_audit + count_lanc + count_wh + count_exp
    if total:
        logger.info(f"Retencao: {total} registros de auditoria removidos (AuditLog={count_audit}, Lancamento={count_lanc}, Webhook={count_wh}, Export={count_exp})")

        # Registrar a propria limpeza
        from apps.auditoria.utils import registrar
        registrar(
            "sistema", "sistema",
            f"Retencao de auditoria: {total} registros com mais de 1 ano removidos",
            detalhes={
                "auditlog": count_audit,
                "auditoria_lancamento": count_lanc,
                "evento_webhook": count_wh,
                "log_exportacao": count_exp,
            },
            fonte="celery",
        )
