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
            content_type__app_label__in=["crm", "accounts", "integracao", "rh", "financeiro"]
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
        ])
        g.permissions.set(perms)
        self._log(g, created)

        # ---------------------------------------------------------------
        # Financeiro — lancamentos, contas, categorias
        # ---------------------------------------------------------------
        g, created = Group.objects.get_or_create(name="Financeiro")
        perms = Permission.objects.filter(codename__in=[
            "view_lancamento", "add_lancamento", "change_lancamento", "delete_lancamento",
            "view_contabancaria", "add_contabancaria", "change_contabancaria", "delete_contabancaria",
            "view_categoriafinanceira", "add_categoriafinanceira", "change_categoriafinanceira", "delete_categoriafinanceira",
            "view_cobranca", "add_cobranca", "change_cobranca", "delete_cobranca",
            "view_despesa", "add_despesa", "change_despesa", "delete_despesa",
            "view_notafiscal", "add_notafiscal", "change_notafiscal", "delete_notafiscal",
            "view_folhapagamento", "add_folhapagamento", "change_folhapagamento", "delete_folhapagamento",
            "view_tributo", "add_tributo", "change_tributo", "delete_tributo",
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
            "view_documentocolaborador", "add_documentocolaborador", "change_documentocolaborador", "delete_documentocolaborador",
            "view_onboardingtemplate", "add_onboardingtemplate", "change_onboardingtemplate", "delete_onboardingtemplate",
            "view_onboardingcolaborador", "add_onboardingcolaborador", "change_onboardingcolaborador", "delete_onboardingcolaborador",
            "view_solicitacaoausencia", "add_solicitacaoausencia", "change_solicitacaoausencia", "delete_solicitacaoausencia",
            "view_saldoferias", "add_saldoferias", "change_saldoferias", "delete_saldoferias",
            "view_treinamento", "add_treinamento", "change_treinamento", "delete_treinamento",
            "view_participacaotreinamento", "add_participacaotreinamento", "change_participacaotreinamento", "delete_participacaotreinamento",
            "view_cicloavaliacao", "add_cicloavaliacao", "change_cicloavaliacao", "delete_cicloavaliacao",
            "view_meta", "add_meta", "change_meta", "delete_meta",
            "view_pdi", "add_pdi", "change_pdi", "delete_pdi",
            "view_acaopdi", "add_acaopdi", "change_acaopdi", "delete_acaopdi",
            "view_pesquisaenps", "add_pesquisaenps", "change_pesquisaenps", "delete_pesquisaenps",
            "view_perguntaenps", "add_perguntaenps", "change_perguntaenps", "delete_perguntaenps",
            "view_respostaenps", "add_respostaenps", "change_respostaenps", "delete_respostaenps",
        ])
        g.permissions.set(perms)
        self._log(g, created)

        # ---------------------------------------------------------------
        # Colaborador — acesso limitado (solicitar ausencias, ver seus dados)
        # ---------------------------------------------------------------
        g, created = Group.objects.get_or_create(name="Colaborador")
        perms = Permission.objects.filter(codename__in=[
            "view_solicitacaoausencia", "add_solicitacaoausencia",
            "view_treinamento",
            "view_participacaotreinamento",
            "view_documentocolaborador",
            "view_onboardingcolaborador",
            "view_saldoferias",
            "view_cicloavaliacao", "view_meta",
            "view_pdi",
            "view_pesquisaenps", "add_respostaenps",
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

        # Atribuir grupo Empresa Parceira a usuarios com EntidadeParceira
        from apps.crm.models import EntidadeParceira
        grupo_parceira = Group.objects.filter(name="Empresa Parceira").first()
        if grupo_parceira:
            parceiros = EntidadeParceira.objects.select_related("usuario").filter(
                usuario__isnull=False, usuario__is_active=True
            )
            count = 0
            for p in parceiros:
                if not p.usuario.groups.filter(pk=grupo_parceira.pk).exists():
                    p.usuario.groups.add(grupo_parceira)
                    count += 1
            if count:
                self.stdout.write(f"  {count} parceiro(s) vinculado(s) ao grupo Empresa Parceira")

        # Remover grupo Colaborador do superuser (nao precisa)
        from apps.accounts.models import Usuario
        grupo_colab = Group.objects.filter(name="Colaborador").first()
        if grupo_colab:
            for su in Usuario.objects.filter(is_superuser=True):
                su.groups.remove(grupo_colab)

        self.stdout.write(self.style.SUCCESS("Grupos configurados com sucesso!"))

    def _log(self, group, created):
        status = "criado" if created else "atualizado"
        self.stdout.write(f"  Grupo '{group.name}' {status} ({group.permissions.count()} permissoes)")
