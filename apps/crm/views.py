from django.db.models import F, Max
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Usuario
from apps.accounts.permissions import IsOperador, IsOwnerParceiro, IsSuperAdmin

from .models import Cliente, ClienteHistorico, EntidadeParceira, ProdutoContratado
from .serializers import (
    ClienteHistoricoSerializer,
    ClienteListSerializer,
    ClienteSerializer,
    ClienteStatusSerializer,
    EntidadeParceiraSerializer,
    ProdutoContratadoSerializer,
)
from .tasks import enviar_cliente_sistema_externo


class EntidadeParceiraViewSet(viewsets.ModelViewSet):
    """CRUD de entidades parceiras — somente Super Admin."""

    queryset = EntidadeParceira.objects.select_related("usuario")
    serializer_class = EntidadeParceiraSerializer
    permission_classes = [IsSuperAdmin]


class ClienteViewSet(viewsets.ModelViewSet):
    """
    Clientes:
    - Super Admin / Operador: veem todos, podem alterar status
    - Parceiro: ve e cria apenas os seus
    """

    permission_classes = [IsAuthenticated, IsOwnerParceiro]
    filterset_fields = ["status", "produto_interesse", "parceiro"]
    search_fields = ["nome", "cnpj", "email"]
    ordering_fields = ["criado_em", "status"]

    def get_serializer_class(self):
        if self.action == "list":
            return ClienteListSerializer
        return ClienteSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Cliente.objects.select_related("parceiro", "operador").prefetch_related("historico")

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
        """PATCH /api/v1/clientes/{id}/status/ — atualiza status."""
        cliente = self.get_object()
        serializer = ClienteStatusSerializer(data=request.data, context={"cliente": cliente})
        serializer.is_valid(raise_exception=True)

        status_anterior = cliente.status
        novo_status = serializer.validated_data["status"]
        observacao = serializer.validated_data.get("observacao", "")

        cliente.status = novo_status
        cliente.save(update_fields=["status", "atualizado_em"])

        ClienteHistorico.objects.create(
            cliente=cliente,
            status_anterior=status_anterior,
            status_novo=novo_status,
            usuario=request.user,
            observacao=observacao,
        )

        if novo_status == Cliente.Status.EM_PROCESSAMENTO:
            enviar_cliente_sistema_externo.delay(cliente.id)

        cliente.refresh_from_db()
        return Response(ClienteSerializer(cliente).data)

    @action(detail=True, methods=["get"], url_path="historico")
    def get_historico(self, request, pk=None):
        """GET /api/v1/clientes/{id}/historico/ — timeline do cliente."""
        cliente = self.get_object()
        historico = cliente.historico.select_related("usuario").all()
        serializer = ClienteHistoricoSerializer(historico, many=True)
        return Response(serializer.data)


class CalendarioClientesView(APIView):
    """GET /api/v1/clientes/calendario/?mes=YYYY-MM"""

    permission_classes = [IsAuthenticated, IsOperador]

    def get(self, request):
        mes = request.query_params.get("mes", "")
        if not mes:
            hoje = timezone.now()
            ano, mes_num = hoje.year, hoje.month
        else:
            try:
                partes = mes.split("-")
                ano, mes_num = int(partes[0]), int(partes[1])
            except (ValueError, IndexError):
                return Response(
                    {"detail": "Formato invalido. Use ?mes=YYYY-MM"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        clientes = (
            Cliente.objects.filter(criado_em__year=ano, criado_em__month=mes_num)
            .select_related("parceiro")
            .order_by("criado_em")
        )

        calendario = {}
        for cliente in clientes:
            dia = cliente.criado_em.strftime("%Y-%m-%d")
            if dia not in calendario:
                calendario[dia] = []
            calendario[dia].append({
                "id": cliente.id,
                "nome": cliente.nome,
                "parceiro": cliente.parceiro.nome_entidade,
                "produto_interesse": cliente.produto_interesse,
                "status": cliente.status,
                "status_display": cliente.get_status_display(),
                "criado_em": cliente.criado_em.isoformat(),
            })

        return Response({
            "mes": f"{ano:04d}-{mes_num:02d}",
            "total_clientes": clientes.count(),
            "dias": calendario,
        })


class SLAClientesView(APIView):
    """GET /api/v1/clientes/sla/?dias=3"""

    permission_classes = [IsAuthenticated, IsOperador]

    def get(self, request):
        dias = int(request.query_params.get("dias", 3))
        limite = timezone.now() - timezone.timedelta(days=dias)

        clientes_parados = (
            Cliente.objects.exclude(status__in=[Cliente.Status.CONCLUIDA, Cliente.Status.PERDIDA])
            .filter(atualizado_em__lt=limite)
            .select_related("parceiro", "operador")
            .order_by("atualizado_em")
        )

        resultado = []
        for cliente in clientes_parados:
            dias_parado = (timezone.now() - cliente.atualizado_em).days
            resultado.append({
                "id": cliente.id,
                "nome": cliente.nome,
                "parceiro": cliente.parceiro.nome_entidade,
                "status": cliente.status,
                "status_display": cliente.get_status_display(),
                "atualizado_em": cliente.atualizado_em.isoformat(),
                "dias_parado": dias_parado,
            })

        return Response({
            "dias_limite": dias,
            "total": len(resultado),
            "clientes": resultado,
        })


class ProdutoContratadoViewSet(viewsets.ModelViewSet):
    queryset = ProdutoContratado.objects.select_related("cliente")
    serializer_class = ProdutoContratadoSerializer
    permission_classes = [IsOperador]
    filterset_fields = ["status", "produto"]
