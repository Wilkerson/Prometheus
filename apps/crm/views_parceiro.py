from django.db.models import Count, Q, Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, mixins

from apps.accounts.permissions import IsParceiro

from .models import Lead
from .serializers import LeadCreateParceiroSerializer, LeadListSerializer


class ParceiroLeadViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    """
    Painel do parceiro — leads:
    - GET  /api/v1/parceiro/leads/         → lista seus leads
    - POST /api/v1/parceiro/leads/         → cadastra novo lead
    - GET  /api/v1/parceiro/leads/{id}/    → detalhe de um lead
    """

    permission_classes = [IsAuthenticated, IsParceiro]
    filterset_fields = ["status", "produto_interesse"]
    search_fields = ["nome", "email"]
    ordering_fields = ["criado_em", "status"]

    def get_serializer_class(self):
        if self.action == "create":
            return LeadCreateParceiroSerializer
        return LeadListSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "parceiro"):
            return Lead.objects.filter(parceiro=user.parceiro).select_related("parceiro", "operador")
        return Lead.objects.none()

    def perform_create(self, serializer):
        serializer.save(parceiro=self.request.user.parceiro)


class ParceiroDashboardView(APIView):
    """
    GET /api/v1/parceiro/dashboard/
    Resumo do painel do parceiro: totais de leads por status e comissões.
    """

    permission_classes = [IsAuthenticated, IsParceiro]

    def get(self, request):
        user = request.user
        if not hasattr(user, "parceiro"):
            return Response(
                {"detail": "Usuário não vinculado a uma entidade parceira."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parceiro = user.parceiro

        # Contagem de leads por status
        leads_stats = (
            Lead.objects.filter(parceiro=parceiro)
            .values("status")
            .annotate(total=Count("id"))
        )
        leads_por_status = {item["status"]: item["total"] for item in leads_stats}
        total_leads = sum(leads_por_status.values())

        # Comissões
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
            "leads": {
                "total": total_leads,
                "por_status": {
                    "recebida": leads_por_status.get("recebida", 0),
                    "em_analise": leads_por_status.get("em_analise", 0),
                    "em_processamento": leads_por_status.get("em_processamento", 0),
                    "concluida": leads_por_status.get("concluida", 0),
                    "perdida": leads_por_status.get("perdida", 0),
                },
            },
            "comissoes": {
                "quantidade": comissoes_stats["quantidade"],
                "total_pendente": str(comissoes_stats["total_pendente"] or 0),
                "total_pago": str(comissoes_stats["total_pago"] or 0),
            },
        })
