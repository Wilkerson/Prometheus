from django.contrib import admin

from .models import Comissao


@admin.register(Comissao)
class ComissaoAdmin(admin.ModelAdmin):
    list_display = ("parceiro", "cliente", "valor_venda", "percentual", "valor_comissao", "status", "gerado_em")
    list_filter = ("status",)
    date_hierarchy = "gerado_em"
