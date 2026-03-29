import csv
import json

from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from .models import AuditLog
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

    PERIODOS = {"7": 7, "30": 30, "90": 90, "365": 365}

    def get(self, request, departamento):
        if departamento not in self.DEPTOS_VALIDOS:
            departamento = "financeiro"

        busca = request.GET.get("q", "").strip()
        fonte = request.GET.get("fonte", "").strip()
        periodo = request.GET.get("periodo", "30").strip()
        dias = self.PERIODOS.get(periodo, 30)

        logs = get_audit_logs(
            departamento=departamento,
            fonte=fonte or None,
            busca=busca or None,
            dias=dias,
            limit=200,
        )

        ctx = {
            "logs": logs,
            "departamento": departamento,
            "departamento_label": self.DEPTOS_VALIDOS[departamento],
            "busca": busca,
            "fonte": fonte,
            "periodo": periodo,
            "deptos": self.DEPTOS_VALIDOS,
        }

        if request.headers.get("HX-Request"):
            return render(request, "auditoria/_table.html", ctx)
        return render(request, "auditoria/list.html", ctx)


class AuditoriaDetailView(AuditorMixin, View):
    """Detalhe de um registro do AuditLog com JSON formatado."""

    def get(self, request, pk):
        log = get_object_or_404(AuditLog.objects.select_related("usuario", "content_type"), pk=pk)
        detalhes_json = json.dumps(log.detalhes, indent=2, ensure_ascii=False) if log.detalhes else "{}"

        # Tentar resolver link para a entidade
        entity_url = None
        if log.content_type and log.object_id:
            model_class = log.content_type.model_class()
            if model_class:
                try:
                    model_class.objects.get(pk=log.object_id)
                    model_name = log.content_type.model
                    url_map = {
                        "cliente": f"/clientes/{log.object_id}/",
                        "colaborador": f"/rh/colaboradores/{log.object_id}/",
                        "usuario": f"/usuarios/{log.object_id}/editar/",
                        "lancamento": f"/financeiro/lancamentos/{log.object_id}/",
                        "cobrancaasaas": f"/financeiro/asaas/cobrancas/{log.object_id}/",
                        "assinaturaasaas": f"/financeiro/asaas/assinaturas/",
                    }
                    entity_url = url_map.get(model_name)
                except model_class.DoesNotExist:
                    pass

        return render(request, "auditoria/detail.html", {
            "log": log,
            "detalhes_json": detalhes_json,
            "entity_url": entity_url,
        })


class AuditoriaExportView(AuditorMixin, View):
    """Exporta logs de auditoria filtrados para CSV."""

    DEPTOS_VALIDOS = AuditoriaListView.DEPTOS_VALIDOS

    def get(self, request):
        departamento = request.GET.get("departamento", "").strip() or None
        fonte = request.GET.get("fonte", "").strip() or None
        busca = request.GET.get("q", "").strip() or None

        logs = get_audit_logs(
            departamento=departamento,
            fonte=fonte,
            busca=busca,
            limit=5000,
        )

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="auditoria.csv"'
        response.write("\ufeff")  # BOM para Excel

        writer = csv.writer(response, delimiter=";")
        writer.writerow(["Data/Hora", "Departamento", "Acao", "Descricao", "Usuario", "Fonte", "Detalhes"])

        for log in logs:
            writer.writerow([
                log["criado_em"].strftime("%d/%m/%Y %H:%M"),
                log["departamento"],
                log["acao"],
                log["descricao"],
                log["usuario"],
                log["fonte"],
                json.dumps(log["detalhes"], ensure_ascii=False) if log["detalhes"] else "",
            ])

        from apps.auditoria.utils import registrar
        registrar("exportacao", "sistema", f"Exportacao de auditoria ({len(logs)} registros)", request=request)

        return response
