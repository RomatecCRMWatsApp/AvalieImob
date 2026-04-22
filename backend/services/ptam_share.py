# @module services.ptam_share — Envio de PTAM por email com PDF em anexo
"""Sharing service for PTAM documents.

Provides:
  - enviar_ptam_email: sends PTAM PDF by email (SendGrid or SMTP)
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("romatec.ptam_share")

PLATFORM_URL = os.environ.get("PLATFORM_URL", "https://avalieimob.consultoriaromatec.com.br")
COLOR_GREEN = "#1B4D1B"
COLOR_GOLD = "#D4A830"


# ── HTML email template ───────────────────────────────────────────────────────

def _build_ptam_email_html(
    numero: str,
    endereco: str,
    nome_dest: str,
    nome_avaliador: str,
    registro_profissional: str,
    mensagem_extra: str,
) -> str:
    year = datetime.utcnow().year
    saudacao = f"Prezado(a) {nome_dest}" if nome_dest else "Prezado(a)"
    imovel_str = endereco or "imóvel avaliado"
    mensagem_bloco = (
        f'<p style="color:#555555;font-size:14px;line-height:1.6;margin:0 0 20px;">'
        f'{mensagem_extra}</p>'
        if mensagem_extra else ""
    )
    avaliador_bloco = ""
    if nome_avaliador:
        avaliador_bloco = f"""
            <tr>
              <td style="padding:8px 12px;background:#f5f5f5;color:#555;font-size:13px;
                          font-weight:600;width:40%;border-bottom:1px solid #ebebeb;">Avaliador</td>
              <td style="padding:8px 12px;color:#222;font-size:13px;
                          border-bottom:1px solid #ebebeb;">{nome_avaliador}</td>
            </tr>"""
    registro_bloco = ""
    if registro_profissional:
        registro_bloco = f"""
            <tr>
              <td style="padding:8px 12px;background:#f5f5f5;color:#555;font-size:13px;
                          font-weight:600;">CREA/CRECI/CFTMA</td>
              <td style="padding:8px 12px;color:#222;font-size:13px;">{registro_profissional}</td>
            </tr>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>PTAM {numero}</title></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#f4f4f4;padding:30px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" border="0"
             style="max-width:600px;background:#ffffff;border-radius:8px;
                    overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.12);">
        <!-- Header -->
        <tr>
          <td style="background:{COLOR_GREEN};padding:28px 32px;text-align:center;">
            <p style="margin:0;color:#ffffff;font-size:13px;letter-spacing:1px;
                       text-transform:uppercase;opacity:0.85;">RomaTec Consultoria Total</p>
            <h1 style="margin:6px 0 0;color:{COLOR_GOLD};font-size:22px;font-weight:700;">
              AvalieImob</h1>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:32px;">
            <h2 style="color:{COLOR_GREEN};margin:0 0 16px;font-size:20px;">
              Parecer Técnico de Avaliação Mercadológica</h2>
            <p style="color:#333333;font-size:15px;line-height:1.7;margin:0 0 20px;">
              {saudacao},<br>
              Segue em anexo o <strong>PTAM nº {numero}</strong>,
              referente ao imóvel <em>{imovel_str}</em>.
            </p>
            {mensagem_bloco}
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="border:1px solid #ebebeb;border-radius:6px;overflow:hidden;margin-bottom:28px;">
              <tr>
                <td style="padding:8px 12px;background:#f5f5f5;color:#555;font-size:13px;
                            font-weight:600;width:40%;border-bottom:1px solid #ebebeb;">Número PTAM</td>
                <td style="padding:8px 12px;color:#222;font-size:13px;
                            border-bottom:1px solid #ebebeb;"><strong>{numero}</strong></td>
              </tr>
              <tr>
                <td style="padding:8px 12px;background:#f5f5f5;color:#555;font-size:13px;
                            font-weight:600;width:40%;border-bottom:1px solid #ebebeb;">Imóvel</td>
                <td style="padding:8px 12px;color:#222;font-size:13px;
                            border-bottom:1px solid #ebebeb;">{imovel_str}</td>
              </tr>
              {avaliador_bloco}
              {registro_bloco}
            </table>
            <p style="color:#888888;font-size:12px;text-align:center;margin:0;">
              O documento está em anexo a este e-mail.
            </p>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f9f9f9;padding:20px 32px;border-top:1px solid #e8e8e8;
                      text-align:center;">
            <p style="margin:0;color:#888888;font-size:12px;line-height:1.6;">
              RomaTec Consultoria Total &bull; AvalieImob<br>
              Este e-mail foi gerado automaticamente pela plataforma AvalieImob.<br>
              O PTAM em anexo possui validade técnica conforme NBR 14.653.<br>
              &copy; {year} RomaTec. Todos os direitos reservados.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── Low-level send helpers ────────────────────────────────────────────────────

def _is_resend_configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


def _is_smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER"))


def _is_sendgrid_configured() -> bool:
    return bool(os.environ.get("SENDGRID_API_KEY"))


def _send_smtp_with_attachment(
    to_email: str, subject: str, html: str,
    pdf_bytes: bytes, filename: str,
) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ.get("SMTP_PASS", "")
    from_addr = os.environ.get("FROM_EMAIL") or os.environ.get("SMTP_FROM", user)

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)

    attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(attachment)

    with smtplib.SMTP(host, port, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        if password:
            server.login(user, password)
        server.sendmail(from_addr, [to_email], msg.as_string())


def _send_sendgrid_with_attachment(
    to_email: str, subject: str, html: str,
    pdf_bytes: bytes, filename: str,
) -> None:
    import sendgrid  # type: ignore
    from sendgrid.helpers.mail import (  # type: ignore
        Attachment, Disposition, FileContent, FileName, FileType, Mail,
    )

    api_key = os.environ["SENDGRID_API_KEY"]
    from_addr = os.environ.get("FROM_EMAIL") or "contato@consultoriaromatec.com.br"

    message = Mail(
        from_email=from_addr,
        to_emails=to_email,
        subject=subject,
        html_content=html,
    )
    encoded = base64.b64encode(pdf_bytes).decode()
    attachment = Attachment(
        FileContent(encoded),
        FileName(filename),
        FileType("application/pdf"),
        Disposition("attachment"),
    )
    message.attachment = attachment

    sg = sendgrid.SendGridAPIClient(api_key=api_key)
    response = sg.send(message)
    if response.status_code >= 400:
        raise RuntimeError(f"SendGrid error {response.status_code}: {response.body}")


def _send_resend_with_attachment(
    to_email: str, subject: str, html: str,
    pdf_bytes: bytes, filename: str,
) -> None:
    import resend  # type: ignore

    resend.api_key = os.environ["RESEND_API_KEY"]
    from_addr = os.environ.get("FROM_EMAIL") or "AvalieImob <onboarding@resend.dev>"

    resend.Emails.send({
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "attachments": [{
            "filename": filename,
            "content": list(pdf_bytes),
        }],
    })


def _send_email_sync(
    to_email: str, subject: str, html: str,
    pdf_bytes: bytes, filename: str,
) -> None:
    if _is_resend_configured():
        logger.info("PTAM email via Resend → %s | %s", to_email, subject)
        _send_resend_with_attachment(to_email, subject, html, pdf_bytes, filename)
    elif _is_sendgrid_configured():
        logger.info("PTAM email via SendGrid → %s | %s", to_email, subject)
        _send_sendgrid_with_attachment(to_email, subject, html, pdf_bytes, filename)
    elif _is_smtp_configured():
        logger.info("PTAM email via SMTP → %s | %s", to_email, subject)
        _send_smtp_with_attachment(to_email, subject, html, pdf_bytes, filename)
    else:
        logger.info(
            "[EMAIL LOG ONLY] PTAM '%s' → %s (sem Resend/SMTP/SendGrid configurado)",
            subject, to_email,
        )


# ── Async public API ──────────────────────────────────────────────────────────

async def enviar_ptam_email(
    to_email: str,
    numero: str,
    endereco: str,
    pdf_bytes: bytes,
    nome_dest: str = "",
    nome_avaliador: str = "",
    registro_profissional: str = "",
    mensagem_extra: str = "",
) -> None:
    """Send PTAM PDF by email with branded HTML body and PDF attachment.

    Args:
        to_email: Recipient email address.
        numero: PTAM number string, e.g. "0001/2025".
        endereco: Property address for display in email body.
        pdf_bytes: Raw PDF bytes to attach.
        nome_dest: Recipient display name (optional).
        nome_avaliador: Evaluator name shown in email info table.
        registro_profissional: CREA/CRECI/CFTMA registration number.
        mensagem_extra: Additional personalised message (optional).
    """
    subject = f"PTAM nº {numero} — Parecer Técnico de Avaliação Mercadológica"
    html = _build_ptam_email_html(
        numero, endereco, nome_dest, nome_avaliador,
        registro_profissional, mensagem_extra,
    )
    filename = f"PTAM_{numero.replace('/', '_').replace('-', '_')}.pdf"

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None, _send_email_sync, to_email, subject, html, pdf_bytes, filename,
        )
    except Exception:
        logger.exception("Falha ao enviar PTAM %s para %s", numero, to_email)
        raise
