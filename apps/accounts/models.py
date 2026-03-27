import hashlib

from django.contrib.auth.models import AbstractUser
from django.db import models


def upload_avatar_path(instance, filename):
    return f"avatars/{instance.pk}/{filename}"


class Usuario(AbstractUser):
    avatar = models.ImageField(
        "Avatar",
        upload_to=upload_avatar_path,
        blank=True,
        null=True,
    )

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

    @property
    def iniciais(self):
        """Retorna as iniciais do usuario (max 2 letras)."""
        fn = self.first_name[:1].upper() if self.first_name else ""
        ln = self.last_name[:1].upper() if self.last_name else ""
        return fn + ln or self.username[:2].upper()

    @property
    def gravatar_url(self):
        """URL do Gravatar baseado no email (fallback: 404 pra detectar ausencia)."""
        email_hash = hashlib.md5(self.email.lower().strip().encode()).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?s=200&d=404"

    @property
    def avatar_url(self):
        """Retorna URL do avatar: foto colaborador > upload local > Gravatar > None (iniciais)."""
        # Foto do colaborador vinculado (prioridade)
        colab = getattr(self, "colaborador", None)
        if colab and colab.foto:
            return colab.foto.url
        # Avatar do usuario
        if self.avatar:
            return self.avatar.url
        return None

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.avatar:
            self._resize_avatar()

    def _resize_avatar(self):
        """Redimensiona avatar para 200x200 se necessario."""
        try:
            from PIL import Image

            img = Image.open(self.avatar.path)
            if img.width > 200 or img.height > 200:
                img.thumbnail((200, 200), Image.LANCZOS)
                img.save(self.avatar.path)
        except Exception:
            pass
