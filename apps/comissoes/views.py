from rest_framework import mixins, viewsets

from .models import Comissao
from .serializers import ComissaoSerializer


class ComissaoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Comissões — somente leitura (listagem e detalhe)."""

    queryset = Comissao.objects.select_related("parceiro", "venda")
    serializer_class = ComissaoSerializer
    filterset_fields = ["status", "parceiro"]
    ordering_fields = ["gerado_em", "valor_comissao"]
