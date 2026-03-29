from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("acao", "departamento", "descricao", "usuario", "fonte", "criado_em")
    list_filter = ("acao", "departamento", "fonte")
    search_fields = ("descricao", "object_repr")
    readonly_fields = (
        "acao", "departamento", "descricao", "detalhes",
        "content_type", "object_id", "object_repr",
        "usuario", "fonte", "criado_em",
    )
    date_hierarchy = "criado_em"
