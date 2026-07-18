# @module services.reativacao — sequência de e-mails para quem se cadastrou e
# NÃO ativou a assinatura.
#
# Lê direto da base de usuários (não copia ninguém para a Prospecção): quem
# ativa sai da fila sozinho, quem se cadastra entra sozinho. Sem lista paralela
# para envelhecer.
#
# CADÊNCIA: 4 e-mails (dias 1, 3, 7 e 14) e PARA. E-mail diário indefinido
# queimaria a reputação do domínio — e junto com ela a entrega de redefinição
# de senha, confirmação de pagamento e envio de PTAM ao cliente.
import asyncio
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("romatec")

APP_URL = os.environ.get("APP_URL", "https://www.romatecavalieimob.com.br").rstrip("/")
if "://romatecavalieimob.com.br" in APP_URL:
    # O apex não resolve para conexões novas — sempre www nos links de e-mail.
    APP_URL = APP_URL.replace("://romatecavalieimob.com.br", "://www.romatecavalieimob.com.br")

# Dias após o cadastro em que cada etapa vence.
ETAPAS_DIAS = [1, 3, 7, 14]
# Espaçamento mínimo entre dois envios ao mesmo usuário. Protege quem está na
# fila há meses de receber a sequência inteira em rajada.
DIAS_MIN_ENTRE_ENVIOS = 2


def _dt(v) -> Optional[datetime]:
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", ""))
        except ValueError:
            return None
    return None


def etapa_devida(user: Dict[str, Any], agora: datetime) -> Optional[int]:
    """Índice da etapa (0..3) que deve ser enviada agora, ou None.

    Função PURA. Regras, em ordem:
      1. Assinante ativo, opt-out ou sem e-mail  -> None
      2. Sequência já concluída                  -> None
      3. Último envio recente demais             -> None (espaçamento)
      4. Primeira etapa não enviada cujo dia já venceu
    """
    if (user.get("plan_status") or "").lower() == "active":
        return None
    if user.get("reativacao_opt_out"):
        return None
    if not (user.get("email") or "").strip():
        return None

    criado = _dt(user.get("created_at"))
    if not criado:
        return None
    dias = (agora - criado).days

    enviadas = set(user.get("reativacao_enviadas") or [])
    if len(enviadas) >= len(ETAPAS_DIAS):
        return None

    ultimo = _dt(user.get("reativacao_ultimo_envio"))
    if ultimo and (agora - ultimo) < timedelta(days=DIAS_MIN_ENTRE_ENVIOS):
        return None

    for i, dia in enumerate(ETAPAS_DIAS):
        if i not in enviadas and dias >= dia:
            return i
    return None


# ── Conteúdo ────────────────────────────────────────────────────────────────
# Quem NUNCA acessou e quem PAROU NO CHECKOUT têm objeções diferentes: um não
# sabe o que o sistema faz, o outro já sabe e travou na hora de pagar.

_ETAPAS_NUNCA = [
    ("{primeiro}, sua conta no AvalieImob está pronta",
     "Você criou sua conta e ela já está esperando por você. Em poucos minutos dá para "
     "emitir o primeiro laudo — o sistema monta o PTAM na NBR 14.653, calcula e gera o PDF."),
    ("Um laudo que levava um dia, em cerca de uma hora",
     "O AvalieImob cuida da parte repetitiva: memorial, cálculo, fotos com coordenadas, "
     "sumário e PDF final. Você cuida do que exige seu julgamento técnico."),
    ("Não é só laudo — contrato, recibo e assinatura digital",
     "Além do PTAM: contratos de exclusividade com assinatura por WhatsApp, recibos de "
     "honorários, propostas com preço calculado e assinatura ICP-Brasil com validade jurídica."),
    ("{primeiro}, posso ajudar em alguma coisa?",
     "Se algo travou ou ficou confuso, me chame — respondo pessoalmente. Se preferir, "
     "faço uma demonstração rápida mostrando o sistema com um caso real."),
]

_ETAPAS_CHECKOUT = [
    ("{primeiro}, faltou pouco para ativar sua conta",
     "Vi que você chegou até a tela de pagamento. Se ficou alguma dúvida sobre plano ou "
     "forma de pagamento, me diga — aceitamos cartão, boleto e PIX."),
    ("Dúvida sobre qual plano escolher?",
     "O mensal serve para experimentar sem compromisso. O anual sai bem mais barato por mês "
     "e vale a pena se você emite laudos com regularidade."),
    ("O que você recebe ao ativar",
     "Laudos ilimitados na NBR 14.653, contratos com assinatura por WhatsApp, recibos, "
     "propostas, topografia e assinatura ICP-Brasil — tudo no mesmo lugar."),
    ("{primeiro}, quer que eu ative para você?",
     "Se o pagamento não passou ou você prefere outra forma, me chame que resolvo junto "
     "com você. Não precisa ficar travado nisso."),
]


def assunto_e_corpo(
    etapa: int, user: Dict[str, Any], cta_url: str, unsub_url: str
) -> Tuple[str, str]:
    """Monta (assunto, html) da etapa para este usuário."""
    from email_service import _base_template, _button  # import tardio: evita ciclo

    etapa = max(0, min(etapa, len(ETAPAS_DIAS) - 1))
    parou_no_checkout = (user.get("status_funil") == "checkout_started") or bool(
        user.get("checkout_started_at")
    )
    tabela = _ETAPAS_CHECKOUT if parou_no_checkout else _ETAPAS_NUNCA
    assunto_tpl, texto = tabela[etapa]

    nome = (user.get("name") or "").strip()
    primeiro = nome.split()[0] if nome else "Olá"
    assunto = assunto_tpl.format(primeiro=primeiro)

    rotulo = "Finalizar assinatura" if parou_no_checkout else "Acessar o AvalieImob"
    corpo = f"""
      <p style="margin:0 0 16px">Olá, {primeiro}!</p>
      <p style="margin:0 0 16px">{texto}</p>
      {_button(rotulo, cta_url)}
      <p style="margin:24px 0 0;font-size:12px;color:#8a8a8a">
        Você recebe este e-mail porque criou uma conta no AvalieImob.
        <a href="{unsub_url}" style="color:#8a8a8a">Não quero mais receber</a>.
      </p>
    """
    return assunto, _base_template(assunto, corpo)


# ── Execução ────────────────────────────────────────────────────────────────
async def _token_opt_out(db, user: Dict[str, Any]) -> str:
    """Token de descadastro do usuário (gera na primeira vez)."""
    tok = user.get("reativacao_opt_out_token")
    if not tok:
        tok = secrets.token_urlsafe(16)
        await db.users.update_one({"id": user["id"]}, {"$set": {"reativacao_opt_out_token": tok}})
    return tok


async def candidatos(db, agora: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Usuários com etapa vencida agora. Não envia nada — só lista."""
    agora = agora or datetime.utcnow()
    fila = []
    cursor = db.users.find({
        "plan_status": {"$ne": "active"},
        "reativacao_opt_out": {"$ne": True},
    })
    async for u in cursor:
        etapa = etapa_devida(u, agora)
        if etapa is not None:
            fila.append({"user": u, "etapa": etapa})
    return fila


async def enviar_etapa(db, user: Dict[str, Any], etapa: int) -> bool:
    """Envia UMA etapa e marca no usuário. Best-effort: nunca levanta."""
    from email_service import _send_email_sync

    try:
        tok = await _token_opt_out(db, user)
        cta = f"{APP_URL}/dashboard/assinatura" if user.get("checkout_started_at") else f"{APP_URL}/dashboard"
        unsub = f"{APP_URL}/api/reativacao/descadastrar/{tok}"
        assunto, html = assunto_e_corpo(etapa, user, cta, unsub)

        await asyncio.to_thread(_send_email_sync, user["email"], assunto, html)
        await db.users.update_one(
            {"id": user["id"]},
            {"$addToSet": {"reativacao_enviadas": etapa},
             "$set": {"reativacao_ultimo_envio": datetime.utcnow()}},
        )
        logger.info("Reativação: etapa %s enviada para %s", etapa + 1, user.get("email"))
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Reativação: falha ao enviar para %s: %s", user.get("email"), e)
        return False


async def rodar(db, limite: int = 50, intervalo: int = 20) -> int:
    """Envia as etapas vencidas. Retorna quantos e-mails saíram."""
    fila = await candidatos(db)
    if not fila:
        return 0
    enviados = 0
    for item in fila[:limite]:
        if await enviar_etapa(db, item["user"], item["etapa"]):
            enviados += 1
        await asyncio.sleep(intervalo)   # espaça os envios (reputação do domínio)
    logger.info("Reativação: %s e-mail(s) enviados", enviados)
    return enviados
