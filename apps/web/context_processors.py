from apps.accounts.models import Usuario


def navigation(request):
    """Contexto de navegação baseado no perfil do usuário."""
    if not request.user.is_authenticated:
        return {"nav_items": []}

    perfil = request.user.perfil
    items = []

    if perfil == Usuario.Perfil.PARCEIRO:
        items = [
            {"url": "/dashboard/", "icon": "home", "label": "Dashboard"},
            {"url": "/leads/", "icon": "users", "label": "Meus Leads"},
            {"url": "/leads/novo/", "icon": "plus-circle", "label": "Novo Lead"},
            {"url": "/comissoes/", "icon": "dollar-sign", "label": "Comissões"},
        ]
    elif perfil in (Usuario.Perfil.SUPER_ADMIN, Usuario.Perfil.OPERADOR):
        items = [
            {"url": "/dashboard/", "icon": "home", "label": "Dashboard"},
            {"url": "/leads/", "icon": "users", "label": "Leads"},
            {"url": "/leads/pipeline/", "icon": "columns", "label": "Pipeline"},
            {"url": "/leads/calendario/", "icon": "calendar", "label": "Calendário"},
            {"url": "/clientes/", "icon": "briefcase", "label": "Clientes"},
            {"url": "/comissoes/", "icon": "dollar-sign", "label": "Comissões"},
        ]

    if perfil == Usuario.Perfil.SUPER_ADMIN:
        items.append({"url": "/admin/", "icon": "settings", "label": "Admin Django"})

    return {"nav_items": items}
