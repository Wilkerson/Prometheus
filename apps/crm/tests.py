from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.comissoes.models import Comissao

from .models import Cliente, EntidadeParceira, Lead, LeadHistorico, ProdutoContratado


class LeadFlowTestCase(TestCase):
    """Testa o fluxo completo: lead → status → cliente → produto → comissão."""

    def setUp(self):
        self.client = APIClient()

        self.admin = Usuario.objects.create_user(
            username="admin", password="TestPass123!", perfil=Usuario.Perfil.SUPER_ADMIN,
        )
        self.parceiro_user = Usuario.objects.create_user(
            username="parceiro", password="TestPass123!", perfil=Usuario.Perfil.PARCEIRO,
        )
        self.parceiro = EntidadeParceira.objects.create(
            usuario=self.parceiro_user,
            nome_entidade="Parceiro Teste",
            percentual_comissao=Decimal("15.00"),
        )
        self.operador = Usuario.objects.create_user(
            username="operador", password="TestPass123!", perfil=Usuario.Perfil.OPERADOR,
        )

    def test_parceiro_cria_lead_com_status_recebida(self):
        """Parceiro cria lead — status inicial deve ser 'recebida'."""
        self.client.force_authenticate(user=self.parceiro_user)
        resp = self.client.post("/api/v1/parceiro/leads/", {
            "nome": "João Silva",
            "email": "joao@email.com",
            "telefone": "11999999999",
            "produto_interesse": "saas",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], "recebida")
        # Verifica que o lead foi vinculado ao parceiro no banco
        lead = Lead.objects.get(id=resp.data["id"])
        self.assertEqual(lead.parceiro, self.parceiro)

    def test_parceiro_ve_apenas_seus_leads(self):
        Lead.objects.create(
            parceiro=self.parceiro, nome="Lead do parceiro",
            email="a@b.com", produto_interesse="crm",
        )
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


class StatusTransicaoTestCase(TestCase):
    """Testa transições de status e histórico."""

    def setUp(self):
        self.client = APIClient()
        self.operador = Usuario.objects.create_user(
            username="operador", password="TestPass123!", perfil=Usuario.Perfil.OPERADOR,
        )
        self.parceiro_user = Usuario.objects.create_user(
            username="parceiro", password="TestPass123!", perfil=Usuario.Perfil.PARCEIRO,
        )
        self.parceiro = EntidadeParceira.objects.create(
            usuario=self.parceiro_user,
            nome_entidade="Parceiro Teste",
            percentual_comissao=Decimal("10.00"),
        )
        self.lead = Lead.objects.create(
            parceiro=self.parceiro, nome="Lead Teste",
            email="t@t.com", produto_interesse="sites",
        )

    def test_transicao_valida_recebida_para_em_analise(self):
        self.client.force_authenticate(user=self.operador)
        resp = self.client.patch(
            f"/api/v1/leads/{self.lead.id}/status/",
            {"status": "em_analise", "observacao": "Iniciando análise"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "em_analise")

        # Verifica histórico
        historico = LeadHistorico.objects.filter(lead=self.lead)
        self.assertEqual(historico.count(), 1)
        self.assertEqual(historico.first().status_anterior, "recebida")
        self.assertEqual(historico.first().status_novo, "em_analise")

    def test_transicao_invalida_recebida_para_concluida(self):
        self.client.force_authenticate(user=self.operador)
        resp = self.client.patch(
            f"/api/v1/leads/{self.lead.id}/status/",
            {"status": "concluida"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transicao_invalida_de_status_final(self):
        """Status final (concluída/perdida) não aceita transição."""
        self.lead.status = Lead.Status.CONCLUIDA
        self.lead.save()

        self.client.force_authenticate(user=self.operador)
        resp = self.client.patch(
            f"/api/v1/leads/{self.lead.id}/status/",
            {"status": "recebida"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.crm.tasks.enviar_lead_sistema_externo.delay")
    def test_em_processamento_dispara_task(self, mock_task):
        """Mudar para em_processamento deve disparar envio via Celery."""
        self.lead.status = Lead.Status.EM_ANALISE
        self.lead.save()

        self.client.force_authenticate(user=self.operador)
        resp = self.client.patch(
            f"/api/v1/leads/{self.lead.id}/status/",
            {"status": "em_processamento"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_task.assert_called_once_with(self.lead.id)

    def test_fluxo_completo_de_status(self):
        """recebida → em_analise → em_processamento → concluida."""
        self.client.force_authenticate(user=self.operador)

        for novo_status in ["em_analise", "em_processamento", "concluida"]:
            with patch("apps.crm.tasks.enviar_lead_sistema_externo.delay"):
                resp = self.client.patch(
                    f"/api/v1/leads/{self.lead.id}/status/",
                    {"status": novo_status},
                )
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

        self.assertEqual(LeadHistorico.objects.filter(lead=self.lead).count(), 3)

    def test_historico_endpoint(self):
        """GET /leads/{id}/historico/ retorna timeline."""
        LeadHistorico.objects.create(
            lead=self.lead, status_anterior="recebida",
            status_novo="em_analise", usuario=self.operador,
        )
        self.client.force_authenticate(user=self.operador)
        resp = self.client.get(f"/api/v1/leads/{self.lead.id}/historico/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)


class CallbackSistemaExternoTestCase(TestCase):
    """Testa o callback do sistema externo."""

    def setUp(self):
        self.client = APIClient()
        self.parceiro_user = Usuario.objects.create_user(
            username="parceiro", password="TestPass123!", perfil=Usuario.Perfil.PARCEIRO,
        )
        self.parceiro = EntidadeParceira.objects.create(
            usuario=self.parceiro_user,
            nome_entidade="Parceiro Callback",
            percentual_comissao=Decimal("10.00"),
        )
        self.lead = Lead.objects.create(
            parceiro=self.parceiro, nome="Lead Processando",
            email="p@p.com", produto_interesse="crm",
            status=Lead.Status.EM_PROCESSAMENTO,
        )

        from apps.integracao.models import TokenIntegracao
        self.token = TokenIntegracao.objects.create(nome="Sistema Teste")

    def test_callback_conclui_lead(self):
        resp = self.client.post(
            "/api/v1/integracao/lead/status/",
            {"lead_id": self.lead.id, "status": "concluida", "observacao": "Implantação OK"},
            HTTP_X_API_KEY=self.token.token,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.CONCLUIDA)

        historico = LeadHistorico.objects.get(lead=self.lead)
        self.assertEqual(historico.status_novo, "concluida")
        self.assertEqual(historico.observacao, "Implantação OK")

    def test_callback_rejeita_lead_nao_em_processamento(self):
        self.lead.status = Lead.Status.RECEBIDA
        self.lead.save()

        resp = self.client.post(
            "/api/v1/integracao/lead/status/",
            {"lead_id": self.lead.id, "status": "concluida"},
            HTTP_X_API_KEY=self.token.token,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ConversaoClienteTestCase(TestCase):
    """Testa conversão de lead concluída em cliente + comissão."""

    def setUp(self):
        self.client = APIClient()
        self.operador = Usuario.objects.create_user(
            username="operador", password="TestPass123!", perfil=Usuario.Perfil.OPERADOR,
        )
        self.parceiro_user = Usuario.objects.create_user(
            username="parceiro", password="TestPass123!", perfil=Usuario.Perfil.PARCEIRO,
        )
        self.parceiro = EntidadeParceira.objects.create(
            usuario=self.parceiro_user,
            nome_entidade="Parceiro Conversão",
            percentual_comissao=Decimal("15.00"),
        )

    def test_converter_lead_concluida(self):
        lead = Lead.objects.create(
            parceiro=self.parceiro, nome="Lead Concluída",
            email="v@v.com", produto_interesse="crm",
            status=Lead.Status.CONCLUIDA,
        )
        self.client.force_authenticate(user=self.operador)
        resp = self.client.post(
            f"/api/v1/leads/{lead.id}/converter/",
            {"cnpj": "12345678000199"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["cnpj"], "12345678000199")

    def test_converter_lead_nao_concluida_falha(self):
        lead = Lead.objects.create(
            parceiro=self.parceiro, nome="Lead Nova",
            email="n@n.com", produto_interesse="erp",
        )
        self.client.force_authenticate(user=self.operador)
        resp = self.client.post(
            f"/api/v1/leads/{lead.id}/converter/",
            {"cnpj": "12345678000199"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_comissao_gerada_automaticamente(self):
        lead = Lead.objects.create(
            parceiro=self.parceiro, nome="Lead Comissão",
            email="c@c.com", produto_interesse="saas",
            status=Lead.Status.CONCLUIDA,
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

    def test_dashboard_parceiro_novos_status(self):
        Lead.objects.create(
            parceiro=self.parceiro, nome="L1", email="l1@t.com",
            produto_interesse="crm", status=Lead.Status.RECEBIDA,
        )
        Lead.objects.create(
            parceiro=self.parceiro, nome="L2", email="l2@t.com",
            produto_interesse="erp", status=Lead.Status.CONCLUIDA,
        )

        self.client.force_authenticate(user=self.parceiro_user)
        resp = self.client.get("/api/v1/parceiro/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["leads"]["total"], 2)
        self.assertEqual(resp.data["leads"]["por_status"]["recebida"], 1)
        self.assertEqual(resp.data["leads"]["por_status"]["concluida"], 1)


class CalendarioSLATestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.operador = Usuario.objects.create_user(
            username="operador", password="TestPass123!", perfil=Usuario.Perfil.OPERADOR,
        )
        self.parceiro_user = Usuario.objects.create_user(
            username="parceiro", password="TestPass123!", perfil=Usuario.Perfil.PARCEIRO,
        )
        self.parceiro = EntidadeParceira.objects.create(
            usuario=self.parceiro_user,
            nome_entidade="Parceiro SLA",
            percentual_comissao=Decimal("10.00"),
        )

    def test_calendario_endpoint(self):
        Lead.objects.create(
            parceiro=self.parceiro, nome="Lead Cal",
            email="c@c.com", produto_interesse="sites",
        )
        self.client.force_authenticate(user=self.operador)
        resp = self.client.get("/api/v1/leads/calendario/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total_leads"], 1)

    def test_sla_endpoint(self):
        self.client.force_authenticate(user=self.operador)
        resp = self.client.get("/api/v1/leads/sla/?dias=3")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("leads", resp.data)
