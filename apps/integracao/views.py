from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.crm.models import Lead, LeadHistorico

from .authentication import APIKeyAuthentication
from .serializers import ClienteIntegracaoSerializer, LeadCallbackSerializer


class ClienteIntegracaoCreateView(generics.CreateAPIView):
    """POST /api/v1/integracao/cliente/ — cria cliente via API Key."""

    serializer_class = ClienteIntegracaoSerializer
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        serializer.save()


class LeadCallbackView(APIView):
    """
    POST /api/v1/integracao/lead/status/
    Callback do sistema externo para atualizar status do lead.
    Usado quando o sistema externo conclui ou rejeita a implantação.
    Autenticação via X-API-Key.
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LeadCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lead_id = serializer.validated_data["lead_id"]
        novo_status = serializer.validated_data["status"]
        observacao = serializer.validated_data.get("observacao", "")

        try:
            lead = Lead.objects.get(id=lead_id)
        except Lead.DoesNotExist:
            return Response(
                {"detail": f"Lead {lead_id} não encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if lead.status != Lead.Status.EM_PROCESSAMENTO:
            return Response(
                {"detail": f"Lead não está em processamento. Status atual: {lead.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        status_anterior = lead.status
        lead.status = novo_status
        lead.save(update_fields=["status", "atualizado_em"])

        LeadHistorico.objects.create(
            lead=lead,
            status_anterior=status_anterior,
            status_novo=novo_status,
            usuario=None,
            observacao=observacao or "Atualizado via sistema externo",
        )

        return Response({
            "detail": f"Lead {lead_id} atualizada para '{novo_status}'.",
            "lead_id": lead.id,
            "status": lead.status,
        })
