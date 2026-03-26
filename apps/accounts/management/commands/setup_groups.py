"""
Cria os grupos padrao com permissoes corretas.
Uso: python manage.py setup_groups
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria os grupos padrao (Administrador, Empresa Parceira, Comercial) com permissoes"

    def handle(self, *args, **options):
        # Grupo: Administrador — acesso total a todos os modulos (menos Admin Django)
        g1, created = Group.objects.get_or_create(name="Administrador")
        perms_admin = Permission.objects.filter(
            content_type__app_label__in=["crm", "comissoes", "accounts", "integracao"]
        )
        g1.permissions.set(perms_admin)
        status = "criado" if created else "atualizado"
        self.stdout.write(f"  Grupo 'Administrador' {status} ({g1.permissions.count()} permissoes)")

        # Grupo: Empresa Parceira — apenas acoes de clientes + ver comissoes
        g2, created = Group.objects.get_or_create(name="Empresa Parceira")
        perms_parceira = Permission.objects.filter(codename__in=[
            "view_cliente", "add_cliente", "change_cliente", "delete_cliente",
            "view_comissao",
        ])
        g2.permissions.set(perms_parceira)
        status = "criado" if created else "atualizado"
        self.stdout.write(f"  Grupo 'Empresa Parceira' {status} ({g2.permissions.count()} permissoes)")

        # Grupo: Comercial — clientes + produtos + planos
        g3, created = Group.objects.get_or_create(name="Comercial")
        perms_comercial = Permission.objects.filter(codename__in=[
            "view_cliente", "add_cliente", "change_cliente", "delete_cliente",
            "view_produto", "add_produto", "change_produto", "delete_produto",
            "view_plano", "add_plano", "change_plano", "delete_plano",
            "view_planoproduto", "add_planoproduto", "change_planoproduto", "delete_planoproduto",
            "view_comissao",
        ])
        g3.permissions.set(perms_comercial)
        status = "criado" if created else "atualizado"
        self.stdout.write(f"  Grupo 'Comercial' {status} ({g3.permissions.count()} permissoes)")

        # Remove grupos antigos se existirem
        Group.objects.filter(name__in=["Entidades Parceiras", "Operadores"]).delete()

        self.stdout.write(self.style.SUCCESS("Grupos configurados com sucesso!"))
