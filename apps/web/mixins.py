from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


def is_htmx(request):
    """Verifica se a requisicao veio do HTMX."""
    return request.headers.get("HX-Request") == "true"


class HtmxMixin:
    """Retorna template parcial se for requisicao HTMX."""

    partial_template_name = None

    def get_template_names(self):
        if is_htmx(self.request) and self.partial_template_name:
            return [self.partial_template_name]
        return super().get_template_names()


class PermissionMixin(PermissionRequiredMixin):
    """
    Mixin que usa o sistema de permissoes do Django (diretas + grupos).
    Superuser passa automaticamente. Define permission_required na view.
    """
    pass
