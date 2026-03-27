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


# =========================================================================
# Documentos
# =========================================================================
class DocumentoColaborador(models.Model):
    class TipoDocumento(models.TextChoices):
        CONTRATO_CLT = "contrato_clt", "Contrato de trabalho"
        CONTRATO_PJ = "contrato_pj", "Contrato de prestacao de servicos"
        NDA = "nda", "NDA / Confidencialidade"
        ADITIVO = "aditivo", "Aditivo contratual"
        EXAME_ADMISSIONAL = "exame_admissional", "Exame admissional"
        EXAME_DEMISSIONAL = "exame_demissional", "Exame demissional"
        TERMO_RESCISAO = "termo_rescisao", "Termo de rescisao"
        DISTRATO = "distrato", "Distrato"
        CERTIFICADO = "certificado", "Certificado / Diploma"
        OUTRO = "outro", "Outro documento"

    colaborador = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        related_name="documentos",
        verbose_name="Colaborador",
    )
    tipo = models.CharField(
        "Tipo de documento",
        max_length=20,
        choices=TipoDocumento.choices,
    )
    nome = models.CharField("Nome / Descricao", max_length=200)
    arquivo = models.FileField("Arquivo", upload_to="rh/documentos/%Y/%m/")
    data_emissao = models.DateField("Data de emissao", null=True, blank=True)
    data_vencimento = models.DateField("Data de vencimento", null=True, blank=True)
    alerta_dias_antes = models.PositiveSmallIntegerField(
        "Alertar X dias antes do vencimento",
        default=30,
    )
    observacao = models.TextField("Observacao", blank=True)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_rh_enviados",
        verbose_name="Enviado por",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Documento do colaborador"
        verbose_name_plural = "Documentos dos colaboradores"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome} — {self.colaborador}"

    @property
    def vencido(self):
        if not self.data_vencimento:
            return False
        from django.utils import timezone
        return self.data_vencimento < timezone.now().date()

    @property
    def proximo_vencimento(self):
        if not self.data_vencimento:
            return False
        from django.utils import timezone
        delta = (self.data_vencimento - timezone.now().date()).days
        return 0 <= delta <= self.alerta_dias_antes


# =========================================================================
# Onboarding — Templates e Checklists
# =========================================================================
class OnboardingTemplate(models.Model):
    """Template reutilizavel de checklist de onboarding."""
    nome = models.CharField("Nome do template", max_length=100)
    tipo_contrato = models.CharField(
        "Tipo de contrato",
        max_length=3,
        choices=Colaborador.TipoContrato.choices,
        blank=True,
        help_text="Deixe vazio para ambos os tipos",
    )
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_templates",
        verbose_name="Departamento",
        help_text="Deixe vazio para todos os departamentos",
    )
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Template de onboarding"
        verbose_name_plural = "Templates de onboarding"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class OnboardingTemplateItem(models.Model):
    class Fase(models.TextChoices):
        ANTES = "antes", "Antes do 1o dia"
        PRIMEIRO_DIA = "primeiro_dia", "Primeiro dia"
        PRIMEIRA_SEMANA = "primeira_semana", "Primeira semana"
        PRIMEIRO_MES = "primeiro_mes", "Primeiro mes"

    template = models.ForeignKey(
        OnboardingTemplate,
        on_delete=models.CASCADE,
        related_name="itens",
        verbose_name="Template",
    )
    fase = models.CharField(
        "Fase",
        max_length=20,
        choices=Fase.choices,
    )
    descricao = models.CharField("Descricao da tarefa", max_length=300)
    ordem = models.PositiveSmallIntegerField("Ordem", default=0)

    class Meta:
        verbose_name = "Item do template"
        verbose_name_plural = "Itens do template"
        ordering = ["fase", "ordem"]

    def __str__(self):
        return self.descricao


class OnboardingColaborador(models.Model):
    """Checklist de onboarding instanciado para um colaborador especifico."""
    colaborador = models.OneToOneField(
        Colaborador,
        on_delete=models.CASCADE,
        related_name="onboarding",
        verbose_name="Colaborador",
    )
    template = models.ForeignKey(
        OnboardingTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instancias",
        verbose_name="Template usado",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    concluido_em = models.DateTimeField("Concluido em", null=True, blank=True)

    class Meta:
        verbose_name = "Onboarding do colaborador"
        verbose_name_plural = "Onboardings dos colaboradores"

    def __str__(self):
        return f"Onboarding — {self.colaborador}"

    @property
    def total_itens(self):
        return self.itens.count()

    @property
    def itens_concluidos(self):
        return self.itens.filter(concluido=True).count()

    @property
    def progresso(self):
        total = self.total_itens
        if total == 0:
            return 0
        return round((self.itens_concluidos / total) * 100)


class OnboardingItem(models.Model):
    """Item concreto do checklist de um colaborador."""
    onboarding = models.ForeignKey(
        OnboardingColaborador,
        on_delete=models.CASCADE,
        related_name="itens",
        verbose_name="Onboarding",
    )
    fase = models.CharField(
        "Fase",
        max_length=20,
        choices=OnboardingTemplateItem.Fase.choices,
    )
    descricao = models.CharField("Descricao", max_length=300)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_itens_responsavel",
        verbose_name="Responsavel",
    )
    prazo = models.DateField("Prazo", null=True, blank=True)
    concluido = models.BooleanField("Concluido", default=False)
    concluido_em = models.DateTimeField("Concluido em", null=True, blank=True)
    ordem = models.PositiveSmallIntegerField("Ordem", default=0)

    class Meta:
        verbose_name = "Item do onboarding"
        verbose_name_plural = "Itens do onboarding"
        ordering = ["fase", "ordem"]

    def __str__(self):
        return self.descricao

    @property
    def atrasado(self):
        if self.concluido or not self.prazo:
            return False
        from django.utils import timezone
        return self.prazo < timezone.now().date()


# =========================================================================
# Ferias e Ausencias
# =========================================================================
class SolicitacaoAusencia(models.Model):
    class TipoAusencia(models.TextChoices):
        FERIAS = "ferias", "Ferias"
        RECESSO = "recesso", "Recesso (PJ)"
        ATESTADO = "atestado", "Atestado medico"
        LICENCA_MATERNIDADE = "licenca_maternidade", "Licenca maternidade"
        LICENCA_PATERNIDADE = "licenca_paternidade", "Licenca paternidade"
        FOLGA_COMPENSATORIA = "folga_compensatoria", "Folga compensatoria"
        LUTO = "luto", "Luto (falecimento)"
        NUPCIAIS = "nupciais", "Licenca nupcial (casamento)"
        FALTA_JUSTIFICADA = "falta_justificada", "Falta justificada"
        FALTA_INJUSTIFICADA = "falta_injustificada", "Falta injustificada"

    class StatusSolicitacao(models.TextChoices):
        SOLICITADA = "solicitada", "Solicitada"
        APROVADA = "aprovada", "Aprovada"
        REJEITADA = "rejeitada", "Rejeitada"
        CANCELADA = "cancelada", "Cancelada"

    colaborador = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        related_name="ausencias",
        verbose_name="Colaborador",
    )
    tipo = models.CharField(
        "Tipo de ausencia",
        max_length=25,
        choices=TipoAusencia.choices,
    )
    data_inicio = models.DateField("Data inicio")
    data_fim = models.DateField("Data fim")
    total_dias = models.PositiveSmallIntegerField("Total de dias")
    observacao = models.TextField("Observacao", blank=True)
    status = models.CharField(
        "Status",
        max_length=12,
        choices=StatusSolicitacao.choices,
        default=StatusSolicitacao.SOLICITADA,
    )
    aprovado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ausencias_aprovadas",
        verbose_name="Aprovado/Rejeitado por",
    )
    justificativa_rejeicao = models.TextField("Justificativa da rejeicao", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Solicitacao de ausencia"
        verbose_name_plural = "Solicitacoes de ausencia"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.colaborador} — {self.get_tipo_display()} ({self.data_inicio} a {self.data_fim})"

    def save(self, *args, **kwargs):
        if self.data_inicio and self.data_fim:
            self.total_dias = (self.data_fim - self.data_inicio).days + 1
        super().save(*args, **kwargs)


class SaldoFerias(models.Model):
    """Controle de saldo de ferias por periodo aquisitivo (CLT)."""
    colaborador = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        related_name="saldos_ferias",
        verbose_name="Colaborador",
    )
    periodo_inicio = models.DateField("Inicio do periodo aquisitivo")
    periodo_fim = models.DateField("Fim do periodo aquisitivo")
    dias_direito = models.PositiveSmallIntegerField("Dias de direito", default=30)
    dias_usufruidos = models.PositiveSmallIntegerField("Dias usufruidos", default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Saldo de ferias"
        verbose_name_plural = "Saldos de ferias"
        ordering = ["-periodo_inicio"]

    def __str__(self):
        return f"{self.colaborador} — {self.periodo_inicio:%d/%m/%Y} a {self.periodo_fim:%d/%m/%Y}"

    @property
    def saldo_disponivel(self):
        return self.dias_direito - self.dias_usufruidos

    @property
    def vencidas(self):
        """Ferias vencem se nao tiradas ate 12 meses apos fim do periodo aquisitivo."""
        from django.utils import timezone
        limite = self.periodo_fim + timezone.timedelta(days=365)
        return timezone.now().date() > limite and self.saldo_disponivel > 0


# =========================================================================
# Treinamento e Capacitacao
# =========================================================================
class Treinamento(models.Model):
    class TipoTreinamento(models.TextChoices):
        TECNICO_INTERNO = "tecnico_interno", "Tecnico interno"
        TECNICO_EXTERNO = "tecnico_externo", "Tecnico externo"
        COMPORTAMENTAL = "comportamental", "Comportamental"
        COMPLIANCE = "compliance", "Compliance"
        ONBOARDING = "onboarding", "Onboarding"

    class Modalidade(models.TextChoices):
        PRESENCIAL = "presencial", "Presencial"
        ONLINE = "online", "Online"
        HIBRIDO = "hibrido", "Hibrido"

    nome = models.CharField("Nome do treinamento", max_length=200)
    tipo = models.CharField(
        "Tipo",
        max_length=20,
        choices=TipoTreinamento.choices,
    )
    modalidade = models.CharField(
        "Modalidade",
        max_length=12,
        choices=Modalidade.choices,
        default=Modalidade.ONLINE,
    )
    carga_horaria = models.PositiveSmallIntegerField("Carga horaria (h)", default=1)
    instituicao = models.CharField("Instituicao / Plataforma", max_length=200, blank=True)
    descricao = models.TextField("Descricao", blank=True)
    obrigatorio = models.BooleanField("Obrigatorio", default=False)
    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Treinamento"
        verbose_name_plural = "Treinamentos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class ParticipacaoTreinamento(models.Model):
    class StatusParticipacao(models.TextChoices):
        INSCRITO = "inscrito", "Inscrito"
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        CONCLUIDO = "concluido", "Concluido"
        CANCELADO = "cancelado", "Cancelado"

    colaborador = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        related_name="treinamentos",
        verbose_name="Colaborador",
    )
    treinamento = models.ForeignKey(
        Treinamento,
        on_delete=models.CASCADE,
        related_name="participacoes",
        verbose_name="Treinamento",
    )
    data_inicio = models.DateField("Data de inicio", null=True, blank=True)
    data_conclusao = models.DateField("Data de conclusao", null=True, blank=True)
    status = models.CharField(
        "Status",
        max_length=15,
        choices=StatusParticipacao.choices,
        default=StatusParticipacao.INSCRITO,
    )
    nota = models.DecimalField(
        "Nota / Aprovacao",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    certificado = models.FileField(
        "Certificado",
        upload_to="rh/certificados/%Y/%m/",
        blank=True,
    )
    observacao = models.TextField("Observacao", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Participacao em treinamento"
        verbose_name_plural = "Participacoes em treinamentos"
        ordering = ["-criado_em"]
        unique_together = [("colaborador", "treinamento")]

    def __str__(self):
        return f"{self.colaborador} — {self.treinamento}"
