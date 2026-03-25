from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.crm.models import ProdutoContratado

from .models import Comissao


@receiver(post_save, sender=ProdutoContratado)
def gerar_comissao(sender, instance, created, **kwargs):
    """
    Ao criar um ProdutoContratado, gera automaticamente a comissão
    para o parceiro que indicou o lead, se houver.
    """
    if not created:
        return

    cliente = instance.cliente

    if not hasattr(cliente, "lead"):
        return

    lead = cliente.lead

    if not hasattr(lead, "parceiro"):
        return

    parceiro = lead.parceiro

    if not parceiro.ativo:
        return

    # Evita duplicação
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
