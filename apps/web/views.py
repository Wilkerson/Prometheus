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

from django.contrib.auth.models import Group

from apps.accounts.models import Usuario
from apps.comissoes.models import Comissao
from apps.crm.models import Cliente, ClienteHistorico, Endereco, EntidadeParceira, Notificacao, Plano, PlanoProduto, Produto
from apps.crm.validators import ACCEPT_HTML, validar_arquivo
from apps.integracao.models import TokenIntegracao
from apps.rh.models import Cargo, Colaborador, Departamento, HistoricoColaborador

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


class AvatarUpdateView(LoginRequiredMixin, View):
    def post(self, request):
        avatar = request.FILES.get("avatar")
        if not avatar:
            return redirect("web:dashboard")

        # Validar tipo
        import os
        _, ext = os.path.splitext(avatar.name.lower())
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            return redirect("web:dashboard")

        # Validar tamanho (max 2MB)
        if avatar.size > 2 * 1024 * 1024:
            return redirect("web:dashboard")

        # Remove avatar antigo se existir
        if request.user.avatar:
            request.user.avatar.delete(save=False)

        request.user.avatar = avatar
        request.user.save()
        return redirect("web:dashboard")


class AvatarRemoveView(LoginRequiredMixin, View):
    def post(self, request):
        if request.user.avatar:
            request.user.avatar.delete(save=False)
            request.user.avatar = None
            request.user.save()
        return redirect("web:dashboard")


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

        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(cnpj__icontains=search) | Q(email__icontains=search))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Cliente.Status.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_search"] = self.request.GET.get("q", "")
        ctx["can_add"] = self.request.user.has_perm("crm.add_cliente")
        return ctx


def _validar_endereco(post_data):
    """Valida campos de endereco. Retorna (dados_endereco, erros)."""
    erros = {}
    dados = {}

    cep = post_data.get("cep", "").strip()
    if not cep:
        erros["cep"] = "O CEP e obrigatorio."
    else:
        digits = "".join(c for c in cep if c.isdigit())
        if len(digits) != 8:
            erros["cep"] = "CEP deve conter 8 digitos."
    dados["cep"] = cep

    logradouro = post_data.get("logradouro", "").strip()
    if not logradouro:
        erros["logradouro"] = "O logradouro e obrigatorio."
    dados["logradouro"] = logradouro

    numero = post_data.get("numero", "").strip()
    if not numero:
        erros["numero"] = "O numero e obrigatorio."
    dados["numero"] = numero

    dados["complemento"] = post_data.get("complemento", "").strip()

    bairro = post_data.get("bairro", "").strip()
    if not bairro:
        erros["bairro"] = "O bairro e obrigatorio."
    dados["bairro"] = bairro

    cidade = post_data.get("cidade", "").strip()
    if not cidade:
        erros["cidade"] = "A cidade e obrigatoria."
    dados["cidade"] = cidade

    uf = post_data.get("uf", "").strip().upper()
    if not uf:
        erros["uf"] = "O UF e obrigatorio."
    dados["uf"] = uf

    return dados, erros


def _validar_cliente_form(post_data, files=None):
    """Valida dados do formulario de cliente + endereco. Retorna (dados, endereco_dados, erros)."""
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

    planos_ids = post_data.getlist("planos")
    if not planos_ids:
        erros["planos"] = "Selecione ao menos um plano."
    dados["planos_ids"] = planos_ids

    arquivo = files.get("arquivo") if files else None
    if not arquivo:
        erros["arquivo"] = "O arquivo de Produtos ou Servicos e obrigatorio."
    else:
        erro_formato = validar_arquivo(arquivo)
        if erro_formato:
            erros["arquivo"] = erro_formato
    dados["arquivo"] = arquivo

    endereco_dados, endereco_erros = _validar_endereco(post_data)
    erros.update(endereco_erros)

    return dados, endereco_dados, erros


def _get_planos_for_user(user):
    """Retorna planos disponiveis para o usuario (parceiro ve os seus)."""
    if hasattr(user, "parceiro"):
        return Plano.objects.filter(parceiro=user.parceiro, ativo=True).prefetch_related("itens__produto")
    return Plano.objects.filter(ativo=True).prefetch_related("itens__produto")


class ClienteCreateView(PermissionRequiredMixin, View):
    permission_required = "crm.add_cliente"

    def get(self, request):
        return render(request, "clientes/create.html", {
            "planos_disponiveis": _get_planos_for_user(request.user),
            "uf_choices": Endereco.UF_CHOICES, "accept_html": ACCEPT_HTML,
            "erros": {},
            "dados": {},
        })

    def post(self, request):
        dados, endereco_dados, erros = _validar_cliente_form(request.POST, request.FILES)

        if erros:
            ctx = {
                "planos_disponiveis": _get_planos_for_user(request.user),
                "uf_choices": Endereco.UF_CHOICES, "accept_html": ACCEPT_HTML,
                "erros": erros,
                "dados": {**dados, **endereco_dados},
            }
            if is_htmx(request):
                return render(request, "clientes/_form_errors.html", ctx)
            return render(request, "clientes/create.html", ctx)

        user = request.user
        planos_ids = dados.pop("planos_ids", [])
        endereco = Endereco.objects.create(**endereco_dados)
        dados["endereco"] = endereco

        if hasattr(user, "parceiro"):
            dados["parceiro"] = user.parceiro
        else:
            parceiro_id = request.POST.get("parceiro")
            if parceiro_id:
                dados["parceiro"] = get_object_or_404(EntidadeParceira, id=parceiro_id)

        cliente = Cliente.objects.create(**dados)
        if planos_ids:
            cliente.planos.set(planos_ids)

        if is_htmx(request):
            return render(request, "clientes/_create_success.html", {"cliente": cliente})
        return redirect("web:cliente-detail", pk=cliente.pk)


class ClienteDetailView(PermissionRequiredMixin, View):
    permission_required = "crm.view_cliente"

    def get(self, request, pk):
        cliente = get_object_or_404(
            Cliente.objects.select_related("parceiro", "operador", "endereco").prefetch_related("planos"),
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
    """Validacao para edicao — arquivo so obrigatorio se cliente ainda nao tem."""
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

    arquivo = files.get("arquivo") if files else None
    if arquivo:
        erro_formato = validar_arquivo(arquivo)
        if erro_formato:
            erros["arquivo"] = erro_formato
        else:
            dados["arquivo"] = arquivo
    elif cliente_existente and not cliente_existente.arquivo:
        erros["arquivo"] = "O arquivo de Produtos ou Servicos e obrigatorio."

    endereco_dados, endereco_erros = _validar_endereco(post_data)
    erros.update(endereco_erros)

    return dados, endereco_dados, erros


class ClienteUpdateView(PermissionRequiredMixin, View):
    permission_required = "crm.change_cliente"

    def get(self, request, pk):
        cliente = get_object_or_404(Cliente.objects.select_related("endereco"), pk=pk)
        return render(request, "clientes/edit.html", {
            "cliente": cliente,
            "uf_choices": Endereco.UF_CHOICES, "accept_html": ACCEPT_HTML,
            "erros": {},
        })

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente.objects.select_related("endereco"), pk=pk)
        dados, endereco_dados, erros = _validar_cliente_edit(request.POST, request.FILES, cliente)

        if erros:
            ctx = {"cliente": cliente, "uf_choices": Endereco.UF_CHOICES, "accept_html": ACCEPT_HTML, "erros": erros}
            if is_htmx(request):
                return render(request, "clientes/_form_errors.html", ctx)
            return render(request, "clientes/edit.html", ctx)

        cliente.nome = dados["nome"]
        cliente.cnpj = dados["cnpj"]
        cliente.email = dados["email"]
        cliente.telefone = dados["telefone"]
        cliente.ativo = "ativo" in request.POST
        if "arquivo" in dados:
            cliente.arquivo = dados["arquivo"]
        cliente.save()

        # Atualiza endereco
        end = cliente.endereco
        for attr, val in endereco_dados.items():
            setattr(end, attr, val)
        end.save()

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
        qs = Comissao.objects.select_related("parceiro", "cliente").order_by("-gerado_em")

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


# ---------------------------------------------------------------------------
# Produtos
# ---------------------------------------------------------------------------
class ProdutoListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "produtos/list.html"
    partial_template_name = "produtos/_table.html"
    context_object_name = "produtos"
    paginate_by = 20
    permission_required = "crm.view_produto"

    def get_queryset(self):
        qs = Produto.objects.order_by("nome")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(Q(nome__icontains=search))
        tier = self.request.GET.get("tier")
        if tier:
            qs = qs.filter(tier=tier)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tier_choices"] = Produto.Tier.choices
        ctx["current_tier"] = self.request.GET.get("tier", "")
        ctx["can_add"] = self.request.user.has_perm("crm.add_produto")
        return ctx


class ProdutoCreateView(PermissionRequiredMixin, View):
    permission_required = "crm.add_produto"

    def get(self, request):
        return render(request, "produtos/create.html", {
            "tier_choices": Produto.Tier.choices, "erros": {}, "dados": {},
        })

    def post(self, request):
        erros = {}
        nome = request.POST.get("nome", "").strip()
        if not nome:
            erros["nome"] = "O nome e obrigatorio."
        descricao = request.POST.get("descricao", "").strip()
        if not descricao:
            erros["descricao"] = "A descricao e obrigatoria."
        tier = request.POST.get("tier", "basico")
        dados = {"nome": nome, "descricao": descricao, "tier": tier}

        if erros:
            ctx = {"tier_choices": Produto.Tier.choices, "erros": erros, "dados": dados}
            if is_htmx(request):
                return render(request, "clientes/_form_errors.html", ctx)
            return render(request, "produtos/create.html", ctx)

        Produto.objects.create(**dados)
        return redirect("web:produtos")


class ProdutoUpdateView(PermissionRequiredMixin, View):
    permission_required = "crm.change_produto"

    def get(self, request, pk):
        produto = get_object_or_404(Produto, pk=pk)
        return render(request, "produtos/edit.html", {
            "produto": produto, "tier_choices": Produto.Tier.choices, "erros": {},
        })

    def post(self, request, pk):
        produto = get_object_or_404(Produto, pk=pk)
        produto.nome = request.POST.get("nome", produto.nome).strip()
        produto.descricao = request.POST.get("descricao", produto.descricao).strip()
        produto.tier = request.POST.get("tier", produto.tier)
        produto.ativo = "ativo" in request.POST
        produto.save()
        return redirect("web:produtos")


class ProdutoDeleteView(PermissionRequiredMixin, View):
    permission_required = "crm.delete_produto"

    def post(self, request, pk):
        get_object_or_404(Produto, pk=pk).delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/produtos/"})
        return redirect("web:produtos")


# ---------------------------------------------------------------------------
# Planos
# ---------------------------------------------------------------------------
class PlanoListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "planos/list.html"
    partial_template_name = "planos/_table.html"
    context_object_name = "planos"
    paginate_by = 20
    permission_required = "crm.view_plano"

    def get_queryset(self):
        user = self.request.user
        qs = Plano.objects.select_related("parceiro").prefetch_related("itens__produto").order_by("-criado_em")
        if hasattr(user, "parceiro"):
            qs = qs.filter(parceiro=user.parceiro)
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(parceiro__nome_entidade__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_add"] = self.request.user.has_perm("crm.add_plano")
        return ctx


class PlanoCreateView(PermissionRequiredMixin, View):
    permission_required = "crm.add_plano"

    def get(self, request):
        return render(request, "planos/create.html", {
            "parceiros": EntidadeParceira.objects.filter(ativo=True),
            "produtos": Produto.objects.filter(ativo=True),
            "erros": {},
        })

    def post(self, request):
        erros = {}
        nome = request.POST.get("nome", "").strip()
        if not nome:
            erros["nome"] = "O nome e obrigatorio."
        parceiro_id = request.POST.get("parceiro")
        if not parceiro_id:
            erros["parceiro"] = "Selecione um parceiro."

        produto_ids = request.POST.getlist("produto_id")
        precos = request.POST.getlist("preco")
        if not produto_ids or not any(produto_ids):
            erros["produtos"] = "Adicione ao menos um produto ao plano."

        if erros:
            ctx = {
                "parceiros": EntidadeParceira.objects.filter(ativo=True),
                "produtos": Produto.objects.filter(ativo=True),
                "erros": erros,
            }
            if is_htmx(request):
                return render(request, "clientes/_form_errors.html", ctx)
            return render(request, "planos/create.html", ctx)

        parceiro = get_object_or_404(EntidadeParceira, pk=parceiro_id)
        plano = Plano.objects.create(nome=nome, parceiro=parceiro)

        for pid, preco in zip(produto_ids, precos):
            if pid and preco:
                PlanoProduto.objects.create(
                    plano=plano,
                    produto_id=int(pid),
                    preco=preco,
                )

        return redirect("web:plano-detail", pk=plano.pk)


class PlanoDetailView(PermissionRequiredMixin, View):
    permission_required = "crm.view_plano"

    def get(self, request, pk):
        plano = get_object_or_404(
            Plano.objects.select_related("parceiro").prefetch_related("itens__produto"), pk=pk,
        )
        return render(request, "planos/detail.html", {
            "plano": plano,
            "can_edit": request.user.has_perm("crm.change_plano"),
            "can_delete": request.user.has_perm("crm.delete_plano"),
        })


class PlanoUpdateView(PermissionRequiredMixin, View):
    permission_required = "crm.change_plano"

    def get(self, request, pk):
        plano = get_object_or_404(Plano.objects.prefetch_related("itens__produto"), pk=pk)
        return render(request, "planos/edit.html", {
            "plano": plano,
            "parceiros": EntidadeParceira.objects.filter(ativo=True),
            "produtos": Produto.objects.filter(ativo=True),
            "erros": {},
        })

    def post(self, request, pk):
        plano = get_object_or_404(Plano, pk=pk)
        plano.nome = request.POST.get("nome", plano.nome).strip()
        parceiro_id = request.POST.get("parceiro")
        if parceiro_id:
            plano.parceiro = get_object_or_404(EntidadeParceira, pk=parceiro_id)
        plano.ativo = "ativo" in request.POST
        plano.save()

        # Recria itens
        plano.itens.all().delete()
        produto_ids = request.POST.getlist("produto_id")
        precos = request.POST.getlist("preco")
        for pid, preco in zip(produto_ids, precos):
            if pid and preco:
                PlanoProduto.objects.create(plano=plano, produto_id=int(pid), preco=preco)

        return redirect("web:plano-detail", pk=plano.pk)


class PlanoDeleteView(PermissionRequiredMixin, View):
    permission_required = "crm.delete_plano"

    def post(self, request, pk):
        get_object_or_404(Plano, pk=pk).delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/planos/"})
        return redirect("web:planos")


# ---------------------------------------------------------------------------
# Comissao — acao marcar como pago
# ---------------------------------------------------------------------------
class ComissaoMarcarPagoView(PermissionRequiredMixin, View):
    permission_required = "comissoes.change_comissao"

    def post(self, request, pk):
        comissao = get_object_or_404(Comissao, pk=pk)
        comissao.status = Comissao.Status.PAGO
        comissao.save(update_fields=["status"])
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/comissoes/"})
        return redirect("web:comissoes")


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------
class UsuarioListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "usuarios/list.html"
    partial_template_name = "usuarios/_table.html"
    context_object_name = "usuarios"
    paginate_by = 20
    permission_required = "accounts.view_usuario"

    def get_queryset(self):
        qs = Usuario.objects.order_by("-date_joined")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(
                Q(username__icontains=search) | Q(first_name__icontains=search)
                | Q(last_name__icontains=search) | Q(email__icontains=search)
            )
        grupo = self.request.GET.get("grupo")
        if grupo:
            qs = qs.filter(groups__id=grupo)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["grupos_filter"] = Group.objects.all()
        ctx["current_grupo"] = self.request.GET.get("grupo", "")
        ctx["can_add"] = self.request.user.has_perm("accounts.add_usuario")
        return ctx


class UsuarioCreateView(PermissionRequiredMixin, View):
    permission_required = "accounts.add_usuario"

    def get(self, request):
        return render(request, "usuarios/create.html", {
            "groups": Group.objects.all(),
            "erros": {},
        })

    def post(self, request):
        erros = {}
        username = request.POST.get("username", "").strip()
        if not username:
            erros["username"] = "O username e obrigatorio."
        elif Usuario.objects.filter(username=username).exists():
            erros["username"] = "Esse username ja esta em uso."

        email = request.POST.get("email", "").strip()
        if not email:
            erros["email"] = "O email e obrigatorio."

        password = request.POST.get("password", "")
        if not password or len(password) < 8:
            erros["password"] = "A senha deve ter no minimo 8 caracteres."

        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()

        if erros:
            ctx = {
                "groups": Group.objects.all(),
                "erros": erros,
            }
            return render(request, "usuarios/create.html", ctx)

        user = Usuario.objects.create_user(
            username=username, email=email, password=password,
            first_name=first_name, last_name=last_name,
        )
        group_ids = request.POST.getlist("groups")
        if group_ids:
            user.groups.set(group_ids)

        return redirect("web:usuarios")


class UsuarioUpdateView(PermissionRequiredMixin, View):
    permission_required = "accounts.change_usuario"

    def get(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        return render(request, "usuarios/edit.html", {
            "usuario": usuario,
            "groups": Group.objects.all(),
            "usuario_groups": list(usuario.groups.values_list("id", flat=True)),
            "erros": {},
        })

    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        usuario.first_name = request.POST.get("first_name", "").strip()
        usuario.last_name = request.POST.get("last_name", "").strip()
        usuario.email = request.POST.get("email", usuario.email).strip()
        usuario.is_active = "is_active" in request.POST
        usuario.save()

        new_password = request.POST.get("new_password", "").strip()
        if new_password and len(new_password) >= 8:
            usuario.set_password(new_password)
            usuario.save()

        group_ids = request.POST.getlist("groups")
        usuario.groups.set(group_ids)

        return redirect("web:usuarios")


class UsuarioDeleteView(PermissionRequiredMixin, View):
    permission_required = "accounts.delete_usuario"

    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        if usuario == request.user:
            return HttpResponse("Nao e possivel excluir seu proprio usuario.", status=400)
        usuario.delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/usuarios/"})
        return redirect("web:usuarios")


# ---------------------------------------------------------------------------
# Entidades Parceiras
# ---------------------------------------------------------------------------
class ParceiroListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "parceiros/list.html"
    partial_template_name = "parceiros/_table.html"
    context_object_name = "parceiros"
    paginate_by = 20
    permission_required = "crm.view_entidadeparceira"

    def get_queryset(self):
        qs = EntidadeParceira.objects.select_related("usuario").order_by("-criado_em")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(Q(nome_entidade__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_add"] = self.request.user.has_perm("crm.add_entidadeparceira")
        return ctx


class ParceiroCreateView(PermissionRequiredMixin, View):
    permission_required = "crm.add_entidadeparceira"

    def get(self, request):
        usuarios_disponiveis = Usuario.objects.filter(
            is_active=True
        ).exclude(parceiro__isnull=False)
        return render(request, "parceiros/create.html", {
            "usuarios": usuarios_disponiveis, "erros": {},
        })

    def post(self, request):
        erros = {}
        nome = request.POST.get("nome_entidade", "").strip()
        if not nome:
            erros["nome_entidade"] = "O nome e obrigatorio."
        usuario_id = request.POST.get("usuario")
        if not usuario_id:
            erros["usuario"] = "Selecione um usuario."
        percentual = request.POST.get("percentual_comissao", "10.00")

        if erros:
            usuarios_disponiveis = Usuario.objects.filter(
                perfil=Usuario.Perfil.PARCEIRO
            ).exclude(parceiro__isnull=False)
            return render(request, "parceiros/create.html", {
                "usuarios": usuarios_disponiveis, "erros": erros,
            })

        EntidadeParceira.objects.create(
            usuario_id=usuario_id, nome_entidade=nome,
            percentual_comissao=percentual,
        )
        return redirect("web:parceiros")


class ParceiroUpdateView(PermissionRequiredMixin, View):
    permission_required = "crm.change_entidadeparceira"

    def get(self, request, pk):
        parceiro = get_object_or_404(EntidadeParceira.objects.select_related("usuario"), pk=pk)
        return render(request, "parceiros/edit.html", {"parceiro": parceiro, "erros": {}})

    def post(self, request, pk):
        parceiro = get_object_or_404(EntidadeParceira, pk=pk)
        parceiro.nome_entidade = request.POST.get("nome_entidade", parceiro.nome_entidade).strip()
        parceiro.percentual_comissao = request.POST.get("percentual_comissao", parceiro.percentual_comissao)
        parceiro.ativo = "ativo" in request.POST
        parceiro.save()
        return redirect("web:parceiros")


class ParceiroDeleteView(PermissionRequiredMixin, View):
    permission_required = "crm.delete_entidadeparceira"

    def post(self, request, pk):
        get_object_or_404(EntidadeParceira, pk=pk).delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/parceiros/"})
        return redirect("web:parceiros")


# ---------------------------------------------------------------------------
# Tokens de integracao
# ---------------------------------------------------------------------------
class TokenListView(PermissionRequiredMixin, ListView):
    template_name = "tokens/list.html"
    context_object_name = "tokens"
    paginate_by = 20
    permission_required = "integracao.view_tokenintegracao"

    def get_queryset(self):
        return TokenIntegracao.objects.order_by("-criado_em")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_add"] = self.request.user.has_perm("integracao.add_tokenintegracao")
        return ctx


class TokenCreateView(PermissionRequiredMixin, View):
    permission_required = "integracao.add_tokenintegracao"

    def get(self, request):
        return render(request, "tokens/create.html", {"erros": {}})

    def post(self, request):
        nome = request.POST.get("nome", "").strip()
        if not nome:
            return render(request, "tokens/create.html", {
                "erros": {"nome": "O nome e obrigatorio."},
            })
        TokenIntegracao.objects.create(nome=nome)
        return redirect("web:tokens")


class TokenDeleteView(PermissionRequiredMixin, View):
    permission_required = "integracao.delete_tokenintegracao"

    def post(self, request, pk):
        get_object_or_404(TokenIntegracao, pk=pk).delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/tokens/"})
        return redirect("web:tokens")


# ---------------------------------------------------------------------------
# Grupos e Permissoes
# ---------------------------------------------------------------------------

# Modulos expostos na matriz de permissoes (label amigavel + app_label.model)
MODULOS_PERMISSOES = [
    {"label": "Clientes", "app": "crm", "model": "cliente"},
    {"label": "Produtos", "app": "crm", "model": "produto"},
    {"label": "Planos", "app": "crm", "model": "plano"},
    {"label": "Comissoes", "app": "comissoes", "model": "comissao"},
    {"label": "Usuarios", "app": "accounts", "model": "usuario"},
    {"label": "Parceiros", "app": "crm", "model": "entidadeparceira"},
    {"label": "Tokens API", "app": "integracao", "model": "tokenintegracao"},
    {"label": "Departamentos", "app": "rh", "model": "departamento"},
    {"label": "Cargos", "app": "rh", "model": "cargo"},
    {"label": "Colaboradores", "app": "rh", "model": "colaborador"},
]

ACOES = [
    {"key": "view", "label": "Ver"},
    {"key": "add", "label": "Criar"},
    {"key": "change", "label": "Editar"},
    {"key": "delete", "label": "Excluir"},
]


def _build_permission_matrix(group=None):
    """Monta a matriz de modulos x acoes com estado checked."""
    from django.contrib.auth.models import Permission

    group_perm_codenames = set()
    if group:
        group_perm_codenames = set(group.permissions.values_list("codename", flat=True))

    matrix = []
    for mod in MODULOS_PERMISSOES:
        row = {"label": mod["label"], "acoes": []}
        for acao in ACOES:
            codename = f"{acao['key']}_{mod['model']}"
            perm = Permission.objects.filter(
                codename=codename,
                content_type__app_label=mod["app"],
            ).first()
            row["acoes"].append({
                "label": acao["label"],
                "perm_id": perm.id if perm else None,
                "codename": codename,
                "checked": codename in group_perm_codenames,
            })
        matrix.append(row)
    return matrix


class GrupoListView(LoginRequiredMixin, ListView):
    template_name = "grupos/list.html"
    context_object_name = "grupos"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Group.objects.prefetch_related("permissions").order_by("name")


class GrupoCreateView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, "grupos/create.html", {
            "matrix": _build_permission_matrix(),
            "erros": {},
        })

    def post(self, request):
        nome = request.POST.get("name", "").strip()
        if not nome:
            return render(request, "grupos/create.html", {
                "matrix": _build_permission_matrix(),
                "erros": {"name": "O nome do grupo e obrigatorio."},
            })
        if Group.objects.filter(name=nome).exists():
            return render(request, "grupos/create.html", {
                "matrix": _build_permission_matrix(),
                "erros": {"name": "Ja existe um grupo com esse nome."},
            })

        group = Group.objects.create(name=nome)
        perm_ids = request.POST.getlist("permissions")
        if perm_ids:
            group.permissions.set(perm_ids)
        return redirect("web:grupos")


class GrupoUpdateView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        return render(request, "grupos/edit.html", {
            "grupo": group,
            "matrix": _build_permission_matrix(group),
            "erros": {},
        })

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        nome = request.POST.get("name", "").strip()
        if nome:
            group.name = nome
            group.save()

        perm_ids = request.POST.getlist("permissions")
        group.permissions.set(perm_ids)
        return redirect("web:grupos")


class GrupoDeleteView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        get_object_or_404(Group, pk=pk).delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/grupos/"})
        return redirect("web:grupos")


# ---------------------------------------------------------------------------
# Notificacoes
# ---------------------------------------------------------------------------
class NotificacaoListView(LoginRequiredMixin, ListView):
    template_name = "notificacoes/list.html"
    context_object_name = "notificacoes"
    paginate_by = 30

    def get_queryset(self):
        return Notificacao.objects.filter(destinatario=self.request.user).order_by("-criado_em")


class NotificacaoLerView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(Notificacao, pk=pk, destinatario=request.user)
        notif.lida = True
        notif.save(update_fields=["lida"])
        if notif.link:
            return redirect(notif.link)
        return redirect("web:notificacoes")


class NotificacaoLerTodasView(LoginRequiredMixin, View):
    def post(self, request):
        Notificacao.objects.filter(destinatario=request.user, lida=False).update(lida=True)
        return redirect("web:notificacoes")


class NotificacaoPainelView(LoginRequiredMixin, View):
    """Partial HTMX: retorna o bloco de notificacoes do right panel (polling)."""

    def get(self, request):
        notif_nao_lidas = Notificacao.objects.filter(destinatario=request.user, lida=False)
        return render(request, "notificacoes/_painel.html", {
            "notif_count": notif_nao_lidas.count(),
            "notif_recentes": notif_nao_lidas[:5],
        })


class NotificacaoPreferenciasView(LoginRequiredMixin, View):
    def get(self, request):
        from apps.crm.models import PreferenciaNotificacao
        prefs, _ = PreferenciaNotificacao.objects.get_or_create(usuario=request.user)
        return render(request, "notificacoes/preferencias.html", {"prefs": prefs})

    def post(self, request):
        from apps.crm.models import PreferenciaNotificacao
        prefs, _ = PreferenciaNotificacao.objects.get_or_create(usuario=request.user)

        campos = [
            "cliente_novo", "cliente_status", "cliente_zypher_ok",
            "cliente_zypher_falha", "comissao_gerada", "comissao_paga",
            "usuario_criado", "sistema",
        ]
        for campo in campos:
            setattr(prefs, campo, campo in request.POST)
        prefs.save()

        return redirect("web:notificacao-preferencias")


# ---------------------------------------------------------------------------
# RH — Departamentos
# ---------------------------------------------------------------------------
class DepartamentoListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "rh/departamentos/list.html"
    partial_template_name = "rh/departamentos/_table.html"
    context_object_name = "departamentos"
    paginate_by = 20
    permission_required = "rh.view_departamento"

    def get_queryset(self):
        qs = Departamento.objects.annotate(total_cargos=Count("cargos"))
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(nome__icontains=search)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_add"] = self.request.user.has_perm("rh.add_departamento")
        return ctx


class DepartamentoCreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_departamento"

    def get(self, request):
        return render(request, "rh/departamentos/create.html", {"erros": {}, "dados": {}})

    def post(self, request):
        erros = {}
        nome = request.POST.get("nome", "").strip()
        if not nome:
            erros["nome"] = "O nome e obrigatorio."
        elif Departamento.objects.filter(nome__iexact=nome).exists():
            erros["nome"] = "Ja existe um departamento com esse nome."
        descricao = request.POST.get("descricao", "").strip()
        dados = {"nome": nome, "descricao": descricao}

        if erros:
            return render(request, "rh/departamentos/create.html", {"erros": erros, "dados": dados})

        Departamento.objects.create(**dados)
        return redirect("web:rh-departamentos")


class DepartamentoDetailView(PermissionRequiredMixin, View):
    permission_required = "rh.view_departamento"

    def get(self, request, pk):
        depto = get_object_or_404(Departamento, pk=pk)
        cargos = depto.cargos.select_related("departamento").order_by("nome")
        colaboradores = depto.colaboradores.select_related("cargo").order_by("nome_completo")
        return render(request, "rh/departamentos/detail.html", {
            "depto": depto,
            "cargos": cargos,
            "colaboradores": colaboradores,
            "can_edit": request.user.has_perm("rh.change_departamento"),
        })


class DepartamentoUpdateView(PermissionRequiredMixin, View):
    permission_required = "rh.change_departamento"

    def get(self, request, pk):
        depto = get_object_or_404(Departamento, pk=pk)
        return render(request, "rh/departamentos/edit.html", {"depto": depto, "erros": {}})

    def post(self, request, pk):
        depto = get_object_or_404(Departamento, pk=pk)
        erros = {}
        nome = request.POST.get("nome", "").strip()
        if not nome:
            erros["nome"] = "O nome e obrigatorio."
        elif Departamento.objects.filter(nome__iexact=nome).exclude(pk=pk).exists():
            erros["nome"] = "Ja existe um departamento com esse nome."

        if erros:
            return render(request, "rh/departamentos/edit.html", {"depto": depto, "erros": erros})

        depto.nome = nome
        depto.descricao = request.POST.get("descricao", "").strip()
        depto.ativo = "ativo" in request.POST
        depto.save()
        return redirect("web:rh-departamento-detail", pk=pk)


class DepartamentoDeleteView(PermissionRequiredMixin, View):
    permission_required = "rh.delete_departamento"

    def post(self, request, pk):
        depto = get_object_or_404(Departamento, pk=pk)
        depto.delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/rh/departamentos/"})
        return redirect("web:rh-departamentos")


# ---------------------------------------------------------------------------
# RH — Cargos
# ---------------------------------------------------------------------------
class CargoListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "rh/cargos/list.html"
    partial_template_name = "rh/cargos/_table.html"
    context_object_name = "cargos"
    paginate_by = 20
    permission_required = "rh.view_cargo"

    def get_queryset(self):
        qs = Cargo.objects.select_related("departamento")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(departamento__nome__icontains=search))
        nivel = self.request.GET.get("nivel")
        if nivel:
            qs = qs.filter(nivel=nivel)
        depto = self.request.GET.get("departamento")
        if depto:
            qs = qs.filter(departamento_id=depto)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["nivel_choices"] = Cargo.Nivel.choices
        ctx["current_nivel"] = self.request.GET.get("nivel", "")
        ctx["departamentos"] = Departamento.objects.filter(ativo=True)
        ctx["current_depto"] = self.request.GET.get("departamento", "")
        ctx["can_add"] = self.request.user.has_perm("rh.add_cargo")
        return ctx


class CargoCreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_cargo"

    def get(self, request):
        return render(request, "rh/cargos/create.html", {
            "nivel_choices": Cargo.Nivel.choices,
            "departamentos": Departamento.objects.filter(ativo=True),
            "erros": {}, "dados": {},
        })

    def post(self, request):
        erros = {}
        nome = request.POST.get("nome", "").strip()
        if not nome:
            erros["nome"] = "O nome e obrigatorio."
        depto_id = request.POST.get("departamento")
        if not depto_id:
            erros["departamento"] = "O departamento e obrigatorio."
        nivel = request.POST.get("nivel", "analista")
        descricao = request.POST.get("descricao", "").strip()
        requisitos = request.POST.get("requisitos", "").strip()
        faixa_min = request.POST.get("faixa_salarial_min", "").strip() or None
        faixa_max = request.POST.get("faixa_salarial_max", "").strip() or None
        dados = {
            "nome": nome, "departamento": depto_id, "nivel": nivel,
            "descricao": descricao, "requisitos": requisitos,
            "faixa_salarial_min": faixa_min, "faixa_salarial_max": faixa_max,
        }

        if not erros and depto_id:
            if Cargo.objects.filter(nome__iexact=nome, departamento_id=depto_id).exists():
                erros["nome"] = "Ja existe um cargo com esse nome neste departamento."

        if erros:
            return render(request, "rh/cargos/create.html", {
                "nivel_choices": Cargo.Nivel.choices,
                "departamentos": Departamento.objects.filter(ativo=True),
                "erros": erros, "dados": dados,
            })

        Cargo.objects.create(
            nome=nome, departamento_id=depto_id, nivel=nivel,
            descricao=descricao, requisitos=requisitos,
            faixa_salarial_min=faixa_min, faixa_salarial_max=faixa_max,
        )
        return redirect("web:rh-cargos")


class CargoDetailView(PermissionRequiredMixin, View):
    permission_required = "rh.view_cargo"

    def get(self, request, pk):
        cargo = get_object_or_404(Cargo.objects.select_related("departamento"), pk=pk)
        colaboradores = cargo.colaboradores.order_by("nome_completo")
        return render(request, "rh/cargos/detail.html", {
            "cargo": cargo,
            "colaboradores": colaboradores,
            "can_edit": request.user.has_perm("rh.change_cargo"),
        })


class CargoUpdateView(PermissionRequiredMixin, View):
    permission_required = "rh.change_cargo"

    def get(self, request, pk):
        cargo = get_object_or_404(Cargo, pk=pk)
        return render(request, "rh/cargos/edit.html", {
            "cargo": cargo,
            "nivel_choices": Cargo.Nivel.choices,
            "departamentos": Departamento.objects.filter(ativo=True),
            "erros": {},
        })

    def post(self, request, pk):
        cargo = get_object_or_404(Cargo, pk=pk)
        erros = {}
        nome = request.POST.get("nome", "").strip()
        if not nome:
            erros["nome"] = "O nome e obrigatorio."
        depto_id = request.POST.get("departamento")
        if not depto_id:
            erros["departamento"] = "O departamento e obrigatorio."

        if not erros and depto_id:
            if Cargo.objects.filter(nome__iexact=nome, departamento_id=depto_id).exclude(pk=pk).exists():
                erros["nome"] = "Ja existe um cargo com esse nome neste departamento."

        if erros:
            return render(request, "rh/cargos/edit.html", {
                "cargo": cargo,
                "nivel_choices": Cargo.Nivel.choices,
                "departamentos": Departamento.objects.filter(ativo=True),
                "erros": erros,
            })

        cargo.nome = nome
        cargo.departamento_id = depto_id
        cargo.nivel = request.POST.get("nivel", cargo.nivel)
        cargo.descricao = request.POST.get("descricao", "").strip()
        cargo.requisitos = request.POST.get("requisitos", "").strip()
        cargo.faixa_salarial_min = request.POST.get("faixa_salarial_min", "").strip() or None
        cargo.faixa_salarial_max = request.POST.get("faixa_salarial_max", "").strip() or None
        cargo.ativo = "ativo" in request.POST
        cargo.save()
        return redirect("web:rh-cargo-detail", pk=pk)


class CargoDeleteView(PermissionRequiredMixin, View):
    permission_required = "rh.delete_cargo"

    def post(self, request, pk):
        cargo = get_object_or_404(Cargo, pk=pk)
        cargo.delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/rh/cargos/"})
        return redirect("web:rh-cargos")


# ---------------------------------------------------------------------------
# RH — Colaboradores
# ---------------------------------------------------------------------------
class ColaboradorListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "rh/colaboradores/list.html"
    partial_template_name = "rh/colaboradores/_table.html"
    context_object_name = "colaboradores"
    paginate_by = 20
    permission_required = "rh.view_colaborador"

    def get_queryset(self):
        qs = Colaborador.objects.select_related("cargo", "departamento")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(
                Q(nome_completo__icontains=search)
                | Q(cpf__icontains=search)
                | Q(email_pessoal__icontains=search)
            )
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        tipo = self.request.GET.get("tipo")
        if tipo:
            qs = qs.filter(tipo_contrato=tipo)
        depto = self.request.GET.get("departamento")
        if depto:
            qs = qs.filter(departamento_id=depto)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Colaborador.Status.choices
        ctx["tipo_choices"] = Colaborador.TipoContrato.choices
        ctx["departamentos"] = Departamento.objects.filter(ativo=True)
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_tipo"] = self.request.GET.get("tipo", "")
        ctx["current_depto"] = self.request.GET.get("departamento", "")
        ctx["can_add"] = self.request.user.has_perm("rh.add_colaborador")
        return ctx


class ColaboradorCreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_colaborador"

    def get(self, request):
        return render(request, "rh/colaboradores/create.html", self._ctx({}))

    def post(self, request):
        erros = {}
        P = request.POST

        # Dados pessoais
        nome_completo = P.get("nome_completo", "").strip()
        if not nome_completo:
            erros["nome_completo"] = "O nome completo e obrigatorio."
        cpf = P.get("cpf", "").strip()
        if not cpf:
            erros["cpf"] = "O CPF e obrigatorio."
        elif Colaborador.objects.filter(cpf=cpf).exists():
            erros["cpf"] = "Ja existe um colaborador com esse CPF."
        data_nascimento = P.get("data_nascimento", "").strip()
        if not data_nascimento:
            erros["data_nascimento"] = "A data de nascimento e obrigatoria."
        telefone = P.get("telefone", "").strip()
        if not telefone:
            erros["telefone"] = "O telefone e obrigatorio."
        email_pessoal = P.get("email_pessoal", "").strip()
        if not email_pessoal:
            erros["email_pessoal"] = "O e-mail pessoal e obrigatorio."

        # Dados contratuais
        tipo_contrato = P.get("tipo_contrato", "").strip()
        if not tipo_contrato:
            erros["tipo_contrato"] = "O tipo de contrato e obrigatorio."
        data_admissao = P.get("data_admissao", "").strip()
        if not data_admissao:
            erros["data_admissao"] = "A data de admissao e obrigatoria."
        cargo_id = P.get("cargo")
        if not cargo_id:
            erros["cargo"] = "O cargo e obrigatorio."
        departamento_id = P.get("departamento")
        if not departamento_id:
            erros["departamento"] = "O departamento e obrigatorio."
        remuneracao = P.get("remuneracao", "").strip()
        if not remuneracao:
            erros["remuneracao"] = "A remuneracao e obrigatoria."

        # Endereco
        cep = P.get("cep", "").strip()
        logradouro = P.get("logradouro", "").strip()
        numero = P.get("numero", "").strip()
        sem_numero = "sem_numero" in P
        if sem_numero:
            numero = "S/N"
        bairro = P.get("bairro", "").strip()
        cidade = P.get("cidade", "").strip()
        uf = P.get("uf", "").strip()
        complemento = P.get("complemento", "").strip()

        dados = dict(P)

        if erros:
            return render(request, "rh/colaboradores/create.html", {**self._ctx(erros), "dados": P})

        # Criar endereco
        endereco = None
        if cep and logradouro and numero and bairro and cidade and uf:
            endereco = Endereco.objects.create(
                cep=cep, logradouro=logradouro, numero=numero,
                complemento=complemento, bairro=bairro, cidade=cidade, uf=uf,
            )

        colab = Colaborador.objects.create(
            nome_completo=nome_completo, cpf=cpf, data_nascimento=data_nascimento,
            telefone=telefone, email_pessoal=email_pessoal,
            contato_emergencia_nome=P.get("contato_emergencia_nome", "").strip(),
            contato_emergencia_telefone=P.get("contato_emergencia_telefone", "").strip(),
            tipo_contrato=tipo_contrato, data_admissao=data_admissao,
            cargo_id=cargo_id, departamento_id=departamento_id,
            remuneracao=remuneracao,
            carga_horaria_semanal=P.get("carga_horaria_semanal", 40) or 40,
            endereco=endereco,
            # CLT
            pis_nit=P.get("pis_nit", "").strip(),
            ctps_numero=P.get("ctps_numero", "").strip(),
            ctps_serie=P.get("ctps_serie", "").strip(),
            banco_deposito=P.get("banco_deposito", "").strip(),
            regime_trabalho=P.get("regime_trabalho", "").strip(),
            # PJ
            cnpj_pj=P.get("cnpj_pj", "").strip(),
            razao_social=P.get("razao_social", "").strip(),
            banco_pagamento_pj=P.get("banco_pagamento_pj", "").strip(),
            chave_pix=P.get("chave_pix", "").strip(),
        )

        # Registrar historico de admissao
        HistoricoColaborador.objects.create(
            colaborador=colab,
            tipo=HistoricoColaborador.TipoEvento.ADMISSAO,
            cargo_novo=str(colab.cargo),
            departamento_novo=str(colab.departamento),
            remuneracao_nova=colab.remuneracao,
            registrado_por=request.user,
            observacao="Admissao registrada no sistema.",
        )

        return redirect("web:rh-colaborador-detail", pk=colab.pk)

    def _ctx(self, erros):
        return {
            "erros": erros,
            "tipo_choices": Colaborador.TipoContrato.choices,
            "regime_choices": Colaborador.RegimeTrabalho.choices,
            "departamentos": Departamento.objects.filter(ativo=True),
            "cargos": Cargo.objects.filter(ativo=True).select_related("departamento"),
            "uf_choices": Endereco.UF_CHOICES,
        }


class ColaboradorDetailView(PermissionRequiredMixin, View):
    permission_required = "rh.view_colaborador"

    def get(self, request, pk):
        colab = get_object_or_404(
            Colaborador.objects.select_related("cargo", "departamento", "endereco"), pk=pk
        )
        historico = colab.historico.select_related("registrado_por").order_by("-criado_em")
        return render(request, "rh/colaboradores/detail.html", {
            "colab": colab,
            "historico": historico,
            "can_edit": request.user.has_perm("rh.change_colaborador"),
        })


class ColaboradorUpdateView(PermissionRequiredMixin, View):
    permission_required = "rh.change_colaborador"

    def get(self, request, pk):
        colab = get_object_or_404(
            Colaborador.objects.select_related("cargo", "departamento", "endereco"), pk=pk
        )
        return render(request, "rh/colaboradores/edit.html", {
            "colab": colab,
            "tipo_choices": Colaborador.TipoContrato.choices,
            "regime_choices": Colaborador.RegimeTrabalho.choices,
            "status_choices": Colaborador.Status.choices,
            "departamentos": Departamento.objects.filter(ativo=True),
            "cargos": Cargo.objects.filter(ativo=True).select_related("departamento"),
            "uf_choices": Endereco.UF_CHOICES,
            "erros": {},
        })

    def post(self, request, pk):
        colab = get_object_or_404(
            Colaborador.objects.select_related("cargo", "departamento", "endereco"), pk=pk
        )
        P = request.POST

        # Rastrear mudancas para historico
        old_cargo = str(colab.cargo)
        old_depto = str(colab.departamento)
        old_rem = colab.remuneracao

        # Atualizar dados pessoais
        colab.nome_completo = P.get("nome_completo", colab.nome_completo).strip()
        colab.cpf = P.get("cpf", colab.cpf).strip()
        colab.data_nascimento = P.get("data_nascimento", colab.data_nascimento)
        colab.telefone = P.get("telefone", colab.telefone).strip()
        colab.email_pessoal = P.get("email_pessoal", colab.email_pessoal).strip()
        colab.contato_emergencia_nome = P.get("contato_emergencia_nome", "").strip()
        colab.contato_emergencia_telefone = P.get("contato_emergencia_telefone", "").strip()

        # Contratuais
        colab.tipo_contrato = P.get("tipo_contrato", colab.tipo_contrato)
        colab.cargo_id = P.get("cargo", colab.cargo_id)
        colab.departamento_id = P.get("departamento", colab.departamento_id)
        new_rem = P.get("remuneracao", "").strip()
        if new_rem:
            colab.remuneracao = new_rem
        colab.carga_horaria_semanal = P.get("carga_horaria_semanal", colab.carga_horaria_semanal) or 40
        colab.status = P.get("status", colab.status)

        # CLT
        colab.pis_nit = P.get("pis_nit", "").strip()
        colab.ctps_numero = P.get("ctps_numero", "").strip()
        colab.ctps_serie = P.get("ctps_serie", "").strip()
        colab.banco_deposito = P.get("banco_deposito", "").strip()
        colab.regime_trabalho = P.get("regime_trabalho", "").strip()

        # PJ
        colab.cnpj_pj = P.get("cnpj_pj", "").strip()
        colab.razao_social = P.get("razao_social", "").strip()
        colab.banco_pagamento_pj = P.get("banco_pagamento_pj", "").strip()
        colab.chave_pix = P.get("chave_pix", "").strip()

        # Endereco
        cep = P.get("cep", "").strip()
        logradouro = P.get("logradouro", "").strip()
        numero = P.get("numero", "").strip()
        sem_numero = "sem_numero" in P
        if sem_numero:
            numero = "S/N"
        bairro = P.get("bairro", "").strip()
        cidade = P.get("cidade", "").strip()
        uf = P.get("uf", "").strip()
        complemento = P.get("complemento", "").strip()

        if cep and logradouro and numero and bairro and cidade and uf:
            if colab.endereco:
                end = colab.endereco
                end.cep = cep
                end.logradouro = logradouro
                end.numero = numero
                end.complemento = complemento
                end.bairro = bairro
                end.cidade = cidade
                end.uf = uf
                end.save()
            else:
                colab.endereco = Endereco.objects.create(
                    cep=cep, logradouro=logradouro, numero=numero,
                    complemento=complemento, bairro=bairro, cidade=cidade, uf=uf,
                )

        colab.save()

        # Gerar historico automatico se houve mudancas relevantes
        new_cargo = str(colab.cargo)
        new_depto = str(colab.departamento)
        new_rem_val = colab.remuneracao

        if old_cargo != new_cargo:
            HistoricoColaborador.objects.create(
                colaborador=colab,
                tipo=HistoricoColaborador.TipoEvento.PROMOCAO,
                cargo_anterior=old_cargo, cargo_novo=new_cargo,
                registrado_por=request.user,
            )
        if old_depto != new_depto:
            HistoricoColaborador.objects.create(
                colaborador=colab,
                tipo=HistoricoColaborador.TipoEvento.TRANSFERENCIA,
                departamento_anterior=old_depto, departamento_novo=new_depto,
                registrado_por=request.user,
            )
        if old_rem != new_rem_val:
            HistoricoColaborador.objects.create(
                colaborador=colab,
                tipo=HistoricoColaborador.TipoEvento.REAJUSTE,
                remuneracao_anterior=old_rem, remuneracao_nova=new_rem_val,
                registrado_por=request.user,
            )

        return redirect("web:rh-colaborador-detail", pk=pk)


class ColaboradorDeleteView(PermissionRequiredMixin, View):
    permission_required = "rh.delete_colaborador"

    def post(self, request, pk):
        get_object_or_404(Colaborador, pk=pk).delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/rh/colaboradores/"})
        return redirect("web:rh-colaboradores")
