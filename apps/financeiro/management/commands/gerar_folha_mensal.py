"""
Gera folha de pagamento automatica para o mes corrente.
Cria pagamentos com status 'calculado' para todos os colaboradores
ativos, com base na remuneracao cadastrada no RH.

Uso: python manage.py gerar_folha_mensal
Recomendado: rodar no 1o dia de cada mes via Celery Beat.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.financeiro.models import ConfiguracaoFolha, FolhaPagamento
from apps.rh.models import Colaborador


class Command(BaseCommand):
    help = "Gera folha de pagamento automatica para o mes corrente"

    def add_arguments(self, parser):
        parser.add_argument(
            "--competencia",
            type=str,
            help="Competencia no formato YYYY-MM-DD (default: 1o dia do mes atual)",
        )

    def handle(self, *args, **options):
        config = ConfiguracaoFolha.get()
        hoje = timezone.now().date()
        competencia_str = options.get("competencia")

        if competencia_str:
            from datetime import date
            competencia = date.fromisoformat(competencia_str)
        else:
            competencia = hoje.replace(day=1)

        total = 0
        colaboradores = Colaborador.objects.filter(status="ativo")

        for colab in colaboradores:
            # Determinar tipo baseado no contrato
            if colab.tipo_contrato == "clt" and config.gerar_salario:
                tipo = "salario"
            elif colab.tipo_contrato == "pj" and config.gerar_pj:
                tipo = "pagamento_pj"
            else:
                continue

            # Verificar se ja existe
            if FolhaPagamento.objects.filter(
                colaborador=colab, tipo=tipo, competencia=competencia
            ).exists():
                continue

            FolhaPagamento.objects.create(
                colaborador=colab,
                tipo=tipo,
                competencia=competencia,
                valor_bruto=colab.remuneracao,
                desconto_inss=0,
                desconto_ir=0,
                outros_descontos=0,
                valor_liquido=colab.remuneracao,
                status="calculado",
                conta=config.conta_padrao,
                observacao=f"Gerado automaticamente — {competencia:%m/%Y}",
            )
            total += 1
            self.stdout.write(f"  {colab.nome_completo} ({tipo}) — R$ {colab.remuneracao}")

        # Gerar pro-labore (se configurado)
        # Pro-labore nao tem colaborador vinculado necessariamente,
        # mas se o socio estiver cadastrado como colaborador, gera tambem
        if config.gerar_pro_labore:
            socios = Colaborador.objects.filter(
                status="ativo",
                cargo__nivel="diretor",
            )
            for socio in socios:
                if FolhaPagamento.objects.filter(
                    colaborador=socio, tipo="pro_labore", competencia=competencia
                ).exists():
                    continue

                FolhaPagamento.objects.create(
                    colaborador=socio,
                    tipo="pro_labore",
                    competencia=competencia,
                    valor_bruto=socio.remuneracao,
                    desconto_inss=0,
                    desconto_ir=0,
                    outros_descontos=0,
                    valor_liquido=socio.remuneracao,
                    status="calculado",
                    conta=config.conta_padrao,
                    observacao=f"Pró-labore gerado automaticamente — {competencia:%m/%Y}",
                )
                total += 1
                self.stdout.write(f"  {socio.nome_completo} (pro-labore) — R$ {socio.remuneracao}")

        if total > 0:
            from apps.financeiro.notifications import notificar_folha_gerada
            notificar_folha_gerada(competencia, total)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Folha {competencia:%m/%Y}: {total} pagamento(s) gerado(s) "
                    f"(pgto previsto: {config.dia_pagamento}o dia util)"
                )
            )
        else:
            existentes = FolhaPagamento.objects.filter(competencia=competencia).count()
            if existentes > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Folha {competencia:%m/%Y}: ja gerada ({existentes} pagamento(s) existentes)"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Folha {competencia:%m/%Y}: nenhum colaborador ativo encontrado"
                    )
                )
