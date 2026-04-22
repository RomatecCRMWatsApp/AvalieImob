# @module services.tvi_share — Compartilhamento de TVI por email e WhatsApp
"""Sharing service for TVI documents.

Provides:
  - enviar_tvi_email: sends PDF attachment via email (SendGrid or SMTP)
  - gerar_link_whatsapp: returns formatted wa.me link with pre-filled message
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import smtplib
from datetime import datetime
from email import encoders
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("romatec.tvi_share")

PLATFORM_URL = os.environ.get("PLATFORM_URL", "https://avalieimob.consultoriaromatec.com.br")
COLOR_GREEN = "#1B4D1B"
COLOR_GOLD = "#D4A830"


# ── HTML email template ───────────────────────────────────────────────────────

def _build_tvi_email_html(numero: str, endereco: str, nome_dest: str, download_url: str) -> str:
    year = datetime.utcnow().year
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>Termo de Vistoria TVI {numero}</title></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#f4f4f4;padding:30px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" border="0"
             style="max-width:600px;background:#ffffff;border-radius:8px;
                    overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.12);">
        <tr>
          <td style="background:{COLOR_GREEN};padding:28px 32px;text-align:center;">
            <p style="margin:0;color:#ffffff;font-size:13px;letter-spacing:1px;
                       text-transform:uppercase;opacity:0.85;">RomaTec Consultoria Imobiliária</p>
            <h1 style="margin:6px 0 0;color:{COLOR_GOLD};font-size:22px;font-weight:700;">
              AvalieImob</h1>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <h2 style="color:{COLOR_GREEN};margin:0 0 16px;font-size:20px;">
              Termo de Vistoria de Imóvel</h2>
            <p style="color:#333;font-size:15px;line-height:1.7;margin:0 0 24px;">
              Olá{', ' + nome_dest if nome_dest else ''}!<br>
              Segue em anexo o <strong>Termo de Vistoria de Imóvel nº {numero}</strong>,
              referente ao imóvel <em>{endereco}</em>.
            </p>
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="border:1px solid #ebebeb;border-radius:6px;overflow:hidden;margin-bottom:28px;">
              <tr>
                <td style="padding:8px 12px;background:#f5f5f5;color:#555;font-size:13px;
                            font-weight:600;width:40%;border-bottom:1px solid #ebebeb;">Número TVI</td>
                <td style="padding:8px 12px;color:#222;font-size:13px;
                            border-bottom:1px solid #ebebeb;"><strong>{numero}</strong></td>
              </tr>
              <tr>
                <td style="padding:8px 12px;background:#f5f5f5;color:#555;font-size:13px;
                            font-weight:600;">Imóvel</td>
                <td style="padding:8px 12px;color:#222;font-size:13px;">{endereco}</td>
              </tr>
            </table>
            <div style="text-align:center;margin:28px 0 8px;">
              <a href="{download_url}"
                 style="display:inline-block;background:{COLOR_GOLD};color:#ffffff;
                        text-decoration:none;font-size:15px;font-weight:700;
                        padding:13px 32px;border-radius:6px;">
                Baixar PDF</a>
            </div>
            <p style="color:#888;font-size:12px;text-align:center;margin-top:16px;">
              O documento também está em anexo a este e-mail.
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#f9f9f9;padding:20px 32px;border-top:1px solid #e8e8e8;
                      text-align:center;">
            <p style="margin:0;color:#888;font-size:12px;line-height:1.6;">
              RomaTec Consultoria Imobiliária &bull; AvalieImob<br>
              Este e-mail foi enviado automaticamente. Não responda a esta mensagem.<br>
              &copy; {year} RomaTec. Todos os direitos reservados.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── low-level send helpers ────────────────────────────────────────────────────

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
        logger.info("TVI email via Resend → %s | %s", to_email, subject)
        _send_resend_with_attachment(to_email, subject, html, pdf_bytes, filename)
    elif _is_sendgrid_configured():
        logger.info("TVI email via SendGrid → %s | %s", to_email, subject)
        _send_sendgrid_with_attachment(to_email, subject, html, pdf_bytes, filename)
    elif _is_smtp_configured():
        logger.info("TVI email via SMTP → %s | %s", to_email, subject)
        _send_smtp_with_attachment(to_email, subject, html, pdf_bytes, filename)
    else:
        logger.info("[EMAIL LOG ONLY] TVI '%s' → %s (sem Resend/SMTP/SendGrid configurado)", subject, to_email)


# ── async public API ──────────────────────────────────────────────────────────

async def enviar_tvi_email(
    to_email: str,
    numero: str,
    endereco: str,
    pdf_bytes: bytes,
    nome_dest: str = "",
    download_url: str = "",
) -> None:
    """Send TVI PDF by email with branded HTML body and PDF attachment.

    Args:
        to_email: Recipient email address.
        numero: TVI number string, e.g. "TVI-0001/2025".
        endereco: Property address for display in email body.
        pdf_bytes: Raw PDF bytes to attach.
        nome_dest: Recipient display name (optional).
        download_url: Link to download PDF online (optional).
    """
    subject = f"Termo de Vistoria de Imóvel nº {numero}"
    url = download_url or PLATFORM_URL
    html = _build_tvi_email_html(numero, endereco, nome_dest, url)
    filename = f"TVI_{numero.replace('/', '_').replace('-', '_')}.pdf"

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None, _send_email_sync, to_email, subject, html, pdf_bytes, filename,
        )
    except Exception:
        logger.exception("Falha ao enviar TVI %s para %s", numero, to_email)
        raise


def gerar_link_whatsapp(
    numero: str,
    endereco: str,
    download_url: str = "",
    telefone: str = "",
) -> str:
    """Generate a WhatsApp share link with a pre-filled message.

    Args:
        numero: TVI number, e.g. "TVI-0001/2025".
        endereco: Property address.
        download_url: Link to the PDF (optional). Falls back to PLATFORM_URL.
        telefone: WhatsApp number with country code (optional, e.g. "5598999990000").
                  When empty, returns an open chat link.

    Returns:
        URL string: https://wa.me/<telefone>?text=... or https://wa.me/?text=...
    """
    link = download_url or PLATFORM_URL
    mensagem = (
        f"Segue o Termo de Vistoria de Imóvel nº {numero}, "
        f"referente ao imóvel {endereco}. "
        f"Acesse: {link}"
    )

    import urllib.parse
    encoded = urllib.parse.quote(mensagem)
    if telefone:
        # Strip non-digits and ensure country code
        digits = "".join(c for c in telefone if c.isdigit())
        return f"https://wa.me/{digits}?text={encoded}"
    return f"https://wa.me/?text={encoded}"
