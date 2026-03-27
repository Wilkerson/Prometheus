"""Tasks Celery do modulo RH."""

from celery import shared_task


@shared_task(name="rh.alertas_diarios")
def alertas_diarios():
    """Dispara alertas de documentos vencendo, ferias vencidas e PDI atrasado.
    Agendado via Celery Beat para rodar diariamente.
    """
    from django.core.management import call_command
    call_command("rh_alertas")
