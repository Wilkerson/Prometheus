"""
Cria os grupos padrao com permissoes corretas.
Uso: python manage.py setup_groups
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria os grupos padrao por departamento com permissoes"

    def handle(self, *args, **options):
        # ---------------------------------------------------------------
        # Administrador — acesso total a todos os modulos
        # ---------------------------------------------------------------
        g, created = Group.objects.get_or_create(name="Administrador")
        perms = Permission.objects.filter(
            content_type__app_label__in=["crm", "comissoes", "accounts", "integracao", "rh"]
        )
        g.permissions.set(perms)
        self._log(g, created)

        # ---------------------------------------------------------------
        # Comercial — clientes, produtos, planos, ver comissoes
        # ---------------------------------------------------------------
        g, created = Group.objects.get_or_create(name="Comercial")
        perms = Permission.objects.filter(codename__in=[
            "view_cliente", "add_cliente", "change_cliente", "delete_cliente",
            "view_produto", "add_produto", "change_produto", "delete_produto",
            "view_plano", "add_plano", "change_plano", "delete_plano",
            "view_planoproduto", "add_planoproduto", "change_planoproduto", "delete_planoproduto",
            "view_comissao",
        ])
        g.permissions.set(perms)
        self._log(g, created)

        # ---------------------------------------------------------------
        # Financeiro — comissoes CRUD
        # ---------------------------------------------------------------
        g, created = Group.objects.get_or_create(name="Financeiro")
        perms = Permission.objects.filter(codename__in=[
            "view_comissao", "add_comissao", "change_comissao", "delete_comissao",
        ])
        g.permissions.set(perms)
        self._log(g, created)

        # ---------------------------------------------------------------
        # RH / Pessoas — colaboradores, cargos, setores CRUD
        # ---------------------------------------------------------------
        g, created = Group.objects.get_or_create(name="RH / Pessoas")
        perms = Permission.objects.filter(codename__in=[
            "view_colaborador", "add_colaborador", "change_colaborador", "delete_colaborador",
            "view_cargo", "add_cargo", "change_cargo", "delete_cargo",
            "view_setor", "add_setor", "change_setor", "delete_setor",
        ])
        g.permissions.set(perms)
        self._log(g, created)

        # ---------------------------------------------------------------
        # Empresa Parceira — apenas clientes (criar/ver/editar)
        # ---------------------------------------------------------------
        g, created = Group.objects.get_or_create(name="Empresa Parceira")
        perms = Permission.objects.filter(codename__in=[
            "view_cliente", "add_cliente", "change_cliente",
        ])
        g.permissions.set(perms)
        self._log(g, created)

        # Remove grupos legados que nao existem mais
        removed = Group.objects.filter(
            name__in=["Entidades Parceiras", "Operadores"]
        ).delete()[0]
        if removed:
            self.stdout.write(f"  Removidos {removed} grupo(s) legado(s)")

        self.stdout.write(self.style.SUCCESS("Grupos configurados com sucesso!"))

    def _log(self, group, created):
        status = "criado" if created else "atualizado"
        self.stdout.write(f"  Grupo '{group.name}' {status} ({group.permissions.count()} permissoes)")
