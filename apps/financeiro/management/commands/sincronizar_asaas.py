"""
Sincroniza cobrancas e assinaturas do Asaas com o sistema local.
Puxa dados que existem no Asaas mas nao no Prometheus.
Idempotente — seguro pra rodar multiplas vezes.

Uso: python manage.py sincronizar_asaas
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sincroniza cobrancas e assinaturas do Asaas com o sistema local"

    def handle(self, *args, **options):
        from apps.financeiro.services.asaas_sync import sincronizar_tudo

        self.stdout.write("\nSincronizando com Asaas...\n")

        resultado = sincronizar_tudo()

        self.stdout.write(f"  Cobrancas criadas:      {resultado['cobrancas_criadas']}")
        self.stdout.write(f"  Cobrancas atualizadas:  {resultado['cobrancas_atualizadas']}")
        self.stdout.write(f"  Assinaturas criadas:    {resultado['assinaturas_criadas']}")
        self.stdout.write(f"  Assinaturas atualizadas:{resultado['assinaturas_atualizadas']}")
        self.stdout.write(f"  Lancamentos criados:    {resultado['lancamentos_criados']}")

        if resultado["erros"]:
            self.stdout.write(self.style.WARNING(f"\n  {len(resultado['erros'])} erro(s):"))
            for erro in resultado["erros"]:
                self.stdout.write(self.style.ERROR(f"    - {erro}"))
        else:
            self.stdout.write(self.style.SUCCESS("\nSincronizacao concluida sem erros!"))
