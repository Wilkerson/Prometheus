"""
Backup do banco PostgreSQL com compressao gzip.
Salva localmente e opcionalmente envia pra storage externo (S3/R2/GCS).

Uso:
  python manage.py backup_db              # backup local
  python manage.py backup_db --upload     # backup local + upload pra storage
  python manage.py backup_db --cleanup 7  # remove backups locais com mais de 7 dias
"""

import gzip
import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Faz backup do banco PostgreSQL (pg_dump + gzip)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--upload",
            action="store_true",
            help="Envia backup pra storage externo (S3/R2/GCS)",
        )
        parser.add_argument(
            "--cleanup",
            type=int,
            default=0,
            help="Remove backups locais com mais de N dias",
        )

    def handle(self, *args, **options):
        db = settings.DATABASES["default"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{db['NAME']}_{timestamp}.sql.gz"

        # Diretorio de backups
        backup_dir = Path(settings.BASE_DIR) / "backups"
        backup_dir.mkdir(exist_ok=True)
        filepath = backup_dir / filename

        self.stdout.write(f"Criando backup: {filename}")

        # pg_dump com gzip
        env = os.environ.copy()
        env["PGPASSWORD"] = db["PASSWORD"]

        cmd = [
            "pg_dump",
            "-h", db.get("HOST", "localhost"),
            "-p", str(db.get("PORT", "5432")),
            "-U", db["USER"],
            "-d", db["NAME"],
            "--no-owner",
            "--no-privileges",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, env=env, timeout=300)

            if result.returncode != 0:
                error = result.stderr.decode("utf-8", errors="replace")
                self.stdout.write(self.style.ERROR(f"Erro no pg_dump: {error}"))
                return

            # Comprimir
            with gzip.open(filepath, "wb") as f:
                f.write(result.stdout)

            size_mb = filepath.stat().st_size / (1024 * 1024)
            self.stdout.write(self.style.SUCCESS(f"Backup criado: {filepath} ({size_mb:.1f} MB)"))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                "pg_dump nao encontrado. Instale o PostgreSQL client ou adicione ao PATH."
            ))
            return
        except subprocess.TimeoutExpired:
            self.stdout.write(self.style.ERROR("Timeout — pg_dump demorou mais de 5 minutos."))
            return

        # Upload pra storage externo
        if options["upload"]:
            self._upload(filepath, filename)

        # Cleanup de backups antigos
        if options["cleanup"] > 0:
            self._cleanup(backup_dir, options["cleanup"])

        # Registrar na auditoria
        try:
            from apps.auditoria.utils import registrar
            registrar(
                "exportacao", "sistema",
                f"Backup do banco: {filename} ({size_mb:.1f} MB)",
                fonte="sistema",
                detalhes={"arquivo": filename, "tamanho_mb": round(size_mb, 1)},
            )
        except Exception:
            pass

    def _upload(self, filepath, filename):
        """Envia backup pra storage configurado (S3/R2/GCS)."""
        provider = getattr(settings, "STORAGE_PROVIDER", "local")

        if provider == "local":
            self.stdout.write(self.style.WARNING(
                "Upload pulado — STORAGE_PROVIDER=local. Configure S3/R2/GCS no .env."
            ))
            return

        try:
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile

            remote_path = f"backups/{filename}"
            with open(filepath, "rb") as f:
                default_storage.save(remote_path, ContentFile(f.read()))

            self.stdout.write(self.style.SUCCESS(f"Upload concluido: {remote_path}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro no upload: {e}"))

    def _cleanup(self, backup_dir, dias):
        """Remove backups locais mais antigos que N dias."""
        limite = datetime.now() - timedelta(days=dias)
        removidos = 0
        for f in backup_dir.glob("backup_*.sql.gz"):
            if datetime.fromtimestamp(f.stat().st_mtime) < limite:
                f.unlink()
                removidos += 1
        if removidos:
            self.stdout.write(self.style.SUCCESS(f"Cleanup: {removidos} backup(s) antigo(s) removido(s)"))
