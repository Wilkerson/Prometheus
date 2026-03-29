import csv
import json
from datetime import date, datetime

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


def _parse_date(value):
    """Converte string YYYY-MM-DD para date ou None."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _extract_filters(request):
    """Extrai filtros comuns do request."""
    busca = request.GET.get("q", "").strip()
    fonte = request.GET.get("fonte", "").strip()
    periodo = request.GET.get("periodo", "30").strip()
    data_de = _parse_date(request.GET.get("data_de"))
    data_ate = _parse_date(request.GET.get("data_ate"))

    PERIODOS = {"7": 7, "30": 30, "90": 90, "365": 365}

    # Se tem datas customizadas, ignorar periodo predefinido
    if data_de:
        dias = None
        periodo = "custom"
    else:
        dias = PERIODOS.get(periodo, 30)

    return {
        "busca": busca or None,
        "fonte": fonte or None,
        "dias": dias,
        "data_de": data_de,
        "data_ate": data_ate,
        "periodo": periodo,
        # Valores originais para o template
        "busca_str": busca,
        "fonte_str": fonte,
        "data_de_str": request.GET.get("data_de", ""),
        "data_ate_str": request.GET.get("data_ate", ""),
    }


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

        f = _extract_filters(request)

        logs = get_audit_logs(
            departamento=departamento,
            fonte=f["fonte"],
            busca=f["busca"],
            dias=f["dias"] or 30,
            data_de=f["data_de"],
            data_ate=f["data_ate"],
            limit=200,
        )

        # Flag: pesquisa ativa (usuario definiu filtros)
        pesquisa_ativa = bool(f["data_de"] or f["fonte"] or f["busca"])

        ctx = {
            "logs": logs,
            "total_logs": len(logs),
            "departamento": departamento,
            "departamento_label": self.DEPTOS_VALIDOS[departamento],
            "busca": f["busca_str"],
            "fonte": f["fonte_str"],
            "periodo": f["periodo"],
            "data_de": f["data_de_str"],
            "data_ate": f["data_ate_str"],
            "pesquisa_ativa": pesquisa_ativa,
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


class AuditoriaExportCSVView(AuditorMixin, View):
    """Exporta logs de auditoria filtrados para CSV."""

    def get(self, request):
        f = _extract_filters(request)
        departamento = request.GET.get("departamento", "").strip() or None

        logs = get_audit_logs(
            departamento=departamento,
            fonte=f["fonte"],
            busca=f["busca"],
            dias=f["dias"] or 365,
            data_de=f["data_de"],
            data_ate=f["data_ate"],
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
        registrar("exportacao", "sistema", f"Exportacao CSV auditoria ({len(logs)} registros)", request=request)

        return response


class AuditoriaExportPDFView(AuditorMixin, View):
    """Exporta logs de auditoria filtrados para PDF."""

    def get(self, request):
        from io import BytesIO

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        f = _extract_filters(request)
        departamento = request.GET.get("departamento", "").strip() or None
        depto_label = AuditoriaListView.DEPTOS_VALIDOS.get(departamento, "Todos")

        logs = get_audit_logs(
            departamento=departamento,
            fonte=f["fonte"],
            busca=f["busca"],
            dias=f["dias"] or 365,
            data_de=f["data_de"],
            data_ate=f["data_ate"],
            limit=5000,
        )

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
        styles = getSampleStyleSheet()
        elements = []

        # Titulo
        elements.append(Paragraph(f"Relatório de Auditoria — {depto_label}", styles["Title"]))

        # Periodo
        if f["data_de"]:
            periodo_txt = f"Período: {f['data_de'].strftime('%d/%m/%Y')} a {f['data_ate'].strftime('%d/%m/%Y') if f['data_ate'] else 'hoje'}"
        else:
            periodo_txt = f"Últimos {f['dias'] or 30} dias"
        elements.append(Paragraph(periodo_txt, styles["Normal"]))
        elements.append(Paragraph(f"Total de registros: {len(logs)}", styles["Normal"]))
        elements.append(Spacer(1, 8*mm))

        if logs:
            # Tabela
            header = ["Data/Hora", "Ação", "Descrição", "Usuário", "Fonte"]
            data = [header]
            cell_style = styles["Normal"]
            cell_style.fontSize = 7
            cell_style.leading = 9

            for log in logs:
                data.append([
                    log["criado_em"].strftime("%d/%m/%Y %H:%M"),
                    log["acao"],
                    Paragraph(log["descricao"][:120], cell_style),
                    log["usuario"],
                    log["fonte"],
                ])

            page_width = landscape(A4)[0] - 30*mm
            col_widths = [35*mm, 22*mm, page_width - 35*mm - 22*mm - 28*mm - 22*mm, 28*mm, 22*mm]

            table = Table(data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d4a3e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph("Nenhum registro encontrado para o período selecionado.", styles["Normal"]))

        # Rodape com data de geracao
        elements.append(Spacer(1, 8*mm))
        from django.utils import timezone as tz
        elements.append(Paragraph(
            f"Gerado em {tz.now().strftime('%d/%m/%Y %H:%M')} por {request.user.get_full_name() or request.user.username} — RUCH Solutions",
            styles["Italic"],
        ))

        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="auditoria.pdf"'

        from apps.auditoria.utils import registrar
        registrar("exportacao", "sistema", f"Exportacao PDF auditoria ({len(logs)} registros)", request=request)

        return response
