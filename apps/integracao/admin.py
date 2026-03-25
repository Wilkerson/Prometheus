from django.contrib import admin

from .models import TokenIntegracao


@admin.register(TokenIntegracao)
class TokenIntegracaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "token", "ativo", "criado_em")
    list_filter = ("ativo",)
    readonly_fields = ("token",)
