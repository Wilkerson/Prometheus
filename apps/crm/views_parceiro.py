from django.db.models import Count, Q, Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, mixins

from apps.accounts.permissions import IsParceiro

from .models import Cliente
from .serializers import ClienteCreateParceiroSerializer, ClienteListSerializer


class ParceiroClienteViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    """
    Painel do parceiro — clientes:
    - GET  /api/v1/parceiro/clientes/         -> lista seus clientes
    - POST /api/v1/parceiro/clientes/         -> cadastra novo cliente
    - GET  /api/v1/parceiro/clientes/{id}/    -> detalhe de um cliente
    """

    permission_classes = [IsAuthenticated, IsParceiro]
    filterset_fields = ["status"]
    search_fields = ["nome", "cnpj", "email"]
    ordering_fields = ["criado_em", "status"]

    def get_serializer_class(self):
        if self.action == "create":
            return ClienteCreateParceiroSerializer
        return ClienteListSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "parceiro"):
            return Cliente.objects.filter(parceiro=user.parceiro).select_related("parceiro", "operador")
        return Cliente.objects.none()

    def perform_create(self, serializer):
        serializer.save(parceiro=self.request.user.parceiro)


class ParceiroDashboardView(APIView):
    """GET /api/v1/parceiro/dashboard/"""

    permission_classes = [IsAuthenticated, IsParceiro]

    def get(self, request):
        user = request.user
        if not hasattr(user, "parceiro"):
            return Response(
                {"detail": "Usuario nao vinculado a uma entidade parceira."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parceiro = user.parceiro

        stats = (
            Cliente.objects.filter(parceiro=parceiro)
            .values("status")
            .annotate(total=Count("id"))
        )
        por_status = {item["status"]: item["total"] for item in stats}
        total = sum(por_status.values())

        from apps.comissoes.models import Comissao

        comissoes_stats = Comissao.objects.filter(parceiro=parceiro).aggregate(
            total_pendente=Sum("valor_comissao", filter=Q(status=Comissao.Status.PENDENTE)),
            total_pago=Sum("valor_comissao", filter=Q(status=Comissao.Status.PAGO)),
            quantidade=Count("id"),
        )

        return Response({
            "parceiro": {
                "id": parceiro.id,
                "nome_entidade": parceiro.nome_entidade,
                "percentual_comissao": str(parceiro.percentual_comissao),
            },
            "clientes": {
                "total": total,
                "por_status": {
                    "recebida": por_status.get("recebida", 0),
                    "em_analise": por_status.get("em_analise", 0),
                    "em_processamento": por_status.get("em_processamento", 0),
                    "concluida": por_status.get("concluida", 0),
                    "perdida": por_status.get("perdida", 0),
                },
            },
            "comissoes": {
                "quantidade": comissoes_stats["quantidade"],
                "total_pendente": str(comissoes_stats["total_pendente"] or 0),
                "total_pago": str(comissoes_stats["total_pago"] or 0),
            },
        })
