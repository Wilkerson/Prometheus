from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Usuario
from apps.accounts.permissions import IsOperador, IsOwnerParceiro, IsSuperAdmin

from .models import Cliente, EntidadeParceira, Lead, ProdutoContratado
from .serializers import (
    ClienteSerializer,
    EntidadeParceiraSerializer,
    LeadSerializer,
    LeadStatusSerializer,
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
    - Super Admin / Operador: veem todos, podem alterar status
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

    @action(detail=True, methods=["patch"], url_path="status", permission_classes=[IsOperador])
    def update_status(self, request, pk=None):
        """PATCH /api/v1/leads/{id}/status/ — atualiza status (admin/operador)."""
        lead = self.get_object()
        serializer = LeadStatusSerializer(lead, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(LeadSerializer(lead).data)

    @action(detail=True, methods=["post"], url_path="converter", permission_classes=[IsOperador])
    def converter_em_cliente(self, request, pk=None):
        """POST /api/v1/leads/{id}/converter/ — converte lead em cliente."""
        lead = self.get_object()

        if hasattr(lead, "cliente"):
            return Response(
                {"detail": "Este lead já foi convertido em cliente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if lead.status != Lead.Status.VENDIDO:
            return Response(
                {"detail": "Somente leads com status 'vendido' podem ser convertidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cnpj = request.data.get("cnpj", "")
        if not cnpj:
            return Response(
                {"detail": "O campo 'cnpj' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cliente = Cliente.objects.create(
            lead=lead,
            nome=lead.nome,
            cnpj=cnpj,
            documento=request.data.get("documento", ""),
            email=lead.email,
            telefone=lead.telefone,
        )
        return Response(ClienteSerializer(cliente).data, status=status.HTTP_201_CREATED)


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
