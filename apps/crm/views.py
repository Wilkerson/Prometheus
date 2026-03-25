from django.db.models import F, Max
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Usuario
from apps.accounts.permissions import IsOperador, IsOwnerParceiro, IsSuperAdmin

from .models import Cliente, EntidadeParceira, Lead, LeadHistorico, ProdutoContratado
from .serializers import (
    ClienteSerializer,
    EntidadeParceiraSerializer,
    LeadHistoricoSerializer,
    LeadListSerializer,
    LeadSerializer,
    LeadStatusSerializer,
    ProdutoContratadoSerializer,
)
from .tasks import enviar_lead_sistema_externo


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

    permission_classes = [IsAuthenticated, IsOwnerParceiro]
    filterset_fields = ["status", "produto_interesse", "parceiro"]
    search_fields = ["nome", "email"]
    ordering_fields = ["criado_em", "status"]

    def get_serializer_class(self):
        if self.action == "list":
            return LeadListSerializer
        return LeadSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Lead.objects.select_related("parceiro", "operador").prefetch_related("historico")

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
        """
        PATCH /api/v1/leads/{id}/status/
        Atualiza status com validação de transição e registro no histórico.
        Ao mudar para 'em_processamento', dispara envio para sistema externo.
        """
        lead = self.get_object()
        serializer = LeadStatusSerializer(data=request.data, context={"lead": lead})
        serializer.is_valid(raise_exception=True)

        status_anterior = lead.status
        novo_status = serializer.validated_data["status"]
        observacao = serializer.validated_data.get("observacao", "")

        # Atualiza o lead
        lead.status = novo_status
        lead.save(update_fields=["status", "atualizado_em"])

        # Registra no histórico
        LeadHistorico.objects.create(
            lead=lead,
            status_anterior=status_anterior,
            status_novo=novo_status,
            usuario=request.user,
            observacao=observacao,
        )

        # Se mudou para em_processamento, envia para sistema externo via Celery
        if novo_status == Lead.Status.EM_PROCESSAMENTO:
            enviar_lead_sistema_externo.delay(lead.id)

        lead.refresh_from_db()
        return Response(LeadSerializer(lead).data)

    @action(detail=True, methods=["get"], url_path="historico")
    def get_historico(self, request, pk=None):
        """GET /api/v1/leads/{id}/historico/ — timeline do lead."""
        lead = self.get_object()
        historico = lead.historico.select_related("usuario").all()
        serializer = LeadHistoricoSerializer(historico, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="converter", permission_classes=[IsOperador])
    def converter_em_cliente(self, request, pk=None):
        """POST /api/v1/leads/{id}/converter/ — converte lead concluída em cliente."""
        lead = self.get_object()

        if hasattr(lead, "cliente"):
            return Response(
                {"detail": "Este lead já foi convertido em cliente."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if lead.status != Lead.Status.CONCLUIDA:
            return Response(
                {"detail": "Somente leads com status 'concluída' podem ser convertidas em cliente."},
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


class CalendarioLeadsView(APIView):
    """
    GET /api/v1/leads/calendario/?mes=2026-03
    Retorna leads agrupadas por dia para visualização no calendário.
    """

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
                    {"detail": "Formato inválido. Use ?mes=YYYY-MM"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        leads = (
            Lead.objects.filter(criado_em__year=ano, criado_em__month=mes_num)
            .select_related("parceiro")
            .order_by("criado_em")
        )

        calendario = {}
        for lead in leads:
            dia = lead.criado_em.strftime("%Y-%m-%d")
            if dia not in calendario:
                calendario[dia] = []
            calendario[dia].append({
                "id": lead.id,
                "nome": lead.nome,
                "parceiro": lead.parceiro.nome_entidade,
                "produto_interesse": lead.produto_interesse,
                "status": lead.status,
                "status_display": lead.get_status_display(),
                "criado_em": lead.criado_em.isoformat(),
            })

        return Response({
            "mes": f"{ano:04d}-{mes_num:02d}",
            "total_leads": leads.count(),
            "dias": calendario,
        })


class SLALeadsView(APIView):
    """
    GET /api/v1/leads/sla/?dias=3
    Retorna leads paradas (sem mudança de status) há mais de X dias.
    """

    permission_classes = [IsAuthenticated, IsOperador]

    def get(self, request):
        dias = int(request.query_params.get("dias", 3))
        limite = timezone.now() - timezone.timedelta(days=dias)

        # Leads que NÃO estão em status final e cuja última atualização é antiga
        leads_paradas = (
            Lead.objects.exclude(status__in=[Lead.Status.CONCLUIDA, Lead.Status.PERDIDA])
            .filter(atualizado_em__lt=limite)
            .select_related("parceiro", "operador")
            .order_by("atualizado_em")
        )

        resultado = []
        for lead in leads_paradas:
            dias_parada = (timezone.now() - lead.atualizado_em).days
            resultado.append({
                "id": lead.id,
                "nome": lead.nome,
                "parceiro": lead.parceiro.nome_entidade,
                "status": lead.status,
                "status_display": lead.get_status_display(),
                "atualizado_em": lead.atualizado_em.isoformat(),
                "dias_parada": dias_parada,
            })

        return Response({
            "dias_limite": dias,
            "total": len(resultado),
            "leads": resultado,
        })


class ClienteViewSet(viewsets.ModelViewSet):
    """Clientes — Operadores e Super Admin."""

    queryset = Cliente.objects.prefetch_related("produtos")
    serializer_class = ClienteSerializer
    permission_classes = [IsOperador]
    filterset_fields = ["ativo"]
    search_fields = ["nome", "documento", "cnpj", "email"]


class ProdutoContratadoViewSet(viewsets.ModelViewSet):
    """Produtos contratados — Operadores e Super Admin."""

    queryset = ProdutoContratado.objects.select_related("cliente")
    serializer_class = ProdutoContratadoSerializer
    permission_classes = [IsOperador]
    filterset_fields = ["status", "produto"]
