from django.conf import settings
from django.db import models


class EntidadeParceira(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="parceiro",
    )
    nome_entidade = models.CharField("Nome da entidade", max_length=200)
    percentual_comissao = models.DecimalField(
        "Percentual de comissão (%)",
        max_digits=5,
        decimal_places=2,
        default=10.00,
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Entidade Parceira"
        verbose_name_plural = "Entidades Parceiras"
        ordering = ["-criado_em"]

    def __str__(self):
        return self.nome_entidade


class Lead(models.Model):
    class Status(models.TextChoices):
        RECEBIDA = "recebida", "Recebida"
        EM_ANALISE = "em_analise", "Em Análise"
        EM_PROCESSAMENTO = "em_processamento", "Em Processamento"
        CONCLUIDA = "concluida", "Concluída"
        PERDIDA = "perdida", "Perdida"

    # Transições válidas de status
    TRANSICOES_VALIDAS = {
        Status.RECEBIDA: (Status.EM_ANALISE, Status.PERDIDA),
        Status.EM_ANALISE: (Status.EM_PROCESSAMENTO, Status.PERDIDA),
        Status.EM_PROCESSAMENTO: (Status.CONCLUIDA, Status.PERDIDA),
        Status.CONCLUIDA: (),
        Status.PERDIDA: (),
    }

    class Produto(models.TextChoices):
        AGENTES_IA = "agentes_ia", "Agentes de IA"
        SAAS = "saas", "SaaS"
        CRM = "crm", "CRM"
        ERP = "erp", "ERP"
        SITES = "sites", "Sites"
        CONSULTORIA = "consultoria", "Consultoria"

    parceiro = models.ForeignKey(
        EntidadeParceira,
        on_delete=models.CASCADE,
        related_name="leads",
    )
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads_operados",
    )
    nome = models.CharField(max_length=200)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True)
    produto_interesse = models.CharField(
        max_length=30,
        choices=Produto.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEBIDA,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome} — {self.get_status_display()}"

    def pode_transitar_para(self, novo_status):
        """Verifica se a transição de status é válida."""
        return novo_status in self.TRANSICOES_VALIDAS.get(self.status, ())


class LeadHistorico(models.Model):
    """Registra cada mudança de status do lead para timeline/SLA."""

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="historico",
    )
    status_anterior = models.CharField(max_length=20, choices=Lead.Status.choices)
    status_novo = models.CharField(max_length=20, choices=Lead.Status.choices)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Histórico do Lead"
        verbose_name_plural = "Históricos de Leads"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.lead.nome}: {self.status_anterior} → {self.status_novo}"


def upload_cliente_path(instance, filename):
    return f"clientes/{instance.cnpj}/{filename}"


class Cliente(models.Model):
    lead = models.OneToOneField(
        Lead,
        on_delete=models.CASCADE,
        related_name="cliente",
    )
    nome = models.CharField(max_length=200)
    cnpj = models.CharField("CNPJ", max_length=18, unique=True)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True)
    endereco = models.CharField("Endereco", max_length=300, blank=True)
    cep = models.CharField("CEP", max_length=9, blank=True)
    arquivo = models.FileField(
        "Produtos ou Servicos",
        upload_to=upload_cliente_path,
        blank=True,
        null=True,
    )
    ativo = models.BooleanField(default=True)
    ativado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["-ativado_em"]

    def __str__(self):
        return self.nome


class ProdutoContratado(models.Model):
    class Status(models.TextChoices):
        ATIVO = "ativo", "Ativo"
        SUSPENSO = "suspenso", "Suspenso"
        CANCELADO = "cancelado", "Cancelado"

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="produtos",
    )
    produto = models.CharField(
        max_length=30,
        choices=Lead.Produto.choices,
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ATIVO,
    )
    contratado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Produto Contratado"
        verbose_name_plural = "Produtos Contratados"
        ordering = ["-contratado_em"]

    def __str__(self):
        return f"{self.get_produto_display()} — {self.cliente.nome}"
