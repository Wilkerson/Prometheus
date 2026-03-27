"""
Servico de notificacoes — funcoes utilitarias.
Uso: notificar(destinatario, tipo, titulo, mensagem, link)
     notificar_grupo(usuarios_qs, tipo, titulo, mensagem, link)
     notificar_admins(tipo, titulo, mensagem, link)
     notificar_parceiro_do_cliente(cliente, tipo, titulo, mensagem, link)
"""

from apps.accounts.models import Usuario

from .models import Notificacao


def notificar(destinatario, tipo, titulo, mensagem="", link=""):
    """Cria uma notificacao para um usuario."""
    return Notificacao.objects.create(
        destinatario=destinatario,
        tipo=tipo,
        titulo=titulo,
        mensagem=mensagem,
        link=link,
    )


def notificar_grupo(usuarios_qs, tipo, titulo, mensagem="", link=""):
    """Cria notificacao para multiplos usuarios."""
    notificacoes = [
        Notificacao(
            destinatario=user,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            link=link,
        )
        for user in usuarios_qs
    ]
    return Notificacao.objects.bulk_create(notificacoes)


def notificar_admins(tipo, titulo, mensagem="", link=""):
    """Notifica todos os superusuarios e usuarios do grupo Administrador."""
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
