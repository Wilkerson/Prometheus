from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.comissoes.models import Comissao

from .models import Cliente, EntidadeParceira, Lead, ProdutoContratado


class LeadFlowTestCase(TestCase):
    """Testa o fluxo completo: lead → cliente → produto → comissão."""

    def setUp(self):
        self.client = APIClient()

        # Super Admin
        self.admin = Usuario.objects.create_user(
            username="admin", password="TestPass123!", perfil=Usuario.Perfil.SUPER_ADMIN,
        )

        # Parceiro
        self.parceiro_user = Usuario.objects.create_user(
            username="parceiro", password="TestPass123!", perfil=Usuario.Perfil.PARCEIRO,
        )
        self.parceiro = EntidadeParceira.objects.create(
            usuario=self.parceiro_user,
            nome_entidade="Parceiro Teste",
            percentual_comissao=Decimal("15.00"),
        )

        # Operador
        self.operador = Usuario.objects.create_user(
            username="operador", password="TestPass123!", perfil=Usuario.Perfil.OPERADOR,
        )

    def test_parceiro_cria_lead(self):
        """Parceiro cria lead via painel restrito."""
        self.client.force_authenticate(user=self.parceiro_user)
        resp = self.client.post("/api/v1/parceiro/leads/", {
            "nome": "João Silva",
            "email": "joao@email.com",
            "telefone": "11999999999",
            "produto_interesse": "saas",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["parceiro"], self.parceiro.id)

    def test_parceiro_ve_apenas_seus_leads(self):
        """Parceiro só vê leads criados por ele."""
        Lead.objects.create(
            parceiro=self.parceiro, nome="Lead do parceiro",
            email="a@b.com", produto_interesse="crm",
        )

        # Cria outro parceiro com lead
        outro_user = Usuario.objects.create_user(
            username="outro", password="TestPass123!", perfil=Usuario.Perfil.PARCEIRO,
        )
        outro_parceiro = EntidadeParceira.objects.create(
            usuario=outro_user, nome_entidade="Outro", percentual_comissao=Decimal("10"),
        )
        Lead.objects.create(
            parceiro=outro_parceiro, nome="Lead alheio",
            email="c@d.com", produto_interesse="erp",
        )

        self.client.force_authenticate(user=self.parceiro_user)
        resp = self.client.get("/api/v1/parceiro/leads/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

    def test_operador_atualiza_status_lead(self):
        """Operador pode mudar status do lead."""
        lead = Lead.objects.create(
            parceiro=self.parceiro, nome="Lead Teste",
            email="t@t.com", produto_interesse="sites",
        )
        self.client.force_authenticate(user=self.operador)
        resp = self.client.patch(f"/api/v1/leads/{lead.id}/status/", {"status": "qualificado"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "qualificado")

    def test_converter_lead_em_cliente(self):
        """Operador converte lead vendido em cliente."""
        lead = Lead.objects.create(
            parceiro=self.parceiro, nome="Lead Vendido",
            email="v@v.com", produto_interesse="crm", status=Lead.Status.VENDIDO,
        )
        self.client.force_authenticate(user=self.operador)
        resp = self.client.post(f"/api/v1/leads/{lead.id}/converter/", {"cnpj": "12345678000199"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["nome"], "Lead Vendido")
        self.assertEqual(resp.data["cnpj"], "12345678000199")

    def test_converter_lead_nao_vendido_falha(self):
        """Não pode converter lead que não está com status vendido."""
        lead = Lead.objects.create(
            parceiro=self.parceiro, nome="Lead Novo",
            email="n@n.com", produto_interesse="erp",
        )
        self.client.force_authenticate(user=self.operador)
        resp = self.client.post(f"/api/v1/leads/{lead.id}/converter/", {"cnpj": "12345678000199"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_comissao_gerada_automaticamente(self):
        """Ao criar ProdutoContratado, comissão é gerada via signal."""
        lead = Lead.objects.create(
            parceiro=self.parceiro, nome="Lead Comissão",
            email="c@c.com", produto_interesse="saas", status=Lead.Status.VENDIDO,
        )
        cliente = Cliente.objects.create(
            lead=lead, nome="Cliente Teste",
            cnpj="12345678000199", email="c@c.com",
        )
        produto = ProdutoContratado.objects.create(
            cliente=cliente, produto="saas", valor=Decimal("1000.00"),
        )

        comissao = Comissao.objects.get(venda=produto)
        self.assertEqual(comissao.parceiro, self.parceiro)
        self.assertEqual(comissao.valor_venda, Decimal("1000.00"))
        self.assertEqual(comissao.percentual, Decimal("15.00"))
        self.assertEqual(comissao.valor_comissao, Decimal("150.00"))
        self.assertEqual(comissao.status, Comissao.Status.PENDENTE)


class DashboardTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.parceiro_user = Usuario.objects.create_user(
            username="parceiro", password="TestPass123!", perfil=Usuario.Perfil.PARCEIRO,
        )
        self.parceiro = EntidadeParceira.objects.create(
            usuario=self.parceiro_user,
            nome_entidade="Parceiro Dashboard",
            percentual_comissao=Decimal("10.00"),
        )

    def test_dashboard_parceiro(self):
        """Dashboard retorna resumo correto."""
        Lead.objects.create(
            parceiro=self.parceiro, nome="L1", email="l1@t.com",
            produto_interesse="crm", status=Lead.Status.NOVO,
        )
        Lead.objects.create(
            parceiro=self.parceiro, nome="L2", email="l2@t.com",
            produto_interesse="erp", status=Lead.Status.VENDIDO,
        )

        self.client.force_authenticate(user=self.parceiro_user)
        resp = self.client.get("/api/v1/parceiro/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["leads"]["total"], 2)
        self.assertEqual(resp.data["leads"]["por_status"]["novo"], 1)
        self.assertEqual(resp.data["leads"]["por_status"]["vendido"], 1)
