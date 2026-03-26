from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_parceiro(self):
        """Verifica se o usuario tem EntidadeParceira vinculada."""
        return hasattr(self, "parceiro")

    @property
    def grupo_nome(self):
        """Retorna o nome do primeiro grupo do usuario."""
        first = self.groups.first()
        return first.name if first else "Sem grupo"
