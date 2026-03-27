"""
Servico de notificacoes do modulo RH.
Usa o model Notificacao do CRM e respeita PreferenciaNotificacao.
"""

from django.contrib.auth.models import Group

from apps.accounts.models import Usuario
from apps.crm.models import Notificacao
from apps.crm.notifications import notificar, notificar_grupo


def _get_grupo_rh_users():
    """Retorna usuarios do grupo RH / Pessoas."""
    try:
        grupo = Group.objects.get(name="RH / Pessoas")
        return grupo.user_set.filter(is_active=True)
    except Group.DoesNotExist:
        return Usuario.objects.none()


def _notificar_rh(tipo, titulo, mensagem="", link=""):
    """Notifica todos do grupo RH."""
    return notificar_grupo(_get_grupo_rh_users(), tipo, titulo, mensagem, link)


def _notificar_colaborador(colaborador, tipo, titulo, mensagem="", link=""):
    """Notifica o usuario vinculado ao colaborador (se tiver acesso)."""
    if colaborador.usuario and colaborador.usuario.is_active:
        return notificar(colaborador.usuario, tipo, titulo, mensagem, link)
    return None


# =========================================================================
# Colaboradores
# =========================================================================
def notificar_novo_colaborador(colaborador):
    _notificar_rh(
        Notificacao.Tipo.RH_COLABORADOR,
        f"Novo colaborador: {colaborador.nome_completo}",
        f"{colaborador.get_tipo_contrato_display()} — {colaborador.cargo}",
        f"/rh/colaboradores/{colaborador.pk}/",
    )


def notificar_colaborador_desligado(colaborador):
    _notificar_rh(
        Notificacao.Tipo.RH_COLABORADOR,
        f"Colaborador desligado: {colaborador.nome_completo}",
        f"Desligamento registrado em {colaborador.data_desligamento:%d/%m/%Y}" if colaborador.data_desligamento else "",
        f"/rh/colaboradores/{colaborador.pk}/",
    )


# =========================================================================
# Documentos
# =========================================================================
def notificar_documento_vencendo(documento):
    """Documento proximo do vencimento — notifica RH e colaborador."""
    dias = (documento.data_vencimento - __import__('django.utils.timezone', fromlist=['timezone']).now().date()).days
    _notificar_rh(
        Notificacao.Tipo.RH_DOCUMENTO,
        f"Documento a vencer: {documento.nome}",
        f"{documento.colaborador.nome_completo} — vence em {dias} dia(s) ({documento.data_vencimento:%d/%m/%Y})",
        f"/rh/documentos/",
    )
    _notificar_colaborador(
        documento.colaborador,
        Notificacao.Tipo.RH_DOCUMENTO,
        f"Seu documento '{documento.nome}' vence em {dias} dia(s)",
        f"Vencimento: {documento.data_vencimento:%d/%m/%Y}",
        f"/rh/documentos/",
    )


def notificar_documento_vencido(documento):
    _notificar_rh(
        Notificacao.Tipo.RH_DOCUMENTO,
        f"Documento VENCIDO: {documento.nome}",
        f"{documento.colaborador.nome_completo} — venceu em {documento.data_vencimento:%d/%m/%Y}",
        f"/rh/documentos/",
    )


# =========================================================================
# Onboarding
# =========================================================================
def notificar_onboarding_iniciado(onboarding):
    _notificar_colaborador(
        onboarding.colaborador,
        Notificacao.Tipo.RH_ONBOARDING,
        "Seu onboarding foi iniciado!",
        f"Checklist com {onboarding.total_itens} itens para completar.",
        f"/rh/onboarding/{onboarding.pk}/",
    )


def notificar_onboarding_concluido(onboarding):
    _notificar_rh(
        Notificacao.Tipo.RH_ONBOARDING,
        f"Onboarding concluido: {onboarding.colaborador.nome_completo}",
        "Todos os itens do checklist foram concluidos.",
        f"/rh/onboarding/{onboarding.pk}/",
    )


# =========================================================================
# Ausencias
# =========================================================================
def notificar_nova_solicitacao_ausencia(ausencia):
    """Nova solicitacao — notifica RH pra aprovar."""
    _notificar_rh(
        Notificacao.Tipo.RH_AUSENCIA,
        f"Nova solicitacao: {ausencia.get_tipo_display()}",
        f"{ausencia.colaborador.nome_completo} — {ausencia.data_inicio:%d/%m/%Y} a {ausencia.data_fim:%d/%m/%Y} ({ausencia.total_dias} dias)",
        f"/rh/ausencias/",
    )


def notificar_ausencia_aprovada(ausencia):
    _notificar_colaborador(
        ausencia.colaborador,
        Notificacao.Tipo.RH_AUSENCIA,
        f"Sua {ausencia.get_tipo_display()} foi aprovada",
        f"{ausencia.data_inicio:%d/%m/%Y} a {ausencia.data_fim:%d/%m/%Y}",
        f"/rh/ausencias/",
    )


def notificar_ausencia_rejeitada(ausencia):
    _notificar_colaborador(
        ausencia.colaborador,
        Notificacao.Tipo.RH_AUSENCIA,
        f"Sua {ausencia.get_tipo_display()} foi rejeitada",
        ausencia.justificativa_rejeicao or "Sem justificativa informada.",
        f"/rh/ausencias/",
    )


def notificar_ferias_vencidas(saldo):
    """Ferias vencidas — notifica RH e colaborador."""
    _notificar_rh(
        Notificacao.Tipo.RH_AUSENCIA,
        f"Ferias VENCIDAS: {saldo.colaborador.nome_completo}",
        f"Saldo: {saldo.saldo_disponivel} dias — periodo {saldo.periodo_inicio:%d/%m/%Y} a {saldo.periodo_fim:%d/%m/%Y}",
        f"/rh/ausencias/",
    )
    _notificar_colaborador(
        saldo.colaborador,
        Notificacao.Tipo.RH_AUSENCIA,
        "Voce tem ferias vencidas!",
        f"Saldo disponivel: {saldo.saldo_disponivel} dias. Solicite suas ferias.",
        f"/rh/ausencias/",
    )


# =========================================================================
# Treinamentos
# =========================================================================
def notificar_inscricao_treinamento(participacao):
    _notificar_colaborador(
        participacao.colaborador,
        Notificacao.Tipo.RH_TREINAMENTO,
        f"Inscrito: {participacao.treinamento.nome}",
        f"{participacao.treinamento.get_modalidade_display()} — {participacao.treinamento.carga_horaria}h",
        f"/rh/treinamentos/{participacao.treinamento.pk}/",
    )


def notificar_treinamento_concluido(participacao):
    _notificar_rh(
        Notificacao.Tipo.RH_TREINAMENTO,
        f"Treinamento concluido: {participacao.colaborador.nome_completo}",
        f"{participacao.treinamento.nome}",
        f"/rh/treinamentos/{participacao.treinamento.pk}/",
    )


# =========================================================================
# Metas / PDI
# =========================================================================
def notificar_novo_ciclo(ciclo):
    """Novo ciclo — notifica todos os colaboradores com acesso."""
    usuarios = Usuario.objects.filter(
        is_active=True,
        colaborador__status="ativo",
    )
    notificar_grupo(
        usuarios,
        Notificacao.Tipo.RH_META,
        f"Novo ciclo de avaliacao: {ciclo.nome}",
        f"Periodo: {ciclo.periodo_inicio:%d/%m/%Y} a {ciclo.periodo_fim:%d/%m/%Y}",
        f"/rh/metas/{ciclo.pk}/",
    )


def notificar_pdi_acao_atrasada(acao):
    _notificar_colaborador(
        acao.pdi.colaborador,
        Notificacao.Tipo.RH_META,
        f"Acao PDI atrasada: {acao.descricao}",
        f"Prazo era {acao.prazo:%d/%m/%Y}. Atualize o status.",
        f"/rh/pdi/{acao.pdi.pk}/",
    )


# =========================================================================
# eNPS
# =========================================================================
def notificar_pesquisa_ativa(pesquisa):
    """Pesquisa ativada — notifica todos os colaboradores com acesso."""
    usuarios = Usuario.objects.filter(
        is_active=True,
        colaborador__status="ativo",
    )
    notificar_grupo(
        usuarios,
        Notificacao.Tipo.RH_ENPS,
        f"Nova pesquisa eNPS: {pesquisa.titulo}",
        f"Responda ate {pesquisa.data_encerramento:%d/%m/%Y}. Sua opiniao e importante!",
        f"/rh/enps/{pesquisa.pk}/responder/",
    )


def notificar_pesquisa_encerrada(pesquisa):
    _notificar_rh(
        Notificacao.Tipo.RH_ENPS,
        f"Pesquisa encerrada: {pesquisa.titulo}",
        f"eNPS Score: {pesquisa.enps_score or 'N/A'} — {pesquisa.total_respondentes} respondentes ({pesquisa.participacao}%)",
        f"/rh/enps/{pesquisa.pk}/",
    )
