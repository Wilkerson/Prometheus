from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.crm.models import ProdutoContratado

from .models import Comissao


@receiver(post_save, sender=ProdutoContratado)
def gerar_comissao(sender, instance, created, **kwargs):
    """
    Ao criar um ProdutoContratado, gera automaticamente a comissao
    para o parceiro do cliente.
    """
    if not created:
        return

    cliente = instance.cliente
    parceiro = cliente.parceiro

    if not parceiro.ativo:
        return

    if Comissao.objects.filter(parceiro=parceiro, venda=instance).exists():
        return

    percentual = parceiro.percentual_comissao
    valor_comissao = (instance.valor * percentual / Decimal("100")).quantize(Decimal("0.01"))

    Comissao.objects.create(
        parceiro=parceiro,
        venda=instance,
        valor_venda=instance.valor,
        percentual=percentual,
        valor_comissao=valor_comissao,
    )
