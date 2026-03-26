def navigation(request):
    """Navegacao baseada nas permissoes reais do usuario."""
    if not request.user.is_authenticated:
        return {"nav_items": []}

    user = request.user

    all_items = [
        {"url": "/dashboard/", "label": "Dashboard", "permission": None, "section": "menu"},
        {"url": "/clientes/", "label": "Clientes", "permission": "crm.view_cliente", "section": "menu"},
        {"url": "/clientes/pipeline/", "label": "Pipeline", "permission": "crm.change_cliente", "section": "menu"},
        {"url": "/clientes/calendario/", "label": "Calendario", "permission": "crm.view_cliente", "section": "menu"},
        {"url": "/produtos/", "label": "Produtos", "permission": "crm.view_produto", "section": "menu"},
        {"url": "/planos/", "label": "Planos", "permission": "crm.view_plano", "section": "menu"},
        {"url": "/comissoes/", "label": "Comissoes", "permission": "comissoes.view_comissao", "section": "menu"},
        # Administracao
        {"url": "/usuarios/", "label": "Usuarios", "permission": "accounts.view_usuario", "section": "admin"},
        {"url": "/parceiros/", "label": "Parceiros", "permission": "crm.view_entidadeparceira", "section": "admin"},
        {"url": "/tokens/", "label": "Tokens API", "permission": "integracao.view_tokenintegracao", "section": "admin"},
    ]

    menu_items = []
    admin_items = []

    for item in all_items:
        perm = item["permission"]
        entry = {"url": item["url"], "label": item["label"]}
        if perm is None or user.has_perm(perm):
            if item["section"] == "menu":
                menu_items.append(entry)
            else:
                admin_items.append(entry)

    if user.is_superuser:
        admin_items.append({"url": "/admin/", "label": "Admin Django"})

    return {
        "nav_items": menu_items,
        "admin_items": admin_items,
    }
