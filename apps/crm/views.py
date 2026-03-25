from rest_framework import viewsets

from .models import Cliente, EntidadeParceira, Lead, ProdutoContratado
from .serializers import (
    ClienteSerializer,
    EntidadeParceiraSerializer,
    LeadSerializer,
    ProdutoContratadoSerializer,
)


class EntidadeParceiraViewSet(viewsets.ModelViewSet):
    queryset = EntidadeParceira.objects.select_related("usuario")
    serializer_class = EntidadeParceiraSerializer


class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.select_related("parceiro", "operador")
    serializer_class = LeadSerializer
    filterset_fields = ["status", "produto_interesse", "parceiro"]
    search_fields = ["nome", "email"]
    ordering_fields = ["criado_em", "status"]


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.prefetch_related("produtos")
    serializer_class = ClienteSerializer
    filterset_fields = ["ativo"]
    search_fields = ["nome", "documento", "email"]


class ProdutoContratadoViewSet(viewsets.ModelViewSet):
    queryset = ProdutoContratado.objects.select_related("cliente")
    serializer_class = ProdutoContratadoSerializer
    filterset_fields = ["status", "produto"]
