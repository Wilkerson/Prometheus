from rest_framework.permissions import BasePermission

from .models import Usuario


class IsSuperAdmin(BasePermission):
    """Acesso exclusivo para Super Admin."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.perfil == Usuario.Perfil.SUPER_ADMIN
        )


class IsOperador(BasePermission):
    """Acesso para Operador Interno ou superior."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.perfil in (
                Usuario.Perfil.SUPER_ADMIN,
                Usuario.Perfil.OPERADOR,
            )
        )


class IsParceiro(BasePermission):
    """Acesso para Entidade Parceira."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.perfil == Usuario.Perfil.PARCEIRO
        )


class IsParceiroOrAdmin(BasePermission):
    """Acesso para Parceiro, Operador ou Super Admin."""

    def has_permission(self, request, view):
        return request.user.is_authenticated


class IsOwnerParceiro(BasePermission):
    """Parceiro só acessa seus próprios recursos."""

    def has_object_permission(self, request, view, obj):
        if request.user.perfil in (
            Usuario.Perfil.SUPER_ADMIN,
            Usuario.Perfil.OPERADOR,
        ):
            return True

        if hasattr(obj, "parceiro"):
            return (
                hasattr(request.user, "parceiro")
                and obj.parceiro == request.user.parceiro
            )
        return False
