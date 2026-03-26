from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """Acesso exclusivo para superusuario."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superuser


class IsParceiro(BasePermission):
    """Acesso para usuario com EntidadeParceira vinculada."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_parceiro


class IsOwnerParceiro(BasePermission):
    """Parceiro so acessa seus proprios recursos."""

    def has_object_permission(self, request, view, obj):
        if not request.user.is_parceiro:
            return True

        if hasattr(obj, "parceiro"):
            return (
                hasattr(request.user, "parceiro")
                and obj.parceiro == request.user.parceiro
            )
        return False
