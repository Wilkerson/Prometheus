def navigation(request):
    """
    Contexto de navegacao baseado nas permissoes reais do usuario.
    Usa user.has_perm() que verifica permissoes diretas + grupos.
    Superuser (is_superuser) ve todos os itens automaticamente.
    """
    if not request.user.is_authenticated:
        return {"nav_items": []}

    user = request.user

    # Todos os itens possiveis com a permissao necessaria
    # permission=None significa que qualquer usuario autenticado ve
    all_items = [
        {
            "url": "/dashboard/",
            "icon": "home",
            "label": "Dashboard",
            "permission": None,
        },
        {
            "url": "/leads/",
            "icon": "users",
            "label": "Leads",
            "permission": "crm.view_lead",
        },
        {
            "url": "/leads/novo/",
            "icon": "plus-circle",
            "label": "Novo Lead",
            "permission": "crm.add_lead",
        },
        {
            "url": "/leads/pipeline/",
            "icon": "columns",
            "label": "Pipeline",
            "permission": "crm.change_lead",
        },
        {
            "url": "/leads/calendario/",
            "icon": "calendar",
            "label": "Calendario",
            "permission": "crm.view_lead",
        },
        {
            "url": "/clientes/",
            "icon": "briefcase",
            "label": "Clientes",
            "permission": "crm.view_cliente",
        },
        {
            "url": "/comissoes/",
            "icon": "dollar-sign",
            "label": "Comissoes",
            "permission": "comissoes.view_comissao",
        },
    ]

    # Filtra itens baseado nas permissoes do usuario
    items = []
    for item in all_items:
        perm = item["permission"]
        if perm is None or user.has_perm(perm):
            items.append({
                "url": item["url"],
                "icon": item["icon"],
                "label": item["label"],
            })

    # Admin Django — so superuser
    if user.is_superuser:
        items.append({"url": "/admin/", "icon": "settings", "label": "Admin Django"})

    return {"nav_items": items}
