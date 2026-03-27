from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.crm.models import Cliente

from .models import Comissao


@receiver(post_save, sender=Cliente)
def gerar_comissao_ao_concluir(sender, instance, **kwargs):
    """
    Ao salvar um Cliente com status 'concluida', gera comissao
    automaticamente baseada no valor total dos planos contratados.
    """
    if instance.status != Cliente.Status.CONCLUIDA:
        return

    parceiro = instance.parceiro

    if not parceiro.ativo:
        return

    # Evita duplicacao
    if Comissao.objects.filter(parceiro=parceiro, cliente=instance).exists():
        return

    # Valor total dos planos do cliente
    valor_total = Decimal("0")
    for plano in instance.planos.prefetch_related("itens").all():
        valor_total += plano.valor_total

    if valor_total <= 0:
        return

    percentual = parceiro.percentual_comissao
    valor_comissao = (valor_total * percentual / Decimal("100")).quantize(Decimal("0.01"))

    comissao = Comissao.objects.create(
        parceiro=parceiro,
        cliente=instance,
        valor_venda=valor_total,
        percentual=percentual,
        valor_comissao=valor_comissao,
    )

    # Notifica o parceiro
    from apps.crm.notifications import notificar_parceiro_do_cliente
    from apps.crm.models import Notificacao

    notificar_parceiro_do_cliente(
        instance,
        tipo=Notificacao.Tipo.COMISSAO_GERADA,
        titulo=f"Comissao de R${valor_comissao} gerada",
        mensagem=f"Cliente {instance.nome} concluido. Comissao: R${valor_comissao} ({percentual}%).",
        link=f"/comissoes/",
    )
