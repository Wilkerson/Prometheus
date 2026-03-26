from django.contrib import admin

from .models import (
    Cliente, ClienteHistorico, Endereco, EntidadeParceira,
    Plano, PlanoProduto, Produto,
)


class ClienteHistoricoInline(admin.TabularInline):
    model = ClienteHistorico
    extra = 0
    readonly_fields = ("status_anterior", "status_novo", "usuario", "observacao", "criado_em")


class PlanoProdutoInline(admin.TabularInline):
    model = PlanoProduto
    extra = 1


@admin.register(EntidadeParceira)
class EntidadeParceiraAdmin(admin.ModelAdmin):
    list_display = ("nome_entidade", "usuario", "percentual_comissao", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome_entidade",)


@admin.register(Endereco)
class EnderecoAdmin(admin.ModelAdmin):
    list_display = ("cep", "logradouro", "numero", "bairro", "cidade", "uf")
    search_fields = ("cep", "logradouro", "cidade")
    list_filter = ("uf",)


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "tier", "ativo", "criado_em")
    list_filter = ("tier", "ativo")
    search_fields = ("nome",)


@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = ("nome", "parceiro", "ativo", "criado_em")
    list_filter = ("ativo", "parceiro")
    search_fields = ("nome", "parceiro__nome_entidade")
    inlines = [PlanoProdutoInline]


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj", "parceiro", "status", "criado_em")
    list_filter = ("status", "ativo")
    search_fields = ("nome", "cnpj", "email")
    date_hierarchy = "criado_em"
    filter_horizontal = ("planos",)
    inlines = [ClienteHistoricoInline]


@admin.register(ClienteHistorico)
class ClienteHistoricoAdmin(admin.ModelAdmin):
    list_display = ("cliente", "status_anterior", "status_novo", "usuario", "criado_em")
    list_filter = ("status_novo",)
    date_hierarchy = "criado_em"
    readonly_fields = ("cliente", "status_anterior", "status_novo", "usuario", "observacao", "criado_em")
