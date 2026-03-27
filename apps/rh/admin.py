from django.contrib import admin

from .models import (
    AcaoPDI, Cargo, CicloAvaliacao, Colaborador, Departamento,
    DocumentoColaborador, HistoricoColaborador, Meta, OnboardingColaborador,
    OnboardingItem, OnboardingTemplate, OnboardingTemplateItem, PDI,
    ParticipacaoTreinamento, PerguntaENPS, PesquisaENPS, RespostaENPS,
    SaldoFerias, Setor, SolicitacaoAusencia, Treinamento,
)


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "ordem", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome",)
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ("nome", "departamento", "ativo")
    list_filter = ("departamento", "ativo")
    search_fields = ("nome",)


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ("nome", "departamento", "nivel", "faixa_salarial_display", "ativo")
    list_filter = ("departamento", "nivel", "ativo")
    search_fields = ("nome",)


class HistoricoInline(admin.TabularInline):
    model = HistoricoColaborador
    extra = 0
    readonly_fields = ("tipo", "criado_em", "registrado_por")


class DocumentoInline(admin.TabularInline):
    model = DocumentoColaborador
    extra = 0


@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "cpf", "tipo_contrato", "cargo", "departamento", "setor", "status")
    list_filter = ("tipo_contrato", "status", "departamento")
    search_fields = ("nome_completo", "cpf", "email_pessoal")
    inlines = [HistoricoInline, DocumentoInline]


@admin.register(HistoricoColaborador)
class HistoricoColaboradorAdmin(admin.ModelAdmin):
    list_display = ("colaborador", "tipo", "criado_em", "registrado_por")
    list_filter = ("tipo",)
    search_fields = ("colaborador__nome_completo",)


@admin.register(DocumentoColaborador)
class DocumentoColaboradorAdmin(admin.ModelAdmin):
    list_display = ("nome", "colaborador", "tipo", "data_vencimento", "vencido")
    list_filter = ("tipo",)
    search_fields = ("nome", "colaborador__nome_completo")


class TemplateItemInline(admin.TabularInline):
    model = OnboardingTemplateItem
    extra = 3


@admin.register(OnboardingTemplate)
class OnboardingTemplateAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo_contrato", "departamento", "ativo")
    list_filter = ("tipo_contrato", "ativo")
    inlines = [TemplateItemInline]


class OnboardingItemInline(admin.TabularInline):
    model = OnboardingItem
    extra = 0


@admin.register(OnboardingColaborador)
class OnboardingColaboradorAdmin(admin.ModelAdmin):
    list_display = ("colaborador", "template", "progresso", "criado_em", "concluido_em")
    inlines = [OnboardingItemInline]


@admin.register(SolicitacaoAusencia)
class SolicitacaoAusenciaAdmin(admin.ModelAdmin):
    list_display = ("colaborador", "tipo", "data_inicio", "data_fim", "total_dias", "status")
    list_filter = ("tipo", "status")
    search_fields = ("colaborador__nome_completo",)


@admin.register(SaldoFerias)
class SaldoFeriasAdmin(admin.ModelAdmin):
    list_display = ("colaborador", "periodo_inicio", "periodo_fim", "dias_direito", "dias_usufruidos", "saldo_disponivel")
    search_fields = ("colaborador__nome_completo",)


@admin.register(Treinamento)
class TreinamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "modalidade", "carga_horaria", "obrigatorio", "ativo")
    list_filter = ("tipo", "modalidade", "obrigatorio", "ativo")
    search_fields = ("nome",)


@admin.register(ParticipacaoTreinamento)
class ParticipacaoTreinamentoAdmin(admin.ModelAdmin):
    list_display = ("colaborador", "treinamento", "status", "data_inicio", "data_conclusao")
    list_filter = ("status",)
    search_fields = ("colaborador__nome_completo", "treinamento__nome")


class MetaInline(admin.TabularInline):
    model = Meta
    extra = 0


@admin.register(CicloAvaliacao)
class CicloAvaliacaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "periodo_inicio", "periodo_fim", "status")
    list_filter = ("status",)
    inlines = [MetaInline]


class AcaoPDIInline(admin.TabularInline):
    model = AcaoPDI
    extra = 0


@admin.register(PDI)
class PDIAdmin(admin.ModelAdmin):
    list_display = ("colaborador", "competencia", "ano", "progresso")
    list_filter = ("ano",)
    search_fields = ("colaborador__nome_completo", "competencia")
    inlines = [AcaoPDIInline]


class PerguntaInline(admin.TabularInline):
    model = PerguntaENPS
    extra = 0


@admin.register(PesquisaENPS)
class PesquisaENPSAdmin(admin.ModelAdmin):
    list_display = ("titulo", "data_inicio", "data_encerramento", "status", "enps_score")
    list_filter = ("status",)
    inlines = [PerguntaInline]
