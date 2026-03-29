"""
Endpoint de webhook do Asaas.
Recebe eventos, valida token, salva log e processa via Celery.
"""

import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import EventoWebhookAsaas

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def asaas_webhook(request):
    """Endpoint que recebe eventos do Asaas via webhook."""

    # 1. Validar token de seguranca
    token = request.headers.get("asaas-access-token", "")
    if settings.ASAAS_WEBHOOK_TOKEN and token != settings.ASAAS_WEBHOOK_TOKEN:
        logger.warning("Webhook Asaas: token invalido")
        return HttpResponse(status=401)

    # 2. Parsear payload
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    evento = payload.get("event", "")
    payment = payload.get("payment", {})
    pay_id = payment.get("id", "")

    # 3. Idempotencia — ignorar eventos ja processados
    if pay_id and EventoWebhookAsaas.objects.filter(
        asaas_payment_id=pay_id, evento=evento, processado=True
    ).exists():
        return HttpResponse(status=200)

    # 4. Salvar log do evento
    log = EventoWebhookAsaas.objects.create(
        evento=evento,
        asaas_payment_id=pay_id,
        payload=payload,
    )

    # 5. Processar via Celery (assincrono)
    from .tasks import processar_webhook_asaas
    processar_webhook_asaas.delay(log.id)

    logger.info(f"Webhook Asaas: {evento} — {pay_id}")
    return HttpResponse(status=200)
