from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import Usuario
from apps.accounts.permissions import IsOperador, IsOwnerParceiro, IsSuperAdmin

from .models import Cliente, EntidadeParceira, Lead, ProdutoContratado
from .serializers import (
    ClienteSerializer,
    EntidadeParceiraSerializer,
    LeadSerializer,
    ProdutoContratadoSerializer,
)


class EntidadeParceiraViewSet(viewsets.ModelViewSet):
    """CRUD de entidades parceiras — somente Super Admin."""

    queryset = EntidadeParceira.objects.select_related("usuario")
    serializer_class = EntidadeParceiraSerializer
    permission_classes = [IsSuperAdmin]


class LeadViewSet(viewsets.ModelViewSet):
    """
    Leads:
    - Super Admin / Operador: veem todos
    - Parceiro: vê e cria apenas os seus
    """

    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated, IsOwnerParceiro]
    filterset_fields = ["status", "produto_interesse", "parceiro"]
    search_fields = ["nome", "email"]
    ordering_fields = ["criado_em", "status"]

    def get_queryset(self):
        user = self.request.user
        qs = Lead.objects.select_related("parceiro", "operador")

        if user.perfil == Usuario.Perfil.PARCEIRO and hasattr(user, "parceiro"):
            return qs.filter(parceiro=user.parceiro)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if user.perfil == Usuario.Perfil.PARCEIRO and hasattr(user, "parceiro"):
            serializer.save(parceiro=user.parceiro)
        else:
            serializer.save()


class ClienteViewSet(viewsets.ModelViewSet):
    """Clientes — Operadores e Super Admin."""

    queryset = Cliente.objects.prefetch_related("produtos")
    serializer_class = ClienteSerializer
    permission_classes = [IsOperador]
    filterset_fields = ["ativo"]
    search_fields = ["nome", "documento", "email"]


class ProdutoContratadoViewSet(viewsets.ModelViewSet):
    """Produtos contratados — Operadores e Super Admin."""

    queryset = ProdutoContratado.objects.select_related("cliente")
    serializer_class = ProdutoContratadoSerializer
    permission_classes = [IsOperador]
    filterset_fields = ["status", "produto"]
