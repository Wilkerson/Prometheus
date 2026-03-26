import calendar

from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.accounts.models import Usuario
from apps.comissoes.models import Comissao
from apps.crm.models import Cliente, ClienteHistorico, EntidadeParceira

from .mixins import HtmxMixin, is_htmx


# ---------------------------------------------------------------------------
# Landing Page (publica)
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

        if user.has_perm("crm.view_cliente"):
            if hasattr(user, "parceiro"):
                clientes_qs = Cliente.objects.filter(parceiro=user.parceiro)
            else:
                clientes_qs = Cliente.objects.all()

            stats = clientes_qs.values("status").annotate(total=Count("id"))
            por_status = {item["status"]: item["total"] for item in stats}
            ctx["clientes_total"] = sum(por_status.values())
            ctx["clientes_por_status"] = por_status
            ctx["clientes_recentes"] = clientes_qs.select_related("parceiro").order_by("-criado_em")[:10]

            limite = timezone.now() - timezone.timedelta(days=3)
            ctx["clientes_atrasados"] = (
                clientes_qs.exclude(status__in=[Cliente.Status.CONCLUIDA, Cliente.Status.PERDIDA])
                .filter(atualizado_em__lt=limite)
                .count()
            )
        else:
            ctx["clientes_total"] = 0
            ctx["clientes_por_status"] = {}
            ctx["clientes_recentes"] = []
            ctx["clientes_atrasados"] = 0

        if user.has_perm("comissoes.view_comissao"):
            if hasattr(user, "parceiro"):
                comissoes_qs = Comissao.objects.filter(parceiro=user.parceiro)
            else:
                comissoes_qs = Comissao.objects.all()

            comissao_stats = comissoes_qs.aggregate(
                pendente=Sum("valor_comissao", filter=Q(status=Comissao.Status.PENDENTE)),
                pago=Sum("valor_comissao", filter=Q(status=Comissao.Status.PAGO)),
            )
            ctx["comissao_pendente"] = comissao_stats["pendente"] or 0
            ctx["comissao_pago"] = comissao_stats["pago"] or 0
        else:
            ctx["comissao_pendente"] = 0
            ctx["comissao_pago"] = 0

        ctx["can_view_clientes"] = user.has_perm("crm.view_cliente")
        ctx["can_view_comissoes"] = user.has_perm("comissoes.view_comissao")

        return ctx


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------
class ClienteListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "clientes/list.html"
    partial_template_name = "clientes/_table.html"
    context_object_name = "clientes"
    paginate_by = 20
    permission_required = "crm.view_cliente"

    def get_queryset(self):
        user = self.request.user
        qs = Cliente.objects.select_related("parceiro", "operador").order_by("-criado_em")

        if hasattr(user, "parceiro"):
            qs = qs.filter(parceiro=user.parceiro)

        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        produto_filter = self.request.GET.get("produto")
        if produto_filter:
            qs = qs.filter(produto_interesse=produto_filter)

        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(cnpj__icontains=search) | Q(email__icontains=search))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Cliente.Status.choices
        ctx["produto_choices"] = Cliente.Produto.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_produto"] = self.request.GET.get("produto", "")
        ctx["current_search"] = self.request.GET.get("q", "")
        ctx["can_add"] = self.request.user.has_perm("crm.add_cliente")
        return ctx


def _validar_cliente_form(post_data, files=None):
    """Valida dados do formulario de cliente. Retorna (dados_limpos, erros)."""
    erros = {}
    dados = {}

    # Nome
    nome = post_data.get("nome", "").strip()
    if not nome:
        erros["nome"] = "O nome e obrigatorio."
    dados["nome"] = nome

    # CNPJ
    cnpj = post_data.get("cnpj", "").strip()
    if not cnpj:
        erros["cnpj"] = "O CNPJ e obrigatorio."
    else:
        digits = "".join(c for c in cnpj if c.isdigit())
        if len(digits) != 14:
            erros["cnpj"] = "CNPJ deve conter 14 digitos."
    dados["cnpj"] = cnpj

    # Email
    email = post_data.get("email", "").strip()
    if not email:
        erros["email"] = "O email e obrigatorio."
    elif "@" not in email:
        erros["email"] = "Informe um email valido."
    dados["email"] = email

    # Telefone
    telefone = post_data.get("telefone", "").strip()
    if not telefone:
        erros["telefone"] = "O telefone e obrigatorio."
    dados["telefone"] = telefone

    # Endereco
    endereco = post_data.get("endereco", "").strip()
    if not endereco:
        erros["endereco"] = "O endereco e obrigatorio."
    dados["endereco"] = endereco

    # CEP
    cep = post_data.get("cep", "").strip()
    if not cep:
        erros["cep"] = "O CEP e obrigatorio."
    else:
        digits = "".join(c for c in cep if c.isdigit())
        if len(digits) != 8:
            erros["cep"] = "CEP deve conter 8 digitos."
    dados["cep"] = cep

    # Produto
    produto = post_data.get("produto_interesse", "")
    if not produto:
        erros["produto_interesse"] = "O produto de interesse e obrigatorio."
    dados["produto_interesse"] = produto

    # Arquivo
    arquivo = files.get("arquivo") if files else None
    if not arquivo:
        erros["arquivo"] = "O arquivo de Produtos ou Servicos e obrigatorio."
    dados["arquivo"] = arquivo

    return dados, erros


class ClienteCreateView(PermissionRequiredMixin, View):
    permission_required = "crm.add_cliente"

    def get(self, request):
        return render(request, "clientes/create.html", {
            "produto_choices": Cliente.Produto.choices,
            "erros": {},
            "dados": {},
        })

    def post(self, request):
        dados, erros = _validar_cliente_form(request.POST, request.FILES)

        if erros:
            ctx = {
                "produto_choices": Cliente.Produto.choices,
                "erros": erros,
                "dados": dados,
            }
            if is_htmx(request):
                return render(request, "clientes/_form_errors.html", ctx)
            return render(request, "clientes/create.html", ctx)

        user = request.user
        if hasattr(user, "parceiro"):
            dados["parceiro"] = user.parceiro
        else:
            parceiro_id = request.POST.get("parceiro")
            if parceiro_id:
                dados["parceiro"] = get_object_or_404(EntidadeParceira, id=parceiro_id)

        cliente = Cliente.objects.create(**dados)

        if is_htmx(request):
            return render(request, "clientes/_create_success.html", {"cliente": cliente})
        return redirect("web:cliente-detail", pk=cliente.pk)


class ClienteDetailView(PermissionRequiredMixin, View):
    permission_required = "crm.view_cliente"

    def get(self, request, pk):
        cliente = get_object_or_404(
            Cliente.objects.select_related("parceiro", "operador").prefetch_related("produtos"),
            pk=pk,
        )
        historico = cliente.historico.select_related("usuario").all()

        if hasattr(request.user, "parceiro") and cliente.parceiro != request.user.parceiro:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        transicoes = []
        if request.user.has_perm("crm.change_cliente"):
            transicoes = [(s, Cliente.Status(s).label) for s in Cliente.TRANSICOES_VALIDAS.get(cliente.status, ())]

        ctx = {
            "cliente": cliente,
            "historico": historico,
            "transicoes": transicoes,
            "can_edit": request.user.has_perm("crm.change_cliente"),
            "can_delete": request.user.has_perm("crm.delete_cliente"),
        }
        return render(request, "clientes/detail.html", ctx)


def _validar_cliente_edit(post_data, files=None, cliente_existente=None):
    """Validacao para edicao — arquivo so obrigatorio se ainda nao tem."""
    erros = {}
    dados = {}

    nome = post_data.get("nome", "").strip()
    if not nome:
        erros["nome"] = "O nome e obrigatorio."
    dados["nome"] = nome

    cnpj = post_data.get("cnpj", "").strip()
    if not cnpj:
        erros["cnpj"] = "O CNPJ e obrigatorio."
    else:
        digits = "".join(c for c in cnpj if c.isdigit())
        if len(digits) != 14:
            erros["cnpj"] = "CNPJ deve conter 14 digitos."
    dados["cnpj"] = cnpj

    email = post_data.get("email", "").strip()
    if not email:
        erros["email"] = "O email e obrigatorio."
    elif "@" not in email:
        erros["email"] = "Informe um email valido."
    dados["email"] = email

    telefone = post_data.get("telefone", "").strip()
    if not telefone:
        erros["telefone"] = "O telefone e obrigatorio."
    dados["telefone"] = telefone

    endereco = post_data.get("endereco", "").strip()
    if not endereco:
        erros["endereco"] = "O endereco e obrigatorio."
    dados["endereco"] = endereco

    cep = post_data.get("cep", "").strip()
    if not cep:
        erros["cep"] = "O CEP e obrigatorio."
    else:
        digits = "".join(c for c in cep if c.isdigit())
        if len(digits) != 8:
            erros["cep"] = "CEP deve conter 8 digitos."
    dados["cep"] = cep

    # Arquivo — na edicao, so obrigatorio se o cliente ainda nao tem
    arquivo = files.get("arquivo") if files else None
    if arquivo:
        dados["arquivo"] = arquivo
    elif cliente_existente and not cliente_existente.arquivo:
        erros["arquivo"] = "O arquivo de Produtos ou Servicos e obrigatorio."

    return dados, erros


class ClienteUpdateView(PermissionRequiredMixin, View):
    permission_required = "crm.change_cliente"

    def get(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        return render(request, "clientes/edit.html", {"cliente": cliente, "erros": {}})

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        dados, erros = _validar_cliente_edit(request.POST, request.FILES, cliente)

        if erros:
            ctx = {"cliente": cliente, "erros": erros}
            if is_htmx(request):
                return render(request, "clientes/_form_errors.html", ctx)
            return render(request, "clientes/edit.html", ctx)

        cliente.nome = dados["nome"]
        cliente.cnpj = dados["cnpj"]
        cliente.email = dados["email"]
        cliente.telefone = dados["telefone"]
        cliente.endereco = dados["endereco"]
        cliente.cep = dados["cep"]
        cliente.ativo = request.POST.get("ativo") == "on"
        if "arquivo" in dados:
            cliente.arquivo = dados["arquivo"]
        cliente.save()

        if is_htmx(request):
            return render(request, "clientes/_edit_success.html", {"cliente": cliente})
        return redirect("web:cliente-detail", pk=cliente.pk)


class ClienteUpdateStatusView(PermissionRequiredMixin, View):
    permission_required = "crm.change_cliente"

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        novo_status = request.POST.get("status")
        observacao = request.POST.get("observacao", "")

        if not cliente.pode_transitar_para(novo_status):
            return render(request, "clientes/_status_error.html", {
                "error": f"Transicao de '{cliente.get_status_display()}' para '{novo_status}' nao e permitida.",
            })

        status_anterior = cliente.status
        cliente.status = novo_status
        cliente.save(update_fields=["status", "atualizado_em"])

        ClienteHistorico.objects.create(
            cliente=cliente,
            status_anterior=status_anterior,
            status_novo=novo_status,
            usuario=request.user,
            observacao=observacao,
        )

        if novo_status == Cliente.Status.EM_PROCESSAMENTO:
            from apps.crm.tasks import enviar_cliente_sistema_externo
            enviar_cliente_sistema_externo.delay(cliente.id)

        historico = cliente.historico.select_related("usuario").all()
        transicoes = [(s, Cliente.Status(s).label) for s in Cliente.TRANSICOES_VALIDAS.get(cliente.status, ())]

        return render(request, "clientes/_detail_content.html", {
            "cliente": cliente,
            "historico": historico,
            "transicoes": transicoes,
            "can_edit": True,
            "can_delete": request.user.has_perm("crm.delete_cliente"),
        })


class ClienteDeleteView(PermissionRequiredMixin, View):
    permission_required = "crm.delete_cliente"

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        cliente.delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/clientes/"})
        return redirect("web:clientes")


class ClientePipelineView(PermissionRequiredMixin, TemplateView):
    template_name = "clientes/pipeline.html"
    permission_required = "crm.change_cliente"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        clientes = Cliente.objects.select_related("parceiro").order_by("-criado_em")
        ctx["colunas"] = [
            {"status": s.value, "label": s.label, "clientes": clientes.filter(status=s.value)}
            for s in Cliente.Status
        ]
        return ctx


class ClienteCalendarioView(PermissionRequiredMixin, TemplateView):
    template_name = "clientes/calendario.html"
    permission_required = "crm.view_cliente"

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

        clientes = (
            Cliente.objects.filter(criado_em__year=ano, criado_em__month=mes_num)
            .select_related("parceiro")
            .order_by("criado_em")
        )

        cal = calendar.monthcalendar(ano, mes_num)
        dias = {}
        for cliente in clientes:
            dia = cliente.criado_em.day
            if dia not in dias:
                dias[dia] = []
            dias[dia].append(cliente)

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
        ctx["total"] = clientes.count()
        ctx["prev_mes"] = prev_mes
        ctx["next_mes"] = next_mes
        return ctx


# ---------------------------------------------------------------------------
# Comissoes
# ---------------------------------------------------------------------------
class ComissaoListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "comissoes/list.html"
    partial_template_name = "comissoes/_table.html"
    context_object_name = "comissoes"
    paginate_by = 20
    permission_required = "comissoes.view_comissao"

    def get_queryset(self):
        user = self.request.user
        qs = Comissao.objects.select_related("parceiro", "venda").order_by("-gerado_em")

        if hasattr(user, "parceiro"):
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
