"""Servico de envio de emails do modulo RH."""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def enviar_acesso_criado(colaborador, username, senha_temporaria):
    """Envia email ao colaborador com dados de acesso ao sistema."""
    contexto = {
        "colaborador": colaborador,
        "username": username,
        "senha": senha_temporaria,
        "url_login": settings.LOGIN_URL,
    }
    assunto = "RUCH — Seu acesso ao sistema foi criado"
    corpo_html = render_to_string("rh/emails/acesso_criado.html", contexto)
    corpo_texto = (
        f"Ola {colaborador.nome_completo},\n\n"
        f"Seu acesso ao sistema Prometheus foi criado.\n\n"
        f"Usuario: {username}\n"
        f"Senha temporaria: {senha_temporaria}\n\n"
        f"Acesse o sistema e altere sua senha no primeiro login.\n\n"
        f"Atenciosamente,\nRUCH Solutions"
    )
    send_mail(
        subject=assunto,
        message=corpo_texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[colaborador.email_pessoal],
        html_message=corpo_html,
        fail_silently=True,
    )


def enviar_ausencia_aprovada(ausencia):
    """Notifica colaborador que sua ausencia foi aprovada."""
    colab = ausencia.colaborador
    if not colab.email_pessoal:
        return
    contexto = {"ausencia": ausencia, "colaborador": colab}
    assunto = f"RUCH — Sua solicitacao de {ausencia.get_tipo_display()} foi aprovada"
    corpo_html = render_to_string("rh/emails/ausencia_aprovada.html", contexto)
    corpo_texto = (
        f"Ola {colab.nome_completo},\n\n"
        f"Sua solicitacao de {ausencia.get_tipo_display()} "
        f"({ausencia.data_inicio:%d/%m/%Y} a {ausencia.data_fim:%d/%m/%Y}) "
        f"foi aprovada.\n\n"
        f"Atenciosamente,\nRUCH Solutions"
    )
    send_mail(
        subject=assunto,
        message=corpo_texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[colab.email_pessoal],
        html_message=corpo_html,
        fail_silently=True,
    )


def enviar_ausencia_rejeitada(ausencia):
    """Notifica colaborador que sua ausencia foi rejeitada."""
    colab = ausencia.colaborador
    if not colab.email_pessoal:
        return
    contexto = {"ausencia": ausencia, "colaborador": colab}
    assunto = f"RUCH — Sua solicitacao de {ausencia.get_tipo_display()} foi rejeitada"
    corpo_html = render_to_string("rh/emails/ausencia_rejeitada.html", contexto)
    corpo_texto = (
        f"Ola {colab.nome_completo},\n\n"
        f"Sua solicitacao de {ausencia.get_tipo_display()} "
        f"({ausencia.data_inicio:%d/%m/%Y} a {ausencia.data_fim:%d/%m/%Y}) "
        f"foi rejeitada.\n\n"
        f"Motivo: {ausencia.justificativa_rejeicao or 'Nao informado'}\n\n"
        f"Atenciosamente,\nRUCH Solutions"
    )
    send_mail(
        subject=assunto,
        message=corpo_texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[colab.email_pessoal],
        html_message=corpo_html,
        fail_silently=True,
    )


def enviar_pesquisa_enps_ativa(pesquisa, colaboradores_emails):
    """Envia email para todos os colaboradores sobre nova pesquisa eNPS."""
    assunto = f"RUCH — Nova pesquisa eNPS: {pesquisa.titulo}"
    corpo_texto = (
        f"Uma nova pesquisa de satisfacao foi aberta.\n\n"
        f"Titulo: {pesquisa.titulo}\n"
        f"Responda ate: {pesquisa.data_encerramento:%d/%m/%Y}\n\n"
        f"Sua opiniao e muito importante para a RUCH.\n"
        f"Acesse o sistema para responder.\n\n"
        f"Atenciosamente,\nRUCH Solutions"
    )
    for email in colaboradores_emails:
        send_mail(
            subject=assunto,
            message=corpo_texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )


def enviar_documento_vencendo(documento):
    """Envia email ao colaborador sobre documento proximo do vencimento."""
    colab = documento.colaborador
    if not colab.email_pessoal:
        return
    from django.utils import timezone
    dias = (documento.data_vencimento - timezone.now().date()).days
    assunto = f"RUCH — Documento a vencer: {documento.nome}"
    corpo_texto = (
        f"Ola {colab.nome_completo},\n\n"
        f"Seu documento '{documento.nome}' vence em {dias} dia(s) "
        f"({documento.data_vencimento:%d/%m/%Y}).\n\n"
        f"Entre em contato com o RH para providenciar a renovacao.\n\n"
        f"Atenciosamente,\nRUCH Solutions"
    )
    send_mail(
        subject=assunto,
        message=corpo_texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[colab.email_pessoal],
        fail_silently=True,
    )
