"""
Sincronizacao bidirecional com Asaas.
Puxa cobrancas e assinaturas que existem no Asaas mas nao no sistema local.
Idempotente — seguro pra rodar multiplas vezes.

Protecoes para producao:
- Paginacao: percorre todas as paginas da API (100 por pagina)
- Rate limiting: 0.5s entre requests pra nao estourar limite do Asaas
- Idempotente: checa asaas_id e id_externo antes de criar
"""

import logging
import time
from decimal import Decimal

from apps.auditoria.utils import registrar as audit
from apps.financeiro.models import (
    AssinaturaAsaas, CategoriaFinanceira, ClienteAsaas, CobrancaAsaas,
    ContaBancaria, Lancamento,
)
from apps.financeiro.services.asaas_client import AsaasClient

logger = logging.getLogger(__name__)

# Pausa entre requests pra respeitar rate limit do Asaas
RATE_LIMIT_DELAY = 0.5  # segundos


def _get_conta_asaas():
    return ContaBancaria.objects.filter(nome__icontains="asaas").first()


def _get_categoria_receita():
    return CategoriaFinanceira.objects.filter(tipo="receita", pai__isnull=False).first()


def _listar_paginado(api, method, customer_id):
    """Percorre todas as paginas da API e retorna lista completa."""
    todos = []
    offset = 0
    limit = 100
    while True:
        time.sleep(RATE_LIMIT_DELAY)
        pagina = method(customer_id, offset=offset, limit=limit)
        if not pagina:
            break
        todos.extend(pagina)
        if len(pagina) < limit:
            break  # ultima pagina
        offset += limit
    return todos


def sincronizar_tudo():
    """Sincroniza cobrancas e assinaturas de todos os clientes vinculados.
    Retorna dict com contadores.
    """
    resultado = {
        "cobrancas_criadas": 0,
        "cobrancas_atualizadas": 0,
        "assinaturas_criadas": 0,
        "assinaturas_atualizadas": 0,
        "lancamentos_criados": 0,
        "erros": [],
    }

    clientes = ClienteAsaas.objects.select_related("cliente").all()
    if not clientes.exists():
        logger.info("Nenhum cliente sincronizado com Asaas.")
        return resultado

    try:
        api = AsaasClient()
    except Exception as e:
        resultado["erros"].append(f"Erro ao conectar com Asaas: {e}")
        return resultado

    for ca in clientes:
        try:
            _sync_cobrancas_cliente(api, ca, resultado)
        except Exception as e:
            erro = f"Erro ao sincronizar cobrancas de {ca.cliente.nome}: {e}"
            logger.error(erro)
            resultado["erros"].append(erro)

        try:
            _sync_assinaturas_cliente(api, ca, resultado)
        except Exception as e:
            erro = f"Erro ao sincronizar assinaturas de {ca.cliente.nome}: {e}"
            logger.error(erro)
            resultado["erros"].append(erro)

        # Rate limit entre clientes
        time.sleep(RATE_LIMIT_DELAY)

    # Registrar na auditoria
    total = resultado["cobrancas_criadas"] + resultado["assinaturas_criadas"] + resultado["lancamentos_criados"]
    if total > 0:
        audit(
            "sistema", "integracao",
            f"Sincronizacao Asaas: {resultado['cobrancas_criadas']} cobrancas, "
            f"{resultado['assinaturas_criadas']} assinaturas, "
            f"{resultado['lancamentos_criados']} lancamentos",
            fonte="celery",
            detalhes=resultado,
        )

    return resultado


def _sync_cobrancas_cliente(api, cliente_asaas, resultado):
    """Sincroniza cobrancas de um cliente com paginacao."""
    cobrancas_api = _listar_paginado(api, api.listar_cobrancas_cliente, cliente_asaas.asaas_id)

    for payment in cobrancas_api:
        asaas_id = payment.get("id", "")
        if not asaas_id:
            continue

        # Verificar se ja existe
        cobranca = CobrancaAsaas.objects.filter(asaas_id=asaas_id).first()

        if cobranca:
            # Atualizar status se mudou
            novo_status = payment.get("status", "")
            if novo_status and novo_status != cobranca.status:
                cobranca.status = novo_status
                cobranca.valor_liquido = Decimal(str(payment.get("netValue", 0) or 0))
                cobranca.billing_type = payment.get("billingType", cobranca.billing_type)
                cobranca.invoice_url = payment.get("invoiceUrl", cobranca.invoice_url)
                cobranca.bank_slip_url = payment.get("bankSlipUrl", cobranca.bank_slip_url)
                if payment.get("paymentDate"):
                    cobranca.pago_em = payment["paymentDate"]
                cobranca.save()
                resultado["cobrancas_atualizadas"] += 1

                # Atualizar lancamento vinculado
                if cobranca.lancamento:
                    if novo_status in ("RECEIVED", "CONFIRMED"):
                        cobranca.lancamento.status = "confirmado"
                        cobranca.lancamento.data_pagamento = payment.get("paymentDate")
                        cobranca.lancamento.valor_liquido = cobranca.valor_liquido
                        cobranca.lancamento.save(update_fields=["status", "data_pagamento", "valor_liquido"])
                    elif novo_status in ("REFUNDED", "DELETED"):
                        cobranca.lancamento.status = "cancelado"
                        cobranca.lancamento.save(update_fields=["status"])
        else:
            # Criar cobranca local
            subscription = payment.get("subscription")
            assinatura_local = None
            if subscription:
                assinatura_local = AssinaturaAsaas.objects.filter(asaas_id=subscription).first()

            cobranca = CobrancaAsaas.objects.create(
                asaas_id=asaas_id,
                cliente=cliente_asaas.cliente,
                assinatura=assinatura_local,
                tipo="mensalidade" if subscription else "avulsa",
                valor=Decimal(str(payment.get("value", 0))),
                valor_liquido=Decimal(str(payment.get("netValue", 0) or 0)),
                vencimento=payment.get("dueDate", ""),
                status=payment.get("status", ""),
                billing_type=payment.get("billingType", ""),
                invoice_url=payment.get("invoiceUrl", ""),
                bank_slip_url=payment.get("bankSlipUrl", ""),
                pago_em=payment.get("paymentDate"),
            )
            resultado["cobrancas_criadas"] += 1

            # Criar lancamento se nao existir
            if not Lancamento.objects.filter(id_externo=asaas_id).exists():
                conta = _get_conta_asaas()
                cat = _get_categoria_receita()
                if conta and cat:
                    status_lanc = "confirmado" if payment.get("status") in ("RECEIVED", "CONFIRMED") else "pendente"
                    if payment.get("status") in ("REFUNDED", "DELETED"):
                        status_lanc = "cancelado"

                    lanc = Lancamento.objects.create(
                        tipo="receita",
                        descricao=f"Asaas: {payment.get('description', asaas_id)}",
                        valor=cobranca.valor,
                        valor_liquido=cobranca.valor_liquido,
                        categoria=cat,
                        conta=conta,
                        canal="gateway",
                        data_vencimento=cobranca.vencimento,
                        data_competencia=cobranca.vencimento,
                        data_pagamento=payment.get("paymentDate"),
                        status=status_lanc,
                        cliente=cliente_asaas.cliente,
                        id_externo=asaas_id,
                    )
                    cobranca.lancamento = lanc
                    cobranca.save(update_fields=["lancamento"])
                    resultado["lancamentos_criados"] += 1


def _sync_assinaturas_cliente(api, cliente_asaas, resultado):
    """Sincroniza assinaturas de um cliente com paginacao."""
    assinaturas_api = _listar_paginado(api, api.listar_assinaturas_cliente, cliente_asaas.asaas_id)

    for sub in assinaturas_api:
        asaas_id = sub.get("id", "")
        if not asaas_id:
            continue

        assinatura = AssinaturaAsaas.objects.filter(asaas_id=asaas_id).first()

        if assinatura:
            # Atualizar status se mudou
            novo_status = sub.get("status", "")
            if novo_status and novo_status != assinatura.status:
                assinatura.status = novo_status
                assinatura.valor = Decimal(str(sub.get("value", assinatura.valor)))
                assinatura.proximo_vencimento = sub.get("nextDueDate")
                assinatura.save()
                resultado["assinaturas_atualizadas"] += 1
        else:
            # Criar assinatura local
            AssinaturaAsaas.objects.create(
                asaas_id=asaas_id,
                cliente=cliente_asaas.cliente,
                valor=Decimal(str(sub.get("value", 0))),
                ciclo=sub.get("cycle", "MONTHLY"),
                proximo_vencimento=sub.get("nextDueDate"),
                status=sub.get("status", "ACTIVE"),
                billing_type=sub.get("billingType", ""),
            )
            resultado["assinaturas_criadas"] += 1
