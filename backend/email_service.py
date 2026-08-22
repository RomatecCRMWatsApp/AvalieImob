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
COLOR_GREEN = "#0C3320"   # verde da marca AvalieImob
COLOR_GOLD = "#C9A84C"    # dourado da marca
# URL canônica da plataforma (força www — o apex não resolve em conexões novas).
PLATFORM_URL = (os.environ.get("PLATFORM_URL") or os.environ.get("APP_URL")
                or "https://www.romatecavalieimob.com.br").rstrip("/").replace(
                    "://romatecavalieimob.com.br", "://www.romatecavalieimob.com.br")


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
              <!-- Monograma "A" desenhado em HTML (autossuficiente — sem imagem remota,
                   que os clientes de e-mail bloqueiam por padrão). -->
              <table cellpadding="0" cellspacing="0" border="0" align="center" style="margin:0 auto 12px;">
                <tr>
                  <td width="64" height="64" align="center" valign="middle"
                      style="width:64px;height:64px;background-color:{COLOR_GOLD};border-radius:14px;
                             font-family:Georgia,'Times New Roman',serif;font-size:38px;font-weight:bold;
                             color:{COLOR_GREEN};line-height:64px;text-align:center;">A</td>
                </tr>
              </table>
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
def _feature(emoji: str, title: str, desc: str) -> str:
    """Uma linha de recurso (ícone + título + descrição) para o e-mail de boas-vindas."""
    return (
        f'<tr>'
        f'<td valign="top" style="padding:9px 10px 9px 0;font-size:20px;width:26px;">{emoji}</td>'
        f'<td valign="top" style="padding:9px 0;border-bottom:1px solid #f0f0f0;">'
        f'<div style="color:{COLOR_GREEN};font-size:14px;font-weight:700;">{title}</div>'
        f'<div style="color:#666666;font-size:13px;line-height:1.5;margin-top:2px;">{desc}</div>'
        f'</td></tr>'
    )


def build_welcome_email(name: str) -> tuple[str, str]:
    """Return (subject, html) for the welcome / registration email."""
    subject = "Bem-vindo(a) ao AvalieImob — veja tudo o que você já pode fazer 🎉"
    features = "".join([
        _feature('📐', 'Avaliação Imobiliária (PTAM)',
                 'Laudos pela NBR 14.653 com a IA escrevendo os textos, fotos com GPS, ART/TRT e o grau de fundamentação calculado.'),
        _feature('✍️', 'Contratos & Procuração',
                 'Compra e venda, exclusividade e mais — com o cliente assinando por link no WhatsApp.'),
        _feature('🧾', 'Recibos de Honorários',
                 'Emita, assine digitalmente e envie ao cliente pelo WhatsApp em segundos.'),
        _feature('🔏', 'Assinatura ICP-Brasil',
                 'Assine PTAMs, contratos e PDFs posicionando o carimbo — com validade jurídica plena.'),
        _feature('🗺️', 'Topografia & Geo (Georreferenciamento)',
                 'INCRA/SIGEF: Requerimento, Memorial, DRL, Laudo, Shapefile SIG-RI e Dossiê — do memorial ao cartório.'),
        _feature('🏙️', 'Geo Urbano',
                 'Remembramento, desdobro, retificação de área e usucapião extrajudicial.'),
        _feature('💼', 'Propostas de Consultoria',
                 'Precifique georreferenciamento, averbação e desmembramento e envie a proposta pronta.'),
        _feature('🤖', 'IA integrada',
                 'Escreve pareceres e textos técnicos por você — você só revisa e assina.'),
        _feature('🔎', 'Consulta CNPJ / CPF',
                 'Consulta rápida com PDF pronto e envio por WhatsApp.'),
    ])
    body = f"""
      <h2 style="color:{COLOR_GREEN};margin:0 0 14px;font-size:21px;">
        Olá, {name or 'seja muito bem-vindo(a)'}! 🎉
      </h2>
      <p style="color:#333333;font-size:15px;line-height:1.7;margin:0 0 6px;">
        Sua conta na plataforma <strong>AvalieImob</strong> (RomaTec Consultoria Total) está
        <strong>ativa</strong>. Aqui você tem, num só lugar, tudo o que precisa para o seu trabalho técnico:
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:14px 0 6px;">
        {features}
      </table>
      {_button('Acessar a plataforma', PLATFORM_URL)}
      <p style="color:#777777;font-size:13px;line-height:1.6;text-align:center;margin:16px 0 0;">
        Dica: comece pelo módulo que você mais usa hoje. Qualquer dúvida, é só falar com a gente. 💬
      </p>
    """
    return subject, _base_template(subject, body)


def build_password_reset_email(name: str, reset_url: str) -> tuple[str, str]:
    """Return (subject, html) for the password-reset email."""
    subject = "Redefinição de senha — AvalieImob"
    body = f"""
      <h2 style="color:{COLOR_GREEN};margin:0 0 16px;font-size:20px;">
        Olá, {name or 'usuário'}!
      </h2>
      <p style="color:#333333;font-size:15px;line-height:1.7;margin:0 0 20px;">
        Recebemos um pedido para <strong>redefinir a senha</strong> da sua conta no
        AvalieImob. Clique no botão abaixo para criar uma nova senha. O link é válido
        por <strong>30 minutos</strong>.
      </p>
      {_button('Redefinir minha senha', reset_url)}
      <p style="color:#888888;font-size:12px;line-height:1.6;margin:18px 0 0;">
        Se você não solicitou isso, ignore este e-mail — sua senha continua a mesma.
        Nunca compartilhe este link com ninguém.
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
def build_trial_email(name: str, email: str, senha: str | None, dias: int,
                      expira_em: str) -> tuple[str, str]:
    """E-mail com as credenciais do ACESSO DE TESTE (trial de N dias).

    `senha` só vem preenchida quando o login foi criado agora — para quem já era
    cadastrado, orientamos a usar a senha do próprio cadastro (nunca a expomos).
    """
    subject = f"Seu acesso de teste ao AvalieImob — {dias} dias liberados 🎉"
    saud = f"Olá, {name.split(' ')[0]}!" if (name or "").strip() else "Olá!"
    if senha:
        credenciais = (
            _info_row("Login (e-mail)", email)
            + _info_row("Senha temporária",
                        f'<strong style="font-family:monospace;font-size:15px;">{senha}</strong>')
        )
        nota = ("<p style=\"color:#666;font-size:13px;line-height:1.6;\">"
                "Por segurança, troque a senha depois em <strong>Configurações</strong>.</p>")
    else:
        credenciais = (_info_row("Login (e-mail)", email)
                       + _info_row("Senha", "a mesma que você já cadastrou"))
        nota = ("<p style=\"color:#666;font-size:13px;line-height:1.6;\">"
                "Esqueceu a senha? Use <strong>“Esqueci minha senha”</strong> na tela de login.</p>")
    features = "".join([
        _feature("🏠", "Avaliação de imóveis e PTAM", "Laudos completos em PDF, NBR 14.653."),
        _feature("📝", "Contratos e recibos", "Exclusividade, procuração e assinatura digital."),
        _feature("📐", "Topografia e georreferenciamento", "Memoriais, SIGEF/ONR e propostas."),
    ])
    body = f"""
      <p style="color:#333;font-size:15px;line-height:1.7;">{saud}</p>
      <p style="color:#333;font-size:15px;line-height:1.7;">
        Seu <strong>acesso de teste</strong> ao AvalieImob está liberado por
        <strong>{dias} dias</strong>, com a plataforma completa — sem cartão, sem compromisso.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;margin:18px 0;">{credenciais}
        {_info_row("Seu teste vai até", f'<strong>{expira_em}</strong>')}
      </table>
      {nota}
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;margin:18px 0;">{features}</table>
      {_button('Entrar na plataforma', PLATFORM_URL + '/login')}
      <p style="color:#888;font-size:12px;line-height:1.6;text-align:center;">
        Qualquer dúvida, é só responder este e-mail.
      </p>
    """
    return subject, _base_template("Seu acesso de teste", body)


def build_lead_email(lead: dict) -> tuple[str, str]:
    """Aviso IMEDIATO de lead novo da Calculadora pública (complementa o WhatsApp)."""
    lead = lead or {}
    imovel = lead.get("imovel") or {}
    est = lead.get("estimativa") or {}
    nome = str(lead.get("nome") or "Lead sem nome")
    cidade = f"{imovel.get('cidade') or ''}/{imovel.get('uf') or ''}".strip("/")
    subject = f"🎯 Novo lead — {nome}" + (f" ({cidade})" if cidade else "")
    zap = str(lead.get("whatsapp") or "").strip()
    zap_link = f'<a href="https://wa.me/{zap}" style="color:{COLOR_GREEN};">{zap}</a>' if zap else "—"
    linhas = (
        _info_row("Nome", nome)
        + _info_row("WhatsApp", zap_link)
        + _info_row("E-mail", lead.get("email") or "—")
        + _info_row("Imóvel", f"{str(imovel.get('tipo') or '—').capitalize()} · "
                              f"{imovel.get('area') or '—'} m² · {cidade or '—'}")
        + _info_row("Padrão / conservação",
                    f"{imovel.get('padrao') or '—'} · {imovel.get('conservacao') or '—'}")
        + _info_row("Estimativa",
                    f"<strong>{est.get('faixa_texto') or '—'}</strong>")
        + _info_row("Origem", lead.get("origem") or "calculadora")
    )
    body = f"""
      <p style="color:#333;font-size:15px;line-height:1.7;">
        Entrou um lead novo pela calculadora <strong>"Quanto vale meu imóvel?"</strong>.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;margin:16px 0;">{linhas}</table>
      {_button('Abrir painel de leads', PLATFORM_URL + '/dashboard/admin/leads')}
      <p style="color:#888;font-size:12px;text-align:center;">
        Responder rápido é o que converte — o lead ainda está com o assunto na cabeça.
      </p>
    """
    return subject, _base_template("Novo lead", body)


def _linha_canal(c: dict, maior: int) -> str:
    """Barra proporcional de um canal no resumo (HTML puro, sem imagem)."""
    total = int(c.get("total") or 0)
    pct = int(round(100 * total / maior)) if maior else 0
    return (
        f'<tr>'
        f'<td style="padding:6px 10px 6px 0;color:{COLOR_GREEN};font-size:13px;'
        f'font-weight:600;white-space:nowrap;">{c.get("label") or c.get("canal")}</td>'
        f'<td style="padding:6px 0;width:100%;">'
        f'<div style="background:#eeeeee;border-radius:4px;height:10px;">'
        f'<div style="background:{COLOR_GOLD};width:{max(pct, 3)}%;height:10px;'
        f'border-radius:4px;"></div></div></td>'
        f'<td style="padding:6px 0 6px 10px;color:#222;font-size:13px;'
        f'font-weight:700;white-space:nowrap;">{total}</td>'
        f'</tr>'
    )


def build_resumo_email(dados: dict) -> tuple[str, str]:
    """Resumo periódico (diário/semanal): cadastros, canais, leads e assinaturas."""
    dados = dados or {}
    dias = int(dados.get("dias") or 7)
    periodo = "do dia" if dias <= 1 else ("da semana" if dias <= 7 else f"dos últimos {dias} dias")
    subject = (f"📊 Resumo {periodo} — AvalieImob: {dados.get('cadastros', 0)} cadastro(s), "
               f"{dados.get('leads_calculadora', 0)} lead(s)")
    canais = dados.get("canais") or []
    maior = max([int(c.get("total") or 0) for c in canais], default=0)
    tabela_canais = "".join(_linha_canal(c, maior) for c in canais) or (
        '<tr><td style="color:#888;font-size:13px;padding:6px 0;">'
        'Nenhum cadastro novo no período.</td></tr>')
    numeros = (
        _info_row("Cadastros novos", f"<strong>{dados.get('cadastros', 0)}</strong>")
        + _info_row("Leads da calculadora", str(dados.get("leads_calculadora", 0)))
        + _info_row("Acessos de teste liberados", str(dados.get("testes_liberados", 0)))
        + _info_row("Assinaturas no período", f"<strong>{dados.get('assinaturas', 0)}</strong>")
        + _info_row("Total de usuários na base", str(dados.get("total_usuarios", 0)))
    )
    body = f"""
      <p style="color:#333;font-size:15px;line-height:1.7;">
        Resumo {periodo} da captação no AvalieImob.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;margin:16px 0;">{numeros}</table>
      <p style="color:{COLOR_GREEN};font-size:14px;font-weight:700;margin:22px 0 6px;">
        De onde vieram os cadastros
      </p>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse;">{tabela_canais}</table>
      {_button('Ver no painel', PLATFORM_URL + '/dashboard/admin/leads')}
    """
    return subject, _base_template("Resumo da captação", body)


def build_prospeccao_email(nome: str, cta_url: str, unsub_url: str = "") -> tuple[str, str]:
    """E-mail de PROSPECÇÃO B2B (proposta de parceria) para imobiliárias/corretores."""
    subject = "Sua imobiliária com laudos, contratos e assinatura digital — AvalieImob (Romatec)"
    saud = f"Olá, {nome}!" if nome else "Olá!"
    features = "".join([
        _feature('📐', 'Avaliação / PTAM (NBR 14.653)',
                 'Laudos com IA, fotos com GPS e ART/TRT — prontos para banco, cartório e financiamento.'),
        _feature('✍️', 'Contratos de exclusividade + assinatura no WhatsApp',
                 'O cliente lê e assina por um link no celular. Você fecha a captação na hora.'),
        _feature('🔏', 'Assinatura ICP-Brasil',
                 'Validade jurídica plena em contratos, laudos, procurações e recibos.'),
        _feature('🗺️', 'Topografia & Georreferenciamento',
                 'Rural (INCRA/SIGEF) e urbano (remembramento, desdobro, retificação, usucapião).'),
    ])
    unsub = (
        f'<p style="color:#999999;font-size:11px;line-height:1.6;text-align:center;margin:14px 0 0;">'
        f'Você recebeu este e-mail porque é um contato comercial (PJ) do setor imobiliário na nossa região. '
        f'Se não desejar mais receber, <a href="{unsub_url}" style="color:#999999;">clique aqui para descadastrar</a>.'
        f'</p>' if unsub_url else "")
    body = f"""
      <h2 style="color:{COLOR_GREEN};margin:0 0 12px;font-size:21px;">{saud}</h2>
      <p style="color:#333333;font-size:15px;line-height:1.7;margin:0 0 6px;">
        Somos a <strong>Romatec Consultoria Total</strong> e criamos a plataforma <strong>AvalieImob</strong> —
        feita para <strong>corretores e imobiliárias</strong> emitirem avaliações, contratos e assinaturas
        com validade jurídica, em minutos e do próprio celular. Veja o que você passa a ter:
      </p>
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:14px 0 6px;">
        {features}
      </table>
      <p style="color:#333333;font-size:15px;line-height:1.7;margin:8px 0 0;">
        O cadastro é <strong>gratuito</strong> e você já testa com os seus imóveis hoje mesmo.
      </p>
      {_button('Cadastre-se grátis', cta_url)}
      <p style="color:#777777;font-size:13px;line-height:1.6;text-align:center;margin:14px 0 0;">
        Prefere falar antes? Chame no WhatsApp <strong>(99) 99181-1246</strong>. 💬
      </p>
      {unsub}
    """
    return subject, _base_template(subject, body)


def send_prospeccao_email_sync(to_email: str, nome: str, cta_url: str, unsub_url: str = "") -> None:
    """Envio SÍNCRONO da proposta (levanta o erro real do provedor — usado na fila throttled)."""
    subject, html = build_prospeccao_email(nome, cta_url, unsub_url)
    _send_email_sync(to_email, subject, html)


def _is_smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER"))


def _is_sendgrid_configured() -> bool:
    return bool(os.environ.get("SENDGRID_API_KEY"))


def _send_via_smtp(to_email: str, subject: str, html: str) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ.get("SMTP_PASS", "")
    from_addr = os.environ.get("FROM_EMAIL") or os.environ.get("SMTP_FROM", user)

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
    from_addr = os.environ.get("FROM_EMAIL") or os.environ.get("SMTP_FROM", "contato@romatecavalieimob.com.br")

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


# ── Diagnóstico / teste (painel admin) ────────────────────────────────
def email_config_status() -> dict:
    """Estado da configuração de e-mail (sem expor segredos) — p/ o diagnóstico."""
    if _is_sendgrid_configured():
        provider = "SendGrid"
    elif _is_smtp_configured():
        provider = "SMTP"
    else:
        provider = None
    from_addr = (os.environ.get("FROM_EMAIL") or os.environ.get("SMTP_FROM")
                 or os.environ.get("SMTP_USER") or "")
    return {
        "provider": provider,
        "configured": provider is not None,
        "from_email": from_addr,
        "smtp_host": os.environ.get("SMTP_HOST", ""),
        "smtp_port": os.environ.get("SMTP_PORT", "587"),
        "smtp_user_set": bool(os.environ.get("SMTP_USER")),
        "smtp_pass_set": bool(os.environ.get("SMTP_PASS")),
        "sendgrid_key_set": bool(os.environ.get("SENDGRID_API_KEY")),
    }


def send_test_email(to_email: str) -> dict:
    """Envia um e-mail de teste SÍNCRONO e devolve o resultado; levanta com o erro real
    do provedor (p/ o painel mostrar exatamente o que falhou)."""
    st = email_config_status()
    if not st["configured"]:
        return {"ok": False, "provider": None,
                "error": "Nenhum provedor configurado. Defina SMTP_HOST/SMTP_USER/SMTP_PASS "
                         "ou SENDGRID_API_KEY (+ FROM_EMAIL) no Railway."}
    subject = "Teste de e-mail — AvalieImob"
    body = _base_template(subject,
        "<p style='color:#333;font-size:15px;line-height:1.7;'>Este é um e-mail de teste do "
        "<strong>AvalieImob</strong>. Se você recebeu esta mensagem, o envio de e-mails "
        "(inclusive o link de <em>redefinição de senha</em>) está funcionando. ✓</p>")
    _send_email_sync(to_email, subject, body)   # levanta em falha real
    return {"ok": True, "provider": st["provider"], "from_email": st["from_email"], "to": to_email}


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


async def send_password_reset_email(to_email: str, name: str, reset_url: str) -> None:
    subject, html = build_password_reset_email(name, reset_url)
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


async def send_lead_email(to_email: str, lead: dict) -> None:
    """Aviso imediato de lead novo da calculadora (fire-and-forget, loga falhas)."""
    subject, html = build_lead_email(lead)
    await _send_in_background(to_email, subject, html)


async def send_resumo_email(to_email: str, dados: dict) -> None:
    """Resumo periódico da captação (fire-and-forget, loga falhas)."""
    subject, html = build_resumo_email(dados)
    await _send_in_background(to_email, subject, html)


async def send_trial_email(to_email: str, name: str, senha: str | None, dias: int,
                           expira_em: str) -> None:
    """Envia as credenciais do acesso de teste (fire-and-forget, loga falhas)."""
    subject, html = build_trial_email(name, to_email, senha, dias, expira_em)
    await _send_in_background(to_email, subject, html)
