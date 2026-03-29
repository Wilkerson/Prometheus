"""
Servico de notificacoes do modulo Financeiro.
Usa o model Notificacao do CRM e respeita PreferenciaNotificacao.
"""

from django.contrib.auth.models import Group

from apps.accounts.models import Usuario
from apps.crm.models import Notificacao
from apps.crm.notifications import notificar, notificar_grupo, notificar_admins


def _get_grupo_financeiro_users():
    """Retorna usuarios do grupo Financeiro."""
    try:
        grupo = Group.objects.get(name="Financeiro")
        return grupo.user_set.filter(is_active=True)
    except Group.DoesNotExist:
        return Usuario.objects.none()


def _notificar_financeiro(tipo, titulo, mensagem="", link=""):
    """Notifica todos do grupo Financeiro."""
    return notificar_grupo(_get_grupo_financeiro_users(), tipo, titulo, mensagem, link)


# =========================================================================
# Lancamentos
# =========================================================================
def notificar_lancamento_confirmado(lancamento):
    _notificar_financeiro(
        Notificacao.Tipo.FIN_LANCAMENTO,
        f"Pagamento confirmado: {lancamento.descricao}",
        f"Valor: R$ {lancamento.valor}",
        f"/financeiro/lancamentos/{lancamento.pk}/",
    )


# =========================================================================
# Cobrancas / Pagamentos Asaas
# =========================================================================
def notificar_pagamento_recebido(cobranca_asaas):
    """Notifica quando pagamento e confirmado via Asaas."""
    _notificar_financeiro(
        Notificacao.Tipo.FIN_ASAAS,
        f"Pagamento recebido: {cobranca_asaas.cliente.nome}",
        f"Cobranca {cobranca_asaas.asaas_id} — R$ {cobranca_asaas.valor}",
        f"/financeiro/asaas/cobrancas/{cobranca_asaas.pk}/",
    )


def notificar_cobranca_vencida(cobranca_asaas):
    """Notifica quando cobranca Asaas vence."""
    _notificar_financeiro(
        Notificacao.Tipo.FIN_ASAAS,
        f"Cobranca vencida: {cobranca_asaas.cliente.nome}",
        f"Cobranca {cobranca_asaas.asaas_id} — R$ {cobranca_asaas.valor}",
        f"/financeiro/asaas/cobrancas/{cobranca_asaas.pk}/",
    )


def notificar_cobranca_cancelada(cobranca_asaas):
    """Notifica quando cobranca e cancelada/estornada."""
    _notificar_financeiro(
        Notificacao.Tipo.FIN_ASAAS,
        f"Cobranca cancelada: {cobranca_asaas.cliente.nome}",
        f"Cobranca {cobranca_asaas.asaas_id} — R$ {cobranca_asaas.valor}",
        f"/financeiro/asaas/cobrancas/{cobranca_asaas.pk}/",
    )


def notificar_assinatura_criada(assinatura):
    """Notifica quando nova assinatura recorrente e criada."""
    _notificar_financeiro(
        Notificacao.Tipo.FIN_ASAAS,
        f"Nova assinatura: {assinatura.cliente.nome}",
        f"{assinatura.get_ciclo_display()} — R$ {assinatura.valor}",
        "/financeiro/asaas/assinaturas/",
    )


def notificar_assinatura_cancelada(assinatura):
    """Notifica quando assinatura e cancelada."""
    _notificar_financeiro(
        Notificacao.Tipo.FIN_ASAAS,
        f"Assinatura cancelada: {assinatura.cliente.nome}",
        f"{assinatura.asaas_id}",
        "/financeiro/asaas/assinaturas/",
    )


# =========================================================================
# Folha de Pagamento
# =========================================================================
def notificar_folha_gerada(competencia, total):
    """Notifica quando folha e gerada automaticamente."""
    _notificar_financeiro(
        Notificacao.Tipo.FIN_FOLHA,
        f"Folha gerada: {competencia:%m/%Y}",
        f"{total} registro(s) gerado(s)",
        "/financeiro/folha/",
    )


def notificar_folha_aprovada(competencia):
    """Notifica quando todas as folhas de uma competencia sao aprovadas."""
    _notificar_financeiro(
        Notificacao.Tipo.FIN_FOLHA,
        f"Folha aprovada: {competencia:%m/%Y}",
        "Todas as folhas foram aprovadas e estao prontas para exportacao.",
        "/financeiro/folha/",
    )


def notificar_folha_exportada(competencia, formato, usuario):
    """Notifica quando folha e exportada."""
    notificar_admins(
        Notificacao.Tipo.FIN_FOLHA,
        f"Folha exportada: {competencia:%m/%Y}",
        f"Formato: {formato.upper()} — Por: {usuario.get_full_name() or usuario.username}",
        "/financeiro/folha/",
    )
