def navigation(request):
    """Navegacao baseada nas permissoes reais do usuario."""
    if not request.user.is_authenticated:
        return {"nav_items": []}

    user = request.user

    all_items = [
        {"url": "/dashboard/", "icon": "home", "label": "Dashboard", "permission": None},
        {"url": "/clientes/", "icon": "users", "label": "Clientes", "permission": "crm.view_cliente"},
        {"url": "/clientes/novo/", "icon": "plus-circle", "label": "Novo Cliente", "permission": "crm.add_cliente"},
        {"url": "/clientes/pipeline/", "icon": "columns", "label": "Pipeline", "permission": "crm.change_cliente"},
        {"url": "/clientes/calendario/", "icon": "calendar", "label": "Calendario", "permission": "crm.view_cliente"},
        {"url": "/comissoes/", "icon": "dollar-sign", "label": "Comissoes", "permission": "comissoes.view_comissao"},
    ]

    items = []
    for item in all_items:
        perm = item["permission"]
        if perm is None or user.has_perm(perm):
            items.append({"url": item["url"], "icon": item["icon"], "label": item["label"]})

    if user.is_superuser:
        items.append({"url": "/admin/", "icon": "settings", "label": "Admin Django"})

    return {"nav_items": items}
