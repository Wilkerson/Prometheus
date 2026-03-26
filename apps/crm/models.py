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
        "Percentual de comissao (%)",
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


class Endereco(models.Model):
    UF_CHOICES = [
        ("AC", "AC"), ("AL", "AL"), ("AP", "AP"), ("AM", "AM"), ("BA", "BA"),
        ("CE", "CE"), ("DF", "DF"), ("ES", "ES"), ("GO", "GO"), ("MA", "MA"),
        ("MT", "MT"), ("MS", "MS"), ("MG", "MG"), ("PA", "PA"), ("PB", "PB"),
        ("PR", "PR"), ("PE", "PE"), ("PI", "PI"), ("RJ", "RJ"), ("RN", "RN"),
        ("RS", "RS"), ("RO", "RO"), ("RR", "RR"), ("SC", "SC"), ("SP", "SP"),
        ("SE", "SE"), ("TO", "TO"),
    ]

    cep = models.CharField("CEP", max_length=9)
    logradouro = models.CharField("Logradouro", max_length=200)
    numero = models.CharField("Numero", max_length=20)
    complemento = models.CharField("Complemento", max_length=100, blank=True)
    bairro = models.CharField("Bairro", max_length=100)
    cidade = models.CharField("Cidade", max_length=100)
    uf = models.CharField("UF", max_length=2, choices=UF_CHOICES)

    class Meta:
        verbose_name = "Endereco"
        verbose_name_plural = "Enderecos"

    def __str__(self):
        partes = [self.logradouro, self.numero]
        if self.complemento:
            partes.append(self.complemento)
        partes.append(self.bairro)
        partes.append(f"{self.cidade} - {self.uf}")
        partes.append(f"CEP {self.cep}")
        return ", ".join(partes)


def upload_cliente_path(instance, filename):
    return f"clientes/{instance.cnpj}/{filename}"


class Cliente(models.Model):
    class Status(models.TextChoices):
        RECEBIDA = "recebida", "Recebida"
        EM_ANALISE = "em_analise", "Em Analise"
        EM_PROCESSAMENTO = "em_processamento", "Em Processamento"
        CONCLUIDA = "concluida", "Concluida"
        PERDIDA = "perdida", "Perdida"

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
        related_name="clientes",
    )
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clientes_operados",
    )
    nome = models.CharField("Nome / Razao Social", max_length=200)
    cnpj = models.CharField("CNPJ", max_length=18, unique=True)
    email = models.EmailField("Email")
    telefone = models.CharField("Telefone", max_length=20)
    endereco = models.OneToOneField(
        Endereco,
        on_delete=models.CASCADE,
        related_name="cliente",
        verbose_name="Endereco",
    )
    produto_interesse = models.CharField(
        "Produto de interesse",
        max_length=30,
        choices=Produto.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEBIDA,
    )
    arquivo = models.FileField(
        "Produtos ou Servicos",
        upload_to=upload_cliente_path,
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome} — {self.get_status_display()}"

    def pode_transitar_para(self, novo_status):
        return novo_status in self.TRANSICOES_VALIDAS.get(self.status, ())


class ClienteHistorico(models.Model):
    """Registra cada mudanca de status do cliente para timeline/SLA."""

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="historico",
    )
    status_anterior = models.CharField(max_length=20, choices=Cliente.Status.choices)
    status_novo = models.CharField(max_length=20, choices=Cliente.Status.choices)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historico do Cliente"
        verbose_name_plural = "Historicos de Clientes"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.cliente.nome}: {self.status_anterior} -> {self.status_novo}"


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
        choices=Cliente.Produto.choices,
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
