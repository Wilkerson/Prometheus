from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.crm.models import Cliente, ClienteHistorico

from .authentication import APIKeyAuthentication
from .serializers import ClienteCallbackSerializer, ClienteIntegracaoSerializer


class ClienteIntegracaoCreateView(generics.CreateAPIView):
    """POST /api/v1/integracao/cliente/ — cria cliente via API Key."""

    serializer_class = ClienteIntegracaoSerializer
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        serializer.save()


class ClienteCallbackView(APIView):
    """
    POST /api/v1/integracao/cliente/status/
    Callback do sistema externo para atualizar status do cliente.
    Autenticacao via X-API-Key.
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ClienteCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cliente_id = serializer.validated_data["cliente_id"]
        novo_status = serializer.validated_data["status"]
        observacao = serializer.validated_data.get("observacao", "")

        try:
            cliente = Cliente.objects.get(id=cliente_id)
        except Cliente.DoesNotExist:
            return Response(
                {"detail": f"Cliente {cliente_id} nao encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if cliente.status != Cliente.Status.EM_PROCESSAMENTO:
            return Response(
                {"detail": f"Cliente nao esta em processamento. Status atual: {cliente.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        status_anterior = cliente.status
        cliente.status = novo_status
        cliente.save(update_fields=["status", "atualizado_em"])

        ClienteHistorico.objects.create(
            cliente=cliente,
            status_anterior=status_anterior,
            status_novo=novo_status,
            usuario=None,
            observacao=observacao or "Atualizado via sistema externo",
        )

        return Response({
            "detail": f"Cliente {cliente_id} atualizado para '{novo_status}'.",
            "cliente_id": cliente.id,
            "status": cliente.status,
        })
