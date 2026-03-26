from django.contrib import admin

from .models import Cliente, ClienteHistorico, EntidadeParceira, ProdutoContratado


class ClienteHistoricoInline(admin.TabularInline):
    model = ClienteHistorico
    extra = 0
    readonly_fields = ("status_anterior", "status_novo", "usuario", "observacao", "criado_em")


@admin.register(EntidadeParceira)
class EntidadeParceiraAdmin(admin.ModelAdmin):
    list_display = ("nome_entidade", "usuario", "percentual_comissao", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome_entidade",)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj", "parceiro", "produto_interesse", "status", "criado_em")
    list_filter = ("status", "produto_interesse", "ativo")
    search_fields = ("nome", "cnpj", "email")
    date_hierarchy = "criado_em"
    inlines = [ClienteHistoricoInline]


@admin.register(ClienteHistorico)
class ClienteHistoricoAdmin(admin.ModelAdmin):
    list_display = ("cliente", "status_anterior", "status_novo", "usuario", "criado_em")
    list_filter = ("status_novo",)
    date_hierarchy = "criado_em"
    readonly_fields = ("cliente", "status_anterior", "status_novo", "usuario", "observacao", "criado_em")


@admin.register(ProdutoContratado)
class ProdutoContratadoAdmin(admin.ModelAdmin):
    list_display = ("produto", "cliente", "valor", "status", "contratado_em")
    list_filter = ("status", "produto")
