"""
Dispara alertas periodicos do modulo RH.
Uso: python manage.py rh_alertas
Recomendado rodar diariamente via Celery Beat ou cron.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.rh.models import AcaoPDI, DocumentoColaborador, SaldoFerias


class Command(BaseCommand):
    help = "Dispara alertas de documentos vencendo, ferias vencidas e acoes PDI atrasadas"

    def handle(self, *args, **options):
        hoje = timezone.now().date()
        total = 0

        # 1. Documentos proximos do vencimento
        from apps.rh.notifications import notificar_documento_vencendo, notificar_documento_vencido

        docs_vencendo = DocumentoColaborador.objects.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + timezone.timedelta(days=30),
        ).select_related("colaborador")

        from apps.rh.emails import enviar_documento_vencendo

        for doc in docs_vencendo:
            dias = (doc.data_vencimento - hoje).days
            if dias <= doc.alerta_dias_antes:
                notificar_documento_vencendo(doc)
                enviar_documento_vencendo(doc)
                total += 1

        docs_vencidos = DocumentoColaborador.objects.filter(
            data_vencimento=hoje - timezone.timedelta(days=1),
        ).select_related("colaborador")

        for doc in docs_vencidos:
            notificar_documento_vencido(doc)
            total += 1

        # 2. Ferias vencidas (CLT com saldo expirado > 12 meses)
        from apps.rh.notifications import notificar_ferias_vencidas

        limite = hoje - timezone.timedelta(days=365)
        from django.db.models import F
        saldos_vencidos = SaldoFerias.objects.filter(
            colaborador__status="ativo",
            periodo_fim__lt=limite,
        ).exclude(
            dias_usufruidos__gte=F("dias_direito")
        ).select_related("colaborador")

        for saldo in saldos_vencidos:
            notificar_ferias_vencidas(saldo)
            total += 1

        # 3. Acoes PDI atrasadas
        from apps.rh.notifications import notificar_pdi_acao_atrasada

        acoes_atrasadas = AcaoPDI.objects.filter(
            prazo__lt=hoje,
            status__in=["pendente", "em_andamento"],
            pdi__colaborador__status="ativo",
        ).select_related("pdi__colaborador")

        for acao in acoes_atrasadas:
            notificar_pdi_acao_atrasada(acao)
            total += 1

        self.stdout.write(
            self.style.SUCCESS(f"Alertas RH: {total} notificacao(es) disparada(s)")
        )
