import secrets

from django.db import models


class TokenIntegracao(models.Model):
    nome = models.CharField("Nome do sistema", max_length=100)
    token = models.CharField(max_length=64, unique=True, default=secrets.token_hex)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Token de Integração"
        verbose_name_plural = "Tokens de Integração"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome} ({'ativo' if self.ativo else 'inativo'})"
