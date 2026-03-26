"""
Cria os grupos padrao com permissoes corretas.
Uso: python manage.py setup_groups
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria os grupos padrao (Entidades Parceiras e Operadores) com permissoes"

    def handle(self, *args, **options):
        # Grupo: Entidades Parceiras
        g1, created = Group.objects.get_or_create(name="Entidades Parceiras")
        perms_parceiro = Permission.objects.filter(codename__in=[
            "view_cliente", "add_cliente", "change_cliente",
            "view_plano",
            "view_comissao",
        ])
        g1.permissions.set(perms_parceiro)
        status = "criado" if created else "atualizado"
        self.stdout.write(f"  Grupo 'Entidades Parceiras' {status} ({g1.permissions.count()} permissoes)")

        # Grupo: Operadores
        g2, created = Group.objects.get_or_create(name="Operadores")
        perms_operador = Permission.objects.filter(
            content_type__app_label__in=["crm", "comissoes"]
        )
        g2.permissions.set(perms_operador)
        status = "criado" if created else "atualizado"
        self.stdout.write(f"  Grupo 'Operadores' {status} ({g2.permissions.count()} permissoes)")

        self.stdout.write(self.style.SUCCESS("Grupos configurados com sucesso!"))
