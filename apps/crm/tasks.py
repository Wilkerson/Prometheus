import logging

import requests
from celery import shared_task
from decouple import config

logger = logging.getLogger(__name__)

SISTEMA_EXTERNO_URL = config("SISTEMA_EXTERNO_URL", default="")
SISTEMA_EXTERNO_API_KEY = config("SISTEMA_EXTERNO_API_KEY", default="")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enviar_lead_sistema_externo(self, lead_id):
    """
    Envia os dados do lead para o sistema externo quando o status
    muda para 'em_processamento'. O sistema externo processará
    a implantação e retornará o status via callback.
    """
    from .models import Lead

    try:
        lead = Lead.objects.select_related("parceiro").get(id=lead_id)
    except Lead.DoesNotExist:
        logger.error("Lead %s não encontrada.", lead_id)
        return

    if not SISTEMA_EXTERNO_URL:
        logger.warning("SISTEMA_EXTERNO_URL não configurada. Envio ignorado para lead %s.", lead_id)
        return

    payload = {
        "lead_id": lead.id,
        "nome": lead.nome,
        "email": lead.email,
        "telefone": lead.telefone,
        "produto_interesse": lead.produto_interesse,
        "parceiro": lead.parceiro.nome_entidade,
    }

    try:
        response = requests.post(
            f"{SISTEMA_EXTERNO_URL}/api/leads/",
            json=payload,
            headers={"X-API-Key": SISTEMA_EXTERNO_API_KEY},
            timeout=30,
        )
        response.raise_for_status()
        logger.info("Lead %s enviada com sucesso para sistema externo.", lead_id)
    except requests.RequestException as exc:
        logger.error("Erro ao enviar lead %s: %s", lead_id, exc)
        raise self.retry(exc=exc)
