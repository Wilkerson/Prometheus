from django.conf import settings
from django.db import models


class Departamento(models.Model):
    """Departamento do sistema — criado automaticamente com cada modulo.
    Nao deve ser criado/excluido manualmente pelo usuario.
    """
    nome = models.CharField("Nome", max_length=100, unique=True)
    slug = models.SlugField("Identificador", max_length=50, unique=True)
    descricao = models.TextField("Descricao", blank=True)
    icone = models.CharField("Icone", max_length=10, blank=True)
    ordem = models.PositiveSmallIntegerField("Ordem na sidebar", default=0)
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome


# Departamentos do sistema — seedados automaticamente
DEPARTAMENTOS_SISTEMA = [
    {"slug": "comercial", "nome": "Comercial", "ordem": 1},
    {"slug": "financeiro", "nome": "Financeiro", "ordem": 2},
    {"slug": "rh", "nome": "RH / Pessoas", "ordem": 3},
    {"slug": "marketing", "nome": "Marketing", "ordem": 4},
    {"slug": "tecnologia", "nome": "Tecnologia", "ordem": 5},
    {"slug": "juridico", "nome": "Juridico", "ordem": 6},
    {"slug": "operacoes", "nome": "Operacoes", "ordem": 7},
    {"slug": "produto", "nome": "Produto", "ordem": 8},
]


class Setor(models.Model):
    """Setor de trabalho — subdivisao de um departamento, gerenciado pelo usuario."""
    nome = models.CharField("Nome", max_length=100)
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name="setores",
        verbose_name="Departamento",
    )
    descricao = models.TextField("Descricao", blank=True)
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"
        ordering = ["departamento__nome", "nome"]
        unique_together = [("nome", "departamento")]

    def __str__(self):
        return f"{self.nome} ({self.departamento.nome})"


class Cargo(models.Model):
    class Nivel(models.TextChoices):
        DIRETOR = "diretor", "Diretor"
        GERENTE = "gerente", "Gerente"
        ESPECIALISTA = "especialista", "Especialista"
        ANALISTA = "analista", "Analista"
        ASSISTENTE = "assistente", "Assistente"
        ESTAGIARIO = "estagiario", "Estagiario"

    nome = models.CharField("Nome do cargo", max_length=100)
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name="cargos",
        verbose_name="Departamento",
    )
    nivel = models.CharField(
        "Nivel hierarquico",
        max_length=20,
        choices=Nivel.choices,
        default=Nivel.ANALISTA,
    )
    faixa_salarial_min = models.DecimalField(
        "Faixa salarial minima",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    faixa_salarial_max = models.DecimalField(
        "Faixa salarial maxima",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    descricao = models.TextField("Descricao de responsabilidades", blank=True)
    requisitos = models.TextField("Requisitos minimos", blank=True)
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"
        ordering = ["departamento__nome", "nome"]
        unique_together = [("nome", "departamento")]

    def __str__(self):
        return f"{self.nome} ({self.departamento.nome})"

    @property
    def faixa_salarial_display(self):
        if self.faixa_salarial_min and self.faixa_salarial_max:
            return f"R$ {self.faixa_salarial_min:,.2f} - R$ {self.faixa_salarial_max:,.2f}"
        if self.faixa_salarial_min:
            return f"A partir de R$ {self.faixa_salarial_min:,.2f}"
        if self.faixa_salarial_max:
            return f"Ate R$ {self.faixa_salarial_max:,.2f}"
        return "Nao definida"


class Colaborador(models.Model):
    class TipoContrato(models.TextChoices):
        CLT = "clt", "CLT"
        PJ = "pj", "PJ"

    class Status(models.TextChoices):
        ATIVO = "ativo", "Ativo"
        AFASTADO = "afastado", "Afastado"
        DESLIGADO = "desligado", "Desligado"

    class RegimeTrabalho(models.TextChoices):
        PRESENCIAL = "presencial", "Presencial"
        REMOTO = "remoto", "Remoto"
        HIBRIDO = "hibrido", "Hibrido"

    # --- Dados pessoais ---
    nome_completo = models.CharField("Nome completo", max_length=200)
    cpf = models.CharField("CPF", max_length=14, unique=True)
    data_nascimento = models.DateField("Data de nascimento")
    endereco = models.OneToOneField(
        "crm.Endereco",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="colaborador",
        verbose_name="Endereco",
    )
    telefone = models.CharField("Telefone", max_length=20)
    email_pessoal = models.EmailField("E-mail pessoal")
    contato_emergencia_nome = models.CharField(
        "Contato de emergencia — nome", max_length=200, blank=True
    )
    contato_emergencia_telefone = models.CharField(
        "Contato de emergencia — telefone", max_length=20, blank=True
    )

    # --- Dados contratuais ---
    tipo_contrato = models.CharField(
        "Tipo de contrato",
        max_length=3,
        choices=TipoContrato.choices,
    )
    data_admissao = models.DateField("Data de admissao")
    data_desligamento = models.DateField("Data de desligamento", null=True, blank=True)
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.PROTECT,
        related_name="colaboradores",
        verbose_name="Cargo",
    )
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name="colaboradores",
        verbose_name="Departamento",
    )
    setor = models.ForeignKey(
        Setor,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="colaboradores",
        verbose_name="Setor",
    )
    remuneracao = models.DecimalField(
        "Remuneracao atual (R$)",
        max_digits=10,
        decimal_places=2,
    )
    carga_horaria_semanal = models.PositiveSmallIntegerField(
        "Carga horaria semanal (h)", default=40
    )
    status = models.CharField(
        "Status",
        max_length=10,
        choices=Status.choices,
        default=Status.ATIVO,
    )

    # --- Campos especificos CLT ---
    pis_nit = models.CharField("PIS / NIT", max_length=20, blank=True)
    ctps_numero = models.CharField("CTPS — numero", max_length=20, blank=True)
    ctps_serie = models.CharField("CTPS — serie", max_length=10, blank=True)
    banco_deposito = models.CharField(
        "Banco para deposito de salario", max_length=100, blank=True
    )
    regime_trabalho = models.CharField(
        "Regime de trabalho",
        max_length=12,
        choices=RegimeTrabalho.choices,
        blank=True,
    )

    # --- Campos especificos PJ ---
    cnpj_pj = models.CharField("CNPJ ou CPF (MEI)", max_length=18, blank=True)
    razao_social = models.CharField("Razao social", max_length=200, blank=True)
    banco_pagamento_pj = models.CharField(
        "Banco para pagamento PJ", max_length=100, blank=True
    )
    chave_pix = models.CharField("Chave Pix", max_length=100, blank=True)

    # --- Vinculo com usuario do sistema (opcional) ---
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="colaborador",
        verbose_name="Usuario do sistema",
    )

    # --- Meta ---
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Colaborador"
        verbose_name_plural = "Colaboradores"
        ordering = ["nome_completo"]

    def __str__(self):
        return self.nome_completo

    @property
    def is_clt(self):
        return self.tipo_contrato == self.TipoContrato.CLT

    @property
    def is_pj(self):
        return self.tipo_contrato == self.TipoContrato.PJ


class HistoricoColaborador(models.Model):
    class TipoEvento(models.TextChoices):
        ADMISSAO = "admissao", "Admissao"
        PROMOCAO = "promocao", "Promocao"
        TRANSFERENCIA = "transferencia", "Transferencia de departamento"
        REAJUSTE = "reajuste", "Reajuste salarial"
        AFASTAMENTO = "afastamento", "Afastamento"
        RETORNO = "retorno", "Retorno de afastamento"
        DESLIGAMENTO = "desligamento", "Desligamento"

    colaborador = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        related_name="historico",
        verbose_name="Colaborador",
    )
    tipo = models.CharField(
        "Tipo de evento",
        max_length=15,
        choices=TipoEvento.choices,
    )
    cargo_anterior = models.CharField("Cargo anterior", max_length=100, blank=True)
    cargo_novo = models.CharField("Cargo novo", max_length=100, blank=True)
    departamento_anterior = models.CharField(
        "Departamento anterior", max_length=100, blank=True
    )
    departamento_novo = models.CharField(
        "Departamento novo", max_length=100, blank=True
    )
    remuneracao_anterior = models.DecimalField(
        "Remuneracao anterior",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    remuneracao_nova = models.DecimalField(
        "Remuneracao nova",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    observacao = models.TextField("Observacao", blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historicos_rh_registrados",
        verbose_name="Registrado por",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historico do colaborador"
        verbose_name_plural = "Historicos dos colaboradores"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.colaborador} — {self.get_tipo_display()} em {self.criado_em:%d/%m/%Y}"
