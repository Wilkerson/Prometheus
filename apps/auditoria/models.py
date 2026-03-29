from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AuditLog(models.Model):
    """Log centralizado de auditoria — recebe eventos de todos os modulos."""

    class Acao(models.TextChoices):
        CRIACAO = "criacao", "Criacao"
        EDICAO = "edicao", "Edicao"
        EXCLUSAO = "exclusao", "Exclusao"
        STATUS = "status", "Mudanca de status"
        EXPORTACAO = "exportacao", "Exportacao"
        WEBHOOK = "webhook", "Evento externo"
        SISTEMA = "sistema", "Sistema"

    class Departamento(models.TextChoices):
        FINANCEIRO = "financeiro", "Financeiro"
        COMERCIAL = "comercial", "Comercial"
        RH = "rh", "RH / Pessoas"
        ADMINISTRACAO = "administracao", "Administracao"
        INTEGRACAO = "integracao", "Integracao"
        SISTEMA = "sistema", "Sistema"

    # O que aconteceu
    acao = models.CharField("Acao", max_length=20, choices=Acao.choices)
    departamento = models.CharField(
        "Departamento", max_length=20, choices=Departamento.choices, db_index=True,
    )
    descricao = models.CharField("Descricao", max_length=500)
    detalhes = models.JSONField("Detalhes", default=dict, blank=True)

    # Entidade afetada (generico — aponta pra qualquer model)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    object_repr = models.CharField("Representacao", max_length=300, blank=True)

    # Quem fez
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Usuario",
    )

    # Origem do evento
    fonte = models.CharField(
        "Fonte", max_length=30, default="interno", db_index=True,
        help_text="interno, asaas_webhook, api, celery, sistema",
    )

    # Quando
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Log de auditoria"
        verbose_name_plural = "Logs de auditoria"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["departamento", "-criado_em"]),
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["usuario", "-criado_em"]),
            models.Index(fields=["fonte", "-criado_em"]),
        ]

    def __str__(self):
        return f"{self.get_acao_display()} — {self.descricao} ({self.criado_em:%d/%m/%Y %H:%M})"
