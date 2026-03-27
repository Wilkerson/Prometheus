from django.contrib import admin

from .models import Cargo, Colaborador, Departamento, HistoricoColaborador


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo", "criado_em")
    list_filter = ("ativo",)
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


@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "cpf", "tipo_contrato", "cargo", "departamento", "status")
    list_filter = ("tipo_contrato", "status", "departamento")
    search_fields = ("nome_completo", "cpf", "email_pessoal")
    inlines = [HistoricoInline]


@admin.register(HistoricoColaborador)
class HistoricoColaboradorAdmin(admin.ModelAdmin):
    list_display = ("colaborador", "tipo", "criado_em", "registrado_por")
    list_filter = ("tipo",)
    search_fields = ("colaborador__nome_completo",)
