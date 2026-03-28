from django.contrib import admin

from .models import CategoriaFinanceira, ContaBancaria, Lancamento


@admin.register(CategoriaFinanceira)
class CategoriaFinanceiraAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "pai", "ativo", "ordem")
    list_filter = ("tipo", "ativo")
    search_fields = ("nome",)


@admin.register(ContaBancaria)
class ContaBancariaAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "banco", "saldo_inicial", "ativo")
    list_filter = ("tipo", "ativo")


@admin.register(Lancamento)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ("descricao", "tipo", "valor", "categoria", "conta", "status", "data_vencimento")
    list_filter = ("tipo", "status", "canal", "conta")
    search_fields = ("descricao",)
    date_hierarchy = "data_vencimento"
