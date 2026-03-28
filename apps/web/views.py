import calendar

from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, F, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView

from django.contrib.auth.models import Group

from apps.accounts.models import Usuario
from apps.crm.models import Cliente, ClienteHistorico, Endereco, EntidadeParceira, Notificacao, Plano, PlanoProduto, Produto
from apps.financeiro.models import (
    Ativo, CategoriaFinanceira, Cobranca, ConfiguracaoFolha, ContaBancaria,
    Despesa, FolhaPagamento, Lancamento, LogExportacaoFolha, NotaFiscal, Tributo,
)
from apps.crm.validators import ACCEPT_HTML, validar_arquivo
from apps.integracao.models import TokenIntegracao
from apps.rh.models import (
    AcaoPDI, Cargo, CicloAvaliacao, Colaborador, Departamento, DocumentoColaborador,
    HistoricoColaborador, Meta, OnboardingColaborador, OnboardingItem,
    OnboardingTemplate, OnboardingTemplateItem, ParticipacaoTreinamento, PDI,
    PerguntaENPS, PesquisaENPS, RespostaENPS, SaldoFerias, Setor,
    SolicitacaoAusencia, Treinamento,
)

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

        ctx["can_view_clientes"] = user.has_perm("crm.view_cliente")

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
            "matrix": _build_permission_matrix(),
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
                "matrix": _build_permission_matrix(),
                "erros": erros,
            }
            return render(request, "usuarios/create.html", ctx)

        user = Usuario.objects.create_user(
            username=username, email=email, password=password,
            first_name=first_name, last_name=last_name,
        )

        group_id = request.POST.get("groups")
        customized = request.POST.get("permissions_customized") == "1"
        perm_ids = set(request.POST.getlist("permissions"))

        if customized and perm_ids:
            # Usuario customizou a matriz — verificar se difere do grupo
            if group_id:
                group = Group.objects.filter(pk=group_id).first()
                group_perm_ids = set(
                    str(p) for p in group.permissions.values_list("id", flat=True)
                ) if group else set()

                if perm_ids == group_perm_ids:
                    # Mesmas permissoes do grupo — manter grupo, sem individuais
                    user.groups.set([group_id])
                else:
                    # Customizou — permissoes viram individuais, sai do grupo
                    user.user_permissions.set(perm_ids)
            else:
                # Sem grupo — permissoes individuais
                user.user_permissions.set(perm_ids)
        elif group_id:
            # Nao customizou — so herda do grupo
            user.groups.set([group_id])

        return redirect("web:usuarios")


class UsuarioPermissoesGroupView(PermissionRequiredMixin, View):
    """Partial HTMX: retorna a matriz de permissoes pre-populada com as do grupo selecionado."""
    permission_required = "accounts.add_usuario"

    def get(self, request):
        group_id = request.GET.get("group_id")
        group = None
        if group_id:
            group = Group.objects.filter(pk=group_id).first()
        matrix = _build_permission_matrix(group=group) if group else _build_permission_matrix()
        return render(request, "grupos/_form_matrix.html", {
            "matrix": matrix,
            "show_group_legend": bool(group),
        })


class UsuarioUpdateView(PermissionRequiredMixin, View):
    permission_required = "accounts.change_usuario"

    def get(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        has_groups = usuario.groups.exists()
        return render(request, "usuarios/edit.html", {
            "usuario": usuario,
            "groups": Group.objects.all(),
            "usuario_groups": list(usuario.groups.values_list("id", flat=True)),
            "matrix": _build_permission_matrix(user=usuario),
            "show_group_legend": has_groups,
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

        group_id = request.POST.get("groups")
        customized = request.POST.get("permissions_customized") == "1"
        perm_ids = set(request.POST.getlist("permissions"))

        if customized:
            # Usuario abriu a matriz — ela e a fonte da verdade
            if group_id:
                group = Group.objects.filter(pk=group_id).first()
                group_perm_ids = set(
                    str(p) for p in group.permissions.values_list("id", flat=True)
                ) if group else set()

                if perm_ids == group_perm_ids:
                    # Identico ao grupo — manter grupo, limpar individuais
                    usuario.groups.set([group_id])
                    usuario.user_permissions.clear()
                else:
                    # Customizou — permissoes viram individuais, sai do grupo
                    usuario.groups.clear()
                    usuario.user_permissions.set(perm_ids)
            else:
                # Sem grupo — permissoes individuais
                usuario.groups.clear()
                usuario.user_permissions.set(perm_ids)
        else:
            # Nao abriu a matriz — so atualiza o grupo
            if group_id:
                usuario.groups.set([group_id])
            else:
                usuario.groups.clear()

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

# Modulos expostos na matriz de permissoes, agrupados por departamento
MODULOS_PERMISSOES_GRUPOS = [
    {"depto": "Comercial", "modulos": [
        {"label": "Clientes", "app": "crm", "model": "cliente"},
        {"label": "Produtos", "app": "crm", "model": "produto"},
        {"label": "Planos", "app": "crm", "model": "plano"},
        {"label": "Parceiros", "app": "crm", "model": "entidadeparceira"},
    ]},
    {"depto": "Financeiro", "modulos": [
        {"label": "Lançamentos", "app": "financeiro", "model": "lancamento"},
        {"label": "Cobranças", "app": "financeiro", "model": "cobranca"},
        {"label": "Despesas", "app": "financeiro", "model": "despesa"},
        {"label": "Notas Fiscais", "app": "financeiro", "model": "notafiscal"},
        {"label": "Folha Pgto", "app": "financeiro", "model": "folhapagamento"},
        {"label": "Tributos", "app": "financeiro", "model": "tributo"},
        {"label": "Patrimônio", "app": "financeiro", "model": "ativo"},
        {"label": "Contas Bancárias", "app": "financeiro", "model": "contabancaria"},
        {"label": "Categorias", "app": "financeiro", "model": "categoriafinanceira"},
    ]},
    {"depto": "RH / Pessoas", "modulos": [
        {"label": "Colaboradores", "app": "rh", "model": "colaborador"},
        {"label": "Cargos", "app": "rh", "model": "cargo"},
        {"label": "Setores", "app": "rh", "model": "setor"},
        {"label": "Documentos", "app": "rh", "model": "documentocolaborador"},
        {"label": "Onboarding", "app": "rh", "model": "onboardingtemplate"},
        {"label": "Ausências", "app": "rh", "model": "solicitacaoausencia"},
        {"label": "Treinamentos", "app": "rh", "model": "treinamento"},
        {"label": "Metas", "app": "rh", "model": "cicloavaliacao"},
        {"label": "PDI", "app": "rh", "model": "pdi"},
        {"label": "eNPS", "app": "rh", "model": "pesquisaenps"},
    ]},
    {"depto": "Administração", "modulos": [
        {"label": "Usuários", "app": "accounts", "model": "usuario"},
        {"label": "Tokens API", "app": "integracao", "model": "tokenintegracao"},
    ]},
]

ACOES = [
    {"key": "view", "label": "Ver"},
    {"key": "add", "label": "Criar"},
    {"key": "change", "label": "Editar"},
    {"key": "delete", "label": "Excluir"},
]


def _build_permission_matrix(group=None, user=None):
    """Monta a matriz de modulos x acoes agrupada por departamento.
    Aceita group (permissoes do grupo) ou user (permissoes diretas do usuario).
    """
    from django.contrib.auth.models import Permission

    checked_codenames = set()
    group_codenames = set()

    if group:
        checked_codenames = set(group.permissions.values_list("codename", flat=True))
    elif user:
        checked_codenames = set(user.user_permissions.values_list("codename", flat=True))
        group_codenames = set(
            Permission.objects.filter(group__user=user).values_list("codename", flat=True)
        )

    matrix = []
    for grupo in MODULOS_PERMISSOES_GRUPOS:
        depto = {"depto": grupo["depto"], "modulos": []}
        for mod in grupo["modulos"]:
            row = {"label": mod["label"], "acoes": []}
            for acao in ACOES:
                codename = f"{acao['key']}_{mod['model']}"
                perm = Permission.objects.filter(
                    codename=codename,
                    content_type__app_label=mod["app"],
                ).first()
                is_direct = codename in checked_codenames
                is_from_group = codename in group_codenames
                row["acoes"].append({
                    "label": acao["label"],
                    "perm_id": perm.id if perm else None,
                    "codename": codename,
                    "checked": is_direct or is_from_group,
                    "from_group": is_from_group and not is_direct,
                })
            depto["modulos"].append(row)
        matrix.append(depto)
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
# RH — Setores
# ---------------------------------------------------------------------------
class SetorListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "rh/setores/list.html"
    partial_template_name = "rh/setores/_table.html"
    context_object_name = "setores"
    paginate_by = 20
    permission_required = "rh.view_setor"

    def get_queryset(self):
        qs = Setor.objects.select_related("departamento")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(departamento__nome__icontains=search))
        depto = self.request.GET.get("departamento")
        if depto:
            qs = qs.filter(departamento_id=depto)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["departamentos"] = Departamento.objects.filter(ativo=True)
        ctx["current_depto"] = self.request.GET.get("departamento", "")
        ctx["can_add"] = self.request.user.has_perm("rh.add_setor")
        return ctx


class SetorCreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_setor"

    def get(self, request):
        return render(request, "rh/setores/create.html", {
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
        descricao = request.POST.get("descricao", "").strip()
        dados = {"nome": nome, "departamento": depto_id, "descricao": descricao}

        if not erros and depto_id:
            if Setor.objects.filter(nome__iexact=nome, departamento_id=depto_id).exists():
                erros["nome"] = "Ja existe um setor com esse nome neste departamento."

        if erros:
            return render(request, "rh/setores/create.html", {
                "departamentos": Departamento.objects.filter(ativo=True),
                "erros": erros, "dados": dados,
            })

        Setor.objects.create(nome=nome, departamento_id=depto_id, descricao=descricao)
        return redirect("web:rh-setores")


class SetorUpdateView(PermissionRequiredMixin, View):
    permission_required = "rh.change_setor"

    def get(self, request, pk):
        setor = get_object_or_404(Setor.objects.select_related("departamento"), pk=pk)
        return render(request, "rh/setores/edit.html", {
            "setor": setor,
            "departamentos": Departamento.objects.filter(ativo=True),
            "erros": {},
        })

    def post(self, request, pk):
        setor = get_object_or_404(Setor, pk=pk)
        nome = request.POST.get("nome", "").strip()
        depto_id = request.POST.get("departamento")
        erros = {}
        if not nome:
            erros["nome"] = "O nome e obrigatorio."
        if not depto_id:
            erros["departamento"] = "O departamento e obrigatorio."
        if not erros and depto_id:
            if Setor.objects.filter(nome__iexact=nome, departamento_id=depto_id).exclude(pk=pk).exists():
                erros["nome"] = "Ja existe um setor com esse nome neste departamento."
        if erros:
            return render(request, "rh/setores/edit.html", {
                "setor": setor,
                "departamentos": Departamento.objects.filter(ativo=True),
                "erros": erros,
            })

        setor.nome = nome
        setor.departamento_id = depto_id
        setor.descricao = request.POST.get("descricao", "").strip()
        setor.ativo = "ativo" in request.POST
        setor.save()
        return redirect("web:rh-setores")


class SetorDeleteView(PermissionRequiredMixin, View):
    permission_required = "rh.delete_setor"

    def post(self, request, pk):
        get_object_or_404(Setor, pk=pk).delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/rh/setores/"})
        return redirect("web:rh-setores")


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
            setor_id=P.get("setor") or None,
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

        from apps.rh.notifications import notificar_novo_colaborador
        notificar_novo_colaborador(colab)

        return redirect("web:rh-colaborador-detail", pk=colab.pk)

    def _ctx(self, erros):
        return {
            "erros": erros,
            "tipo_choices": Colaborador.TipoContrato.choices,
            "regime_choices": Colaborador.RegimeTrabalho.choices,
            "departamentos": Departamento.objects.filter(ativo=True),
            "setores": Setor.objects.filter(ativo=True).select_related("departamento"),
            "cargos": Cargo.objects.filter(ativo=True).select_related("departamento"),
            "uf_choices": Endereco.UF_CHOICES,
        }


class ColaboradorDetailView(PermissionRequiredMixin, View):
    permission_required = "rh.view_colaborador"

    def get(self, request, pk):
        colab = get_object_or_404(
            Colaborador.objects.select_related("cargo", "departamento", "setor", "endereco"), pk=pk
        )
        historico = colab.historico.select_related("registrado_por").order_by("-criado_em")
        documentos = colab.documentos.order_by("-criado_em")
        return render(request, "rh/colaboradores/detail.html", {
            "colab": colab,
            "historico": historico,
            "documentos": documentos,
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
            "setores": Setor.objects.filter(ativo=True).select_related("departamento"),
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
        colab.setor_id = P.get("setor") or None
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

        # Notificar se foi desligado
        if colab.status == "desligado":
            from apps.rh.notifications import notificar_colaborador_desligado
            notificar_colaborador_desligado(colab)

        # Sincronizar usuario vinculado (nome + permissoes)
        if colab.usuario:
            from apps.rh.permissions import atribuir_permissoes
            atribuir_permissoes(colab)

        return redirect("web:rh-colaborador-detail", pk=pk)


class ColaboradorDeleteView(PermissionRequiredMixin, View):
    permission_required = "rh.delete_colaborador"

    def post(self, request, pk):
        get_object_or_404(Colaborador, pk=pk).delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/rh/colaboradores/"})
        return redirect("web:rh-colaboradores")


class ColaboradorFotoView(PermissionRequiredMixin, View):
    """Upload de foto do colaborador."""
    permission_required = "rh.change_colaborador"

    def post(self, request, pk):
        colab = get_object_or_404(Colaborador, pk=pk)
        foto = request.FILES.get("foto")
        if not foto:
            return redirect("web:rh-colaborador-detail", pk=pk)

        import os
        _, ext = os.path.splitext(foto.name.lower())
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            return redirect("web:rh-colaborador-detail", pk=pk)

        if foto.size > 2 * 1024 * 1024:
            return redirect("web:rh-colaborador-detail", pk=pk)

        # Remover foto anterior se existir
        if colab.foto:
            colab.foto.delete(save=False)

        colab.foto = foto
        colab.save(update_fields=["foto"])

        # Redimensionar
        try:
            from PIL import Image
            img = Image.open(colab.foto.path)
            if img.width > 200 or img.height > 200:
                img.thumbnail((200, 200), Image.LANCZOS)
                img.save(colab.foto.path)
        except Exception:
            pass

        return redirect("web:rh-colaborador-detail", pk=pk)


class ColaboradorFotoRemoverView(PermissionRequiredMixin, View):
    """Remove foto do colaborador."""
    permission_required = "rh.change_colaborador"

    def post(self, request, pk):
        colab = get_object_or_404(Colaborador, pk=pk)
        if colab.foto:
            colab.foto.delete(save=False)
            colab.foto = None
            colab.save(update_fields=["foto"])
        return redirect("web:rh-colaborador-detail", pk=pk)


class ColaboradorCriarAcessoView(PermissionRequiredMixin, View):
    """Cria usuario no sistema para o colaborador com grupo Colaborador."""
    permission_required = "rh.change_colaborador"

    @staticmethod
    def _gerar_senha():
        """Gera senha temporaria segura (12 chars alfanumericos)."""
        from django.utils.crypto import get_random_string
        return get_random_string(12, "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789")

    @staticmethod
    def _username_unico(base):
        """Garante username unico adicionando numero se necessario."""
        username = base
        contador = 1
        while Usuario.objects.filter(username=username).exists():
            username = f"{base}{contador}"
            contador += 1
        return username

    def get(self, request, pk):
        colab = get_object_or_404(Colaborador, pk=pk)
        if colab.usuario:
            return redirect("web:rh-colaborador-detail", pk=pk)
        email = colab.email_pessoal
        base = email.split("@")[0] if email else colab.nome_completo.lower().replace(" ", ".")
        username_sugerido = self._username_unico(base)
        return render(request, "rh/colaboradores/criar_acesso.html", {
            "colab": colab,
            "username_sugerido": username_sugerido,
            "email": email,
            "erros": {},
        })

    def post(self, request, pk):
        colab = get_object_or_404(Colaborador, pk=pk)
        if colab.usuario:
            return redirect("web:rh-colaborador-detail", pk=pk)

        erros = {}
        username = request.POST.get("username", "").strip()
        if not username:
            erros["username"] = "O username e obrigatorio."
        elif Usuario.objects.filter(username=username).exists():
            erros["username"] = "Esse username ja esta em uso."

        email = request.POST.get("email", "").strip()
        if not email:
            erros["email"] = "O email e obrigatorio."

        if erros:
            return render(request, "rh/colaboradores/criar_acesso.html", {
                "colab": colab,
                "username_sugerido": username,
                "email": email,
                "erros": erros,
            })

        # Gerar senha temporaria automaticamente
        password = self._gerar_senha()

        # Extrair nome/sobrenome do nome completo
        partes = colab.nome_completo.split()
        first_name = partes[0] if partes else ""
        last_name = " ".join(partes[1:]) if len(partes) > 1 else ""

        user = Usuario.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # Vincular ao colaborador
        colab.usuario = user
        colab.save(update_fields=["usuario"])

        # Atribuir permissoes baseadas no departamento + nivel hierarquico
        from apps.rh.permissions import atribuir_permissoes
        atribuir_permissoes(colab)

        # Enviar email com dados de acesso
        from apps.rh.emails import enviar_acesso_criado
        enviar_acesso_criado(colab, username, password)

        from django.contrib import messages
        messages.success(request, f"Acesso criado para {colab.nome_completo} (usuario: {username}). Email enviado para {colab.email_pessoal}.")
        return redirect("web:rh-colaborador-detail", pk=pk)


class ColaboradorRevogarAcessoView(PermissionRequiredMixin, View):
    """Revoga acesso ao sistema — desativa o usuario vinculado."""
    permission_required = "rh.change_colaborador"

    def post(self, request, pk):
        colab = get_object_or_404(Colaborador, pk=pk)
        if colab.usuario:
            colab.usuario.is_active = False
            colab.usuario.save(update_fields=["is_active"])
            from django.contrib import messages
            messages.success(request, f"Acesso revogado para {colab.nome_completo}")
        return redirect("web:rh-colaborador-detail", pk=pk)


# ---------------------------------------------------------------------------
# RH — Documentos do Colaborador
# ---------------------------------------------------------------------------
class DocumentoListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "rh/documentos/list.html"
    partial_template_name = "rh/documentos/_table.html"
    context_object_name = "documentos"
    paginate_by = 20
    permission_required = "rh.view_documentocolaborador"

    def get_queryset(self):
        qs = DocumentoColaborador.objects.select_related("colaborador", "enviado_por")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(
                Q(nome__icontains=search)
                | Q(colaborador__nome_completo__icontains=search)
            )
        tipo = self.request.GET.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)
        vencimento = self.request.GET.get("vencimento")
        if vencimento == "vencido":
            from django.utils import timezone
            qs = qs.filter(data_vencimento__lt=timezone.now().date())
        elif vencimento == "proximo":
            from django.utils import timezone
            from datetime import timedelta
            hoje = timezone.now().date()
            qs = qs.filter(data_vencimento__gte=hoje, data_vencimento__lte=hoje + timedelta(days=30))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipo_choices"] = DocumentoColaborador.TipoDocumento.choices
        ctx["current_tipo"] = self.request.GET.get("tipo", "")
        ctx["current_vencimento"] = self.request.GET.get("vencimento", "")
        ctx["can_add"] = self.request.user.has_perm("rh.add_documentocolaborador")
        return ctx


class DocumentoCreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_documentocolaborador"

    def get(self, request):
        colab_id = request.GET.get("colaborador")
        return render(request, "rh/documentos/create.html", {
            "tipo_choices": DocumentoColaborador.TipoDocumento.choices,
            "colaboradores": Colaborador.objects.filter(status="ativo"),
            "colab_id": int(colab_id) if colab_id else None,
            "erros": {},
        })

    def post(self, request):
        erros = {}
        colab_id = request.POST.get("colaborador")
        if not colab_id:
            erros["colaborador"] = "O colaborador e obrigatorio."
        tipo = request.POST.get("tipo", "").strip()
        if not tipo:
            erros["tipo"] = "O tipo e obrigatorio."
        nome = request.POST.get("nome", "").strip()
        if not nome:
            erros["nome"] = "O nome e obrigatorio."
        arquivo = request.FILES.get("arquivo")
        if not arquivo:
            erros["arquivo"] = "O arquivo e obrigatorio."

        if erros:
            return render(request, "rh/documentos/create.html", {
                "tipo_choices": DocumentoColaborador.TipoDocumento.choices,
                "colaboradores": Colaborador.objects.filter(status="ativo"),
                "erros": erros,
            })

        DocumentoColaborador.objects.create(
            colaborador_id=colab_id,
            tipo=tipo,
            nome=nome,
            arquivo=arquivo,
            data_emissao=request.POST.get("data_emissao") or None,
            data_vencimento=request.POST.get("data_vencimento") or None,
            alerta_dias_antes=request.POST.get("alerta_dias_antes", 30) or 30,
            observacao=request.POST.get("observacao", "").strip(),
            enviado_por=request.user,
        )
        return redirect("web:rh-documentos")


class DocumentoDeleteView(PermissionRequiredMixin, View):
    permission_required = "rh.delete_documentocolaborador"

    def post(self, request, pk):
        get_object_or_404(DocumentoColaborador, pk=pk).delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/rh/documentos/"})
        return redirect("web:rh-documentos")


# ---------------------------------------------------------------------------
# RH — Onboarding Templates
# ---------------------------------------------------------------------------
class OnboardingTemplateListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "rh/onboarding/templates_list.html"
    partial_template_name = "rh/onboarding/_templates_table.html"
    context_object_name = "templates"
    paginate_by = 20
    permission_required = "rh.view_onboardingtemplate"

    def get_queryset(self):
        return OnboardingTemplate.objects.prefetch_related("itens").all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_add"] = self.request.user.has_perm("rh.add_onboardingtemplate")
        return ctx


class OnboardingTemplateCreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_onboardingtemplate"

    def get(self, request):
        return render(request, "rh/onboarding/template_create.html", {
            "tipo_choices": Colaborador.TipoContrato.choices,
            "fase_choices": OnboardingTemplateItem.Fase.choices,
            "departamentos": Departamento.objects.filter(ativo=True),
            "erros": {},
        })

    def post(self, request):
        erros = {}
        nome = request.POST.get("nome", "").strip()
        if not nome:
            erros["nome"] = "O nome e obrigatorio."
        tipo_contrato = request.POST.get("tipo_contrato", "").strip()
        depto_id = request.POST.get("departamento") or None

        if erros:
            return render(request, "rh/onboarding/template_create.html", {
                "tipo_choices": Colaborador.TipoContrato.choices,
                "fase_choices": OnboardingTemplateItem.Fase.choices,
                "departamentos": Departamento.objects.filter(ativo=True),
                "erros": erros,
            })

        template = OnboardingTemplate.objects.create(
            nome=nome,
            tipo_contrato=tipo_contrato,
            departamento_id=depto_id,
        )

        # Salvar itens dinamicos
        descricoes = request.POST.getlist("item_descricao")
        fases = request.POST.getlist("item_fase")
        for i, desc in enumerate(descricoes):
            desc = desc.strip()
            if desc:
                fase = fases[i] if i < len(fases) else "antes"
                OnboardingTemplateItem.objects.create(
                    template=template,
                    fase=fase,
                    descricao=desc,
                    ordem=i,
                )

        return redirect("web:rh-onboarding-templates")


class OnboardingTemplateEditView(PermissionRequiredMixin, View):
    permission_required = "rh.change_onboardingtemplate"

    def get(self, request, pk):
        template = get_object_or_404(OnboardingTemplate.objects.prefetch_related("itens"), pk=pk)
        return render(request, "rh/onboarding/template_edit.html", {
            "template": template,
            "tipo_choices": Colaborador.TipoContrato.choices,
            "fase_choices": OnboardingTemplateItem.Fase.choices,
            "departamentos": Departamento.objects.filter(ativo=True),
            "erros": {},
        })

    def post(self, request, pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        template.nome = request.POST.get("nome", template.nome).strip()
        template.tipo_contrato = request.POST.get("tipo_contrato", "").strip()
        template.departamento_id = request.POST.get("departamento") or None
        template.ativo = "ativo" in request.POST
        template.save()

        # Recriar itens
        template.itens.all().delete()
        descricoes = request.POST.getlist("item_descricao")
        fases = request.POST.getlist("item_fase")
        for i, desc in enumerate(descricoes):
            desc = desc.strip()
            if desc:
                fase = fases[i] if i < len(fases) else "antes"
                OnboardingTemplateItem.objects.create(
                    template=template,
                    fase=fase,
                    descricao=desc,
                    ordem=i,
                )

        return redirect("web:rh-onboarding-templates")


class OnboardingTemplateDeleteView(PermissionRequiredMixin, View):
    permission_required = "rh.delete_onboardingtemplate"

    def post(self, request, pk):
        get_object_or_404(OnboardingTemplate, pk=pk).delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/rh/onboarding/templates/"})
        return redirect("web:rh-onboarding-templates")


# ---------------------------------------------------------------------------
# RH — Onboarding do Colaborador (instancia)
# ---------------------------------------------------------------------------
class OnboardingIniciarView(PermissionRequiredMixin, View):
    """Inicia o onboarding de um colaborador a partir de um template."""
    permission_required = "rh.add_onboardingcolaborador"

    def get(self, request, colab_pk):
        colab = get_object_or_404(Colaborador, pk=colab_pk)
        templates = OnboardingTemplate.objects.filter(ativo=True).prefetch_related("itens")
        return render(request, "rh/onboarding/iniciar.html", {
            "colab": colab,
            "templates": templates,
        })

    def post(self, request, colab_pk):
        colab = get_object_or_404(Colaborador, pk=colab_pk)
        template_id = request.POST.get("template")
        template = get_object_or_404(OnboardingTemplate, pk=template_id)

        # Criar onboarding do colaborador
        onboarding, created = OnboardingColaborador.objects.get_or_create(
            colaborador=colab,
            defaults={"template": template},
        )
        if not created:
            return redirect("web:rh-onboarding-detail", pk=onboarding.pk)

        # Copiar itens do template
        for item in template.itens.all():
            OnboardingItem.objects.create(
                onboarding=onboarding,
                fase=item.fase,
                descricao=item.descricao,
                ordem=item.ordem,
            )

        from apps.rh.notifications import notificar_onboarding_iniciado
        notificar_onboarding_iniciado(onboarding)

        return redirect("web:rh-onboarding-detail", pk=onboarding.pk)


class OnboardingDetailView(PermissionRequiredMixin, View):
    permission_required = "rh.view_onboardingcolaborador"

    def get(self, request, pk):
        onboarding = get_object_or_404(
            OnboardingColaborador.objects.select_related("colaborador", "template")
            .prefetch_related("itens__responsavel"),
            pk=pk,
        )
        fases = OnboardingTemplateItem.Fase.choices
        itens_por_fase = {}
        for fase_key, fase_label in fases:
            itens_por_fase[fase_key] = {
                "label": fase_label,
                "itens": onboarding.itens.filter(fase=fase_key),
            }
        return render(request, "rh/onboarding/detail.html", {
            "onboarding": onboarding,
            "itens_por_fase": itens_por_fase,
            "can_edit": request.user.has_perm("rh.change_onboardingcolaborador"),
        })


class OnboardingToggleItemView(PermissionRequiredMixin, View):
    """HTMX: marca/desmarca um item do onboarding."""
    permission_required = "rh.change_onboardingcolaborador"

    def post(self, request, item_pk):
        item = get_object_or_404(OnboardingItem.objects.select_related("onboarding"), pk=item_pk)
        from django.utils import timezone
        item.concluido = not item.concluido
        item.concluido_em = timezone.now() if item.concluido else None
        item.save(update_fields=["concluido", "concluido_em"])

        # Verificar se todos concluidos
        onboarding = item.onboarding
        if onboarding.progresso == 100:
            onboarding.concluido_em = timezone.now()
            onboarding.save(update_fields=["concluido_em"])
            from apps.rh.notifications import notificar_onboarding_concluido
            notificar_onboarding_concluido(onboarding)
        elif onboarding.concluido_em:
            onboarding.concluido_em = None
            onboarding.save(update_fields=["concluido_em"])

        return redirect("web:rh-onboarding-detail", pk=onboarding.pk)


# ---------------------------------------------------------------------------
# RH — Ferias e Ausencias
# ---------------------------------------------------------------------------
class AusenciaListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "rh/ausencias/list.html"
    partial_template_name = "rh/ausencias/_table.html"
    context_object_name = "ausencias"
    paginate_by = 20
    permission_required = "rh.view_solicitacaoausencia"

    def _is_rh(self):
        return self.request.user.has_perm("rh.change_solicitacaoausencia")

    def _get_colaborador(self):
        """Retorna o Colaborador vinculado ao usuario logado, se houver."""
        return getattr(self.request.user, "colaborador", None)

    def get_queryset(self):
        qs = SolicitacaoAusencia.objects.select_related("colaborador", "aprovado_por")
        # Colaborador comum ve apenas suas proprias ausencias
        if not self._is_rh():
            colab = self._get_colaborador()
            if colab:
                qs = qs.filter(colaborador=colab)
            else:
                return qs.none()
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(colaborador__nome_completo__icontains=search)
        tipo = self.request.GET.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipo_choices"] = SolicitacaoAusencia.TipoAusencia.choices
        ctx["status_choices"] = SolicitacaoAusencia.StatusSolicitacao.choices
        ctx["current_tipo"] = self.request.GET.get("tipo", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["can_add"] = self.request.user.has_perm("rh.add_solicitacaoausencia")
        ctx["can_approve"] = self._is_rh()
        ctx["is_rh"] = self._is_rh()
        return ctx


class AusenciaCreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_solicitacaoausencia"

    def _is_rh(self, user):
        return user.has_perm("rh.change_solicitacaoausencia")

    def get(self, request):
        is_rh = self._is_rh(request.user)
        colab_proprio = getattr(request.user, "colaborador", None)
        return render(request, "rh/ausencias/create.html", {
            "tipo_choices": SolicitacaoAusencia.TipoAusencia.choices,
            "colaboradores": Colaborador.objects.filter(status="ativo") if is_rh else [],
            "is_rh": is_rh,
            "colab_proprio": colab_proprio,
            "erros": {},
        })

    def post(self, request):
        erros = {}
        is_rh = self._is_rh(request.user)

        # Determinar colaborador
        if is_rh:
            colab_id = request.POST.get("colaborador")
            if not colab_id:
                erros["colaborador"] = "O colaborador e obrigatorio."
        else:
            colab = getattr(request.user, "colaborador", None)
            if not colab:
                erros["colaborador"] = "Seu usuario nao esta vinculado a um colaborador."
            else:
                colab_id = colab.pk

        tipo = request.POST.get("tipo", "").strip()
        if not tipo:
            erros["tipo"] = "O tipo e obrigatorio."
        data_inicio = request.POST.get("data_inicio", "").strip()
        if not data_inicio:
            erros["data_inicio"] = "A data de inicio e obrigatoria."
        data_fim = request.POST.get("data_fim", "").strip()
        if not data_fim:
            erros["data_fim"] = "A data de fim e obrigatoria."

        if erros:
            colab_proprio = getattr(request.user, "colaborador", None)
            return render(request, "rh/ausencias/create.html", {
                "tipo_choices": SolicitacaoAusencia.TipoAusencia.choices,
                "colaboradores": Colaborador.objects.filter(status="ativo") if is_rh else [],
                "is_rh": is_rh,
                "colab_proprio": colab_proprio,
                "erros": erros,
            })

        ausencia = SolicitacaoAusencia.objects.create(
            colaborador_id=colab_id,
            tipo=tipo,
            data_inicio=data_inicio,
            data_fim=data_fim,
            total_dias=0,
            observacao=request.POST.get("observacao", "").strip(),
        )
        from apps.rh.notifications import notificar_nova_solicitacao_ausencia
        notificar_nova_solicitacao_ausencia(ausencia)
        return redirect("web:rh-ausencias")


class AusenciaAprovarView(PermissionRequiredMixin, View):
    permission_required = "rh.change_solicitacaoausencia"

    def post(self, request, pk):
        ausencia = get_object_or_404(
            SolicitacaoAusencia.objects.select_related("colaborador"), pk=pk
        )
        acao = request.POST.get("acao")
        if acao == "aprovar":
            ausencia.status = SolicitacaoAusencia.StatusSolicitacao.APROVADA
            ausencia.aprovado_por = request.user
            ausencia.save()
            from apps.rh.emails import enviar_ausencia_aprovada
            from apps.rh.notifications import notificar_ausencia_aprovada
            enviar_ausencia_aprovada(ausencia)
            notificar_ausencia_aprovada(ausencia)
        elif acao == "rejeitar":
            ausencia.status = SolicitacaoAusencia.StatusSolicitacao.REJEITADA
            ausencia.aprovado_por = request.user
            ausencia.justificativa_rejeicao = request.POST.get("justificativa", "").strip()
            ausencia.save()
            from apps.rh.emails import enviar_ausencia_rejeitada
            from apps.rh.notifications import notificar_ausencia_rejeitada
            enviar_ausencia_rejeitada(ausencia)
            notificar_ausencia_rejeitada(ausencia)
        elif acao == "cancelar":
            ausencia.status = SolicitacaoAusencia.StatusSolicitacao.CANCELADA
            ausencia.save()
        return redirect("web:rh-ausencias")


class AusenciaCalendarioView(PermissionRequiredMixin, View):
    permission_required = "rh.view_solicitacaoausencia"

    def get(self, request):
        from django.utils import timezone
        import calendar as cal_module

        hoje = timezone.now().date()
        mes = int(request.GET.get("mes", hoje.month))
        ano = int(request.GET.get("ano", hoje.year))

        primeiro_dia = hoje.replace(year=ano, month=mes, day=1)
        _, ultimo = cal_module.monthrange(ano, mes)
        ultimo_dia = primeiro_dia.replace(day=ultimo)

        ausencias = SolicitacaoAusencia.objects.filter(
            status="aprovada",
            data_inicio__lte=ultimo_dia,
            data_fim__gte=primeiro_dia,
        ).select_related("colaborador").order_by("data_inicio")

        # Navegacao
        if mes == 1:
            prev_mes, prev_ano = 12, ano - 1
        else:
            prev_mes, prev_ano = mes - 1, ano
        if mes == 12:
            next_mes, next_ano = 1, ano + 1
        else:
            next_mes, next_ano = mes + 1, ano

        return render(request, "rh/ausencias/calendario.html", {
            "ausencias": ausencias,
            "mes": mes,
            "ano": ano,
            "mes_nome": primeiro_dia.strftime("%B %Y").capitalize(),
            "prev_mes": prev_mes,
            "prev_ano": prev_ano,
            "next_mes": next_mes,
            "next_ano": next_ano,
        })


# ---------------------------------------------------------------------------
# RH — Treinamentos
# ---------------------------------------------------------------------------
class TreinamentoListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "rh/treinamentos/list.html"
    partial_template_name = "rh/treinamentos/_table.html"
    context_object_name = "treinamentos"
    paginate_by = 20
    permission_required = "rh.view_treinamento"

    def get_queryset(self):
        qs = Treinamento.objects.annotate(total_participantes=Count("participacoes"))
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(nome__icontains=search)
        tipo = self.request.GET.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipo_choices"] = Treinamento.TipoTreinamento.choices
        ctx["current_tipo"] = self.request.GET.get("tipo", "")
        ctx["can_add"] = self.request.user.has_perm("rh.add_treinamento")
        return ctx


class TreinamentoCreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_treinamento"

    def get(self, request):
        return render(request, "rh/treinamentos/create.html", {
            "tipo_choices": Treinamento.TipoTreinamento.choices,
            "modalidade_choices": Treinamento.Modalidade.choices,
            "erros": {}, "dados": {},
        })

    def post(self, request):
        erros = {}
        nome = request.POST.get("nome", "").strip()
        if not nome:
            erros["nome"] = "O nome e obrigatorio."
        tipo = request.POST.get("tipo", "").strip()
        if not tipo:
            erros["tipo"] = "O tipo e obrigatorio."

        if erros:
            return render(request, "rh/treinamentos/create.html", {
                "tipo_choices": Treinamento.TipoTreinamento.choices,
                "modalidade_choices": Treinamento.Modalidade.choices,
                "erros": erros, "dados": request.POST,
            })

        Treinamento.objects.create(
            nome=nome,
            tipo=tipo,
            modalidade=request.POST.get("modalidade", "online"),
            carga_horaria=request.POST.get("carga_horaria", 1) or 1,
            instituicao=request.POST.get("instituicao", "").strip(),
            descricao=request.POST.get("descricao", "").strip(),
            obrigatorio="obrigatorio" in request.POST,
        )
        return redirect("web:rh-treinamentos")


class TreinamentoDetailView(PermissionRequiredMixin, View):
    permission_required = "rh.view_treinamento"

    def get(self, request, pk):
        treinamento = get_object_or_404(Treinamento, pk=pk)
        participacoes = treinamento.participacoes.select_related("colaborador").order_by("-criado_em")
        return render(request, "rh/treinamentos/detail.html", {
            "treinamento": treinamento,
            "participacoes": participacoes,
            "can_edit": request.user.has_perm("rh.change_treinamento"),
            "can_add_participacao": request.user.has_perm("rh.add_participacaotreinamento"),
        })


class TreinamentoUpdateView(PermissionRequiredMixin, View):
    permission_required = "rh.change_treinamento"

    def get(self, request, pk):
        treinamento = get_object_or_404(Treinamento, pk=pk)
        return render(request, "rh/treinamentos/edit.html", {
            "treinamento": treinamento,
            "tipo_choices": Treinamento.TipoTreinamento.choices,
            "modalidade_choices": Treinamento.Modalidade.choices,
            "erros": {},
        })

    def post(self, request, pk):
        treinamento = get_object_or_404(Treinamento, pk=pk)
        treinamento.nome = request.POST.get("nome", treinamento.nome).strip()
        treinamento.tipo = request.POST.get("tipo", treinamento.tipo)
        treinamento.modalidade = request.POST.get("modalidade", treinamento.modalidade)
        treinamento.carga_horaria = request.POST.get("carga_horaria", treinamento.carga_horaria) or 1
        treinamento.instituicao = request.POST.get("instituicao", "").strip()
        treinamento.descricao = request.POST.get("descricao", "").strip()
        treinamento.obrigatorio = "obrigatorio" in request.POST
        treinamento.ativo = "ativo" in request.POST
        treinamento.save()
        return redirect("web:rh-treinamento-detail", pk=pk)


class TreinamentoDeleteView(PermissionRequiredMixin, View):
    permission_required = "rh.delete_treinamento"

    def post(self, request, pk):
        get_object_or_404(Treinamento, pk=pk).delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/rh/treinamentos/"})
        return redirect("web:rh-treinamentos")


class ParticipacaoCreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_participacaotreinamento"

    def get(self, request, treinamento_pk):
        treinamento = get_object_or_404(Treinamento, pk=treinamento_pk)
        ja_inscritos = treinamento.participacoes.values_list("colaborador_id", flat=True)
        colaboradores = Colaborador.objects.filter(status="ativo").exclude(pk__in=ja_inscritos)
        return render(request, "rh/treinamentos/participacao_create.html", {
            "treinamento": treinamento,
            "colaboradores": colaboradores,
            "status_choices": ParticipacaoTreinamento.StatusParticipacao.choices,
            "erros": {},
        })

    def post(self, request, treinamento_pk):
        treinamento = get_object_or_404(Treinamento, pk=treinamento_pk)
        colab_id = request.POST.get("colaborador")
        if not colab_id:
            return redirect("web:rh-treinamento-detail", pk=treinamento_pk)

        part, created = ParticipacaoTreinamento.objects.get_or_create(
            colaborador_id=colab_id,
            treinamento=treinamento,
            defaults={
                "status": request.POST.get("status", "inscrito"),
                "data_inicio": request.POST.get("data_inicio") or None,
                "observacao": request.POST.get("observacao", "").strip(),
            },
        )
        if created:
            from apps.rh.notifications import notificar_inscricao_treinamento
            notificar_inscricao_treinamento(part)
        return redirect("web:rh-treinamento-detail", pk=treinamento_pk)


class ParticipacaoUpdateView(PermissionRequiredMixin, View):
    permission_required = "rh.change_participacaotreinamento"

    def post(self, request, pk):
        part = get_object_or_404(ParticipacaoTreinamento, pk=pk)
        part.status = request.POST.get("status", part.status)
        part.data_inicio = request.POST.get("data_inicio") or part.data_inicio
        part.data_conclusao = request.POST.get("data_conclusao") or None
        nota = request.POST.get("nota", "").strip()
        part.nota = nota if nota else None
        cert = request.FILES.get("certificado")
        if cert:
            part.certificado = cert
        part.observacao = request.POST.get("observacao", "").strip()
        old_status = ParticipacaoTreinamento.objects.filter(pk=pk).values_list("status", flat=True).first()
        part.save()
        if part.status == "concluido" and old_status != "concluido":
            from apps.rh.notifications import notificar_treinamento_concluido
            notificar_treinamento_concluido(part)
        return redirect("web:rh-treinamento-detail", pk=part.treinamento_id)


# ---------------------------------------------------------------------------
# RH — Ciclos de Avaliacao e Metas
# ---------------------------------------------------------------------------
class CicloListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "rh/metas/ciclos_list.html"
    partial_template_name = "rh/metas/_ciclos_table.html"
    context_object_name = "ciclos"
    paginate_by = 20
    permission_required = "rh.view_cicloavaliacao"

    def get_queryset(self):
        return CicloAvaliacao.objects.annotate(total_metas=Count("metas"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_add"] = self.request.user.has_perm("rh.add_cicloavaliacao")
        return ctx


class CicloCreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_cicloavaliacao"

    def get(self, request):
        return render(request, "rh/metas/ciclo_create.html", {"erros": {}})

    def post(self, request):
        erros = {}
        nome = request.POST.get("nome", "").strip()
        if not nome:
            erros["nome"] = "O nome e obrigatorio."
        inicio = request.POST.get("periodo_inicio", "").strip()
        if not inicio:
            erros["periodo_inicio"] = "O inicio e obrigatorio."
        fim = request.POST.get("periodo_fim", "").strip()
        if not fim:
            erros["periodo_fim"] = "O fim e obrigatorio."
        if erros:
            return render(request, "rh/metas/ciclo_create.html", {"erros": erros})

        ciclo = CicloAvaliacao.objects.create(
            nome=nome, periodo_inicio=inicio, periodo_fim=fim,
            status=request.POST.get("status", "aberto"),
            descricao=request.POST.get("descricao", "").strip(),
        )
        from apps.rh.notifications import notificar_novo_ciclo
        notificar_novo_ciclo(ciclo)
        return redirect("web:rh-ciclos")


class CicloDetailView(PermissionRequiredMixin, View):
    permission_required = "rh.view_cicloavaliacao"

    def get(self, request, pk):
        ciclo = get_object_or_404(CicloAvaliacao, pk=pk)
        metas = ciclo.metas.select_related("colaborador").order_by("colaborador__nome_completo")
        # Agrupar metas por colaborador
        metas_por_colab = {}
        for m in metas:
            if m.colaborador_id not in metas_por_colab:
                metas_por_colab[m.colaborador_id] = {
                    "colaborador": m.colaborador,
                    "metas": [],
                    "atingimento_geral": 0,
                }
            metas_por_colab[m.colaborador_id]["metas"].append(m)
        # Calcular atingimento geral por colaborador
        for data in metas_por_colab.values():
            total_peso = sum(m.peso for m in data["metas"])
            if total_peso > 0:
                data["atingimento_geral"] = round(
                    sum(m.atingimento_ponderado for m in data["metas"]) * 100 / total_peso
                )
        return render(request, "rh/metas/ciclo_detail.html", {
            "ciclo": ciclo,
            "metas_por_colab": metas_por_colab.values(),
            "can_edit": request.user.has_perm("rh.change_cicloavaliacao"),
            "can_add_meta": request.user.has_perm("rh.add_meta"),
        })


class MetaCreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_meta"

    def get(self, request, ciclo_pk):
        ciclo = get_object_or_404(CicloAvaliacao, pk=ciclo_pk)
        return render(request, "rh/metas/meta_create.html", {
            "ciclo": ciclo,
            "colaboradores": Colaborador.objects.filter(status="ativo"),
            "erros": {},
        })

    def post(self, request, ciclo_pk):
        ciclo = get_object_or_404(CicloAvaliacao, pk=ciclo_pk)
        erros = {}
        colab_id = request.POST.get("colaborador")
        if not colab_id:
            erros["colaborador"] = "O colaborador e obrigatorio."
        descricao = request.POST.get("descricao", "").strip()
        if not descricao:
            erros["descricao"] = "A descricao e obrigatoria."
        indicador = request.POST.get("indicador", "").strip()
        if not indicador:
            erros["indicador"] = "O indicador e obrigatorio."
        valor_meta = request.POST.get("valor_meta", "").strip()
        if not valor_meta:
            erros["valor_meta"] = "O valor da meta e obrigatorio."

        if erros:
            return render(request, "rh/metas/meta_create.html", {
                "ciclo": ciclo,
                "colaboradores": Colaborador.objects.filter(status="ativo"),
                "erros": erros,
            })

        Meta.objects.create(
            ciclo=ciclo, colaborador_id=colab_id,
            descricao=descricao, indicador=indicador,
            valor_meta=valor_meta,
            peso=request.POST.get("peso", 100) or 100,
            observacao=request.POST.get("observacao", "").strip(),
        )
        return redirect("web:rh-ciclo-detail", pk=ciclo_pk)


class MetaUpdateView(PermissionRequiredMixin, View):
    permission_required = "rh.change_meta"

    def post(self, request, pk):
        meta = get_object_or_404(Meta, pk=pk)
        meta.valor_realizado = request.POST.get("valor_realizado", meta.valor_realizado)
        meta.observacao = request.POST.get("observacao", "").strip()
        meta.save()
        return redirect("web:rh-ciclo-detail", pk=meta.ciclo_id)


# ---------------------------------------------------------------------------
# RH — PDI
# ---------------------------------------------------------------------------
class PDIListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "rh/pdi/list.html"
    partial_template_name = "rh/pdi/_table.html"
    context_object_name = "pdis"
    paginate_by = 20
    permission_required = "rh.view_pdi"

    def get_queryset(self):
        qs = PDI.objects.select_related("colaborador").prefetch_related("acoes")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(
                Q(colaborador__nome_completo__icontains=search) | Q(competencia__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_add"] = self.request.user.has_perm("rh.add_pdi")
        return ctx


class PDICreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_pdi"

    def get(self, request):
        return render(request, "rh/pdi/create.html", {
            "colaboradores": Colaborador.objects.filter(status="ativo"),
            "erros": {},
        })

    def post(self, request):
        erros = {}
        colab_id = request.POST.get("colaborador")
        if not colab_id:
            erros["colaborador"] = "O colaborador e obrigatorio."
        competencia = request.POST.get("competencia", "").strip()
        if not competencia:
            erros["competencia"] = "A competencia e obrigatoria."
        ano = request.POST.get("ano", "").strip()
        if not ano:
            erros["ano"] = "O ano e obrigatorio."

        if erros:
            return render(request, "rh/pdi/create.html", {
                "colaboradores": Colaborador.objects.filter(status="ativo"),
                "erros": erros,
            })

        pdi = PDI.objects.create(
            colaborador_id=colab_id, competencia=competencia, ano=ano,
            observacao=request.POST.get("observacao", "").strip(),
        )
        return redirect("web:rh-pdi-detail", pk=pdi.pk)


class PDIDetailView(PermissionRequiredMixin, View):
    permission_required = "rh.view_pdi"

    def get(self, request, pk):
        pdi = get_object_or_404(
            PDI.objects.select_related("colaborador").prefetch_related("acoes__treinamento"), pk=pk
        )
        return render(request, "rh/pdi/detail.html", {
            "pdi": pdi,
            "treinamentos": Treinamento.objects.filter(ativo=True),
            "can_edit": request.user.has_perm("rh.change_pdi"),
        })


class AcaoPDICreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_acaopdi"

    def post(self, request, pdi_pk):
        pdi = get_object_or_404(PDI, pk=pdi_pk)
        descricao = request.POST.get("descricao", "").strip()
        if descricao:
            AcaoPDI.objects.create(
                pdi=pdi, descricao=descricao,
                prazo=request.POST.get("prazo") or None,
                responsavel=request.POST.get("responsavel", "").strip(),
                treinamento_id=request.POST.get("treinamento") or None,
            )
        return redirect("web:rh-pdi-detail", pk=pdi_pk)


class AcaoPDIUpdateView(PermissionRequiredMixin, View):
    permission_required = "rh.change_acaopdi"

    def post(self, request, pk):
        acao = get_object_or_404(AcaoPDI, pk=pk)
        acao.status = request.POST.get("status", acao.status)
        acao.save(update_fields=["status"])
        return redirect("web:rh-pdi-detail", pk=acao.pdi_id)


# ---------------------------------------------------------------------------
# RH — eNPS
# ---------------------------------------------------------------------------
class ENPSListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "rh/enps/list.html"
    partial_template_name = "rh/enps/_table.html"
    context_object_name = "pesquisas"
    paginate_by = 20
    permission_required = "rh.view_pesquisaenps"

    def get_queryset(self):
        return PesquisaENPS.objects.prefetch_related("perguntas").all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_add"] = self.request.user.has_perm("rh.add_pesquisaenps")
        return ctx


class ENPSCreateView(PermissionRequiredMixin, View):
    permission_required = "rh.add_pesquisaenps"

    def get(self, request):
        return render(request, "rh/enps/create.html", {
            "tipo_choices": PerguntaENPS.TipoPergunta.choices,
            "erros": {},
        })

    def post(self, request):
        erros = {}
        titulo = request.POST.get("titulo", "").strip()
        if not titulo:
            erros["titulo"] = "O titulo e obrigatorio."
        inicio = request.POST.get("data_inicio", "").strip()
        if not inicio:
            erros["data_inicio"] = "A data de inicio e obrigatoria."
        fim = request.POST.get("data_encerramento", "").strip()
        if not fim:
            erros["data_encerramento"] = "A data de encerramento e obrigatoria."

        if erros:
            return render(request, "rh/enps/create.html", {
                "tipo_choices": PerguntaENPS.TipoPergunta.choices,
                "erros": erros,
            })

        pesquisa = PesquisaENPS.objects.create(
            titulo=titulo, data_inicio=inicio, data_encerramento=fim,
            descricao=request.POST.get("descricao", "").strip(),
        )

        # Perguntas dinamicas
        textos = request.POST.getlist("pergunta_texto")
        tipos = request.POST.getlist("pergunta_tipo")
        for i, texto in enumerate(textos):
            texto = texto.strip()
            if texto:
                tipo = tipos[i] if i < len(tipos) else "escala"
                PerguntaENPS.objects.create(
                    pesquisa=pesquisa, texto=texto, tipo=tipo, ordem=i,
                )

        return redirect("web:rh-enps")


class ENPSDetailView(PermissionRequiredMixin, View):
    permission_required = "rh.view_pesquisaenps"

    def get(self, request, pk):
        pesquisa = get_object_or_404(
            PesquisaENPS.objects.prefetch_related("perguntas"), pk=pk
        )
        return render(request, "rh/enps/detail.html", {
            "pesquisa": pesquisa,
            "can_edit": request.user.has_perm("rh.change_pesquisaenps"),
            "can_respond": request.user.has_perm("rh.add_respostaenps"),
        })


class ENPSResponderView(PermissionRequiredMixin, View):
    """Colaborador responde a pesquisa."""
    permission_required = "rh.add_respostaenps"

    def get(self, request, pk):
        pesquisa = get_object_or_404(
            PesquisaENPS.objects.prefetch_related("perguntas"), pk=pk
        )
        colab = getattr(request.user, "colaborador", None)
        if not colab:
            from django.contrib import messages
            messages.error(request, "Seu usuario nao esta vinculado a um colaborador.")
            return redirect("web:rh-enps-detail", pk=pk)
        # Verificar se ja respondeu
        ja_respondeu = RespostaENPS.objects.filter(pesquisa=pesquisa, colaborador=colab).exists()
        return render(request, "rh/enps/responder.html", {
            "pesquisa": pesquisa,
            "colab": colab,
            "ja_respondeu": ja_respondeu,
        })

    def post(self, request, pk):
        pesquisa = get_object_or_404(
            PesquisaENPS.objects.prefetch_related("perguntas"), pk=pk
        )
        colab = getattr(request.user, "colaborador", None)
        if not colab:
            return redirect("web:rh-enps-detail", pk=pk)

        for pergunta in pesquisa.perguntas.all():
            RespostaENPS.objects.update_or_create(
                pesquisa=pesquisa, colaborador=colab, pergunta=pergunta,
                defaults={
                    "nota": request.POST.get(f"nota_{pergunta.pk}") or None,
                    "texto": request.POST.get(f"texto_{pergunta.pk}", "").strip(),
                },
            )
        from django.contrib import messages
        messages.success(request, "Respostas registradas com sucesso!")
        return redirect("web:rh-enps-detail", pk=pk)


class ENPSStatusView(PermissionRequiredMixin, View):
    """Altera status da pesquisa (ativar/encerrar)."""
    permission_required = "rh.change_pesquisaenps"

    def post(self, request, pk):
        pesquisa = get_object_or_404(PesquisaENPS, pk=pk)
        old_status = pesquisa.status
        pesquisa.status = request.POST.get("status", pesquisa.status)
        pesquisa.save(update_fields=["status"])

        from apps.rh.notifications import notificar_pesquisa_ativa, notificar_pesquisa_encerrada
        if pesquisa.status == "ativa" and old_status != "ativa":
            notificar_pesquisa_ativa(pesquisa)
            # Email para todos os colaboradores ativos
            from apps.rh.emails import enviar_pesquisa_enps_ativa
            emails = list(Colaborador.objects.filter(status="ativo").exclude(
                email_pessoal=""
            ).values_list("email_pessoal", flat=True))
            enviar_pesquisa_enps_ativa(pesquisa, emails)
        elif pesquisa.status == "encerrada" and old_status != "encerrada":
            notificar_pesquisa_encerrada(pesquisa)

        return redirect("web:rh-enps-detail", pk=pk)


# ---------------------------------------------------------------------------
# RH — Relatorios e Indicadores
# ---------------------------------------------------------------------------
class RelatoriosRHView(PermissionRequiredMixin, View):
    permission_required = "rh.view_colaborador"

    def get(self, request):
        from django.utils import timezone
        from django.db.models import Sum
        hoje = timezone.now().date()

        # Headcount
        ativos = Colaborador.objects.filter(status="ativo")
        total_ativos = ativos.count()
        total_clt = ativos.filter(tipo_contrato="clt").count()
        total_pj = ativos.filter(tipo_contrato="pj").count()
        total_afastados = Colaborador.objects.filter(status="afastado").count()

        # Turnover (ultimos 12 meses)
        inicio_12m = hoje.replace(year=hoje.year - 1)
        desligados_12m = Colaborador.objects.filter(
            status="desligado", data_desligamento__gte=inicio_12m
        ).count()
        total_geral = Colaborador.objects.count()
        turnover = round((desligados_12m / total_geral) * 100) if total_geral else 0

        # Custo de pessoal
        custo_total = ativos.aggregate(total=Sum("remuneracao"))["total"] or 0
        custo_clt = ativos.filter(tipo_contrato="clt").aggregate(t=Sum("remuneracao"))["t"] or 0
        custo_pj = ativos.filter(tipo_contrato="pj").aggregate(t=Sum("remuneracao"))["t"] or 0

        # Ferias vencidas (CLT com saldo e periodo expirado > 12 meses)
        ferias_vencidas = SaldoFerias.objects.filter(
            colaborador__status="ativo",
            periodo_fim__lt=hoje - timezone.timedelta(days=365),
        ).exclude(dias_usufruidos__gte=F("dias_direito")).count()

        # Documentos a vencer (proximos 30 dias)
        docs_vencer = DocumentoColaborador.objects.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + timezone.timedelta(days=30),
        ).count()
        docs_vencidos = DocumentoColaborador.objects.filter(
            data_vencimento__lt=hoje,
        ).count()

        # Treinamentos
        trein_concluidos = ParticipacaoTreinamento.objects.filter(status="concluido").count()
        trein_andamento = ParticipacaoTreinamento.objects.filter(status="em_andamento").count()
        trein_inscritos = ParticipacaoTreinamento.objects.filter(status="inscrito").count()

        # Ausencias pendentes de aprovacao
        ausencias_pendentes = SolicitacaoAusencia.objects.filter(status="solicitada").count()

        # Onboarding em andamento
        onb_andamento = OnboardingColaborador.objects.filter(concluido_em__isnull=True).count()

        # eNPS (ultima pesquisa encerrada ou ativa)
        ultima_pesquisa = PesquisaENPS.objects.filter(
            status__in=["ativa", "encerrada"]
        ).order_by("-data_inicio").first()
        enps_score = ultima_pesquisa.enps_score if ultima_pesquisa else None
        enps_participacao = ultima_pesquisa.participacao if ultima_pesquisa else 0

        # PDIs em andamento
        pdis_ativos = PDI.objects.filter(ano=hoje.year).count()

        return render(request, "rh/relatorios/dashboard.html", {
            # Headcount
            "total_ativos": total_ativos,
            "total_clt": total_clt,
            "total_pj": total_pj,
            "total_afastados": total_afastados,
            # Turnover
            "turnover": turnover,
            "desligados_12m": desligados_12m,
            # Custo
            "custo_total": custo_total,
            "custo_clt": custo_clt,
            "custo_pj": custo_pj,
            # Alertas
            "ferias_vencidas": ferias_vencidas,
            "docs_vencer": docs_vencer,
            "docs_vencidos": docs_vencidos,
            "ausencias_pendentes": ausencias_pendentes,
            "onb_andamento": onb_andamento,
            # Treinamentos
            "trein_concluidos": trein_concluidos,
            "trein_andamento": trein_andamento,
            "trein_inscritos": trein_inscritos,
            # eNPS
            "enps_score": enps_score,
            "enps_participacao": enps_participacao,
            "ultima_pesquisa": ultima_pesquisa,
            # PDI
            "pdis_ativos": pdis_ativos,
        })


# ===========================================================================
# FINANCEIRO
# ===========================================================================

# ---------------------------------------------------------------------------
# Lancamentos
# ---------------------------------------------------------------------------
class LancamentoListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "financeiro/lancamentos/list.html"
    partial_template_name = "financeiro/lancamentos/_table.html"
    context_object_name = "lancamentos"
    paginate_by = 20
    permission_required = "financeiro.view_lancamento"

    def get_queryset(self):
        qs = Lancamento.objects.select_related("categoria", "conta", "departamento")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(descricao__icontains=search)
        tipo = self.request.GET.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        conta = self.request.GET.get("conta")
        if conta:
            qs = qs.filter(conta_id=conta)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipo_choices"] = Lancamento.Tipo.choices
        ctx["status_choices"] = Lancamento.Status.choices
        ctx["contas"] = ContaBancaria.objects.filter(ativo=True)
        ctx["current_tipo"] = self.request.GET.get("tipo", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_conta"] = self.request.GET.get("conta", "")
        ctx["can_add"] = self.request.user.has_perm("financeiro.add_lancamento")
        return ctx


class LancamentoCreateView(PermissionRequiredMixin, View):
    permission_required = "financeiro.add_lancamento"

    def _ctx(self, erros=None):
        receita_cats = CategoriaFinanceira.objects.filter(tipo="receita", ativo=True)
        despesa_cats = CategoriaFinanceira.objects.filter(tipo="despesa", ativo=True)
        return {
            "receita_cats": receita_cats,
            "despesa_cats": despesa_cats,
            "contas": ContaBancaria.objects.filter(ativo=True),
            "departamentos": Departamento.objects.filter(ativo=True),
            "canal_choices": Lancamento.Canal.choices,
            "erros": erros or {},
        }

    def get(self, request):
        return render(request, "financeiro/lancamentos/create.html", self._ctx())

    def post(self, request):
        erros = {}
        tipo = request.POST.get("tipo", "").strip()
        if not tipo:
            erros["tipo"] = "O tipo e obrigatorio."
        descricao = request.POST.get("descricao", "").strip()
        if not descricao:
            erros["descricao"] = "A descricao e obrigatoria."
        valor = request.POST.get("valor", "").strip()
        if not valor:
            erros["valor"] = "O valor e obrigatorio."
        categoria_id = request.POST.get("categoria")
        if not categoria_id:
            erros["categoria"] = "A categoria e obrigatoria."
        conta_id = request.POST.get("conta")
        if not conta_id:
            erros["conta"] = "A conta e obrigatoria."
        data_vencimento = request.POST.get("data_vencimento", "").strip()
        if not data_vencimento:
            erros["data_vencimento"] = "A data de vencimento e obrigatoria."

        if erros:
            return render(request, "financeiro/lancamentos/create.html", self._ctx(erros))

        Lancamento.objects.create(
            tipo=tipo,
            descricao=descricao,
            valor=valor,
            valor_liquido=request.POST.get("valor_liquido") or None,
            categoria_id=categoria_id,
            conta_id=conta_id,
            departamento_id=request.POST.get("departamento") or None,
            canal=request.POST.get("canal", "manual"),
            data_vencimento=data_vencimento,
            data_competencia=request.POST.get("data_competencia") or None,
            data_pagamento=request.POST.get("data_pagamento") or None,
            status=request.POST.get("status", "pendente"),
            cliente_id=request.POST.get("cliente") or None,
            parceiro_id=request.POST.get("parceiro") or None,
            observacao=request.POST.get("observacao", "").strip(),
            comprovante=request.FILES.get("comprovante"),
            criado_por=request.user,
        )
        return redirect("web:fin-lancamentos")


class LancamentoDetailView(PermissionRequiredMixin, View):
    permission_required = "financeiro.view_lancamento"

    def get(self, request, pk):
        lanc = get_object_or_404(
            Lancamento.objects.select_related(
                "categoria", "conta", "departamento", "cliente", "parceiro", "criado_por"
            ), pk=pk
        )
        return render(request, "financeiro/lancamentos/detail.html", {
            "lanc": lanc,
            "can_edit": request.user.has_perm("financeiro.change_lancamento"),
        })


class LancamentoStatusView(PermissionRequiredMixin, View):
    """Altera status de um lancamento (confirmar, cancelar)."""
    permission_required = "financeiro.change_lancamento"

    def post(self, request, pk):
        lanc = get_object_or_404(Lancamento, pk=pk)
        novo_status = request.POST.get("status")
        if novo_status in dict(Lancamento.Status.choices):
            lanc.status = novo_status
            if novo_status == "confirmado" and not lanc.data_pagamento:
                from django.utils import timezone
                lanc.data_pagamento = timezone.now().date()
            lanc.save()
        return redirect("web:fin-lancamento-detail", pk=pk)


# ---------------------------------------------------------------------------
# Contas Bancarias
# ---------------------------------------------------------------------------
class ContaListView(PermissionRequiredMixin, ListView):
    template_name = "financeiro/contas/list.html"
    context_object_name = "contas"
    permission_required = "financeiro.view_contabancaria"

    def get_queryset(self):
        return ContaBancaria.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_add"] = self.request.user.has_perm("financeiro.add_contabancaria")
        return ctx


class ContaCreateView(PermissionRequiredMixin, View):
    permission_required = "financeiro.add_contabancaria"

    def get(self, request):
        return render(request, "financeiro/contas/create.html", {
            "tipo_choices": ContaBancaria.TipoConta.choices,
            "erros": {},
        })

    def post(self, request):
        erros = {}
        nome = request.POST.get("nome", "").strip()
        if not nome:
            erros["nome"] = "O nome e obrigatorio."
        tipo = request.POST.get("tipo", "").strip()
        if not tipo:
            erros["tipo"] = "O tipo e obrigatorio."
        if erros:
            return render(request, "financeiro/contas/create.html", {
                "tipo_choices": ContaBancaria.TipoConta.choices,
                "erros": erros,
            })
        ContaBancaria.objects.create(
            nome=nome, tipo=tipo,
            banco=request.POST.get("banco", "").strip(),
            agencia=request.POST.get("agencia", "").strip(),
            numero=request.POST.get("numero", "").strip(),
            saldo_inicial=request.POST.get("saldo_inicial", 0) or 0,
        )
        return redirect("web:fin-contas")


# ---------------------------------------------------------------------------
# Cobrancas (Contas a Receber)
# ---------------------------------------------------------------------------
class CobrancaListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "financeiro/cobrancas/list.html"
    partial_template_name = "financeiro/cobrancas/_table.html"
    context_object_name = "cobrancas"
    paginate_by = 20
    permission_required = "financeiro.view_cobranca"

    def get_queryset(self):
        qs = Cobranca.objects.select_related("cliente", "plano")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(Q(descricao__icontains=search) | Q(cliente__nome__icontains=search))
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Cobranca.StatusCobranca.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["can_add"] = self.request.user.has_perm("financeiro.add_cobranca")
        return ctx


class CobrancaCreateView(PermissionRequiredMixin, View):
    permission_required = "financeiro.add_cobranca"

    def get(self, request):
        return render(request, "financeiro/cobrancas/create.html", {
            "tipo_choices": Cobranca.TipoCobranca.choices,
            "canal_choices": Lancamento.Canal.choices,
            "clientes": Cliente.objects.filter(ativo=True),
            "planos": Plano.objects.filter(ativo=True).select_related("parceiro"),
            "erros": {},
        })

    def post(self, request):
        erros = {}
        cliente_id = request.POST.get("cliente")
        if not cliente_id:
            erros["cliente"] = "O cliente é obrigatório."
        descricao = request.POST.get("descricao", "").strip()
        if not descricao:
            erros["descricao"] = "A descrição é obrigatória."
        valor = request.POST.get("valor", "").strip()
        if not valor:
            erros["valor"] = "O valor é obrigatório."
        vencimento = request.POST.get("vencimento", "").strip()
        if not vencimento:
            erros["vencimento"] = "O vencimento é obrigatório."

        if erros:
            return render(request, "financeiro/cobrancas/create.html", {
                "tipo_choices": Cobranca.TipoCobranca.choices,
                "canal_choices": Lancamento.Canal.choices,
                "clientes": Cliente.objects.filter(ativo=True),
                "planos": Plano.objects.filter(ativo=True).select_related("parceiro"),
                "erros": erros,
            })

        Cobranca.objects.create(
            cliente_id=cliente_id,
            plano_id=request.POST.get("plano") or None,
            tipo=request.POST.get("tipo", "avulsa"),
            descricao=descricao,
            valor=valor,
            vencimento=vencimento,
            canal=request.POST.get("canal", "manual"),
            observacao=request.POST.get("observacao", "").strip(),
        )
        return redirect("web:fin-cobrancas")


class CobrancaConfirmarView(PermissionRequiredMixin, View):
    """Confirma pagamento de cobranca e gera lancamento de receita."""
    permission_required = "financeiro.change_cobranca"

    def post(self, request, pk):
        cobranca = get_object_or_404(Cobranca.objects.select_related("cliente"), pk=pk)
        if cobranca.status == "pago":
            return redirect("web:fin-cobrancas")

        from django.utils import timezone
        hoje = timezone.now().date()

        # Buscar categoria de receita de servicos
        cat = CategoriaFinanceira.objects.filter(tipo="receita", pai__isnull=False).first()
        conta = ContaBancaria.objects.filter(ativo=True).first()

        lanc = Lancamento.objects.create(
            tipo="receita",
            descricao=f"Cobrança: {cobranca.descricao}",
            valor=cobranca.valor,
            categoria=cat,
            conta=conta,
            canal=cobranca.canal,
            data_vencimento=cobranca.vencimento,
            data_competencia=cobranca.vencimento,
            data_pagamento=hoje,
            status="confirmado",
            cliente=cobranca.cliente,
            criado_por=request.user,
        )
        cobranca.status = "pago"
        cobranca.data_pagamento = hoje
        cobranca.lancamento = lanc
        cobranca.save()
        return redirect("web:fin-cobrancas")


# ---------------------------------------------------------------------------
# Despesas (Contas a Pagar)
# ---------------------------------------------------------------------------
class DespesaListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "financeiro/despesas/list.html"
    partial_template_name = "financeiro/despesas/_table.html"
    context_object_name = "despesas"
    paginate_by = 20
    permission_required = "financeiro.view_despesa"

    def get_queryset(self):
        qs = Despesa.objects.select_related("categoria", "conta")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(Q(descricao__icontains=search) | Q(fornecedor__icontains=search))
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Despesa.StatusDespesa.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["can_add"] = self.request.user.has_perm("financeiro.add_despesa")
        return ctx


class DespesaCreateView(PermissionRequiredMixin, View):
    permission_required = "financeiro.add_despesa"

    def get(self, request):
        return render(request, "financeiro/despesas/create.html", {
            "categorias": CategoriaFinanceira.objects.filter(tipo="despesa", ativo=True),
            "recorrencia_choices": Despesa.Recorrencia.choices,
            "contas": ContaBancaria.objects.filter(ativo=True),
            "departamentos": Departamento.objects.filter(ativo=True),
            "erros": {},
        })

    def post(self, request):
        erros = {}
        fornecedor = request.POST.get("fornecedor", "").strip()
        if not fornecedor:
            erros["fornecedor"] = "O fornecedor é obrigatório."
        descricao = request.POST.get("descricao", "").strip()
        if not descricao:
            erros["descricao"] = "A descrição é obrigatória."
        valor = request.POST.get("valor", "").strip()
        if not valor:
            erros["valor"] = "O valor é obrigatório."
        categoria_id = request.POST.get("categoria")
        if not categoria_id:
            erros["categoria"] = "A categoria é obrigatória."
        vencimento = request.POST.get("vencimento", "").strip()
        if not vencimento:
            erros["vencimento"] = "O vencimento é obrigatório."

        if erros:
            return render(request, "financeiro/despesas/create.html", {
                "categorias": CategoriaFinanceira.objects.filter(tipo="despesa", ativo=True),
                "recorrencia_choices": Despesa.Recorrencia.choices,
                "contas": ContaBancaria.objects.filter(ativo=True),
                "departamentos": Departamento.objects.filter(ativo=True),
                "erros": erros,
            })

        Despesa.objects.create(
            fornecedor=fornecedor,
            descricao=descricao,
            categoria_id=categoria_id,
            valor=valor,
            vencimento=vencimento,
            recorrencia=request.POST.get("recorrencia", "unico"),
            conta_id=request.POST.get("conta") or None,
            departamento_id=request.POST.get("departamento") or None,
            observacao=request.POST.get("observacao", "").strip(),
            comprovante=request.FILES.get("comprovante"),
        )
        return redirect("web:fin-despesas")


class DespesaConfirmarView(PermissionRequiredMixin, View):
    """Confirma pagamento de despesa e gera lancamento de despesa."""
    permission_required = "financeiro.change_despesa"

    def post(self, request, pk):
        despesa = get_object_or_404(Despesa, pk=pk)
        if despesa.status == "pago":
            return redirect("web:fin-despesas")

        from django.utils import timezone
        hoje = timezone.now().date()

        conta = despesa.conta or ContaBancaria.objects.filter(ativo=True).first()

        lanc = Lancamento.objects.create(
            tipo="despesa",
            descricao=f"Despesa: {despesa.descricao}",
            valor=despesa.valor,
            categoria=despesa.categoria,
            conta=conta,
            departamento=despesa.departamento,
            canal="manual",
            data_vencimento=despesa.vencimento,
            data_competencia=despesa.vencimento,
            data_pagamento=hoje,
            status="confirmado",
            criado_por=request.user,
        )
        despesa.status = "pago"
        despesa.data_pagamento = hoje
        despesa.lancamento = lanc
        despesa.save()
        return redirect("web:fin-despesas")


# ---------------------------------------------------------------------------
# Notas Fiscais
# ---------------------------------------------------------------------------
class NotaFiscalListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "financeiro/nfs/list.html"
    partial_template_name = "financeiro/nfs/_table.html"
    context_object_name = "nfs"
    paginate_by = 20
    permission_required = "financeiro.view_notafiscal"

    def get_queryset(self):
        qs = NotaFiscal.objects.select_related("cliente")
        tipo = self.request.GET.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(Q(numero__icontains=search) | Q(fornecedor__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipo_choices"] = NotaFiscal.TipoNF.choices
        ctx["current_tipo"] = self.request.GET.get("tipo", "")
        ctx["can_add"] = self.request.user.has_perm("financeiro.add_notafiscal")
        return ctx


class NotaFiscalCreateView(PermissionRequiredMixin, View):
    permission_required = "financeiro.add_notafiscal"

    def get(self, request):
        return render(request, "financeiro/nfs/create.html", {
            "tipo_choices": NotaFiscal.TipoNF.choices,
            "clientes": Cliente.objects.filter(ativo=True),
            "erros": {},
        })

    def post(self, request):
        erros = {}
        tipo = request.POST.get("tipo", "").strip()
        if not tipo:
            erros["tipo"] = "O tipo é obrigatório."
        numero = request.POST.get("numero", "").strip()
        if not numero:
            erros["numero"] = "O número é obrigatório."
        valor = request.POST.get("valor", "").strip()
        if not valor:
            erros["valor"] = "O valor é obrigatório."
        data_emissao = request.POST.get("data_emissao", "").strip()
        if not data_emissao:
            erros["data_emissao"] = "A data de emissão é obrigatória."

        if erros:
            return render(request, "financeiro/nfs/create.html", {
                "tipo_choices": NotaFiscal.TipoNF.choices,
                "clientes": Cliente.objects.filter(ativo=True),
                "erros": erros,
            })

        NotaFiscal.objects.create(
            tipo=tipo,
            numero=numero,
            valor=valor,
            data_emissao=data_emissao,
            cliente_id=request.POST.get("cliente") or None,
            fornecedor=request.POST.get("fornecedor", "").strip(),
            arquivo=request.FILES.get("arquivo"),
            observacao=request.POST.get("observacao", "").strip(),
        )
        return redirect("web:fin-nfs")


# ---------------------------------------------------------------------------
# Folha de Pagamento
# ---------------------------------------------------------------------------
class FolhaListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "financeiro/folha/list.html"
    partial_template_name = "financeiro/folha/_table.html"
    context_object_name = "folhas"
    paginate_by = 20
    permission_required = "financeiro.view_folhapagamento"

    def get_queryset(self):
        qs = FolhaPagamento.objects.select_related("colaborador", "conta")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(colaborador__nome_completo__icontains=search)
        tipo = self.request.GET.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        competencia = self.request.GET.get("competencia")
        if competencia:
            if len(competencia) == 7:
                competencia = f"{competencia}-01"
            qs = qs.filter(competencia=competencia)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipo_choices"] = FolhaPagamento.TipoPagamento.choices
        ctx["status_choices"] = FolhaPagamento.StatusFolha.choices
        ctx["current_tipo"] = self.request.GET.get("tipo", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_competencia"] = self.request.GET.get("competencia", "")
        ctx["can_add"] = self.request.user.has_perm("financeiro.add_folhapagamento")
        # Meses disponiveis
        ctx["competencias"] = (
            FolhaPagamento.objects.dates("competencia", "month", order="DESC")
        )
        return ctx


class FolhaColaboradoresView(PermissionRequiredMixin, View):
    """Partial HTMX: retorna options de colaboradores filtrados por departamento."""
    permission_required = "financeiro.add_folhapagamento"

    def get(self, request):
        depto_id = request.GET.get("departamento")
        qs = Colaborador.objects.filter(status="ativo")
        if depto_id:
            qs = qs.filter(departamento_id=depto_id)
        options = '<option value="">Selecione...</option>'
        for c in qs:
            options += f'<option value="{c.pk}">{c.nome_completo} ({c.get_tipo_contrato_display()} — R$ {c.remuneracao:,.2f})</option>'
        return HttpResponse(options)


class FolhaCreateView(PermissionRequiredMixin, View):
    permission_required = "financeiro.add_folhapagamento"

    def get(self, request):
        return render(request, "financeiro/folha/create.html", {
            "tipo_choices": FolhaPagamento.TipoPagamento.choices,
            "departamentos": Departamento.objects.filter(ativo=True),
            "colaboradores": Colaborador.objects.filter(status="ativo"),
            "contas": ContaBancaria.objects.filter(ativo=True),
            "erros": {},
        })

    def post(self, request):
        erros = {}
        colab_id = request.POST.get("colaborador")
        if not colab_id:
            erros["colaborador"] = "O colaborador é obrigatório."
        tipo = request.POST.get("tipo", "").strip()
        if not tipo:
            erros["tipo"] = "O tipo é obrigatório."
        competencia = request.POST.get("competencia", "").strip()
        if not competencia:
            erros["competencia"] = "A competência é obrigatória."
        valor_bruto = request.POST.get("valor_bruto", "").strip()
        if not valor_bruto:
            erros["valor_bruto"] = "O valor bruto é obrigatório."

        if erros:
            return render(request, "financeiro/folha/create.html", {
                "tipo_choices": FolhaPagamento.TipoPagamento.choices,
                "departamentos": Departamento.objects.filter(ativo=True),
                "colaboradores": Colaborador.objects.filter(status="ativo"),
                "contas": ContaBancaria.objects.filter(ativo=True),
                "erros": erros,
            })

        from decimal import Decimal
        # type="month" envia YYYY-MM, adicionar -01 pra DateField
        if competencia and len(competencia) == 7:
            competencia = f"{competencia}-01"
        FolhaPagamento.objects.create(
            colaborador_id=colab_id,
            tipo=tipo,
            competencia=competencia,
            valor_bruto=Decimal(valor_bruto),
            desconto_inss=Decimal(request.POST.get("desconto_inss") or "0"),
            desconto_ir=Decimal(request.POST.get("desconto_ir") or "0"),
            outros_descontos=Decimal(request.POST.get("outros_descontos") or "0"),
            valor_liquido=0,  # calculado no save()
            conta_id=request.POST.get("conta") or None,
            observacao=request.POST.get("observacao", "").strip(),
        )
        return redirect("web:fin-folha")


class FolhaEditView(PermissionRequiredMixin, View):
    """Edita um pagamento de folha (so quando calculado)."""
    permission_required = "financeiro.change_folhapagamento"

    def get(self, request, pk):
        folha = get_object_or_404(FolhaPagamento.objects.select_related("colaborador"), pk=pk)
        return render(request, "financeiro/folha/edit.html", {
            "folha": folha,
            "tipo_choices": FolhaPagamento.TipoPagamento.choices,
            "contas": ContaBancaria.objects.filter(ativo=True),
            "erros": {},
        })

    def post(self, request, pk):
        folha = get_object_or_404(FolhaPagamento, pk=pk)
        if folha.status == "pago":
            return redirect("web:fin-folha")

        from decimal import Decimal
        folha.tipo = request.POST.get("tipo", folha.tipo)
        folha.valor_bruto = Decimal(request.POST.get("valor_bruto") or str(folha.valor_bruto))
        folha.desconto_inss = Decimal(request.POST.get("desconto_inss") or "0")
        folha.desconto_ir = Decimal(request.POST.get("desconto_ir") or "0")
        folha.outros_descontos = Decimal(request.POST.get("outros_descontos") or "0")
        folha.conta_id = request.POST.get("conta") or folha.conta_id
        folha.observacao = request.POST.get("observacao", "").strip()
        folha.save()  # valor_liquido calculado no save()
        return redirect("web:fin-folha")


class FolhaDeleteView(PermissionRequiredMixin, View):
    """Remove pagamento da folha (so quando calculado)."""
    permission_required = "financeiro.delete_folhapagamento"

    def post(self, request, pk):
        folha = get_object_or_404(FolhaPagamento, pk=pk)
        if folha.status == "pago":
            return redirect("web:fin-folha")
        folha.delete()
        if is_htmx(request):
            return HttpResponse(headers={"HX-Redirect": "/financeiro/folha/"})
        return redirect("web:fin-folha")


class FolhaConfirmarView(PermissionRequiredMixin, View):
    """Confirma pagamento de folha e gera lancamento."""
    permission_required = "financeiro.change_folhapagamento"

    def post(self, request, pk):
        folha = get_object_or_404(FolhaPagamento.objects.select_related("colaborador"), pk=pk)
        if folha.status == "pago":
            return redirect("web:fin-folha")

        acao = request.POST.get("acao", "pagar")
        if acao == "aprovar":
            folha.status = "aprovado"
            folha.save(update_fields=["status"])
            return redirect("web:fin-folha")

        from django.utils import timezone
        hoje = timezone.now().date()

        cat = CategoriaFinanceira.objects.filter(
            tipo="despesa", nome__icontains="salario" if folha.tipo == "salario" else "pro-labore"
        ).first() or CategoriaFinanceira.objects.filter(tipo="despesa", pai__isnull=False).first()
        conta = folha.conta or ContaBancaria.objects.filter(ativo=True).first()

        lanc = Lancamento.objects.create(
            tipo="despesa",
            descricao=f"Folha: {folha.get_tipo_display()} — {folha.colaborador.nome_completo} ({folha.competencia:%m/%Y})",
            valor=folha.valor_liquido,
            categoria=cat,
            conta=conta,
            departamento=folha.colaborador.departamento,
            canal="manual",
            data_vencimento=hoje,
            data_competencia=folha.competencia,
            data_pagamento=hoje,
            status="confirmado",
            criado_por=request.user,
        )
        folha.status = "pago"
        folha.data_pagamento = hoje
        folha.lancamento = lanc
        folha.save()
        return redirect("web:fin-folha")


# ---------------------------------------------------------------------------
# Tributos
# ---------------------------------------------------------------------------
class TributoListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "financeiro/tributos/list.html"
    partial_template_name = "financeiro/tributos/_table.html"
    context_object_name = "tributos"
    paginate_by = 20
    permission_required = "financeiro.view_tributo"

    def get_queryset(self):
        qs = Tributo.objects.all()
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(tipo__icontains=search)
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Tributo.StatusTributo.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["can_add"] = self.request.user.has_perm("financeiro.add_tributo")
        return ctx


class TributoCreateView(PermissionRequiredMixin, View):
    permission_required = "financeiro.add_tributo"

    def get(self, request):
        return render(request, "financeiro/tributos/create.html", {
            "contas": ContaBancaria.objects.filter(ativo=True),
            "erros": {},
        })

    def post(self, request):
        erros = {}
        tipo = request.POST.get("tipo", "").strip()
        if not tipo:
            erros["tipo"] = "O tipo é obrigatório."
        competencia = request.POST.get("competencia", "").strip()
        if not competencia:
            erros["competencia"] = "A competência é obrigatória."
        valor = request.POST.get("valor", "").strip()
        if not valor:
            erros["valor"] = "O valor é obrigatório."
        vencimento = request.POST.get("vencimento", "").strip()
        if not vencimento:
            erros["vencimento"] = "O vencimento é obrigatório."

        if erros:
            return render(request, "financeiro/tributos/create.html", {
                "contas": ContaBancaria.objects.filter(ativo=True),
                "erros": erros,
            })

        # type="month" envia YYYY-MM
        if competencia and len(competencia) == 7:
            competencia = f"{competencia}-01"
        Tributo.objects.create(
            tipo=tipo,
            competencia=competencia,
            valor=valor,
            vencimento=vencimento,
            numero_guia=request.POST.get("numero_guia", "").strip(),
            conta_id=request.POST.get("conta") or None,
            observacao=request.POST.get("observacao", "").strip(),
            comprovante=request.FILES.get("comprovante"),
        )
        return redirect("web:fin-tributos")


class TributoConfirmarView(PermissionRequiredMixin, View):
    """Confirma pagamento de tributo e gera lancamento."""
    permission_required = "financeiro.change_tributo"

    def post(self, request, pk):
        tributo = get_object_or_404(Tributo, pk=pk)
        if tributo.status == "pago":
            return redirect("web:fin-tributos")

        from django.utils import timezone
        hoje = timezone.now().date()

        cat = CategoriaFinanceira.objects.filter(
            tipo="despesa", nome__icontains=tributo.tipo.split()[0]
        ).first() or CategoriaFinanceira.objects.filter(
            tipo="despesa", nome__icontains="imposto"
        ).first() or CategoriaFinanceira.objects.filter(tipo="despesa", pai__isnull=False).first()

        conta = tributo.conta or ContaBancaria.objects.filter(ativo=True).first()

        lanc = Lancamento.objects.create(
            tipo="despesa",
            descricao=f"Tributo: {tributo.tipo} — {tributo.competencia:%m/%Y}",
            valor=tributo.valor,
            categoria=cat,
            conta=conta,
            canal="manual",
            data_vencimento=tributo.vencimento,
            data_competencia=tributo.competencia,
            data_pagamento=hoje,
            status="confirmado",
            criado_por=request.user,
        )
        tributo.status = "pago"
        tributo.data_pagamento = hoje
        tributo.lancamento = lanc
        tributo.comprovante = request.FILES.get("comprovante") or tributo.comprovante
        tributo.save()
        return redirect("web:fin-tributos")


# ---------------------------------------------------------------------------
# Configuracao de Folha
# ---------------------------------------------------------------------------
class ConfiguracaoFolhaView(PermissionRequiredMixin, View):
    permission_required = "financeiro.change_folhapagamento"

    def get(self, request):
        config = ConfiguracaoFolha.get()
        return render(request, "financeiro/folha/configuracao.html", {
            "config": config,
            "contas": ContaBancaria.objects.filter(ativo=True),
        })

    def post(self, request):
        config = ConfiguracaoFolha.get()
        config.dia_pagamento = int(request.POST.get("dia_pagamento", 5))
        config.gerar_salario = "gerar_salario" in request.POST
        config.gerar_pj = "gerar_pj" in request.POST
        config.gerar_pro_labore = "gerar_pro_labore" in request.POST
        config.conta_padrao_id = request.POST.get("conta_padrao") or None
        config.save()
        from django.contrib import messages
        messages.success(request, "Configuração de folha salva com sucesso!")
        return redirect("web:fin-folha-config")


class GerarFolhaView(PermissionRequiredMixin, View):
    """Gera folha do mes corrente manualmente."""
    permission_required = "financeiro.add_folhapagamento"

    def post(self, request):
        from django.core.management import call_command
        from django.contrib import messages
        from django.utils import timezone
        from io import StringIO

        competencia = timezone.now().date().replace(day=1)
        existentes = FolhaPagamento.objects.filter(competencia=competencia).count()

        if existentes > 0:
            messages.warning(request, f"Folha de {competencia:%m/%Y} já foi gerada ({existentes} pagamento(s) existentes).")
        else:
            out = StringIO()
            call_command("gerar_folha_mensal", stdout=out)
            resultado = out.getvalue().strip()
            if "0 pagamento" in resultado:
                messages.warning(request, resultado)
            else:
                messages.success(request, resultado)
        return redirect("web:fin-folha")


class FolhaAprovarTodosView(PermissionRequiredMixin, View):
    """Aprova todos os pagamentos calculados do mes."""
    permission_required = "financeiro.change_folhapagamento"

    def post(self, request):
        from django.utils import timezone
        competencia = request.POST.get("competencia")
        if not competencia:
            competencia = timezone.now().date().replace(day=1)

        atualizados = FolhaPagamento.objects.filter(
            competencia=competencia, status="calculado",
        ).update(status="aprovado")

        from django.contrib import messages
        if atualizados > 0:
            messages.success(request, f"{atualizados} pagamento(s) aprovado(s) para {competencia.strftime('%m/%Y') if hasattr(competencia, 'strftime') else competencia}.")
        else:
            messages.info(request, "Nenhum pagamento pendente de aprovação.")
        return redirect("web:fin-folha")


class FolhaExportarView(PermissionRequiredMixin, View):
    """Exporta folha do mes (so se todos aprovados/pagos)."""
    permission_required = "financeiro.view_folhapagamento"

    def get(self, request):
        from django.utils import timezone
        from datetime import date
        import csv
        import json
        from io import BytesIO

        competencia_str = request.GET.get("mes")
        formato = request.GET.get("formato", "csv")

        if not competencia_str:
            from django.contrib import messages
            messages.warning(request, "Selecione uma competência.")
            return redirect("web:fin-folha")

        ano, mes_num = int(competencia_str[:4]), int(competencia_str[5:7])
        competencia = date(ano, mes_num, 1)

        # Verificar se todos estao aprovados ou pagos
        folhas = FolhaPagamento.objects.filter(competencia=competencia).select_related("colaborador")
        nao_aprovados = folhas.filter(status="calculado").count()

        if nao_aprovados > 0:
            from django.contrib import messages
            messages.warning(request, f"Existem {nao_aprovados} pagamento(s) não aprovado(s). Aprove todos antes de exportar.")
            return redirect("web:fin-folha")

        if not folhas.exists():
            from django.contrib import messages
            messages.warning(request, "Nenhum pagamento encontrado para esta competência.")
            return redirect("web:fin-folha")

        # Montar dados agrupados por colaborador
        from decimal import Decimal
        from collections import OrderedDict

        agrupado = OrderedDict()
        valor_total = Decimal("0")
        for f in folhas.order_by("colaborador__nome_completo", "tipo"):
            nome = f.colaborador.nome_completo
            if nome not in agrupado:
                agrupado[nome] = {"pagamentos": [], "subtotal_liquido": Decimal("0")}
            agrupado[nome]["pagamentos"].append(f)
            agrupado[nome]["subtotal_liquido"] += f.valor_liquido
            valor_total += f.valor_liquido

        # Dados planos pra CSV/JSON/XML (com linha de subtotal)
        dados = []
        for nome, info in agrupado.items():
            for f in info["pagamentos"]:
                dados.append({
                    "colaborador": nome,
                    "tipo": f.get_tipo_display(),
                    "competencia": str(f.competencia),
                    "valor_bruto": str(f.valor_bruto),
                    "desconto_inss": str(f.desconto_inss),
                    "desconto_ir": str(f.desconto_ir),
                    "outros_descontos": str(f.outros_descontos),
                    "valor_liquido": str(f.valor_liquido),
                    "status": f.get_status_display(),
                })
            # Subtotal se tem mais de 1 pagamento
            if len(info["pagamentos"]) > 1:
                dados.append({
                    "colaborador": f"  SUBTOTAL — {nome}",
                    "tipo": "",
                    "competencia": "",
                    "valor_bruto": "",
                    "desconto_inss": "",
                    "desconto_ir": "",
                    "outros_descontos": "",
                    "valor_liquido": str(info["subtotal_liquido"]),
                    "status": "",
                })

        # Registrar log
        LogExportacaoFolha.objects.create(
            competencia=competencia,
            formato=formato,
            total_registros=len(dados),
            valor_total=valor_total,
            exportado_por=request.user,
        )

        nome_arquivo = f"folha_{ano}_{mes_num:02d}"

        if formato == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}.csv"'
            response.write("\ufeff")
            if dados:
                writer = csv.DictWriter(response, fieldnames=dados[0].keys(), delimiter=";")
                writer.writeheader()
                writer.writerows(dados)
            return response

        elif formato == "json":
            response = HttpResponse(
                json.dumps({"competencia": str(competencia), "folha": dados}, indent=2, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
            )
            response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}.json"'
            return response

        elif formato == "xml":
            xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<folha competencia="{competencia}">\n'
            for d in dados:
                xml += "  <pagamento>\n"
                for k, v in d.items():
                    xml += f"    <{k}>{v}</{k}>\n"
                xml += "  </pagamento>\n"
            xml += "</folha>"
            response = HttpResponse(xml, content_type="application/xml; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}.xml"'
            return response

        elif formato == "pdf":
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER
            from django.conf import settings as django_settings
            import os

            buf = BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
            styles = getSampleStyleSheet()
            elements = []

            logo_path = os.path.join(django_settings.BASE_DIR, "static", "img", "logo.png")
            if os.path.exists(logo_path):
                elements.append(Image(logo_path, width=80, height=22))
                elements.append(Spacer(1, 8))

            title_style = ParagraphStyle("T", parent=styles["Title"], fontSize=14, textColor=colors.HexColor("#2d4a3e"))
            elements.append(Paragraph(f"Folha de Pagamento — {mes_num:02d}/{ano}", title_style))
            elements.append(Spacer(1, 16))

            page_width = landscape(A4)[0] - 4 * cm
            headers = ["Colaborador", "Tipo", "Bruto", "INSS", "IR", "Outros", "Líquido", "Status"]
            col_widths = [page_width*0.25, page_width*0.12, page_width*0.12, page_width*0.10,
                          page_width*0.10, page_width*0.10, page_width*0.12, page_width*0.09]
            table_data = [headers]

            def fmt_v(v):
                from decimal import Decimal as D
                num = D(v)
                inteiro = f"{int(num):,}".replace(",", ".")
                centavos = f"{abs(num) % 1:.2f}"[2:]
                return f"R$ {inteiro},{centavos}"

            subtotal_rows = []
            row_idx = 1
            for d in dados:
                is_subtotal = d["colaborador"].startswith("  SUBTOTAL")
                if is_subtotal:
                    table_data.append([
                        d["colaborador"], "", "", "", "", "",
                        fmt_v(d["valor_liquido"]) if d["valor_liquido"] else "", "",
                    ])
                    subtotal_rows.append(row_idx)
                else:
                    table_data.append([
                        d["colaborador"][:30], d["tipo"],
                        fmt_v(d["valor_bruto"]), fmt_v(d["desconto_inss"]),
                        fmt_v(d["desconto_ir"]), fmt_v(d["outros_descontos"]),
                        fmt_v(d["valor_liquido"]), d["status"],
                    ])
                row_idx += 1

            style_cmds = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d4a3e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
            # Destacar linhas de subtotal
            for sr in subtotal_rows:
                style_cmds.append(("BACKGROUND", (0, sr), (-1, sr), colors.HexColor("#e8e8e8")))
                style_cmds.append(("FONTNAME", (0, sr), (-1, sr), "Helvetica-Bold"))

            t = Table(table_data, repeatRows=1, colWidths=col_widths)
            t.setStyle(TableStyle(style_cmds))
            elements.append(t)
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"Total líquido: {fmt_v(str(valor_total))}", styles["Normal"]))

            doc.build(elements)
            buf.seek(0)
            response = HttpResponse(buf.read(), content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}.pdf"'
            return response

        return redirect("web:fin-folha")


# ---------------------------------------------------------------------------
# Patrimonio (Ativos)
# ---------------------------------------------------------------------------
class AtivoListView(PermissionRequiredMixin, HtmxMixin, ListView):
    template_name = "financeiro/ativos/list.html"
    partial_template_name = "financeiro/ativos/_table.html"
    context_object_name = "ativos"
    paginate_by = 20
    permission_required = "financeiro.view_ativo"

    def get_queryset(self):
        qs = Ativo.objects.select_related("departamento")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(numero_serie__icontains=search))
        categoria = self.request.GET.get("categoria")
        if categoria:
            qs = qs.filter(categoria=categoria)
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categoria_choices"] = Ativo.CategoriaAtivo.choices
        ctx["status_choices"] = Ativo.StatusAtivo.choices
        ctx["current_categoria"] = self.request.GET.get("tipo", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["can_add"] = self.request.user.has_perm("financeiro.add_ativo")
        from django.db.models import Sum
        ativos_qs = Ativo.objects.filter(status="ativo")
        ctx["total_valor_compra"] = ativos_qs.aggregate(t=Sum("valor_compra"))["t"] or 0
        return ctx


class AtivoCreateView(PermissionRequiredMixin, View):
    permission_required = "financeiro.add_ativo"

    def _ctx(self, erros=None):
        tipos_existentes = (
            Ativo.objects.values_list("tipo", flat=True).distinct().order_by("tipo")
        )
        return {
            "categoria_choices": Ativo.CategoriaAtivo.choices,
            "tipos_existentes": tipos_existentes,
            "departamentos": Departamento.objects.filter(ativo=True),
            "setores": Setor.objects.filter(ativo=True).select_related("departamento"),
            "erros": erros or {},
        }

    def get(self, request):
        return render(request, "financeiro/ativos/create.html", self._ctx())

    def post(self, request):
        erros = {}
        nome = request.POST.get("nome", "").strip()
        if not nome:
            erros["nome"] = "O nome é obrigatório."
        tipo = request.POST.get("tipo", "").strip()
        if not tipo:
            erros["tipo"] = "O tipo é obrigatório."
        valor_compra = request.POST.get("valor_compra", "").strip()
        if not valor_compra:
            erros["valor_compra"] = "O valor é obrigatório."
        data_aquisicao = request.POST.get("data_aquisicao", "").strip()
        if not data_aquisicao:
            erros["data_aquisicao"] = "A data é obrigatória."

        if erros:
            return render(request, "financeiro/ativos/create.html", self._ctx(erros))

        Ativo.objects.create(
            nome=nome, tipo=tipo,
            categoria=request.POST.get("categoria", "movel_duravel"),
            numero_serie=request.POST.get("numero_serie", "").strip(),
            descricao=request.POST.get("descricao", "").strip(),
            valor_compra=valor_compra,
            data_aquisicao=data_aquisicao,
            vida_util_anos=request.POST.get("vida_util_anos", 5) or 5,
            taxa_depreciacao=request.POST.get("taxa_depreciacao", 20) or 20,
            responsavel=request.POST.get("responsavel", "").strip(),
            departamento_id=request.POST.get("departamento") or None,
            setor_id=request.POST.get("setor") or None,
            observacao=request.POST.get("observacao", "").strip(),
        )
        return redirect("web:fin-ativos")


class AtivoDetailView(PermissionRequiredMixin, View):
    permission_required = "financeiro.view_ativo"

    def get(self, request, pk):
        ativo = get_object_or_404(
            Ativo.objects.select_related("departamento", "setor"), pk=pk
        )
        return render(request, "financeiro/ativos/detail.html", {
            "ativo": ativo,
            "can_edit": request.user.has_perm("financeiro.change_ativo"),
        })


class AtivoEditView(PermissionRequiredMixin, View):
    permission_required = "financeiro.change_ativo"

    def get(self, request, pk):
        ativo = get_object_or_404(Ativo, pk=pk)
        tipos_existentes = Ativo.objects.values_list("tipo", flat=True).distinct().order_by("tipo")
        return render(request, "financeiro/ativos/edit.html", {
            "ativo": ativo,
            "categoria_choices": Ativo.CategoriaAtivo.choices,
            "status_choices": Ativo.StatusAtivo.choices,
            "tipos_existentes": tipos_existentes,
            "departamentos": Departamento.objects.filter(ativo=True),
            "setores": Setor.objects.filter(ativo=True).select_related("departamento"),
            "erros": {},
        })

    def post(self, request, pk):
        ativo = get_object_or_404(Ativo, pk=pk)
        ativo.nome = request.POST.get("nome", ativo.nome).strip()
        ativo.categoria = request.POST.get("categoria", ativo.categoria)
        ativo.tipo = request.POST.get("tipo", ativo.tipo).strip()
        ativo.numero_serie = request.POST.get("numero_serie", "").strip()
        ativo.descricao = request.POST.get("descricao", "").strip()
        ativo.valor_compra = request.POST.get("valor_compra", ativo.valor_compra)
        ativo.taxa_depreciacao = request.POST.get("taxa_depreciacao", ativo.taxa_depreciacao)
        ativo.vida_util_anos = request.POST.get("vida_util_anos", ativo.vida_util_anos)
        ativo.responsavel = request.POST.get("responsavel", "").strip()
        ativo.departamento_id = request.POST.get("departamento") or None
        ativo.setor_id = request.POST.get("setor") or None
        ativo.status = request.POST.get("status", ativo.status)
        ativo.observacao = request.POST.get("observacao", "").strip()
        ativo.save()
        return redirect("web:fin-ativo-detail", pk=pk)


class AtivoBaixaView(PermissionRequiredMixin, View):
    permission_required = "financeiro.change_ativo"

    def post(self, request, pk):
        ativo = get_object_or_404(Ativo, pk=pk)
        if ativo.status == "baixado":
            return redirect("web:fin-ativos")
        from django.utils import timezone
        ativo.status = "baixado"
        ativo.data_baixa = timezone.now().date()
        ativo.motivo_baixa = request.POST.get("motivo", "").strip()
        ativo.save()
        return redirect("web:fin-ativos")


# ---------------------------------------------------------------------------
# Dashboard Financeiro
# ---------------------------------------------------------------------------
class DashboardFinanceiroView(PermissionRequiredMixin, View):
    permission_required = "financeiro.view_lancamento"

    def get(self, request):
        from django.utils import timezone
        from django.db.models import Sum
        from datetime import timedelta

        hoje = timezone.now().date()
        inicio_mes = hoje.replace(day=1)

        # Receitas e despesas do mes (confirmadas)
        lancs_mes = Lancamento.objects.filter(
            status="confirmado", data_pagamento__gte=inicio_mes, data_pagamento__lte=hoje,
        )
        receita_mes = lancs_mes.filter(tipo="receita").aggregate(t=Sum("valor"))["t"] or 0
        despesa_mes = lancs_mes.filter(tipo="despesa").aggregate(t=Sum("valor"))["t"] or 0

        # Saldo total das contas
        saldo_total = sum(c.saldo_atual for c in ContaBancaria.objects.filter(ativo=True))

        # Inadimplencia (cobrancas vencidas)
        cobrancas_vencidas = Cobranca.objects.filter(
            status="pendente", vencimento__lt=hoje,
        ).count()
        valor_inadimplente = Cobranca.objects.filter(
            status="pendente", vencimento__lt=hoje,
        ).aggregate(t=Sum("valor"))["t"] or 0

        # Tributos a vencer (proximos 30 dias)
        tributos_vencer = Tributo.objects.filter(
            status="a_vencer", vencimento__lte=hoje + timedelta(days=30),
        ).aggregate(t=Sum("valor"))["t"] or 0

        # Despesas pendentes
        despesas_pendentes = Despesa.objects.filter(
            status="agendado",
        ).aggregate(t=Sum("valor"))["t"] or 0

        # Folha pendente
        folha_pendente = FolhaPagamento.objects.filter(
            status__in=["calculado", "aprovado"],
        ).aggregate(t=Sum("valor_liquido"))["t"] or 0

        # Patrimonio
        patrimonio_total = Ativo.objects.filter(status="ativo").aggregate(t=Sum("valor_compra"))["t"] or 0

        return render(request, "financeiro/relatorios/dashboard.html", {
            "receita_mes": receita_mes,
            "despesa_mes": despesa_mes,
            "resultado_mes": receita_mes - despesa_mes,
            "saldo_total": saldo_total,
            "cobrancas_vencidas": cobrancas_vencidas,
            "valor_inadimplente": valor_inadimplente,
            "tributos_vencer": tributos_vencer,
            "despesas_pendentes": despesas_pendentes,
            "folha_pendente": folha_pendente,
            "patrimonio_total": patrimonio_total,
            "mes_nome": inicio_mes.strftime("%B %Y").capitalize(),
        })


# ---------------------------------------------------------------------------
# DRE
# ---------------------------------------------------------------------------
class DREView(PermissionRequiredMixin, View):
    permission_required = "financeiro.view_lancamento"

    def get(self, request):
        from django.utils import timezone
        from django.db.models import Sum

        hoje = timezone.now().date()
        mes = int(request.GET.get("mes", hoje.month))
        ano = int(request.GET.get("ano", hoje.year))
        inicio = hoje.replace(year=ano, month=mes, day=1)
        if mes == 12:
            fim = inicio.replace(year=ano + 1, month=1, day=1)
        else:
            fim = inicio.replace(month=mes + 1, day=1)

        # Lancamentos confirmados no periodo (competencia)
        lancs = Lancamento.objects.filter(
            status="confirmado",
            data_competencia__gte=inicio,
            data_competencia__lt=fim,
        )

        # Receitas por categoria
        receitas = lancs.filter(tipo="receita").values(
            "categoria__nome", "categoria__pai__nome"
        ).annotate(total=Sum("valor")).order_by("-total")

        # Despesas por categoria
        despesas = lancs.filter(tipo="despesa").values(
            "categoria__nome", "categoria__pai__nome"
        ).annotate(total=Sum("valor")).order_by("-total")

        receita_bruta = lancs.filter(tipo="receita").aggregate(t=Sum("valor"))["t"] or 0
        despesa_total = lancs.filter(tipo="despesa").aggregate(t=Sum("valor"))["t"] or 0

        # Navegacao
        if mes == 1:
            prev_mes, prev_ano = 12, ano - 1
        else:
            prev_mes, prev_ano = mes - 1, ano
        if mes == 12:
            next_mes, next_ano = 1, ano + 1
        else:
            next_mes, next_ano = mes + 1, ano

        return render(request, "financeiro/relatorios/dre.html", {
            "receitas": receitas,
            "despesas": despesas,
            "receita_bruta": receita_bruta,
            "despesa_total": despesa_total,
            "resultado": receita_bruta - despesa_total,
            "mes": mes, "ano": ano,
            "mes_nome": inicio.strftime("%B %Y").capitalize(),
            "prev_mes": prev_mes, "prev_ano": prev_ano,
            "next_mes": next_mes, "next_ano": next_ano,
        })


# ---------------------------------------------------------------------------
# Fluxo de Caixa
# ---------------------------------------------------------------------------
class FluxoCaixaView(PermissionRequiredMixin, View):
    permission_required = "financeiro.view_lancamento"

    def get(self, request):
        from django.utils import timezone
        from django.db.models import Sum
        from datetime import timedelta

        hoje = timezone.now().date()
        inicio_mes = hoje.replace(day=1)

        # Realizado (confirmados no mes)
        lancs_realizados = Lancamento.objects.filter(
            status="confirmado", data_pagamento__gte=inicio_mes,
        )
        entradas = lancs_realizados.filter(tipo="receita").aggregate(t=Sum("valor"))["t"] or 0
        saidas = lancs_realizados.filter(tipo="despesa").aggregate(t=Sum("valor"))["t"] or 0

        # Projetado 30 dias
        futuro_30 = hoje + timedelta(days=30)
        projetado = Lancamento.objects.filter(
            status__in=["previsto", "pendente"],
            data_vencimento__gte=hoje, data_vencimento__lte=futuro_30,
        )
        entradas_proj = projetado.filter(tipo="receita").aggregate(t=Sum("valor"))["t"] or 0
        saidas_proj = projetado.filter(tipo="despesa").aggregate(t=Sum("valor"))["t"] or 0

        # Cobrancas pendentes
        cobrancas_pendentes = Cobranca.objects.filter(
            status="pendente", vencimento__gte=hoje, vencimento__lte=futuro_30,
        ).select_related("cliente").order_by("vencimento")[:10]

        # Despesas agendadas
        despesas_agendadas = Despesa.objects.filter(
            status="agendado", vencimento__gte=hoje, vencimento__lte=futuro_30,
        ).order_by("vencimento")[:10]

        return render(request, "financeiro/relatorios/fluxo_caixa.html", {
            "entradas": entradas,
            "saidas": saidas,
            "saldo_realizado": entradas - saidas,
            "entradas_proj": entradas_proj,
            "saidas_proj": saidas_proj,
            "saldo_projetado": entradas_proj - saidas_proj,
            "cobrancas_pendentes": cobrancas_pendentes,
            "despesas_agendadas": despesas_agendadas,
        })


# ---------------------------------------------------------------------------
# Fechamento Mensal (exportacao pro contador)
# ---------------------------------------------------------------------------
class FechamentoMensalView(PermissionRequiredMixin, View):
    permission_required = "financeiro.view_lancamento"

    def get(self, request):
        from django.utils import timezone
        hoje = timezone.now().date()
        # Meses disponiveis
        meses = Lancamento.objects.dates("data_competencia", "month", order="DESC")[:12]
        return render(request, "financeiro/relatorios/fechamento.html", {
            "meses": meses,
            "current_mes": request.GET.get("mes", ""),
        })


class FechamentoExportView(PermissionRequiredMixin, View):
    """Exporta dados do mes em CSV, JSON, XML ou PDF."""
    permission_required = "financeiro.view_lancamento"

    def get(self, request):
        from django.utils import timezone
        from datetime import date
        import csv
        import json
        from io import BytesIO, StringIO

        competencia = request.GET.get("mes")
        formato = request.GET.get("formato", "csv")

        if not competencia:
            return redirect("web:fin-fechamento")

        ano, mes_num = int(competencia[:4]), int(competencia[5:7])
        inicio = date(ano, mes_num, 1)
        if mes_num == 12:
            fim = date(ano + 1, 1, 1)
        else:
            fim = date(ano, mes_num + 1, 1)

        # Dados do periodo
        lancamentos = Lancamento.objects.filter(
            data_competencia__gte=inicio, data_competencia__lt=fim,
        ).select_related("categoria", "conta").order_by("data_competencia")

        dados = []
        for l in lancamentos:
            dados.append({
                "data_competencia": str(l.data_competencia),
                "data_vencimento": str(l.data_vencimento),
                "data_pagamento": str(l.data_pagamento) if l.data_pagamento else "",
                "tipo": l.tipo,
                "descricao": l.descricao,
                "categoria": str(l.categoria),
                "valor": str(l.valor),
                "valor_liquido": str(l.valor_liquido),
                "status": l.status,
                "conta": l.conta.nome if l.conta else "",
                "canal": l.get_canal_display(),
            })

        nome_arquivo = f"fechamento_{ano}_{mes_num:02d}"

        if formato == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}.csv"'
            response.write("\ufeff")  # BOM pra Excel
            if dados:
                writer = csv.DictWriter(response, fieldnames=dados[0].keys(), delimiter=";")
                writer.writeheader()
                writer.writerows(dados)
            return response

        elif formato == "json":
            response = HttpResponse(
                json.dumps(dados, indent=2, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
            )
            response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}.json"'
            return response

        elif formato == "xml":
            xml = '<?xml version="1.0" encoding="UTF-8"?>\n<fechamento>\n'
            for d in dados:
                xml += "  <lancamento>\n"
                for k, v in d.items():
                    xml += f"    <{k}>{v}</{k}>\n"
                xml += "  </lancamento>\n"
            xml += "</fechamento>"
            response = HttpResponse(xml, content_type="application/xml; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}.xml"'
            return response

        elif formato == "pdf":
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER
            import os

            buf = BytesIO()
            doc = SimpleDocTemplate(
                buf, pagesize=landscape(A4),
                topMargin=2 * cm, bottomMargin=2 * cm,
                leftMargin=2 * cm, rightMargin=2 * cm,
            )
            styles = getSampleStyleSheet()
            elements = []

            # Logo
            from django.conf import settings as django_settings
            logo_path = os.path.join(django_settings.BASE_DIR, "static", "img", "logo.png")
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=80, height=22)
                elements.append(logo)
                elements.append(Spacer(1, 8))

            title_style = ParagraphStyle(
                "CustomTitle", parent=styles["Title"],
                fontSize=14, textColor=colors.HexColor("#2d4a3e"),
            )
            elements.append(Paragraph(f"Fechamento Mensal — {mes_num:02d}/{ano}", title_style))
            sub_style = ParagraphStyle(
                "Sub", parent=styles["Normal"],
                fontSize=8, textColor=colors.grey, alignment=TA_CENTER,
            )
            elements.append(Paragraph("RUCH Solutions — Prometheus", sub_style))
            elements.append(Spacer(1, 16))

            if dados:
                page_width = landscape(A4)[0] - 4 * cm  # largura total - margens
                headers = ["Data", "Tipo", "Descrição", "Categoria", "Valor", "Status", "Conta"]
                # Proporcoes: data=10%, tipo=7%, descricao=30%, categoria=20%, valor=12%, status=10%, conta=11%
                col_widths = [
                    page_width * 0.10, page_width * 0.07, page_width * 0.30,
                    page_width * 0.20, page_width * 0.12, page_width * 0.10, page_width * 0.11,
                ]
                table_data = [headers]
                def fmt_data(d):
                    if d and len(d) == 10:
                        return f"{d[8:10]}/{d[5:7]}/{d[:4]}"
                    return d

                def fmt_valor(v):
                    from decimal import Decimal
                    num = Decimal(v)
                    inteiro = f"{int(num):,}".replace(",", ".")
                    centavos = f"{abs(num) % 1:.2f}"[2:]
                    return f"R$ {inteiro},{centavos}"

                for d in dados:
                    table_data.append([
                        fmt_data(d["data_competencia"]),
                        d["tipo"].capitalize(),
                        d["descricao"][:50],
                        d["categoria"][:30],
                        fmt_valor(d["valor"]),
                        d["status"].capitalize(),
                        d["conta"][:20],
                    ])
                t = Table(table_data, repeatRows=1, colWidths=col_widths)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d4a3e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]))
                elements.append(t)
            else:
                elements.append(Paragraph("Nenhum lançamento no período.", styles["Normal"]))

            doc.build(elements)
            buf.seek(0)
            response = HttpResponse(buf.read(), content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}.pdf"'
            return response

        return redirect("web:fin-fechamento")
