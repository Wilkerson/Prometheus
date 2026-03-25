from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from apps.accounts.models import Usuario


def is_htmx(request):
    """Verifica se a requisição veio do HTMX."""
    return request.headers.get("HX-Request") == "true"


class HtmxMixin:
    """Retorna template parcial se for requisição HTMX."""

    partial_template_name = None

    def get_template_names(self):
        if is_htmx(self.request) and self.partial_template_name:
            return [self.partial_template_name]
        return super().get_template_names()


class SuperAdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.perfil != Usuario.Perfil.SUPER_ADMIN:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class OperadorRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.perfil not in (Usuario.Perfil.SUPER_ADMIN, Usuario.Perfil.OPERADOR):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ParceiroRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.perfil != Usuario.Perfil.PARCEIRO:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
