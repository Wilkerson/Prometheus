from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Comissao
from .serializers import ComissaoSerializer


class ComissaoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Comissoes: parceiro ve apenas as suas, demais veem todas."""

    serializer_class = ComissaoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "parceiro"]
    ordering_fields = ["gerado_em", "valor_comissao"]

    def get_queryset(self):
        user = self.request.user
        qs = Comissao.objects.select_related("parceiro", "cliente")

        if user.is_parceiro:
            return qs.filter(parceiro=user.parceiro)
        return qs
