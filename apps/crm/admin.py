from django.contrib import admin

from .models import Cliente, EntidadeParceira, Lead, ProdutoContratado


@admin.register(EntidadeParceira)
class EntidadeParceiraAdmin(admin.ModelAdmin):
    list_display = ("nome_entidade", "usuario", "percentual_comissao", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome_entidade",)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("nome", "parceiro", "produto_interesse", "status", "criado_em")
    list_filter = ("status", "produto_interesse")
    search_fields = ("nome", "email")
    date_hierarchy = "criado_em"


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "documento", "cnpj", "email", "ativo", "ativado_em")
    list_filter = ("ativo",)
    search_fields = ("nome", "documento", "cnpj", "email")


@admin.register(ProdutoContratado)
class ProdutoContratadoAdmin(admin.ModelAdmin):
    list_display = ("produto", "cliente", "valor", "status", "contratado_em")
    list_filter = ("status", "produto")
