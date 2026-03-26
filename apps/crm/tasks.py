import logging

import requests
from celery import shared_task
from decouple import config

logger = logging.getLogger(__name__)

SISTEMA_EXTERNO_URL = config("SISTEMA_EXTERNO_URL", default="")
SISTEMA_EXTERNO_API_KEY = config("SISTEMA_EXTERNO_API_KEY", default="")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enviar_cliente_sistema_externo(self, cliente_id):
    """
    Envia os dados do cliente para o Zypher quando o status muda
    para 'em_processamento'. O Zypher processara a implantacao e
    retornara via callback: concluida ou falha_implantacao.
    """
    from .models import Cliente

    try:
        cliente = Cliente.objects.select_related("parceiro").get(id=cliente_id)
    except Cliente.DoesNotExist:
        logger.error("Cliente %s nao encontrado.", cliente_id)
        return

    if not SISTEMA_EXTERNO_URL:
        logger.warning("SISTEMA_EXTERNO_URL nao configurada. Envio ignorado para cliente %s.", cliente_id)
        return

    payload = {
        "cliente_id": cliente.id,
        "nome": cliente.nome,
        "cnpj": cliente.cnpj,
        "email": cliente.email,
        "telefone": cliente.telefone,
        "endereco": cliente.endereco,
        "cep": cliente.cep,
        "produto_interesse": cliente.produto_interesse,
        "parceiro": cliente.parceiro.nome_entidade,
    }

    try:
        response = requests.post(
            f"{SISTEMA_EXTERNO_URL}/api/clientes/",
            json=payload,
            headers={"X-API-Key": SISTEMA_EXTERNO_API_KEY},
            timeout=30,
        )
        response.raise_for_status()
        logger.info("Cliente %s enviado com sucesso para sistema externo.", cliente_id)
    except requests.RequestException as exc:
        logger.error("Erro ao enviar cliente %s: %s", cliente_id, exc)
        raise self.retry(exc=exc)
