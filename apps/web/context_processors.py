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
    groups_def = [
        {
            "key": "comercial",
            "label": "Comercial",
            "items": [
                {"url": "/clientes/", "label": "Clientes", "permission": "crm.view_cliente"},
                {"url": "/clientes/pipeline/", "label": "Pipeline", "permission": "crm.change_cliente"},
                {"url": "/clientes/calendario/", "label": "Calendario", "permission": "crm.view_cliente"},
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
                {"url": "/financeiro/contas/", "label": "Contas Bancárias", "permission": "financeiro.view_contabancaria"},
            ],
        },
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
            "key": "admin",
            "label": "Administração",
            "items": [
                {"url": "/usuarios/", "label": "Usuarios", "permission": "accounts.view_usuario"},
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

    return {
        "nav_standalone": nav_standalone,
        "nav_groups": nav_groups,
        "nav_placeholders": placeholders,
        "notif_count": notif_count,
        "notif_recentes": notif_recentes,
    }
