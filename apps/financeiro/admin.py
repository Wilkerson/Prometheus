from django.contrib import admin

from .models import CategoriaFinanceira, Cobranca, ContaBancaria, Despesa, Lancamento, NotaFiscal


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


@admin.register(Cobranca)
class CobrancaAdmin(admin.ModelAdmin):
    list_display = ("descricao", "cliente", "valor", "vencimento", "status", "tipo")
    list_filter = ("status", "tipo")
    search_fields = ("descricao", "cliente__nome")
    date_hierarchy = "vencimento"


@admin.register(Despesa)
class DespesaAdmin(admin.ModelAdmin):
    list_display = ("descricao", "fornecedor", "valor", "vencimento", "recorrencia", "status")
    list_filter = ("status", "recorrencia", "categoria")
    search_fields = ("descricao", "fornecedor")
    date_hierarchy = "vencimento"


@admin.register(NotaFiscal)
class NotaFiscalAdmin(admin.ModelAdmin):
    list_display = ("numero", "tipo", "valor", "data_emissao", "cliente", "fornecedor")
    list_filter = ("tipo",)
    search_fields = ("numero", "fornecedor")
    date_hierarchy = "data_emissao"
