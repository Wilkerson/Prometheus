"""
Gera despesas recorrentes para o proximo mes.
Uso: python manage.py gerar_recorrentes
Recomendado rodar no dia 1 de cada mes via Celery Beat.
"""

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.financeiro.models import Despesa


DELTA = {
    "mensal": relativedelta(months=1),
    "trimestral": relativedelta(months=3),
    "anual": relativedelta(years=1),
}


class Command(BaseCommand):
    help = "Gera despesas recorrentes para o proximo periodo"

    def handle(self, *args, **options):
        hoje = timezone.now().date()
        total = 0

        # Busca despesas recorrentes pagas cuja proxima ocorrencia ainda nao existe
        recorrentes = Despesa.objects.filter(
            recorrencia__in=["mensal", "trimestral", "anual"],
            status="pago",
        )

        for despesa in recorrentes:
            delta = DELTA.get(despesa.recorrencia)
            if not delta:
                continue

            proximo_vencimento = despesa.vencimento + delta

            # Verifica se ja existe despesa para o proximo periodo
            ja_existe = Despesa.objects.filter(
                fornecedor=despesa.fornecedor,
                descricao=despesa.descricao,
                vencimento=proximo_vencimento,
            ).exists()

            if ja_existe:
                continue

            # Criar nova despesa para o proximo periodo
            Despesa.objects.create(
                fornecedor=despesa.fornecedor,
                descricao=despesa.descricao,
                categoria=despesa.categoria,
                valor=despesa.valor,
                vencimento=proximo_vencimento,
                recorrencia=despesa.recorrencia,
                conta=despesa.conta,
                departamento=despesa.departamento,
                observacao=f"Gerada automaticamente (recorrente {despesa.get_recorrencia_display()})",
            )
            total += 1

        self.stdout.write(
            self.style.SUCCESS(f"Despesas recorrentes: {total} gerada(s)")
        )
