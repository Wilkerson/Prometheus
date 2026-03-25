from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Perfil(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        OPERADOR = "operador", "Operador Interno"
        PARCEIRO = "parceiro", "Entidade Parceira"

    perfil = models.CharField(
        max_length=20,
        choices=Perfil.choices,
        default=Perfil.OPERADOR,
    )

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.get_full_name()} ({self.perfil})"
