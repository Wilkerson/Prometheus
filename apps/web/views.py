from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.accounts.models import Usuario
from apps.comissoes.models import Comissao
from apps.crm.models import Cliente, EntidadeParceira, Lead, LeadHistorico

from .mixins import HtmxMixin, OperadorRequiredMixin, is_htmx


# ---------------------------------------------------------------------------
# Landing Page (p&uacute;blica)
# ---------------------------------------------------------------------------
class HomeView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("web:dashboard")

        produtos = [
            {"nome": "Agentes de IA", "descricao": "Assistentes inteligentes que automatizam atendimento, vendas e processos operacionais."},
            {"nome": "SaaS", "descricao": "Plataformas sob medida para otimizar a gestao e escalar seu negocio."},
            {"nome": "CRM", "descricao": "Gestao completa do relacionamento com clientes em uma interface intuitiva."},
            {"nome": "ERP", "descricao": "Sistema integrado de gestao empresarial para controle total da operacao."},
            {"nome": "Sites", "descricao": "Sites institucionais e landing pages de alta conversao com design profissional."},
            {"nome": "Consultoria", "descricao": "Consultoria em tecnologia e automacao para transformar digitalmente seu negocio."},
        ]

        return render(request, "public/home.html", {"produtos": produtos})


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("web:dashboard")
        return render(request, "accounts/login.html", {"form": AuthenticationForm()})

    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("web:dashboard")
        return render(request, "accounts/login.html", {"form": form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect("web:login")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        if user.perfil == Usuario.Perfil.PARCEIRO and hasattr(user, "parceiro"):
            parceiro = user.parceiro
            leads_qs = Lead.objects.filter(parceiro=parceiro)
            comissoes_qs = Comissao.objects.filter(parceiro=parceiro)
        else:
            leads_qs = Lead.objects.all()
            comissoes_qs = Comissao.objects.all()

        # Stats de leads
        stats = leads_qs.values("status").annotate(total=Count("id"))
        por_status = {item["status"]: item["total"] for item in stats}
        ctx["leads_total"] = sum(por_status.values())
        ctx["leads_por_status"] = por_status

        # Stats de comissões
        comissao_stats = comissoes_qs.aggregate(
            pendente=Sum("valor_comissao", filter=Q(status=Comissao.Status.PENDENTE)),
            pago=Sum("valor_comissao", filter=Q(status=Comissao.Status.PAGO)),
            total_count=Count("id"),
        )
        ctx["comissao_pendente"] = comissao_stats["pendente"] or 0
        ctx["comissao_pago"] = comissao_stats["pago"] or 0

        # Leads recentes
        ctx["leads_recentes"] = leads_qs.select_related("parceiro").order_by("-criado_em")[:10]

        # SLA: leads paradas há mais de 3 dias
        limite = timezone.now() - timezone.timedelta(days=3)
        ctx["leads_atrasadas"] = (
            leads_qs.exclude(status__in=[Lead.Status.CONCLUIDA, Lead.Status.PERDIDA])
            .filter(atualizado_em__lt=limite)
            .count()
        )

        return ctx


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------
class LeadListView(LoginRequiredMixin, HtmxMixin, ListView):
    template_name = "leads/list.html"
    partial_template_name = "leads/_table.html"
    context_object_name = "leads"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Lead.objects.select_related("parceiro", "operador").order_by("-criado_em")

        if user.perfil == Usuario.Perfil.PARCEIRO and hasattr(user, "parceiro"):
            qs = qs.filter(parceiro=user.parceiro)

        # Filtros
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        produto_filter = self.request.GET.get("produto")
        if produto_filter:
            qs = qs.filter(produto_interesse=produto_filter)

        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(email__icontains=search))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Lead.Status.choices
        ctx["produto_choices"] = Lead.Produto.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_produto"] = self.request.GET.get("produto", "")
        ctx["current_search"] = self.request.GET.get("q", "")
        return ctx


class LeadCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "leads/create.html", {
            "produto_choices": Lead.Produto.choices,
        })

    def post(self, request):
        user = request.user
        lead_data = {
            "nome": request.POST.get("nome", ""),
            "email": request.POST.get("email", ""),
            "telefone": request.POST.get("telefone", ""),
            "produto_interesse": request.POST.get("produto_interesse", ""),
        }

        if user.perfil == Usuario.Perfil.PARCEIRO and hasattr(user, "parceiro"):
            lead_data["parceiro"] = user.parceiro
        else:
            parceiro_id = request.POST.get("parceiro")
            if parceiro_id:
                lead_data["parceiro"] = get_object_or_404(EntidadeParceira, id=parceiro_id)

        Lead.objects.create(**lead_data)

        if is_htmx(request):
            return render(request, "leads/_create_success.html")
        return redirect("web:leads")


class LeadDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        lead = get_object_or_404(
            Lead.objects.select_related("parceiro", "operador"),
            pk=pk,
        )
        historico = lead.historico.select_related("usuario").all()

        # Verifica permissão do parceiro
        if (
            request.user.perfil == Usuario.Perfil.PARCEIRO
            and hasattr(request.user, "parceiro")
            and lead.parceiro != request.user.parceiro
        ):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        transicoes = Lead.TRANSICOES_VALIDAS.get(lead.status, ())

        return render(request, "leads/detail.html", {
            "lead": lead,
            "historico": historico,
            "transicoes": [(s, Lead.Status(s).label) for s in transicoes],
        })


class LeadUpdateStatusView(OperadorRequiredMixin, View):
    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
        novo_status = request.POST.get("status")
        observacao = request.POST.get("observacao", "")

        if not lead.pode_transitar_para(novo_status):
            return render(request, "leads/_status_error.html", {
                "error": f"Transição de '{lead.get_status_display()}' para '{novo_status}' não é permitida.",
            })

        status_anterior = lead.status
        lead.status = novo_status
        lead.save(update_fields=["status", "atualizado_em"])

        LeadHistorico.objects.create(
            lead=lead,
            status_anterior=status_anterior,
            status_novo=novo_status,
            usuario=request.user,
            observacao=observacao,
        )

        # Dispara envio para sistema externo
        if novo_status == Lead.Status.EM_PROCESSAMENTO:
            from apps.crm.tasks import enviar_lead_sistema_externo
            enviar_lead_sistema_externo.delay(lead.id)

        historico = lead.historico.select_related("usuario").all()
        transicoes = Lead.TRANSICOES_VALIDAS.get(lead.status, ())

        return render(request, "leads/_detail_content.html", {
            "lead": lead,
            "historico": historico,
            "transicoes": [(s, Lead.Status(s).label) for s in transicoes],
        })


class LeadPipelineView(OperadorRequiredMixin, TemplateView):
    template_name = "leads/pipeline.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        leads = Lead.objects.select_related("parceiro").order_by("-criado_em")
        ctx["colunas"] = [
            {"status": s.value, "label": s.label, "leads": leads.filter(status=s.value)}
            for s in Lead.Status
        ]
        return ctx


class LeadCalendarioView(OperadorRequiredMixin, TemplateView):
    template_name = "leads/calendario.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        mes = self.request.GET.get("mes", "")

        if mes:
            try:
                partes = mes.split("-")
                ano, mes_num = int(partes[0]), int(partes[1])
            except (ValueError, IndexError):
                hoje = timezone.now()
                ano, mes_num = hoje.year, hoje.month
        else:
            hoje = timezone.now()
            ano, mes_num = hoje.year, hoje.month

        leads = (
            Lead.objects.filter(criado_em__year=ano, criado_em__month=mes_num)
            .select_related("parceiro")
            .order_by("criado_em")
        )

        import calendar
        cal = calendar.monthcalendar(ano, mes_num)

        dias = {}
        for lead in leads:
            dia = lead.criado_em.day
            if dia not in dias:
                dias[dia] = []
            dias[dia].append(lead)

        # Navegação
        if mes_num == 1:
            prev_mes = f"{ano - 1:04d}-12"
        else:
            prev_mes = f"{ano:04d}-{mes_num - 1:02d}"
        if mes_num == 12:
            next_mes = f"{ano + 1:04d}-01"
        else:
            next_mes = f"{ano:04d}-{mes_num + 1:02d}"

        ctx["ano"] = ano
        ctx["mes_num"] = mes_num
        ctx["mes_nome"] = calendar.month_name[mes_num]
        ctx["semanas"] = cal
        ctx["dias"] = dias
        ctx["total"] = leads.count()
        ctx["prev_mes"] = prev_mes
        ctx["next_mes"] = next_mes
        return ctx


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------
class ClienteListView(OperadorRequiredMixin, HtmxMixin, ListView):
    template_name = "clientes/list.html"
    partial_template_name = "clientes/_table.html"
    context_object_name = "clientes"
    paginate_by = 20

    def get_queryset(self):
        qs = Cliente.objects.prefetch_related("produtos").order_by("-ativado_em")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(cnpj__icontains=search) | Q(email__icontains=search))
        return qs


class ClienteDetailView(OperadorRequiredMixin, View):
    def get(self, request, pk):
        cliente = get_object_or_404(
            Cliente.objects.prefetch_related("produtos"),
            pk=pk,
        )
        return render(request, "clientes/detail.html", {"cliente": cliente})


# ---------------------------------------------------------------------------
# Comissões
# ---------------------------------------------------------------------------
class ComissaoListView(LoginRequiredMixin, HtmxMixin, ListView):
    template_name = "comissoes/list.html"
    partial_template_name = "comissoes/_table.html"
    context_object_name = "comissoes"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Comissao.objects.select_related("parceiro", "venda").order_by("-gerado_em")

        if user.perfil == Usuario.Perfil.PARCEIRO and hasattr(user, "parceiro"):
            qs = qs.filter(parceiro=user.parceiro)

        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Comissao.Status.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        return ctx
