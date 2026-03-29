"""
Cliente HTTP para a API do Asaas.
Documentacao: https://docs.asaas.com/reference
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AsaasClient:
    """Cliente HTTP para comunicacao com a API do Asaas."""

    def __init__(self):
        self.base_url = settings.ASAAS_BASE_URL
        self.headers = {
            "access_token": settings.ASAAS_API_KEY,
            "Content-Type": "application/json",
        }
        self.timeout = 30

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        kwargs.setdefault("headers", self.headers)
        kwargs.setdefault("timeout", self.timeout)
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code >= 400:
                # Extrair mensagem de erro do Asaas
                try:
                    body = response.json()
                    errors = body.get("errors", [])
                    if errors:
                        msgs = [e.get("description", e.get("code", "")) for e in errors]
                        error_msg = " | ".join(msgs)
                    else:
                        error_msg = response.text
                except Exception:
                    error_msg = response.text
                logger.error(f"Asaas API {response.status_code}: {method} {path} — {error_msg}")
                raise Exception(f"Asaas: {error_msg}")
            return response.json() if response.content else {}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Asaas API connection error: {method} {path} — {e}")
            raise Exception("Não foi possível conectar ao Asaas. Verifique sua conexão.")
        except requests.exceptions.Timeout:
            raise Exception("Asaas: tempo limite excedido. Tente novamente.")

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def post(self, path, data):
        return self._request("POST", path, json=data)

    def put(self, path, data):
        return self._request("PUT", path, json=data)

    def delete(self, path):
        url = f"{self.base_url}{path}"
        response = requests.delete(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.status_code

    # -----------------------------------------------------------------
    # Clientes
    # -----------------------------------------------------------------
    def criar_cliente(self, nome, cpf_cnpj, email, telefone=None):
        """Cria cliente no Asaas. Retorna dict com 'id' (cus_xxxx)."""
        data = {
            "name": nome,
            "cpfCnpj": cpf_cnpj,
            "email": email,
        }
        if telefone:
            data["mobilePhone"] = telefone
        return self.post("/customers", data)

    def buscar_cliente_por_cpf(self, cpf_cnpj):
        """Busca cliente por CPF/CNPJ. Retorna lista."""
        result = self.get("/customers", params={"cpfCnpj": cpf_cnpj})
        return result.get("data", [])

    # -----------------------------------------------------------------
    # Cobrancas
    # -----------------------------------------------------------------
    def criar_cobranca(self, customer_id, valor, vencimento, descricao="",
                       billing_type="UNDEFINED"):
        """Cria cobranca avulsa. billing_type: BOLETO, PIX, CREDIT_CARD, UNDEFINED."""
        data = {
            "customer": customer_id,
            "billingType": billing_type,
            "value": float(valor),
            "dueDate": str(vencimento),
            "description": descricao,
        }
        return self.post("/payments", data)

    def buscar_cobranca(self, payment_id):
        """Busca cobranca por ID (pay_xxxx)."""
        return self.get(f"/payments/{payment_id}")

    def pix_qrcode(self, payment_id):
        """Retorna QR Code Pix da cobranca."""
        return self.get(f"/payments/{payment_id}/pixQrCode")

    def linha_digitavel(self, payment_id):
        """Retorna linha digitavel do boleto."""
        return self.get(f"/payments/{payment_id}/identificationField")

    def estornar(self, payment_id):
        """Estorna cobranca."""
        return self.post(f"/payments/{payment_id}/refund", {})

    # -----------------------------------------------------------------
    # Assinaturas
    # -----------------------------------------------------------------
    def criar_assinatura(self, customer_id, valor, ciclo="MONTHLY",
                         vencimento=None, descricao="",
                         billing_type="UNDEFINED"):
        """Cria assinatura recorrente."""
        data = {
            "customer": customer_id,
            "billingType": billing_type,
            "value": float(valor),
            "cycle": ciclo,
            "description": descricao,
        }
        if vencimento:
            data["nextDueDate"] = str(vencimento)
        return self.post("/subscriptions", data)

    def atualizar_assinatura(self, subscription_id, data):
        """Atualiza assinatura."""
        return self.put(f"/subscriptions/{subscription_id}", data)

    def cancelar_assinatura(self, subscription_id):
        """Cancela assinatura."""
        return self.delete(f"/subscriptions/{subscription_id}")

    def cobrancas_da_assinatura(self, subscription_id):
        """Lista cobrancas de uma assinatura."""
        result = self.get(f"/subscriptions/{subscription_id}/payments")
        return result.get("data", [])

    # -----------------------------------------------------------------
    # Listagens (para sincronizacao)
    # -----------------------------------------------------------------
    def listar_cobrancas_cliente(self, customer_id, offset=0, limit=100):
        """Lista cobrancas de um cliente."""
        result = self.get("/payments", params={
            "customer": customer_id,
            "offset": offset,
            "limit": limit,
        })
        return result.get("data", [])

    def listar_assinaturas_cliente(self, customer_id, offset=0, limit=100):
        """Lista assinaturas de um cliente."""
        result = self.get("/subscriptions", params={
            "customer": customer_id,
            "offset": offset,
            "limit": limit,
        })
        return result.get("data", [])
