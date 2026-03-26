def navigation(request):
    """Navegacao baseada nas permissoes reais do usuario."""
    if not request.user.is_authenticated:
        return {"nav_items": []}

    user = request.user

    all_items = [
        {"url": "/dashboard/", "label": "Dashboard", "permission": None},
        {"url": "/clientes/", "label": "Clientes", "permission": "crm.view_cliente"},
        {"url": "/clientes/pipeline/", "label": "Pipeline", "permission": "crm.change_cliente"},
        {"url": "/clientes/calendario/", "label": "Calendario", "permission": "crm.view_cliente"},
        {"url": "/produtos/", "label": "Produtos", "permission": "crm.view_produto"},
        {"url": "/planos/", "label": "Planos", "permission": "crm.view_plano"},
        {"url": "/comissoes/", "label": "Comissoes", "permission": "comissoes.view_comissao"},
    ]

    items = []
    for item in all_items:
        perm = item["permission"]
        if perm is None or user.has_perm(perm):
            items.append({"url": item["url"], "label": item["label"]})

    if user.is_superuser:
        items.append({"url": "/admin/", "label": "Admin Django"})

    return {"nav_items": items}
