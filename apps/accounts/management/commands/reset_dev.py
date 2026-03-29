"""
Reseta o banco de dev e recarrega tudo na ordem correta.
Uso: python manage.py reset_dev

Sequencia:
1. Drop todas as tabelas (evita conflitos de FK)
2. Migrate (recria tabelas + seeds de departamentos e categorias)
3. Criar superuser admin (pk=1, antes das fixtures que referenciam)
4. Carregar fixtures na ordem: CRM → RH → Financeiro
5. Setup groups (permissoes e grupos)
6. Resumo final
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Reseta o banco de dev: drop tables, migrate, fixtures, groups"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Nao pede confirmacao",
        )

    def handle(self, *args, **options):
        if not options["no_input"]:
            confirm = input(
                "\n⚠  Isso vai APAGAR TODOS os dados do banco e recriar do zero.\n"
                "   Tem certeza? (sim/nao): "
            )
            if confirm.lower() not in ("sim", "s", "yes", "y"):
                self.stdout.write("Cancelado.")
                return

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  RESET DEV — Recriando banco do zero")
        self.stdout.write("=" * 60 + "\n")

        self._drop_tables()
        self._migrate()
        self._create_superuser()
        self._load_fixtures()
        self._setup_groups()
        self._atribuir_permissoes_colaboradores()
        self._sincronizar_asaas()
        self._summary()

    def _drop_tables(self):
        self.stdout.write("1/7  Removendo tabelas...")
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            if tables:
                quoted = ",".join(f'"{t}"' for t in tables)
                cursor.execute(f"DROP TABLE IF EXISTS {quoted} CASCADE")
        self.stdout.write(self.style.SUCCESS(f"     {len(tables)} tabelas removidas"))

    def _migrate(self):
        self.stdout.write("2/7  Rodando migrations...")
        from django.core.management import call_command
        call_command("migrate", verbosity=0)
        self.stdout.write(self.style.SUCCESS("     Migrations aplicadas (inclui seeds de departamentos e categorias)"))

    def _create_superuser(self):
        self.stdout.write("3/7  Criando superuser admin...")
        from apps.accounts.models import Usuario
        admin = Usuario(
            pk=1,
            username="admin",
            email="admin@ruch.solutions",
            is_superuser=True,
            is_staff=True,
            first_name="Wilkerson",
            last_name="Carlos",
        )
        admin.set_password("admin123")
        admin.save()
        self.stdout.write(self.style.SUCCESS("     admin / admin123 (pk=1)"))

    def _load_fixtures(self):
        self.stdout.write("4/7  Carregando fixtures...")
        from django.core.management import call_command

        fixtures = [
            ("fixtures/dev_seed.json", "CRM"),
            ("fixtures/dev_seed_rh.json", "RH"),
            ("fixtures/dev_seed_financeiro.json", "Financeiro"),
        ]
        for path, label in fixtures:
            try:
                call_command("loaddata", path, verbosity=0)
                self.stdout.write(self.style.SUCCESS(f"     {label}: OK"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"     {label}: ERRO — {e}"))

    def _setup_groups(self):
        self.stdout.write("5/7  Configurando grupos e permissoes...")
        from django.core.management import call_command
        call_command("setup_groups", verbosity=0)
        self.stdout.write(self.style.SUCCESS("     7 grupos configurados"))

    def _atribuir_permissoes_colaboradores(self):
        self.stdout.write("6/7  Atribuindo permissoes por departamento/cargo...")
        from apps.rh.models import Colaborador
        from apps.rh.permissions import atribuir_permissoes
        count = 0
        for colab in Colaborador.objects.filter(usuario__isnull=False).select_related("cargo", "departamento", "usuario"):
            try:
                atribuir_permissoes(colab)
                count += 1
            except Exception:
                pass
        self.stdout.write(self.style.SUCCESS(f"     {count} colaborador(es) com permissoes atribuidas"))

    def _sincronizar_asaas(self):
        self.stdout.write("7/7  Sincronizando clientes com Asaas (opcional)...")
        try:
            from django.conf import settings
            if not getattr(settings, "ASAAS_API_KEY", "") or settings.ASAAS_API_KEY == "sua_chave_aqui":
                self.stdout.write(self.style.WARNING("     Pulado — ASAAS_API_KEY nao configurada"))
                return

            from apps.crm.models import Cliente
            from apps.financeiro.models import ClienteAsaas
            from apps.financeiro.services.asaas_client import AsaasClient

            api = AsaasClient()
            clientes = Cliente.objects.filter(ativo=True)
            count = 0
            for cliente in clientes:
                # Ja sincronizado?
                if ClienteAsaas.objects.filter(cliente=cliente).exists():
                    continue
                try:
                    existentes = api.buscar_cliente_por_cpf(cliente.cnpj)
                    if existentes:
                        asaas_id = existentes[0]["id"]
                    else:
                        resultado = api.criar_cliente(
                            nome=cliente.nome,
                            cpf_cnpj=cliente.cnpj,
                            email=cliente.email,
                            telefone=cliente.telefone,
                        )
                        asaas_id = resultado["id"]
                    ClienteAsaas.objects.create(cliente=cliente, asaas_id=asaas_id)
                    count += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"     {cliente.nome}: {e}"))
            self.stdout.write(self.style.SUCCESS(f"     {count} cliente(s) sincronizado(s) com Asaas"))

            # Sincronizar cobrancas e assinaturas
            if count > 0 or ClienteAsaas.objects.exists():
                from apps.financeiro.services.asaas_sync import sincronizar_tudo
                resultado = sincronizar_tudo()
                self.stdout.write(self.style.SUCCESS(
                    f"     {resultado['cobrancas_criadas']} cobranca(s), "
                    f"{resultado['assinaturas_criadas']} assinatura(s) importada(s)"
                ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"     Erro na sincronizacao Asaas: {e}"))

    def _summary(self):
        from apps.accounts.models import Usuario
        from apps.crm.models import Cliente
        from apps.rh.models import Colaborador, Departamento

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  PRONTO!")
        self.stdout.write("=" * 60)
        from apps.financeiro.models import ClienteAsaas, CobrancaAsaas

        self.stdout.write(f"  Usuarios:      {Usuario.objects.count()}")
        self.stdout.write(f"  Clientes:      {Cliente.objects.count()}")
        self.stdout.write(f"  Colaboradores: {Colaborador.objects.count()}")
        self.stdout.write(f"  Departamentos: {Departamento.objects.count()}")
        self.stdout.write(f"  Asaas sync:    {ClienteAsaas.objects.count()} clientes, {CobrancaAsaas.objects.count()} cobrancas")
        self.stdout.write(f"  Superuser:     admin / admin123")
        self.stdout.write(f"  Seed users:    testpass123")
        self.stdout.write("=" * 60 + "\n")
