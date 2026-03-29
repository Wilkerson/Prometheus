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

    _skip_audit = False  # Flag para pular log legado quando view ja registrou

    def get_mudancas(self):
        """Retorna dict de mudancas comparando com o estado no banco."""
        if not self.pk:
            return {}
        try:
            antigo = Lancamento.objects.get(pk=self.pk)
        except Lancamento.DoesNotExist:
            return {}
        mudancas = {}
        for field in ["descricao", "valor", "valor_liquido", "status",
                      "data_vencimento", "data_pagamento", "categoria_id",
                      "conta_id", "canal", "observacao"]:
            val_antigo = getattr(antigo, field)
            val_novo = getattr(self, field)
            if str(val_antigo) != str(val_novo):
                mudancas[field] = {"de": str(val_antigo), "para": str(val_novo)}
        return mudancas

    def save(self, *args, **kwargs):
        # Registrar auditoria se e uma edicao (pk ja existe)
        if self.pk and not self._skip_audit:
            mudancas = self.get_mudancas()
            if mudancas:
                AuditoriaLancamento.objects.create(
                    lancamento=self,
                    acao="edicao",
                    detalhes="; ".join(f"{k}: {v['de']} → {v['para']}" for k, v in mudancas.items()),
                )
        self._skip_audit = False  # Reset flag

        if not self.data_competencia:
            self.data_competencia = self.data_vencimento
        if self.valor_liquido is None:
            self.valor_liquido = self.valor
        super().save(*args, **kwargs)


# =========================================================================
# Auditoria de Lancamentos
# =========================================================================
class AuditoriaLancamento(models.Model):
    """Log imutavel de todas as alteracoes em lancamentos."""
    lancamento = models.ForeignKey(
        Lancamento, on_delete=models.CASCADE,
        related_name="auditoria", verbose_name="Lançamento",
    )
    acao = models.CharField("Ação", max_length=20)
    detalhes = models.TextField("Detalhes da alteração")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Usuário",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Auditoria de lançamento"
        verbose_name_plural = "Auditorias de lançamentos"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.acao} — {self.lancamento} ({self.criado_em:%d/%m/%Y %H:%M})"


# =========================================================================
# Cobranca (Contas a Receber)
# =========================================================================
class Cobranca(models.Model):
    class TipoCobranca(models.TextChoices):
        IMPLANTACAO = "implantacao", "Implantação"
        MENSALIDADE = "mensalidade", "Mensalidade"
        AVULSA = "avulsa", "Avulsa (projeto/consultoria)"
        PARCELADA = "parcelada", "Parcelada"

    class StatusCobranca(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        PAGO = "pago", "Pago"
        VENCIDO = "vencido", "Vencido"
        CANCELADO = "cancelado", "Cancelado"

    cliente = models.ForeignKey(
        "crm.Cliente",
        on_delete=models.CASCADE,
        related_name="cobrancas",
        verbose_name="Cliente",
    )
    plano = models.ForeignKey(
        "crm.Plano",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cobrancas",
        verbose_name="Plano vinculado",
    )
    tipo = models.CharField("Tipo", max_length=12, choices=TipoCobranca.choices)
    descricao = models.CharField("Descrição", max_length=300)
    valor = models.DecimalField("Valor", max_digits=12, decimal_places=2)
    vencimento = models.DateField("Vencimento")
    status = models.CharField(
        "Status", max_length=10, choices=StatusCobranca.choices,
        default=StatusCobranca.PENDENTE,
    )
    canal = models.CharField(
        "Canal de cobrança", max_length=10,
        choices=Lancamento.Canal.choices, default=Lancamento.Canal.MANUAL,
    )
    data_pagamento = models.DateField("Data de pagamento", null=True, blank=True)
    lancamento = models.OneToOneField(
        Lancamento, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="cobranca_origem", verbose_name="Lançamento gerado",
    )
    nota_fiscal = models.ForeignKey(
        "NotaFiscal", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="cobrancas", verbose_name="NF vinculada",
    )
    observacao = models.TextField("Observação", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cobrança"
        verbose_name_plural = "Cobranças"
        ordering = ["-vencimento"]

    def __str__(self):
        return f"{self.cliente.nome} — R${self.valor} ({self.get_tipo_display()})"

    @property
    def esta_vencido(self):
        if self.status in ("pago", "cancelado"):
            return False
        from django.utils import timezone
        return self.vencimento < timezone.now().date()


# =========================================================================
# Despesa (Contas a Pagar)
# =========================================================================
class Despesa(models.Model):
    class Recorrencia(models.TextChoices):
        UNICO = "unico", "Único"
        MENSAL = "mensal", "Mensal"
        TRIMESTRAL = "trimestral", "Trimestral"
        ANUAL = "anual", "Anual"

    class StatusDespesa(models.TextChoices):
        AGENDADO = "agendado", "Agendado"
        PAGO = "pago", "Pago"
        VENCIDO = "vencido", "Vencido"
        CANCELADO = "cancelado", "Cancelado"

    fornecedor = models.CharField("Fornecedor / Beneficiário", max_length=200)
    descricao = models.CharField("Descrição", max_length=300)
    categoria = models.ForeignKey(
        CategoriaFinanceira, on_delete=models.PROTECT,
        related_name="despesas", verbose_name="Categoria",
    )
    valor = models.DecimalField("Valor", max_digits=12, decimal_places=2)
    vencimento = models.DateField("Vencimento")
    recorrencia = models.CharField(
        "Recorrência", max_length=11, choices=Recorrencia.choices,
        default=Recorrencia.UNICO,
    )
    status = models.CharField(
        "Status", max_length=10, choices=StatusDespesa.choices,
        default=StatusDespesa.AGENDADO,
    )
    conta = models.ForeignKey(
        ContaBancaria, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="despesas", verbose_name="Conta de pagamento",
    )
    departamento = models.ForeignKey(
        "rh.Departamento", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="despesas", verbose_name="Centro de custo",
    )
    data_pagamento = models.DateField("Data de pagamento", null=True, blank=True)
    comprovante = models.FileField(
        "Comprovante", upload_to="financeiro/comprovantes_desp/%Y/%m/", blank=True,
    )
    lancamento = models.OneToOneField(
        Lancamento, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="despesa_origem", verbose_name="Lançamento gerado",
    )
    nota_fiscal = models.ForeignKey(
        "NotaFiscal", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="despesas", verbose_name="NF vinculada",
    )
    observacao = models.TextField("Observação", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Despesa"
        verbose_name_plural = "Despesas"
        ordering = ["-vencimento"]

    def __str__(self):
        return f"{self.fornecedor} — R${self.valor} ({self.get_recorrencia_display()})"

    @property
    def esta_vencido(self):
        if self.status in ("pago", "cancelado"):
            return False
        from django.utils import timezone
        return self.vencimento < timezone.now().date()


# =========================================================================
# Nota Fiscal
# =========================================================================
class NotaFiscal(models.Model):
    class TipoNF(models.TextChoices):
        EMITIDA = "emitida", "Emitida (para cliente)"
        RECEBIDA = "recebida", "Recebida (de fornecedor)"

    tipo = models.CharField("Tipo", max_length=8, choices=TipoNF.choices)
    numero = models.CharField("Número da NF", max_length=50)
    valor = models.DecimalField("Valor", max_digits=12, decimal_places=2)
    data_emissao = models.DateField("Data de emissão")

    # Emitida: cliente / Recebida: fornecedor
    cliente = models.ForeignKey(
        "crm.Cliente", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notas_fiscais", verbose_name="Cliente",
    )
    fornecedor = models.CharField("Fornecedor", max_length=200, blank=True)

    arquivo = models.FileField(
        "Arquivo (PDF)", upload_to="financeiro/nfs/%Y/%m/", blank=True,
    )
    lancamento = models.ForeignKey(
        Lancamento, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notas_fiscais", verbose_name="Lançamento vinculado",
    )
    observacao = models.TextField("Observação", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Nota fiscal"
        verbose_name_plural = "Notas fiscais"
        ordering = ["-data_emissao"]

    def __str__(self):
        return f"NF {self.numero} — R${self.valor} ({self.get_tipo_display()})"


# =========================================================================
# Configuracao de Folha
# =========================================================================
class ConfiguracaoFolha(models.Model):
    """Configuracao unica — singleton."""
    dia_pagamento = models.PositiveSmallIntegerField(
        "Dia util para pagamento",
        default=5,
        help_text="Ex: 5 = quinto dia util do mes",
    )
    gerar_salario = models.BooleanField("Gerar salários CLT automaticamente", default=True)
    gerar_pj = models.BooleanField("Gerar pagamentos PJ automaticamente", default=True)
    gerar_pro_labore = models.BooleanField("Gerar pró-labore automaticamente", default=True)
    conta_padrao = models.ForeignKey(
        ContaBancaria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Conta padrão para pagamentos",
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de folha"
        verbose_name_plural = "Configuração de folha"

    def __str__(self):
        return f"Pagamento no {self.dia_pagamento}º dia útil"

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# =========================================================================
# Folha de Pagamento
# =========================================================================
class FolhaPagamento(models.Model):
    class TipoPagamento(models.TextChoices):
        SALARIO = "salario", "Salário"
        PRO_LABORE = "pro_labore", "Pró-labore"
        PAGAMENTO_PJ = "pagamento_pj", "Pagamento PJ"
        COMISSAO = "comissao", "Comissão"
        BONUS = "bonus", "Bônus / Gratificação"
        DECIMO_TERCEIRO = "13o", "13º Salário"
        FERIAS = "ferias", "Férias"
        ADIANTAMENTO = "adiantamento", "Adiantamento"
        RESCISAO = "rescisao", "Rescisão"

    class StatusFolha(models.TextChoices):
        CALCULADO = "calculado", "Calculado"
        APROVADO = "aprovado", "Aprovado"
        PAGO = "pago", "Pago"

    colaborador = models.ForeignKey(
        "rh.Colaborador",
        on_delete=models.CASCADE,
        related_name="folhas",
        verbose_name="Colaborador",
    )
    tipo = models.CharField("Tipo", max_length=15, choices=TipoPagamento.choices)
    competencia = models.DateField(
        "Competência (mês/ano)",
        help_text="Usar o 1o dia do mês de referência",
    )
    valor_bruto = models.DecimalField("Valor bruto", max_digits=12, decimal_places=2)
    desconto_inss = models.DecimalField(
        "Desconto INSS", max_digits=10, decimal_places=2, default=0,
    )
    desconto_ir = models.DecimalField(
        "Desconto IR", max_digits=10, decimal_places=2, default=0,
    )
    outros_descontos = models.DecimalField(
        "Outros descontos", max_digits=10, decimal_places=2, default=0,
    )
    valor_liquido = models.DecimalField("Valor líquido", max_digits=12, decimal_places=2)
    status = models.CharField(
        "Status", max_length=10, choices=StatusFolha.choices,
        default=StatusFolha.CALCULADO,
    )
    data_pagamento = models.DateField("Data de pagamento", null=True, blank=True)
    conta = models.ForeignKey(
        ContaBancaria, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="folhas", verbose_name="Conta de pagamento",
    )
    lancamento = models.OneToOneField(
        Lancamento, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="folha_origem", verbose_name="Lançamento gerado",
    )
    observacao = models.TextField("Observação", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Folha de pagamento"
        verbose_name_plural = "Folhas de pagamento"
        ordering = ["-competencia", "colaborador__nome_completo"]
        unique_together = [("colaborador", "tipo", "competencia")]

    def __str__(self):
        return f"{self.colaborador} — {self.get_tipo_display()} {self.competencia:%m/%Y}"

    def save(self, *args, **kwargs):
        # Competencia sempre no dia 1 do mes
        if self.competencia and self.competencia.day != 1:
            self.competencia = self.competencia.replace(day=1)
        self.valor_liquido = (
            self.valor_bruto - self.desconto_inss - self.desconto_ir - self.outros_descontos
        )
        super().save(*args, **kwargs)


# =========================================================================
# Log de Exportacao da Folha
# =========================================================================
class LogExportacaoFolha(models.Model):
    competencia = models.DateField("Competência")
    formato = models.CharField("Formato", max_length=4)
    total_registros = models.PositiveIntegerField("Total de registros")
    valor_total = models.DecimalField("Valor total", max_digits=14, decimal_places=2)
    exportado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="exportacoes_folha",
        verbose_name="Exportado por",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log de exportação da folha"
        verbose_name_plural = "Logs de exportação da folha"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Folha {self.competencia:%m/%Y} — {self.formato.upper()} por {self.exportado_por} em {self.criado_em:%d/%m/%Y %H:%M}"


# =========================================================================
# Tributo (extensivel pra qualquer regime fiscal)
# =========================================================================
class Tributo(models.Model):
    class StatusTributo(models.TextChoices):
        A_VENCER = "a_vencer", "A vencer"
        PAGO = "pago", "Pago"
        VENCIDO = "vencido", "Vencido"

    tipo = models.CharField(
        "Tipo de tributo", max_length=100,
        help_text="Ex: DAS, ISS, IRPJ, CSLL, PIS, COFINS, INSS patronal",
    )
    competencia = models.DateField(
        "Competência",
        help_text="Período de referência (1o dia do mês)",
    )
    valor = models.DecimalField("Valor", max_digits=12, decimal_places=2)
    vencimento = models.DateField("Vencimento")
    numero_guia = models.CharField("Número da guia / DARF", max_length=100, blank=True)
    status = models.CharField(
        "Status", max_length=10, choices=StatusTributo.choices,
        default=StatusTributo.A_VENCER,
    )
    data_pagamento = models.DateField("Data de pagamento", null=True, blank=True)
    comprovante = models.FileField(
        "Comprovante", upload_to="financeiro/tributos/%Y/%m/", blank=True,
    )
    conta = models.ForeignKey(
        ContaBancaria, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tributos", verbose_name="Conta de pagamento",
    )
    lancamento = models.OneToOneField(
        Lancamento, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tributo_origem", verbose_name="Lançamento gerado",
    )
    observacao = models.TextField("Observação", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tributo"
        verbose_name_plural = "Tributos"
        ordering = ["-vencimento"]

    def __str__(self):
        return f"{self.tipo} — {self.competencia:%m/%Y} (R${self.valor})"

    @property
    def esta_vencido(self):
        if self.status == "pago":
            return False
        from django.utils import timezone
        return self.vencimento < timezone.now().date()

    @property
    def dias_para_vencer(self):
        if self.status == "pago":
            return None
        from django.utils import timezone
        return (self.vencimento - timezone.now().date()).days


# =========================================================================
# Patrimonio e Ativos
# =========================================================================
class Ativo(models.Model):
    class CategoriaAtivo(models.TextChoices):
        IMOVEL = "imovel", "Bem imóvel"
        MOVEL_DURAVEL = "movel_duravel", "Bem móvel durável"
        MOVEL_CONSUMO = "movel_consumo", "Bem móvel de consumo"

    class StatusAtivo(models.TextChoices):
        ATIVO = "ativo", "Ativo"
        DEPRECIADO = "depreciado", "Totalmente depreciado"
        BAIXADO = "baixado", "Baixado"
        CONSUMIDO = "consumido", "Consumido"

    nome = models.CharField("Nome do ativo", max_length=200)
    categoria = models.CharField(
        "Categoria", max_length=15, choices=CategoriaAtivo.choices,
        default=CategoriaAtivo.MOVEL_DURAVEL,
    )
    tipo = models.CharField(
        "Tipo", max_length=100,
        help_text="Ex: Notebook, Monitor, Licença Adobe, Mesa, Veículo",
    )
    numero_serie = models.CharField("Nº de série / Identificador", max_length=100, blank=True)
    descricao = models.TextField("Descrição", blank=True)
    valor_compra = models.DecimalField("Valor de compra (R$)", max_digits=12, decimal_places=2)
    data_aquisicao = models.DateField("Data de aquisição")
    vida_util_anos = models.PositiveSmallIntegerField(
        "Vida útil estimada (anos)", default=5,
    )
    taxa_depreciacao = models.DecimalField(
        "Taxa de depreciação anual (%)", max_digits=5, decimal_places=2, default=20,
        help_text="Ex: 20% ao ano para equipamentos de informática",
    )
    status = models.CharField(
        "Status", max_length=10, choices=StatusAtivo.choices,
        default=StatusAtivo.ATIVO,
    )
    responsavel = models.CharField("Responsável", max_length=200, blank=True)
    departamento = models.ForeignKey(
        "rh.Departamento", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ativos", verbose_name="Departamento",
    )
    setor = models.ForeignKey(
        "rh.Setor", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ativos", verbose_name="Setor",
    )
    data_baixa = models.DateField("Data de baixa", null=True, blank=True)
    motivo_baixa = models.CharField(
        "Motivo da baixa", max_length=200, blank=True,
        help_text="Venda, descarte, perda, etc.",
    )
    observacao = models.TextField("Observação", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ativo"
        verbose_name_plural = "Ativos"
        ordering = ["-data_aquisicao"]

    def __str__(self):
        return f"{self.nome} (R${self.valor_compra})"

    @property
    def is_consumo(self):
        return self.categoria == self.CategoriaAtivo.MOVEL_CONSUMO

    @property
    def depreciacao_mensal(self):
        """Valor da depreciação mensal. Bens de consumo não depreciam."""
        if self.is_consumo:
            return 0
        return round(self.valor_compra * self.taxa_depreciacao / 100 / 12, 2)

    @property
    def depreciacao_acumulada(self):
        """Total depreciado desde a aquisição até hoje."""
        if self.is_consumo:
            return 0
        if self.status == "baixado" and self.data_baixa:
            from django.utils import timezone
            meses = (self.data_baixa.year - self.data_aquisicao.year) * 12 + (self.data_baixa.month - self.data_aquisicao.month)
        else:
            from django.utils import timezone
            hoje = timezone.now().date()
            meses = (hoje.year - self.data_aquisicao.year) * 12 + (hoje.month - self.data_aquisicao.month)
        total = round(self.depreciacao_mensal * meses, 2)
        return min(total, self.valor_compra)

    @property
    def valor_residual(self):
        """Valor contábil atual. Consumo = 0 (virou despesa)."""
        if self.is_consumo:
            return 0
        return max(self.valor_compra - self.depreciacao_acumulada, 0)


# =========================================================================
# Gateway Asaas
# =========================================================================
class ClienteAsaas(models.Model):
    """Vinculo entre o cliente do CRM e o cadastro no Asaas."""
    cliente = models.OneToOneField(
        "crm.Cliente", on_delete=models.CASCADE,
        related_name="asaas", verbose_name="Cliente",
    )
    asaas_id = models.CharField("ID no Asaas", max_length=50, unique=True,
        help_text="Ex: cus_xxxx",
    )
    sincronizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cliente Asaas"
        verbose_name_plural = "Clientes Asaas"

    def __str__(self):
        return f"{self.cliente} → {self.asaas_id}"


class AssinaturaAsaas(models.Model):
    """Assinatura recorrente criada no Asaas vinculada a um plano."""
    class StatusAssinatura(models.TextChoices):
        ACTIVE = "ACTIVE", "Ativa"
        INACTIVE = "INACTIVE", "Inativa"
        EXPIRED = "EXPIRED", "Expirada"

    class Ciclo(models.TextChoices):
        WEEKLY = "WEEKLY", "Semanal"
        BIWEEKLY = "BIWEEKLY", "Quinzenal"
        MONTHLY = "MONTHLY", "Mensal"
        QUARTERLY = "QUARTERLY", "Trimestral"
        SEMIANNUALLY = "SEMIANNUALLY", "Semestral"
        YEARLY = "YEARLY", "Anual"

    asaas_id = models.CharField("ID no Asaas", max_length=50, unique=True,
        help_text="Ex: sub_xxxx",
    )
    cliente = models.ForeignKey(
        "crm.Cliente", on_delete=models.PROTECT,
        related_name="assinaturas_asaas", verbose_name="Cliente",
    )
    plano = models.ForeignKey(
        "crm.Plano", null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="assinaturas_asaas", verbose_name="Plano",
    )
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2)
    ciclo = models.CharField("Ciclo", max_length=15, choices=Ciclo.choices)
    proximo_vencimento = models.DateField("Próximo vencimento", null=True, blank=True)
    status = models.CharField("Status", max_length=10,
        choices=StatusAssinatura.choices, default=StatusAssinatura.ACTIVE,
    )
    billing_type = models.CharField("Forma de pagamento", max_length=20, blank=True,
        help_text="BOLETO, PIX, CREDIT_CARD, etc.",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    cancelado_em = models.DateTimeField("Cancelado em", null=True, blank=True)

    class Meta:
        verbose_name = "Assinatura Asaas"
        verbose_name_plural = "Assinaturas Asaas"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.cliente} — {self.get_ciclo_display()} {self.valor}"


class CobrancaAsaas(models.Model):
    """Espelho de cada cobranca criada no Asaas.
    Ao ser paga, cria/atualiza Lancamento no modulo principal.
    """
    class TipoCobranca(models.TextChoices):
        IMPLANTACAO = "implantacao", "Implantação"
        MENSALIDADE = "mensalidade", "Mensalidade"
        AVULSA = "avulsa", "Avulsa"

    asaas_id = models.CharField("ID no Asaas", max_length=50, unique=True,
        help_text="Ex: pay_xxxx",
    )
    assinatura = models.ForeignKey(
        AssinaturaAsaas, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="cobrancas", verbose_name="Assinatura",
    )
    cliente = models.ForeignKey(
        "crm.Cliente", on_delete=models.PROTECT,
        related_name="cobrancas_asaas", verbose_name="Cliente",
    )
    cobranca = models.OneToOneField(
        Cobranca, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="asaas", verbose_name="Cobrança vinculada",
    )
    lancamento = models.OneToOneField(
        Lancamento, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="cobranca_asaas", verbose_name="Lançamento gerado",
    )
    tipo = models.CharField("Tipo", max_length=15, choices=TipoCobranca.choices)
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2)
    valor_liquido = models.DecimalField("Valor líquido", max_digits=10, decimal_places=2,
        null=True, blank=True, help_text="Após taxas do Asaas",
    )
    vencimento = models.DateField("Vencimento")
    status = models.CharField("Status Asaas", max_length=40)
    billing_type = models.CharField("Forma de pagamento", max_length=20, blank=True)
    invoice_url = models.URLField("URL do boleto/fatura", blank=True)
    bank_slip_url = models.URLField("URL do boleto bancário", blank=True)
    pago_em = models.DateField("Pago em", null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cobrança Asaas"
        verbose_name_plural = "Cobranças Asaas"
        ordering = ["-vencimento"]

    def __str__(self):
        return f"{self.asaas_id} — {self.cliente} R${self.valor}"


class EventoWebhookAsaas(models.Model):
    """Log de todos os eventos recebidos do Asaas.
    Essencial para auditoria e idempotencia.
    """
    evento = models.CharField("Evento", max_length=60)
    asaas_payment_id = models.CharField("Payment ID", max_length=50, blank=True)
    payload = models.JSONField("Payload")
    processado = models.BooleanField("Processado", default=False)
    erro = models.TextField("Erro", blank=True)
    recebido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento Webhook Asaas"
        verbose_name_plural = "Eventos Webhook Asaas"
        ordering = ["-recebido_em"]
        indexes = [
            models.Index(fields=["asaas_payment_id", "processado"]),
        ]

    def __str__(self):
        return f"{self.evento} — {self.asaas_payment_id} ({'✓' if self.processado else '⏳'})"
