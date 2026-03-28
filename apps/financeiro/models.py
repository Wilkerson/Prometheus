from django.conf import settings
from django.db import models


# =========================================================================
# Categoria Financeira
# =========================================================================
class CategoriaFinanceira(models.Model):
    class Tipo(models.TextChoices):
        RECEITA = "receita", "Receita"
        DESPESA = "despesa", "Despesa"

    nome = models.CharField("Nome", max_length=100)
    tipo = models.CharField("Tipo", max_length=7, choices=Tipo.choices)
    pai = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcategorias",
        verbose_name="Categoria pai",
    )
    ativo = models.BooleanField("Ativo", default=True)
    ordem = models.PositiveSmallIntegerField("Ordem", default=0)

    class Meta:
        verbose_name = "Categoria financeira"
        verbose_name_plural = "Categorias financeiras"
        ordering = ["tipo", "ordem", "nome"]

    def __str__(self):
        if self.pai:
            return f"{self.pai.nome} > {self.nome}"
        return self.nome

    @property
    def is_subcategoria(self):
        return self.pai is not None


# =========================================================================
# Conta Bancaria
# =========================================================================
class ContaBancaria(models.Model):
    class TipoConta(models.TextChoices):
        CORRENTE = "corrente", "Conta corrente"
        POUPANCA = "poupanca", "Poupanca"
        PAGAMENTO = "pagamento", "Conta de pagamento"
        CAIXA = "caixa", "Caixa"

    nome = models.CharField("Nome da conta", max_length=100)
    tipo = models.CharField("Tipo", max_length=10, choices=TipoConta.choices)
    banco = models.CharField("Banco", max_length=100, blank=True)
    agencia = models.CharField("Agencia", max_length=20, blank=True)
    numero = models.CharField("Numero da conta", max_length=30, blank=True)
    saldo_inicial = models.DecimalField(
        "Saldo inicial",
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Saldo na data de abertura no sistema",
    )
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Conta bancaria"
        verbose_name_plural = "Contas bancarias"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def saldo_atual(self):
        """Saldo = saldo_inicial + receitas confirmadas - despesas confirmadas."""
        from django.db.models import Sum, Q
        resultado = self.lancamentos.filter(
            status=Lancamento.Status.CONFIRMADO
        ).aggregate(
            receitas=Sum("valor", filter=Q(tipo="receita")),
            despesas=Sum("valor", filter=Q(tipo="despesa")),
        )
        receitas = resultado["receitas"] or 0
        despesas = resultado["despesas"] or 0
        return self.saldo_inicial + receitas - despesas


# =========================================================================
# Lancamento (CORE)
# =========================================================================
class Lancamento(models.Model):
    class Tipo(models.TextChoices):
        RECEITA = "receita", "Receita"
        DESPESA = "despesa", "Despesa"

    class Status(models.TextChoices):
        PREVISTO = "previsto", "Previsto"
        PENDENTE = "pendente", "Pendente"
        CONFIRMADO = "confirmado", "Confirmado"
        CANCELADO = "cancelado", "Cancelado"

    class Canal(models.TextChoices):
        MANUAL = "manual", "Manual"
        PIX = "pix", "Pix"
        TED = "ted", "TED / DOC"
        BOLETO = "boleto", "Boleto"
        CARTAO = "cartao", "Cartao"
        DINHEIRO = "dinheiro", "Dinheiro"
        GATEWAY = "gateway", "Gateway (Asaas)"
        SISTEMA = "sistema", "Gerado pelo sistema"

    # Tipo e descricao
    tipo = models.CharField("Tipo", max_length=7, choices=Tipo.choices)
    descricao = models.CharField("Descricao", max_length=300)

    # Valores
    valor = models.DecimalField("Valor bruto", max_digits=12, decimal_places=2)
    valor_liquido = models.DecimalField(
        "Valor liquido",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Apos taxas do gateway (se aplicavel)",
    )

    # Classificacao
    categoria = models.ForeignKey(
        CategoriaFinanceira,
        on_delete=models.PROTECT,
        related_name="lancamentos",
        verbose_name="Categoria",
    )
    conta = models.ForeignKey(
        ContaBancaria,
        on_delete=models.PROTECT,
        related_name="lancamentos",
        verbose_name="Conta bancaria",
    )
    departamento = models.ForeignKey(
        "rh.Departamento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lancamentos",
        verbose_name="Centro de custo",
    )

    # Canal
    canal = models.CharField(
        "Canal de origem",
        max_length=10,
        choices=Canal.choices,
        default=Canal.MANUAL,
    )

    # Datas
    data_vencimento = models.DateField("Data de vencimento")
    data_competencia = models.DateField(
        "Data de competencia",
        null=True,
        blank=True,
        help_text="Regime de competencia (fato gerador)",
    )
    data_pagamento = models.DateField(
        "Data de pagamento",
        null=True,
        blank=True,
    )

    # Status
    status = models.CharField(
        "Status",
        max_length=10,
        choices=Status.choices,
        default=Status.PENDENTE,
    )

    # Vinculos opcionais (CRM)
    cliente = models.ForeignKey(
        "crm.Cliente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lancamentos",
        verbose_name="Cliente vinculado",
    )
    parceiro = models.ForeignKey(
        "crm.EntidadeParceira",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lancamentos",
        verbose_name="Parceiro vinculado",
    )

    # Rastreabilidade
    id_externo = models.CharField(
        "ID externo (gateway)",
        max_length=100,
        blank=True,
        help_text="Para rastreabilidade com sistemas externos",
    )
    observacao = models.TextField("Observacao", blank=True)
    comprovante = models.FileField(
        "Comprovante",
        upload_to="financeiro/comprovantes/%Y/%m/",
        blank=True,
    )

    # Auditoria
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lancamentos_criados",
        verbose_name="Criado por",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lancamento"
        verbose_name_plural = "Lancamentos"
        ordering = ["-data_vencimento", "-criado_em"]

    def __str__(self):
        sinal = "+" if self.tipo == self.Tipo.RECEITA else "-"
        return f"{sinal} R${self.valor} — {self.descricao}"

    def save(self, *args, **kwargs):
        if not self.data_competencia:
            self.data_competencia = self.data_vencimento
        if self.valor_liquido is None:
            self.valor_liquido = self.valor
        super().save(*args, **kwargs)
