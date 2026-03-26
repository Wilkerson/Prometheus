from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.comissoes.models import Comissao

from .models import Cliente, ClienteHistorico, EntidadeParceira, ProdutoContratado


class ClienteFlowTestCase(TestCase):
    """Testa o fluxo de cadastro de cliente pelo parceiro."""

    def setUp(self):
        self.client = APIClient()
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

    def test_parceiro_cria_cliente_com_status_recebida(self):
        self.client.force_authenticate(user=self.parceiro_user)
        resp = self.client.post("/api/v1/parceiro/clientes/", {
            "nome": "Empresa ABC",
            "cnpj": "12345678000199",
            "email": "abc@email.com",
            "telefone": "11999999999",
            "produto_interesse": "saas",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], "recebida")
        cliente = Cliente.objects.get(id=resp.data["id"])
        self.assertEqual(cliente.parceiro, self.parceiro)

    def test_parceiro_ve_apenas_seus_clientes(self):
        Cliente.objects.create(
            parceiro=self.parceiro, nome="Cliente do parceiro",
            cnpj="11111111000111", email="a@b.com", produto_interesse="crm",
        )
        outro_user = Usuario.objects.create_user(
            username="outro", password="TestPass123!", perfil=Usuario.Perfil.PARCEIRO,
        )
        outro_parceiro = EntidadeParceira.objects.create(
            usuario=outro_user, nome_entidade="Outro", percentual_comissao=Decimal("10"),
        )
        Cliente.objects.create(
            parceiro=outro_parceiro, nome="Cliente alheio",
            cnpj="22222222000222", email="c@d.com", produto_interesse="erp",
        )

        self.client.force_authenticate(user=self.parceiro_user)
        resp = self.client.get("/api/v1/parceiro/clientes/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)


class StatusTransicaoTestCase(TestCase):
    """Testa transicoes de status e historico."""

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
        self.cliente_obj = Cliente.objects.create(
            parceiro=self.parceiro, nome="Cliente Teste",
            cnpj="33333333000133", email="t@t.com", produto_interesse="sites",
        )

    def test_transicao_valida_recebida_para_em_analise(self):
        self.client.force_authenticate(user=self.operador)
        resp = self.client.patch(
            f"/api/v1/clientes/{self.cliente_obj.id}/status/",
            {"status": "em_analise", "observacao": "Iniciando analise"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "em_analise")
        historico = ClienteHistorico.objects.filter(cliente=self.cliente_obj)
        self.assertEqual(historico.count(), 1)

    def test_transicao_invalida_recebida_para_concluida(self):
        self.client.force_authenticate(user=self.operador)
        resp = self.client.patch(
            f"/api/v1/clientes/{self.cliente_obj.id}/status/",
            {"status": "concluida"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transicao_invalida_de_status_final(self):
        self.cliente_obj.status = Cliente.Status.CONCLUIDA
        self.cliente_obj.save()
        self.client.force_authenticate(user=self.operador)
        resp = self.client.patch(
            f"/api/v1/clientes/{self.cliente_obj.id}/status/",
            {"status": "recebida"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.crm.tasks.enviar_cliente_sistema_externo.delay")
    def test_em_processamento_dispara_task(self, mock_task):
        self.cliente_obj.status = Cliente.Status.EM_ANALISE
        self.cliente_obj.save()
        self.client.force_authenticate(user=self.operador)
        resp = self.client.patch(
            f"/api/v1/clientes/{self.cliente_obj.id}/status/",
            {"status": "em_processamento"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_task.assert_called_once_with(self.cliente_obj.id)

    def test_fluxo_completo_de_status(self):
        self.client.force_authenticate(user=self.operador)
        for novo_status in ["em_analise", "em_processamento", "concluida"]:
            with patch("apps.crm.tasks.enviar_cliente_sistema_externo.delay"):
                resp = self.client.patch(
                    f"/api/v1/clientes/{self.cliente_obj.id}/status/",
                    {"status": novo_status},
                )
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(ClienteHistorico.objects.filter(cliente=self.cliente_obj).count(), 3)

    def test_historico_endpoint(self):
        ClienteHistorico.objects.create(
            cliente=self.cliente_obj, status_anterior="recebida",
            status_novo="em_analise", usuario=self.operador,
        )
        self.client.force_authenticate(user=self.operador)
        resp = self.client.get(f"/api/v1/clientes/{self.cliente_obj.id}/historico/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)


class CallbackSistemaExternoTestCase(TestCase):
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
        self.cliente_obj = Cliente.objects.create(
            parceiro=self.parceiro, nome="Cliente Processando",
            cnpj="44444444000144", email="p@p.com", produto_interesse="crm",
            status=Cliente.Status.EM_PROCESSAMENTO,
        )
        from apps.integracao.models import TokenIntegracao
        self.token = TokenIntegracao.objects.create(nome="Sistema Teste")

    def test_callback_conclui_cliente(self):
        resp = self.client.post(
            "/api/v1/integracao/cliente/status/",
            {"cliente_id": self.cliente_obj.id, "status": "concluida", "observacao": "Implantacao OK"},
            HTTP_X_API_KEY=self.token.token,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.cliente_obj.refresh_from_db()
        self.assertEqual(self.cliente_obj.status, Cliente.Status.CONCLUIDA)
        historico = ClienteHistorico.objects.get(cliente=self.cliente_obj)
        self.assertEqual(historico.observacao, "Implantacao OK")

    def test_callback_rejeita_cliente_nao_em_processamento(self):
        self.cliente_obj.status = Cliente.Status.RECEBIDA
        self.cliente_obj.save()
        resp = self.client.post(
            "/api/v1/integracao/cliente/status/",
            {"cliente_id": self.cliente_obj.id, "status": "concluida"},
            HTTP_X_API_KEY=self.token.token,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ComissaoTestCase(TestCase):
    def setUp(self):
        self.parceiro_user = Usuario.objects.create_user(
            username="parceiro", password="TestPass123!", perfil=Usuario.Perfil.PARCEIRO,
        )
        self.parceiro = EntidadeParceira.objects.create(
            usuario=self.parceiro_user,
            nome_entidade="Parceiro Comissao",
            percentual_comissao=Decimal("15.00"),
        )

    def test_comissao_gerada_automaticamente(self):
        cliente = Cliente.objects.create(
            parceiro=self.parceiro, nome="Cliente Comissao",
            cnpj="55555555000155", email="c@c.com", produto_interesse="saas",
            status=Cliente.Status.CONCLUIDA,
        )
        produto = ProdutoContratado.objects.create(
            cliente=cliente, produto="saas", valor=Decimal("1000.00"),
        )
        comissao = Comissao.objects.get(venda=produto)
        self.assertEqual(comissao.parceiro, self.parceiro)
        self.assertEqual(comissao.valor_comissao, Decimal("150.00"))


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
        Cliente.objects.create(
            parceiro=self.parceiro, nome="C1", cnpj="66666666000166",
            email="c1@t.com", produto_interesse="crm", status=Cliente.Status.RECEBIDA,
        )
        Cliente.objects.create(
            parceiro=self.parceiro, nome="C2", cnpj="77777777000177",
            email="c2@t.com", produto_interesse="erp", status=Cliente.Status.CONCLUIDA,
        )
        self.client.force_authenticate(user=self.parceiro_user)
        resp = self.client.get("/api/v1/parceiro/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["clientes"]["total"], 2)
        self.assertEqual(resp.data["clientes"]["por_status"]["recebida"], 1)
        self.assertEqual(resp.data["clientes"]["por_status"]["concluida"], 1)
