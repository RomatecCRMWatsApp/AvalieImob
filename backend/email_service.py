"""RomaTec AvalieImob - Email notification service.

Uses smtplib (stdlib) by default.
If SENDGRID_API_KEY is set, uses SendGrid instead.
If no email env vars are set, logs only (graceful fallback).
"""
import asyncio
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger("romatec.email")

# ── Branding constants ────────────────────────────────────────────────
LOGO_URL = "https://customer-assets.emergentagent.com/job_review-simples/artifacts/0n08eo2p_02_icone_512.png"
COLOR_GREEN = "#1B4D1B"
COLOR_GOLD = "#D4A830"
PLATFORM_URL = os.environ.get("PLATFORM_URL", "https://avalieimob.consultoriaromatec.com.br")


# ── HTML template helpers ─────────────────────────────────────────────
def _base_template(title: str, body_html: str) -> str:
    """Wrap body_html in the Romatec branded email shell."""
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f4;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f4f4f4;padding:30px 0;">
    <tr>
      <td align="center">
        <!-- Card container -->
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;background-color:#ffffff;border-radius:8px;
                      overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.12);">

          <!-- Header -->
          <tr>
            <td style="background-color:{COLOR_GREEN};padding:28px 32px;text-align:center;">
              <img src="{LOGO_URL}" alt="RomaTec AvalieImob"
                   width="72" height="72"
                   style="display:block;margin:0 auto 12px;border-radius:8px;" />
              <p style="margin:0;color:#ffffff;font-size:13px;letter-spacing:1px;
                         text-transform:uppercase;opacity:0.85;">
                RomaTec Consultoria Total
              </p>
              <h1 style="margin:6px 0 0;color:{COLOR_GOLD};font-size:22px;font-weight:700;">
                AvalieImob
              </h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              {body_html}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#f9f9f9;padding:20px 32px;border-top:1px solid #e8e8e8;
                        text-align:center;">
              <p style="margin:0;color:#888888;font-size:12px;line-height:1.6;">
                RomaTec Consultoria Total &bull; AvalieImob<br>
                Este e-mail foi enviado automaticamente. N&atilde;o responda a esta mensagem.<br>
                &copy; {datetime.utcnow().year} RomaTec. Todos os direitos reservados.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _button(label: str, url: str) -> str:
    return (
        f'<div style="text-align:center;margin:28px 0 8px;">'
        f'<a href="{url}" '
        f'style="display:inline-block;background-color:{COLOR_GOLD};color:#ffffff;'
        f'text-decoration:none;font-size:15px;font-weight:700;padding:13px 32px;'
        f'border-radius:6px;letter-spacing:0.5px;">'
        f'{label}</a></div>'
    )


def _info_row(label: str, value: str) -> str:
    return (
        f'<tr>'
        f'<td style="padding:8px 12px;background-color:#f5f5f5;color:#555555;'
        f'font-size:13px;font-weight:600;width:40%;border-bottom:1px solid #ebebeb;">'
        f'{label}</td>'
        f'<td style="padding:8px 12px;color:#222222;font-size:13px;'
        f'border-bottom:1px solid #ebebeb;">{value}</td>'
        f'</tr>'
    )


# ── Template builders ─────────────────────────────────────────────────
def build_welcome_email(name: str) -> tuple[str, str]:
    """Return (subject, html) for the welcome / registration email."""
    subject = "Bem-vindo ao AvalieImob!"
    body = f"""
      <h2 style="color:{COLOR_GREEN};margin:0 0 16px;font-size:20px;">
        Olá, {name}!
      </h2>
      <p style="color:#333333;font-size:15px;line-height:1.7;margin:0 0 20px;">
        Sua conta foi criada com sucesso na plataforma <strong>AvalieImob</strong>.<br>
        Agora você tem acesso completo às ferramentas de avaliação imobiliária,
        geração de PTAM, gestão de clientes e imóveis — tudo em um único lugar.
      </p>
      <p style="color:#555555;font-size:14px;line-height:1.6;margin:0 0 24px;">
        Acesse a plataforma, configure seu perfil e comece a emitir seus laudos
        com a qualidade e agilidade que só a RomaTec oferece.
      </p>
      {_button('Acessar plataforma', PLATFORM_URL)}
      <p style="color:#888888;font-size:12px;text-align:center;margin-top:16px;">
        Em caso de dúvidas, entre em contato com o nosso suporte.
      </p>
    """
    return subject, _base_template(subject, body)


def build_payment_email(name: str, plan: str, amount: float, date: str | None = None) -> tuple[str, str]:
    """Return (subject, html) for a confirmed-payment email."""
    subject = f"Pagamento confirmado - Plano {plan}"
    date_str = date or datetime.utcnow().strftime("%d/%m/%Y")
    amount_str = f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    body = f"""
      <h2 style="color:{COLOR_GREEN};margin:0 0 16px;font-size:20px;">
        Pagamento confirmado!
      </h2>
      <p style="color:#333333;font-size:15px;line-height:1.7;margin:0 0 24px;">
        Olá, {name}! Recebemos seu pagamento e sua assinatura está ativa.
        Obrigado por confiar na <strong>RomaTec AvalieImob</strong>!
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0"
             style="border:1px solid #ebebeb;border-radius:6px;overflow:hidden;margin-bottom:28px;">
        {_info_row('Plano', plan)}
        {_info_row('Valor', amount_str)}
        {_info_row('Data do pagamento', date_str)}
        {_info_row('Status', '<span style="color:#2e7d32;font-weight:700;">Confirmado ✓</span>')}
      </table>
      {_button('Acessar dashboard', PLATFORM_URL + '/dashboard')}
    """
    return subject, _base_template(subject, body)


def build_ptam_issued_email(
    name: str,
    number: str,
    imovel: str,
    date: str | None = None,
    download_url: str | None = None,
) -> tuple[str, str]:
    """Return (subject, html) for a PTAM-issued notification email."""
    subject = f"Seu PTAM #{number} foi emitido"
    date_str = date or datetime.utcnow().strftime("%d/%m/%Y")
    btn_url = download_url or (PLATFORM_URL + "/dashboard/ptam")
    body = f"""
      <h2 style="color:{COLOR_GREEN};margin:0 0 16px;font-size:20px;">
        Laudo emitido com sucesso!
      </h2>
      <p style="color:#333333;font-size:15px;line-height:1.7;margin:0 0 24px;">
        Olá, {name}! Seu Parecer Técnico de Avaliação Mercadológica foi gerado
        e está disponível para download.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0"
             style="border:1px solid #ebebeb;border-radius:6px;overflow:hidden;margin-bottom:28px;">
        {_info_row('Número do PTAM', f'<strong>#{number}</strong>')}
        {_info_row('Imóvel', imovel)}
        {_info_row('Data de emissão', date_str)}
        {_info_row('Status', '<span style="color:#2e7d32;font-weight:700;">Emitido ✓</span>')}
      </table>
      {_button('Baixar PDF', btn_url)}
      <p style="color:#888888;font-size:12px;text-align:center;margin-top:16px;">
        O documento também está disponível na seção <em>PTAM</em> do seu painel.
      </p>
    """
    return subject, _base_template(subject, body)


# ── Low-level send helpers ────────────────────────────────────────────
def _is_smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER"))


def _is_sendgrid_configured() -> bool:
    return bool(os.environ.get("SENDGRID_API_KEY"))


def _send_via_smtp(to_email: str, subject: str, html: str) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ.get("SMTP_PASS", "")
    from_addr = os.environ.get("SMTP_FROM", user)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(host, port, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        if password:
            server.login(user, password)
        server.sendmail(from_addr, [to_email], msg.as_string())


def _send_via_sendgrid(to_email: str, subject: str, html: str) -> None:
    import sendgrid  # type: ignore
    from sendgrid.helpers.mail import Mail  # type: ignore

    api_key = os.environ["SENDGRID_API_KEY"]
    from_addr = os.environ.get("SMTP_FROM", "noreply@consultoriaromatec.com.br")

    message = Mail(
        from_email=from_addr,
        to_emails=to_email,
        subject=subject,
        html_content=html,
    )
    sg = sendgrid.SendGridAPIClient(api_key=api_key)
    response = sg.send(message)
    if response.status_code >= 400:
        raise RuntimeError(f"SendGrid error {response.status_code}: {response.body}")


def _send_email_sync(to_email: str, subject: str, html: str) -> None:
    """Synchronous send — chooses provider based on env vars."""
    if _is_sendgrid_configured():
        logger.info("Sending email via SendGrid to %s | %s", to_email, subject)
        _send_via_sendgrid(to_email, subject, html)
    elif _is_smtp_configured():
        logger.info("Sending email via SMTP to %s | %s", to_email, subject)
        _send_via_smtp(to_email, subject, html)
    else:
        logger.info("[EMAIL LOG ONLY] Would send '%s' to %s (no SMTP/SendGrid configured)", subject, to_email)


# ── Async public API ──────────────────────────────────────────────────
async def _send_in_background(to_email: str, subject: str, html: str) -> None:
    """Run the blocking send in a thread-pool so the event loop is not blocked."""
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _send_email_sync, to_email, subject, html)
    except Exception:
        logger.exception("Failed to send email to %s (%s)", to_email, subject)


async def send_welcome_email(to_email: str, name: str) -> None:
    subject, html = build_welcome_email(name)
    await _send_in_background(to_email, subject, html)


async def send_payment_email(
    to_email: str,
    name: str,
    plan: str,
    amount: float,
    date: str | None = None,
) -> None:
    subject, html = build_payment_email(name, plan, amount, date)
    await _send_in_background(to_email, subject, html)


async def send_ptam_issued_email(
    to_email: str,
    name: str,
    number: str,
    imovel: str,
    date: str | None = None,
    download_url: str | None = None,
) -> None:
    subject, html = build_ptam_issued_email(name, number, imovel, date, download_url)
    await _send_in_background(to_email, subject, html)
