from django.contrib import admin

from .models import (
    Cargo, Colaborador, Departamento, DocumentoColaborador,
    HistoricoColaborador, OnboardingColaborador, OnboardingItem,
    OnboardingTemplate, OnboardingTemplateItem, Setor,
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
