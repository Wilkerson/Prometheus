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


# =========================================================================
# Produtos e Planos
# =========================================================================
class Produto(models.Model):
    class Tier(models.TextChoices):
        BASICO = "basico", "Basico"
        INTERMEDIARIO = "intermediario", "Intermediario"
        AVANCADO = "avancado", "Avancado"

    nome = models.CharField("Nome", max_length=200)
    descricao = models.TextField("Descricao")
    tier = models.CharField(
        "Tier",
        max_length=20,
        choices=Tier.choices,
        default=Tier.BASICO,
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.get_tier_display()})"


class Plano(models.Model):
    """Plano vinculado a um parceiro, com produtos e precos personalizados."""

    nome = models.CharField("Nome do plano", max_length=200)
    parceiro = models.ForeignKey(
        EntidadeParceira,
        on_delete=models.CASCADE,
        related_name="planos",
    )
    produtos = models.ManyToManyField(
        Produto,
        through="PlanoProduto",
        related_name="planos",
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Plano"
        verbose_name_plural = "Planos"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome} — {self.parceiro.nome_entidade}"

    @property
    def valor_total(self):
        return self.itens.aggregate(total=models.Sum("preco"))["total"] or 0


class PlanoProduto(models.Model):
    """Tabela intermediaria: produto dentro de um plano com preco personalizado."""

    plano = models.ForeignKey(
        Plano,
        on_delete=models.CASCADE,
        related_name="itens",
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="plano_itens",
    )
    preco = models.DecimalField("Preco", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Produto do Plano"
        verbose_name_plural = "Produtos do Plano"
        unique_together = ("plano", "produto")

    def __str__(self):
        return f"{self.produto.nome} — R${self.preco}"


# =========================================================================
# Cliente
# =========================================================================
def upload_cliente_path(instance, filename):
    return f"clientes/{instance.cnpj}/{filename}"


class Cliente(models.Model):
    class Status(models.TextChoices):
        RECEBIDA = "recebida", "Recebida"
        EM_ANALISE = "em_analise", "Em Analise"
        EM_PROCESSAMENTO = "em_processamento", "Em Processamento"
        CONCLUIDA = "concluida", "Concluida"
        FALHA_IMPLANTACAO = "falha_implantacao", "Falha na Implantacao"
        PERDIDA = "perdida", "Perdida"

    TRANSICOES_VALIDAS = {
        Status.RECEBIDA: (Status.EM_ANALISE, Status.PERDIDA),
        Status.EM_ANALISE: (Status.EM_PROCESSAMENTO, Status.PERDIDA),
        Status.EM_PROCESSAMENTO: (Status.CONCLUIDA, Status.FALHA_IMPLANTACAO),
        Status.CONCLUIDA: (),
        Status.FALHA_IMPLANTACAO: (Status.EM_PROCESSAMENTO,),
        Status.PERDIDA: (),
    }

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
    planos = models.ManyToManyField(
        Plano,
        related_name="clientes",
        verbose_name="Planos contratados",
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


# =========================================================================
# Notificacoes
# =========================================================================
class Notificacao(models.Model):
    class Tipo(models.TextChoices):
        CLIENTE_NOVO = "cliente_novo", "Novo cliente cadastrado"
        CLIENTE_STATUS = "cliente_status", "Status do cliente alterado"
        CLIENTE_ZYPHER_OK = "cliente_zypher_ok", "Implantacao concluida"
        CLIENTE_ZYPHER_FALHA = "cliente_zypher_falha", "Falha na implantacao"
        COMISSAO_GERADA = "comissao_gerada", "Comissao gerada"
        COMISSAO_PAGA = "comissao_paga", "Comissao paga"
        USUARIO_CRIADO = "usuario_criado", "Novo usuario criado"
        SISTEMA = "sistema", "Sistema"

    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificacoes",
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices, default=Tipo.SISTEMA)
    titulo = models.CharField(max_length=200)
    mensagem = models.TextField(blank=True)
    link = models.CharField(max_length=300, blank=True)
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notificacao"
        verbose_name_plural = "Notificacoes"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.titulo} -> {self.destinatario}"


class PreferenciaNotificacao(models.Model):
    """Preferencias do usuario: quais tipos de notificacao deseja receber."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferencias_notificacao",
    )
    cliente_novo = models.BooleanField("Novo cliente cadastrado", default=True)
    cliente_status = models.BooleanField("Status do cliente alterado", default=True)
    cliente_zypher_ok = models.BooleanField("Implantacao concluida (Zypher)", default=True)
    cliente_zypher_falha = models.BooleanField("Falha na implantacao (Zypher)", default=True)
    comissao_gerada = models.BooleanField("Comissao gerada", default=True)
    comissao_paga = models.BooleanField("Comissao paga", default=True)
    usuario_criado = models.BooleanField("Novo usuario criado", default=True)
    sistema = models.BooleanField("Notificacoes do sistema", default=True)

    class Meta:
        verbose_name = "Preferencia de Notificacao"
        verbose_name_plural = "Preferencias de Notificacao"

    def __str__(self):
        return f"Preferencias de {self.usuario}"

    def aceita(self, tipo):
        """Verifica se o usuario aceita notificacoes deste tipo."""
        return getattr(self, tipo, True)
