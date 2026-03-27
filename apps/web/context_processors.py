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

    # Grupos colapsaveis
    groups_def = [
        {
            "key": "clientes",
            "label": "Clientes",
            "items": [
                {"url": "/clientes/", "label": "Listagem", "permission": "crm.view_cliente"},
                {"url": "/clientes/pipeline/", "label": "Pipeline", "permission": "crm.change_cliente"},
                {"url": "/clientes/calendario/", "label": "Calendario", "permission": "crm.view_cliente"},
                {"url": "/clientes/novo/", "label": "+ Novo", "permission": "crm.add_cliente"},
            ],
        },
        {
            "key": "catalogo",
            "label": "Catalogo",
            "items": [
                {"url": "/produtos/", "label": "Produtos", "permission": "crm.view_produto"},
                {"url": "/planos/", "label": "Planos", "permission": "crm.view_plano"},
            ],
        },
        {
            "key": "financeiro",
            "label": "Financeiro",
            "items": [
                {"url": "/comissoes/", "label": "Comissoes", "permission": "comissoes.view_comissao"},
            ],
        },
        {
            "key": "rh",
            "label": "RH / Pessoas",
            "items": [
                {"url": "/rh/colaboradores/", "label": "Colaboradores", "permission": "rh.view_colaborador"},
                {"url": "/rh/cargos/", "label": "Cargos", "permission": "rh.view_cargo"},
                {"url": "/rh/departamentos/", "label": "Departamentos", "permission": "rh.view_departamento"},
            ],
        },
        {
            "key": "admin",
            "label": "Administracao",
            "items": [
                {"url": "/usuarios/", "label": "Usuarios", "permission": "accounts.view_usuario"},
                {"url": "/parceiros/", "label": "Parceiros", "permission": "crm.view_entidadeparceira"},
                {"url": "/tokens/", "label": "Tokens API", "permission": "integracao.view_tokenintegracao"},
            ],
        },
    ]

    # Adiciona Grupos (so superuser)
    if user.is_superuser:
        groups_def[-1]["items"].append({"url": "/grupos/", "label": "Grupos", "permission": None})
        groups_def[-1]["items"].append({"url": "/admin/", "label": "Admin Django", "permission": None})

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
        "notif_count": notif_count,
        "notif_recentes": notif_recentes,
    }
