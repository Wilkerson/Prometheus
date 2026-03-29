"""
Servico de agregacao — unifica logs legados + AuditLog em formato comum.
"""

from itertools import chain
from operator import attrgetter


def _normalize_auditlog(entry):
    """Normaliza AuditLog para dict padrao."""
    return {
        "id": f"audit-{entry.pk}",
        "pk_num": entry.pk,
        "acao": entry.get_acao_display(),
        "acao_raw": entry.acao,
        "departamento": entry.departamento,
        "descricao": entry.descricao,
        "detalhes": entry.detalhes,
        "usuario": entry.usuario.get_full_name() if entry.usuario else "Sistema",
        "fonte": entry.fonte,
        "criado_em": entry.criado_em,
        "object_repr": entry.object_repr,
        "model": "AuditLog",
    }


def _normalize_auditoria_lancamento(entry):
    """Normaliza AuditoriaLancamento legado."""
    return {
        "id": f"lancamento-{entry.pk}",
        "acao": entry.acao.capitalize(),
        "acao_raw": entry.acao,
        "departamento": "financeiro",
        "descricao": f"Lancamento: {entry.lancamento}",
        "detalhes": {"mudancas": entry.detalhes},
        "usuario": entry.usuario.get_full_name() if entry.usuario else "Sistema",
        "fonte": "interno",
        "criado_em": entry.criado_em,
        "object_repr": str(entry.lancamento),
        "model": "AuditoriaLancamento",
    }


def _normalize_evento_webhook(entry):
    """Normaliza EventoWebhookAsaas legado."""
    return {
        "id": f"webhook-{entry.pk}",
        "acao": "Webhook",
        "acao_raw": "webhook",
        "departamento": "integracao",
        "descricao": f"{entry.evento} — {entry.asaas_payment_id or 'sem ID'}",
        "detalhes": entry.payload or {},
        "usuario": "Asaas",
        "fonte": "asaas_webhook",
        "criado_em": entry.recebido_em,
        "object_repr": entry.asaas_payment_id or "",
        "model": "EventoWebhookAsaas",
        "processado": entry.processado,
        "erro": entry.erro,
    }


def _normalize_log_exportacao(entry):
    """Normaliza LogExportacaoFolha legado."""
    return {
        "id": f"export-{entry.pk}",
        "acao": "Exportacao",
        "acao_raw": "exportacao",
        "departamento": "financeiro",
        "descricao": f"Exportacao folha {entry.competencia:%m/%Y} ({entry.formato})",
        "detalhes": {
            "formato": entry.formato,
            "total_registros": entry.total_registros,
            "valor_total": str(entry.valor_total),
        },
        "usuario": entry.exportado_por.get_full_name() if entry.exportado_por else "Sistema",
        "fonte": "interno",
        "criado_em": entry.criado_em,
        "object_repr": f"Folha {entry.competencia:%m/%Y}",
        "model": "LogExportacaoFolha",
    }


def _normalize_cliente_historico(entry):
    """Normaliza ClienteHistorico legado."""
    return {
        "id": f"hist-{entry.pk}",
        "acao": "Mudanca de status",
        "acao_raw": "status",
        "departamento": "comercial",
        "descricao": f"{entry.cliente.nome}: {entry.status_anterior} → {entry.status_novo}",
        "detalhes": {
            "status_anterior": entry.status_anterior,
            "status_novo": entry.status_novo,
            "observacao": entry.observacao,
        },
        "usuario": entry.usuario.get_full_name() if entry.usuario else "Sistema",
        "fonte": "interno",
        "criado_em": entry.criado_em,
        "object_repr": entry.cliente.nome,
        "model": "ClienteHistorico",
    }


def get_audit_logs(departamento=None, fonte=None, busca=None, dias=30, data_de=None, data_ate=None, limit=50):
    """Retorna logs de auditoria unificados, ordenados por data desc.

    Se data_de/data_ate forem fornecidos, ignoram o parametro dias.
    """
    from datetime import datetime, timedelta

    from django.utils import timezone

    from apps.auditoria.models import AuditLog
    from apps.crm.models import ClienteHistorico
    from apps.financeiro.models import (
        AuditoriaLancamento, EventoWebhookAsaas, LogExportacaoFolha,
    )

    results = []

    # Resolver periodo
    if data_de:
        desde = timezone.make_aware(datetime.combine(data_de, datetime.min.time())) if timezone.is_naive(datetime.combine(data_de, datetime.min.time())) else datetime.combine(data_de, datetime.min.time())
    else:
        desde = timezone.now() - timedelta(days=dias)

    if data_ate:
        ate = timezone.make_aware(datetime.combine(data_ate, datetime.max.time())) if timezone.is_naive(datetime.combine(data_ate, datetime.max.time())) else datetime.combine(data_ate, datetime.max.time())
    else:
        ate = None

    # 1. AuditLog (modelo canonico)
    qs_audit = AuditLog.objects.select_related("usuario").filter(criado_em__gte=desde)
    if ate:
        qs_audit = qs_audit.filter(criado_em__lte=ate)
    if departamento:
        qs_audit = qs_audit.filter(departamento=departamento)
    if fonte:
        qs_audit = qs_audit.filter(fonte=fonte)
    if busca:
        qs_audit = qs_audit.filter(descricao__icontains=busca)
    for e in qs_audit[:limit]:
        results.append(_normalize_auditlog(e))

    # 2. AuditoriaLancamento (legado — departamento financeiro)
    if not departamento or departamento == "financeiro":
        qs_lanc = AuditoriaLancamento.objects.select_related("lancamento", "usuario").filter(criado_em__gte=desde)
        if ate:
            qs_lanc = qs_lanc.filter(criado_em__lte=ate)
        if busca:
            qs_lanc = qs_lanc.filter(detalhes__icontains=busca)
        if not fonte or fonte == "interno":
            for e in qs_lanc[:limit]:
                results.append(_normalize_auditoria_lancamento(e))

    # 3. EventoWebhookAsaas (legado — departamento integracao)
    if not departamento or departamento == "integracao":
        qs_wh = EventoWebhookAsaas.objects.filter(recebido_em__gte=desde)
        if ate:
            qs_wh = qs_wh.filter(recebido_em__lte=ate)
        if busca:
            qs_wh = qs_wh.filter(evento__icontains=busca)
        if not fonte or fonte == "asaas_webhook":
            for e in qs_wh[:limit]:
                results.append(_normalize_evento_webhook(e))

    # 4. LogExportacaoFolha (legado — departamento financeiro)
    if not departamento or departamento == "financeiro":
        qs_exp = LogExportacaoFolha.objects.select_related("exportado_por").filter(criado_em__gte=desde)
        if ate:
            qs_exp = qs_exp.filter(criado_em__lte=ate)
        if not fonte or fonte == "interno":
            for e in qs_exp[:limit]:
                results.append(_normalize_log_exportacao(e))

    # 5. ClienteHistorico (legado — departamento comercial)
    if not departamento or departamento == "comercial":
        qs_hist = ClienteHistorico.objects.select_related("cliente", "usuario").filter(criado_em__gte=desde)
        if ate:
            qs_hist = qs_hist.filter(criado_em__lte=ate)
        if busca:
            qs_hist = qs_hist.filter(cliente__nome__icontains=busca)
        if not fonte or fonte == "interno":
            for e in qs_hist[:limit]:
                results.append(_normalize_cliente_historico(e))

    # Ordenar por data desc e limitar
    results.sort(key=lambda x: x["criado_em"], reverse=True)
    return results[:limit]


def get_audit_stats():
    """Retorna contadores por departamento para o dashboard."""
    from datetime import timedelta

    from django.db.models import Count
    from django.utils import timezone

    from apps.auditoria.models import AuditLog
    from apps.crm.models import ClienteHistorico
    from apps.financeiro.models import (
        AuditoriaLancamento, EventoWebhookAsaas, LogExportacaoFolha,
    )

    agora = timezone.now()
    h24 = agora - timedelta(hours=24)
    d7 = agora - timedelta(days=7)
    d30 = agora - timedelta(days=30)

    # Contadores do AuditLog canonico
    audit_24h = AuditLog.objects.filter(criado_em__gte=h24).count()
    audit_7d = AuditLog.objects.filter(criado_em__gte=d7).count()
    audit_30d = AuditLog.objects.filter(criado_em__gte=d30).count()

    # Contadores legados
    lanc_30d = AuditoriaLancamento.objects.filter(criado_em__gte=d30).count()
    wh_30d = EventoWebhookAsaas.objects.filter(recebido_em__gte=d30).count()
    exp_30d = LogExportacaoFolha.objects.filter(criado_em__gte=d30).count()
    hist_30d = ClienteHistorico.objects.filter(criado_em__gte=d30).count()

    # Por departamento (legados + canonico)
    audit_by_depto = dict(
        AuditLog.objects.filter(criado_em__gte=d30)
        .values_list("departamento")
        .annotate(total=Count("id"))
        .values_list("departamento", "total")
    )

    return {
        "total_24h": audit_24h,
        "total_7d": audit_7d,
        "total_30d": audit_30d + lanc_30d + wh_30d + exp_30d + hist_30d,
        "financeiro_30d": audit_by_depto.get("financeiro", 0) + lanc_30d + exp_30d,
        "comercial_30d": audit_by_depto.get("comercial", 0) + hist_30d,
        "integracao_30d": audit_by_depto.get("integracao", 0) + wh_30d,
        "rh_30d": audit_by_depto.get("rh", 0),
        "admin_30d": audit_by_depto.get("administracao", 0),
    }
