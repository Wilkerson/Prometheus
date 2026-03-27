"""
Servico de notificacoes — funcoes utilitarias.
Respeita PreferenciaNotificacao de cada usuario.
"""

from apps.accounts.models import Usuario

from .models import Notificacao, PreferenciaNotificacao


def _usuario_aceita(user, tipo):
    """Verifica se o usuario aceita notificacoes deste tipo."""
    try:
        prefs = user.preferencias_notificacao
        return prefs.aceita(tipo)
    except PreferenciaNotificacao.DoesNotExist:
        return True  # Sem preferencias = aceita tudo


def notificar(destinatario, tipo, titulo, mensagem="", link=""):
    """Cria notificacao se o usuario aceita este tipo."""
    if not _usuario_aceita(destinatario, tipo):
        return None
    return Notificacao.objects.create(
        destinatario=destinatario,
        tipo=tipo,
        titulo=titulo,
        mensagem=mensagem,
        link=link,
    )


def notificar_grupo(usuarios_qs, tipo, titulo, mensagem="", link=""):
    """Cria notificacao para multiplos usuarios (respeitando preferencias)."""
    notificacoes = []
    for user in usuarios_qs:
        if _usuario_aceita(user, tipo):
            notificacoes.append(
                Notificacao(
                    destinatario=user,
                    tipo=tipo,
                    titulo=titulo,
                    mensagem=mensagem,
                    link=link,
                )
            )
    return Notificacao.objects.bulk_create(notificacoes) if notificacoes else []


def notificar_admins(tipo, titulo, mensagem="", link=""):
    """Notifica superusuarios e usuarios do grupo Administrador."""
    from django.contrib.auth.models import Group

    admins = Usuario.objects.filter(is_superuser=True)
    try:
        grupo_admin = Group.objects.get(name="Administrador")
        admins = admins | grupo_admin.user_set.all()
    except Group.DoesNotExist:
        pass
    return notificar_grupo(admins.distinct(), tipo, titulo, mensagem, link)


def notificar_parceiro_do_cliente(cliente, tipo, titulo, mensagem="", link=""):
    """Notifica o usuario da entidade parceira dona do cliente."""
    parceiro_user = cliente.parceiro.usuario
    return notificar(parceiro_user, tipo, titulo, mensagem, link)
