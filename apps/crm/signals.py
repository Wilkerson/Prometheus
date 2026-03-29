"""Signals para gerar notificacoes automaticas de eventos de cliente."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Cliente, ClienteHistorico, Notificacao
from .notifications import notificar_admins, notificar_parceiro_do_cliente


@receiver(post_save, sender=Cliente)
def notificar_novo_cliente(sender, instance, created, **kwargs):
    """Notifica admins quando um novo cliente e cadastrado."""
    if not created:
        return

    notificar_admins(
        tipo=Notificacao.Tipo.CLIENTE_NOVO,
        titulo=f"Novo cliente: {instance.nome}",
        mensagem=f"Cadastrado por {instance.parceiro.nome_entidade}." if instance.parceiro else "Cadastrado no sistema.",
        link=f"/clientes/{instance.pk}/",
    )

    from apps.crm.emails import enviar_cliente_novo
    enviar_cliente_novo(instance)


@receiver(post_save, sender=ClienteHistorico)
def notificar_mudanca_status(sender, instance, created, **kwargs):
    """Notifica parceiro e admins quando status do cliente muda."""
    if not created:
        return

    cliente = instance.cliente
    status_display = dict(Cliente.Status.choices).get(instance.status_novo, instance.status_novo)

    # Notifica o parceiro dono
    notificar_parceiro_do_cliente(
        cliente,
        tipo=Notificacao.Tipo.CLIENTE_STATUS,
        titulo=f"{cliente.nome}: {status_display}",
        mensagem=instance.observacao or f"Status alterado para {status_display}.",
        link=f"/clientes/{cliente.pk}/",
    )

    # Zypher OK
    if instance.status_novo == Cliente.Status.CONCLUIDA and instance.usuario is None:
        notificar_parceiro_do_cliente(
            cliente,
            tipo=Notificacao.Tipo.CLIENTE_ZYPHER_OK,
            titulo=f"Implantacao concluida: {cliente.nome}",
            mensagem="O sistema Zypher concluiu a implantacao com sucesso.",
            link=f"/clientes/{cliente.pk}/",
        )

    # Zypher FALHA
    if instance.status_novo == Cliente.Status.FALHA_IMPLANTACAO and instance.usuario is None:
        notificar_parceiro_do_cliente(
            cliente,
            tipo=Notificacao.Tipo.CLIENTE_ZYPHER_FALHA,
            titulo=f"Falha na implantacao: {cliente.nome}",
            mensagem="O sistema Zypher retornou erro na implantacao.",
            link=f"/clientes/{cliente.pk}/",
        )
        notificar_admins(
            tipo=Notificacao.Tipo.CLIENTE_ZYPHER_FALHA,
            titulo=f"Falha Zypher: {cliente.nome}",
            mensagem="Implantacao falhou. Acao necessaria.",
            link=f"/clientes/{cliente.pk}/",
        )
