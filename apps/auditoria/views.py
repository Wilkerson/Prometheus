from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import render
from django.views import View

from .services import get_audit_logs, get_audit_stats


class AuditorMixin(UserPassesTestMixin):
    """Permite acesso apenas para auditores, admins e superusers."""

    def test_func(self):
        return (
            self.request.user.is_superuser
            or self.request.user.has_perm("auditoria.view_auditlog")
        )


class AuditoriaDashboardView(AuditorMixin, View):
    """Visao geral da auditoria com resumo por departamento."""

    def get(self, request):
        stats = get_audit_stats()
        recentes = get_audit_logs(limit=20)
        return render(request, "auditoria/dashboard.html", {
            "stats": stats,
            "recentes": recentes,
        })


class AuditoriaListView(AuditorMixin, View):
    """Lista de logs filtrada por departamento."""

    DEPTOS_VALIDOS = {
        "financeiro": "Financeiro",
        "comercial": "Comercial",
        "rh": "RH / Pessoas",
        "administracao": "Administracao",
        "integracao": "Integracoes",
    }

    def get(self, request, departamento):
        if departamento not in self.DEPTOS_VALIDOS:
            departamento = "financeiro"

        busca = request.GET.get("q", "").strip()
        fonte = request.GET.get("fonte", "").strip()

        logs = get_audit_logs(
            departamento=departamento,
            fonte=fonte or None,
            busca=busca or None,
            limit=100,
        )

        ctx = {
            "logs": logs,
            "departamento": departamento,
            "departamento_label": self.DEPTOS_VALIDOS[departamento],
            "busca": busca,
            "fonte": fonte,
            "deptos": self.DEPTOS_VALIDOS,
        }

        if request.headers.get("HX-Request"):
            return render(request, "auditoria/_table.html", ctx)
        return render(request, "auditoria/list.html", ctx)
