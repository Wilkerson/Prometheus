"""Tasks Celery do modulo Accounts / Sistema."""

from celery import shared_task


@shared_task(name="sistema.backup_db")
def backup_db():
    """Backup diario do banco PostgreSQL.
    Salva localmente + upload pra storage externo (se configurado).
    Remove backups locais com mais de 30 dias.
    Agendado via Celery Beat.
    """
    from django.core.management import call_command
    call_command("backup_db", "--upload", "--cleanup", "30")
