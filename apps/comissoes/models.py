from django.db import models

from apps.crm.models import EntidadeParceira, ProdutoContratado


class Comissao(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        PAGO = "pago", "Pago"

    parceiro = models.ForeignKey(
        EntidadeParceira,
        on_delete=models.CASCADE,
        related_name="comissoes",
    )
    venda = models.ForeignKey(
        ProdutoContratado,
        on_delete=models.CASCADE,
        related_name="comissoes",
    )
    valor_venda = models.DecimalField(max_digits=12, decimal_places=2)
    percentual = models.DecimalField(max_digits=5, decimal_places=2)
    valor_comissao = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    gerado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Comissão"
        verbose_name_plural = "Comissões"
        ordering = ["-gerado_em"]

    def __str__(self):
        return f"Comissão {self.parceiro} — R${self.valor_comissao}"
