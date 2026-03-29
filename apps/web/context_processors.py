def navigation(request):
    """Navegacao em grupos colapsaveis, baseada nas permissoes do usuario."""
    if not request.user.is_authenticated:
        return {"nav_groups": [], "nav_standalone": []}

    user = request.user
    path = request.path

    # Itens standalone (sem grupo)
    standalone = [
        {"url": "/dashboard/", "label": "Dashboard", "permission": None},
    ]

    # Grupos colapsaveis — departamentos como menus da sidebar
    # Ordem: RH → Comercial → Financeiro → Administração
    groups_def = [
        {
            "key": "rh",
            "label": "RH / Pessoas",
            "items": [
                {"url": "/rh/colaboradores/", "label": "Colaboradores", "permission": "rh.view_colaborador"},
                {"url": "/rh/documentos/", "label": "Documentos", "permission": "rh.view_documentocolaborador"},
                {"url": "/rh/onboarding/templates/", "label": "Onboarding", "permission": "rh.view_onboardingtemplate"},
                {"url": "/rh/ausencias/", "label": "Férias / Ausências", "permission": "rh.view_solicitacaoausencia"},
                {"url": "/rh/treinamentos/", "label": "Treinamentos", "permission": "rh.view_treinamento"},
                {"url": "/rh/metas/", "label": "Metas", "permission": "rh.view_cicloavaliacao"},
                {"url": "/rh/pdi/", "label": "PDI", "permission": "rh.view_pdi"},
                {"url": "/rh/enps/", "label": "eNPS", "permission": "rh.view_pesquisaenps"},
                {"url": "/rh/relatorios/", "label": "Relatórios", "permission": "rh.view_colaborador"},
                {"url": "/rh/cargos/", "label": "Cargos", "permission": "rh.view_cargo"},
                {"url": "/rh/setores/", "label": "Setores", "permission": "rh.view_setor"},
            ],
        },
        {
            "key": "comercial",
            "label": "Comercial",
            "items": [
                {"url": "/clientes/", "label": "Clientes", "permission": "crm.view_cliente"},
                {"url": "/clientes/pipeline/", "label": "Pipeline", "permission": "crm.change_cliente"},
                {"url": "/clientes/calendario/", "label": "Calendário", "permission": "crm.view_cliente"},
                {"url": "/clientes/novo/", "label": "+ Novo Cliente", "permission": "crm.add_cliente"},
                {"url": "/produtos/", "label": "Produtos", "permission": "crm.view_produto"},
                {"url": "/planos/", "label": "Planos", "permission": "crm.view_plano"},
            ],
        },
        {
            "key": "financeiro",
            "label": "Financeiro",
            "items": [
                {"url": "/financeiro/lancamentos/", "label": "Lançamentos", "permission": "financeiro.view_lancamento"},
                {"url": "/financeiro/cobrancas/", "label": "Contas a Receber", "permission": "financeiro.view_cobranca"},
                {"url": "/financeiro/despesas/", "label": "Contas a Pagar", "permission": "financeiro.view_despesa"},
                {"url": "/financeiro/nfs/", "label": "Notas Fiscais", "permission": "financeiro.view_notafiscal"},
                {"url": "/financeiro/folha/", "label": "Folha", "permission": "financeiro.view_folhapagamento"},
                {"url": "/financeiro/tributos/", "label": "Tributos", "permission": "financeiro.view_tributo"},
                {"url": "/financeiro/ativos/", "label": "Patrimônio", "permission": "financeiro.view_ativo"},
                {"url": "/financeiro/asaas/", "label": "Asaas", "permission": "financeiro.view_clienteasaas"},
                {"url": "/financeiro/dashboard/", "label": "Relatórios", "permission": "financeiro.view_lancamento"},
                {"url": "/financeiro/contas/", "label": "Contas Bancárias", "permission": "financeiro.view_contabancaria"},
            ],
        },
        {
            "key": "admin",
            "label": "Administração",
            "items": [
                {"url": "/usuarios/", "label": "Usuários", "permission": "accounts.view_usuario"},
                {"url": "/parceiros/", "label": "Parceiros", "permission": "crm.view_entidadeparceira"},
                {"url": "/tokens/", "label": "Tokens API", "permission": "integracao.view_tokenintegracao"},
            ],
        },
    ]

    # Adiciona Grupos e Admin Django (so superuser)
    if user.is_superuser:
        groups_def[-1]["items"].append({"url": "/grupos/", "label": "Grupos", "permission": None})
        groups_def[-1]["items"].append({"url": "/admin/", "label": "Admin Django", "permission": None})

    # Placeholders de departamentos futuros
    placeholders = [
        {"label": "Marketing", "sublabel": "em breve"},
        {"label": "Tecnologia", "sublabel": "em breve"},
        {"label": "Jurídico", "sublabel": "em breve"},
        {"label": "Operações", "sublabel": "em breve"},
        {"label": "Produto", "sublabel": "em breve"},
    ]

    # Filtra itens por permissao e detecta grupo ativo
    nav_standalone = []
    for item in standalone:
        perm = item["permission"]
        if perm is None or user.has_perm(perm):
            nav_standalone.append({
                "url": item["url"],
                "label": item["label"],
                "active": path == item["url"],
            })

    nav_groups = []
    for group in groups_def:
        visible_items = []
        group_active = False
        for item in group["items"]:
            perm = item["permission"]
            if perm is None or user.has_perm(perm):
                is_active = path == item["url"]
                if is_active or path.startswith(item["url"]) and item["url"] != "/":
                    group_active = True
                visible_items.append({
                    "url": item["url"],
                    "label": item["label"],
                    "active": is_active,
                })
        if visible_items:
            nav_groups.append({
                "key": group["key"],
                "label": group["label"],
                "items": visible_items,
                "active": group_active,
            })

    # Notificacoes nao-lidas
    from apps.crm.models import Notificacao
    notif_nao_lidas = Notificacao.objects.filter(destinatario=user, lida=False)
    notif_count = notif_nao_lidas.count()
    notif_recentes = notif_nao_lidas[:5]

    any_group_active = any(g["active"] for g in nav_groups)

    # Breadcrumbs
    breadcrumbs = _build_breadcrumbs(path)

    return {
        "nav_standalone": nav_standalone,
        "nav_groups": nav_groups,
        "any_group_active": any_group_active,
        "nav_placeholders": placeholders,
        "notif_count": notif_count,
        "notif_recentes": notif_recentes,
        "breadcrumbs": breadcrumbs,
    }


# Mapa de segmentos de URL para labels de breadcrumb
BREADCRUMB_LABELS = {
    "dashboard": ("Dashboard", "/dashboard/"),
    # Comercial
    "clientes": ("Clientes", "/clientes/"),
    "pipeline": ("Pipeline", "/clientes/pipeline/"),
    "calendario": ("Calendário", "/clientes/calendario/"),
    "produtos": ("Produtos", "/produtos/"),
    "planos": ("Planos", "/planos/"),
    # Financeiro
    "financeiro": ("Financeiro", "/financeiro/lancamentos/"),
    "lancamentos": ("Lançamentos", "/financeiro/lancamentos/"),
    "cobrancas": ("Cobranças", "/financeiro/cobrancas/"),
    "despesas": ("Despesas", "/financeiro/despesas/"),
    "nfs": ("Notas Fiscais", "/financeiro/nfs/"),
    "folha": ("Folha", "/financeiro/folha/"),
    "tributos": ("Tributos", "/financeiro/tributos/"),
    "ativos": ("Patrimônio", "/financeiro/ativos/"),
    "contas": ("Contas Bancárias", "/financeiro/contas/"),
    "asaas": ("Asaas", "/financeiro/asaas/"),
    "assinaturas": ("Assinaturas", "/financeiro/asaas/assinaturas/"),
    "webhook-log": ("Webhook Log", "/financeiro/asaas/webhook-log/"),
    "dre": ("DRE", "/financeiro/dre/"),
    "fluxo-caixa": ("Fluxo de Caixa", "/financeiro/fluxo-caixa/"),
    "fechamento": ("Fechamento", "/financeiro/fechamento/"),
    # RH
    "rh": ("RH", "/rh/colaboradores/"),
    "colaboradores": ("Colaboradores", "/rh/colaboradores/"),
    "documentos": ("Documentos", "/rh/documentos/"),
    "onboarding": ("Onboarding", "/rh/onboarding/templates/"),
    "ausencias": ("Ausências", "/rh/ausencias/"),
    "treinamentos": ("Treinamentos", "/rh/treinamentos/"),
    "metas": ("Metas", "/rh/metas/"),
    "pdi": ("PDI", "/rh/pdi/"),
    "enps": ("eNPS", "/rh/enps/"),
    "relatorios": ("Relatórios", None),
    "cargos": ("Cargos", "/rh/cargos/"),
    "setores": ("Setores", "/rh/setores/"),
    # Administracao
    "usuarios": ("Usuários", "/usuarios/"),
    "parceiros": ("Parceiros", "/parceiros/"),
    "tokens": ("Tokens API", "/tokens/"),
    "grupos": ("Grupos", "/grupos/"),
    # Acoes
    "novo": ("Novo", None),
    "editar": ("Editar", None),
    "excluir": ("Excluir", None),
    "configuracao": ("Configuração", None),
    "exportar": ("Exportar", None),
    "iniciar": ("Iniciar", None),
    "responder": ("Responder", None),
    "templates": ("Templates", None),
    "criar-acesso": ("Criar Acesso", None),
    "aprovar-todos": ("Aprovar Todos", None),
    "gerar": ("Gerar", None),
    "sincronizar": ("Sincronizar", None),
}

# Mapa de prefixo de URL para departamento
BREADCRUMB_DEPTOS = {
    "/clientes/": "Comercial",
    "/produtos/": "Comercial",
    "/planos/": "Comercial",
    "/financeiro/": "Financeiro",
    "/rh/": "RH / Pessoas",
    "/usuarios/": "Administração",
    "/parceiros/": "Administração",
    "/tokens/": "Administração",
    "/grupos/": "Administração",
}


def _build_breadcrumbs(path):
    """Gera breadcrumbs a partir do URL path."""
    if path == "/dashboard/" or path == "/":
        return [{"label": "Dashboard", "url": None}]

    crumbs = [{"label": "Dashboard", "url": "/dashboard/"}]

    # Adicionar departamento
    for prefix, depto in BREADCRUMB_DEPTOS.items():
        if path.startswith(prefix):
            crumbs.append({"label": depto, "url": None})
            break

    # Quebrar URL em segmentos
    segments = [s for s in path.strip("/").split("/") if s]

    for i, seg in enumerate(segments):
        # Pular numeros (PKs) — serao substituidos pelo page_title
        if seg.isdigit():
            continue

        if seg in BREADCRUMB_LABELS:
            label, url = BREADCRUMB_LABELS[seg]
            # Ultimo segmento nao tem link
            is_last = (i == len(segments) - 1) or (
                i == len(segments) - 2 and segments[-1].isdigit()
            )
            crumbs.append({
                "label": label,
                "url": None if is_last else url,
            })

    return crumbs
