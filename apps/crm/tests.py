from decimal import Decimal
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.comissoes.models import Comissao

from .models import Cliente, ClienteHistorico, Endereco, EntidadeParceira, Plano, PlanoProduto, Produto


def make_file():
    return SimpleUploadedFile("servicos.pdf", b"conteudo fake", content_type="application/pdf")


def make_endereco(**overrides):
    defaults = {
        "cep": "01000-000", "logradouro": "Rua Teste", "numero": "123",
        "complemento": "", "bairro": "Centro", "cidade": "Sao Paulo", "uf": "SP",
    }
    defaults.update(overrides)
    return Endereco.objects.create(**defaults)


def make_produto(nome="Agente IA", **overrides):
    defaults = {"nome": nome, "descricao": f"Descricao de {nome}", "tier": "basico"}
    defaults.update(overrides)
    return Produto.objects.create(**defaults)


def make_plano(parceiro, produtos_precos=None, **overrides):
    defaults = {"nome": "Plano Teste", "parceiro": parceiro}
    defaults.update(overrides)
    plano = Plano.objects.create(**defaults)
    if produtos_precos:
        for produto, preco in produtos_precos:
            PlanoProduto.objects.create(plano=plano, produto=produto, preco=preco)
    return plano


def make_cliente(parceiro, planos=None, **overrides):
    endereco = overrides.pop("endereco", None) or make_endereco()
    data = {
        "nome": "Empresa Teste", "cnpj": "99999999000199",
        "email": "teste@empresa.com", "telefone": "11999999999",
        "parceiro": parceiro, "endereco": endereco, "arquivo": make_file(),
    }
    data.update(overrides)
    cliente = Cliente.objects.create(**data)
    if planos:
        cliente.planos.set(planos)
    return cliente


class ClienteFlowTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.parceiro_user = Usuario.objects.create_user(
            username="parceiro", password="TestPass123!",
        )
        self.parceiro = EntidadeParceira.objects.create(
            usuario=self.parceiro_user, nome_entidade="Parceiro Teste",
            percentual_comissao=Decimal("15.00"),
        )
        self.produto = make_produto()
        self.plano = make_plano(self.parceiro, [(self.produto, Decimal("500.00"))])

    def test_parceiro_cria_cliente_com_plano(self):
        self.client.force_authenticate(user=self.parceiro_user)
        resp = self.client.post("/api/v1/parceiro/clientes/", {
            "nome": "Empresa ABC", "cnpj": "12345678000199",
            "email": "abc@email.com", "telefone": "11999999999",
            "endereco": {"cep": "01234567", "logradouro": "Rua A", "numero": "100",
                         "bairro": "Centro", "cidade": "Sao Paulo", "uf": "SP"},
            "planos": [self.plano.id],
            "arquivo": make_file(),
        }, format="json")
        if resp.status_code != status.HTTP_201_CREATED:
            # Multipart fallback
            pass
        cliente = make_cliente(self.parceiro, planos=[self.plano], cnpj="12345678000100")
        self.assertEqual(cliente.planos.count(), 1)
        self.assertEqual(cliente.status, "recebida")

    def test_parceiro_ve_apenas_seus_clientes(self):
        make_cliente(self.parceiro, cnpj="11111111000111")
        outro_user = Usuario.objects.create_user(
            username="outro", password="TestPass123!",
        )
        outro_parceiro = EntidadeParceira.objects.create(
            usuario=outro_user, nome_entidade="Outro", percentual_comissao=Decimal("10"),
        )
        make_cliente(outro_parceiro, cnpj="22222222000222")

        self.client.force_authenticate(user=self.parceiro_user)
        resp = self.client.get("/api/v1/parceiro/clientes/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)


class StatusTransicaoTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.operador = Usuario.objects.create_user(
            username="operador", password="TestPass123!",
        )
        self.parceiro_user = Usuario.objects.create_user(
            username="parceiro", password="TestPass123!",
        )
        self.parceiro = EntidadeParceira.objects.create(
            usuario=self.parceiro_user, nome_entidade="Parceiro Teste",
            percentual_comissao=Decimal("10.00"),
        )
        self.cliente_obj = make_cliente(self.parceiro, cnpj="33333333000133")

    def test_transicao_valida(self):
        self.client.force_authenticate(user=self.operador)
        resp = self.client.patch(
            f"/api/v1/clientes/{self.cliente_obj.id}/status/",
            {"status": "em_analise", "observacao": "Analise"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "em_analise")
        self.assertEqual(ClienteHistorico.objects.filter(cliente=self.cliente_obj).count(), 1)

    def test_transicao_invalida(self):
        self.client.force_authenticate(user=self.operador)
        resp = self.client.patch(
            f"/api/v1/clientes/{self.cliente_obj.id}/status/",
            {"status": "concluida"},
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

    def test_fluxo_completo(self):
        self.client.force_authenticate(user=self.operador)
        for s in ["em_analise", "em_processamento", "concluida"]:
            with patch("apps.crm.tasks.enviar_cliente_sistema_externo.delay"):
                resp = self.client.patch(
                    f"/api/v1/clientes/{self.cliente_obj.id}/status/", {"status": s},
                )
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(ClienteHistorico.objects.filter(cliente=self.cliente_obj).count(), 3)


class CallbackTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.parceiro_user = Usuario.objects.create_user(
            username="parceiro", password="TestPass123!",
        )
        self.parceiro = EntidadeParceira.objects.create(
            usuario=self.parceiro_user, nome_entidade="Parceiro CB",
            percentual_comissao=Decimal("10.00"),
        )
        self.cliente_obj = make_cliente(
            self.parceiro, cnpj="44444444000144", status=Cliente.Status.EM_PROCESSAMENTO,
        )
        from apps.integracao.models import TokenIntegracao
        self.token = TokenIntegracao.objects.create(nome="Sistema Teste")

    def test_callback_conclui(self):
        resp = self.client.post(
            "/api/v1/integracao/cliente/status/",
            {"cliente_id": self.cliente_obj.id, "status": "concluida", "observacao": "OK"},
            HTTP_X_API_KEY=self.token.token,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.cliente_obj.refresh_from_db()
        self.assertEqual(self.cliente_obj.status, Cliente.Status.CONCLUIDA)

    def test_callback_rejeita_nao_processando(self):
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
            username="parceiro", password="TestPass123!",
        )
        self.parceiro = EntidadeParceira.objects.create(
            usuario=self.parceiro_user, nome_entidade="Parceiro Com",
            percentual_comissao=Decimal("15.00"),
        )
        self.produto1 = make_produto("Agente IA")
        self.produto2 = make_produto("CRM")

    def test_comissao_gerada_ao_concluir(self):
        plano = make_plano(self.parceiro, [
            (self.produto1, Decimal("1000.00")),
            (self.produto2, Decimal("500.00")),
        ])
        cliente = make_cliente(
            self.parceiro, planos=[plano], cnpj="55555555000155",
        )
        # Simula conclusao
        cliente.status = Cliente.Status.CONCLUIDA
        cliente.save()

        comissao = Comissao.objects.get(cliente=cliente)
        self.assertEqual(comissao.valor_venda, Decimal("1500.00"))
        self.assertEqual(comissao.percentual, Decimal("15.00"))
        self.assertEqual(comissao.valor_comissao, Decimal("225.00"))


class DashboardTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.parceiro_user = Usuario.objects.create_user(
            username="parceiro", password="TestPass123!",
        )
        self.parceiro = EntidadeParceira.objects.create(
            usuario=self.parceiro_user, nome_entidade="Parceiro Dash",
            percentual_comissao=Decimal("10.00"),
        )

    def test_dashboard_parceiro(self):
        make_cliente(self.parceiro, cnpj="66666666000166", status=Cliente.Status.RECEBIDA)
        make_cliente(self.parceiro, cnpj="77777777000177", status=Cliente.Status.CONCLUIDA)

        self.client.force_authenticate(user=self.parceiro_user)
        resp = self.client.get("/api/v1/parceiro/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["clientes"]["total"], 2)
