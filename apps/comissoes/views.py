from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import Usuario

from .models import Comissao
from .serializers import ComissaoSerializer


class ComissaoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Comissões (somente leitura):
    - Super Admin / Operador: veem todas
    - Parceiro: vê apenas as suas
    """

    serializer_class = ComissaoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "parceiro"]
    ordering_fields = ["gerado_em", "valor_comissao"]

    def get_queryset(self):
        user = self.request.user
        qs = Comissao.objects.select_related("parceiro", "venda")

        if user.perfil == Usuario.Perfil.PARCEIRO and hasattr(user, "parceiro"):
            return qs.filter(parceiro=user.parceiro)
        return qs
