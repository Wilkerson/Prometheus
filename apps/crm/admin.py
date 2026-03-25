from django.contrib import admin

from .models import Cliente, EntidadeParceira, Lead, LeadHistorico, ProdutoContratado


class LeadHistoricoInline(admin.TabularInline):
    model = LeadHistorico
    extra = 0
    readonly_fields = ("status_anterior", "status_novo", "usuario", "observacao", "criado_em")


@admin.register(EntidadeParceira)
class EntidadeParceiraAdmin(admin.ModelAdmin):
    list_display = ("nome_entidade", "usuario", "percentual_comissao", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome_entidade",)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("nome", "parceiro", "produto_interesse", "status", "criado_em", "atualizado_em")
    list_filter = ("status", "produto_interesse")
    search_fields = ("nome", "email")
    date_hierarchy = "criado_em"
    inlines = [LeadHistoricoInline]


@admin.register(LeadHistorico)
class LeadHistoricoAdmin(admin.ModelAdmin):
    list_display = ("lead", "status_anterior", "status_novo", "usuario", "criado_em")
    list_filter = ("status_novo",)
    date_hierarchy = "criado_em"
    readonly_fields = ("lead", "status_anterior", "status_novo", "usuario", "observacao", "criado_em")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj", "email", "cep", "ativo", "ativado_em")
    list_filter = ("ativo",)
    search_fields = ("nome", "cnpj", "email", "cep")


@admin.register(ProdutoContratado)
class ProdutoContratadoAdmin(admin.ModelAdmin):
    list_display = ("produto", "cliente", "valor", "status", "contratado_em")
    list_filter = ("status", "produto")
