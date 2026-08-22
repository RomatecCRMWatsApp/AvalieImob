# @module services.trial_service — Acesso de Teste (trial gratuito por N dias).
#
# COMO O ACESSO É CONCEDIDO (e revogado sozinho):
#   O gate de acesso do sistema é `dependencies.get_active_subscriber`, que exige
#   plan_status == "active" e, se houver `plan_expires` no passado, JÁ marca o
#   usuário como "expired" na próxima requisição. Portanto um trial é apenas:
#       plan_status = "active"  +  plan_expires = agora + N dias
#   Não precisa de cron/scheduler: o acesso morre sozinho no vencimento.
#
#   Os campos `trial*` são MARCADORES (diagnóstico/relatório) — quem decide
#   acesso continua sendo plan_status, como no resto do projeto.
#
# Datas: naive UTC (datetime.utcnow), igual ao restante das rotas de plano.
import os
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional

from services.auth_service import hash_password

PLANO_TRIAL = "trial"
MAX_DIAS = 365
# Alfabeto sem caracteres ambíguos (0/O, 1/l/I) — a senha é ditada por WhatsApp.
_ALFABETO_SENHA = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class TrialError(Exception):
    """Erro de regra de negócio do trial (vira HTTP 409 na rota)."""


# ── Helpers puros ────────────────────────────────────────────────────────────
def app_url() -> str:
    """Base pública canônica (força www — o apex não resolve em conexões novas)."""
    raw = (os.environ.get("APP_URL") or os.environ.get("PUBLIC_BASE_URL")
           or "https://www.romatecavalieimob.com.br").rstrip("/")
    return raw.replace("://romatecavalieimob.com.br", "://www.romatecavalieimob.com.br")


def gerar_senha_temporaria(n: int = 10) -> str:
    """Senha temporária legível, sem caracteres ambíguos: Teste-K7QX."""
    return "Teste-" + "".join(secrets.choice(_ALFABETO_SENHA) for _ in range(max(4, n - 7)))


def validar_dias(dias) -> int:
    try:
        d = int(str(dias).strip())
    except (TypeError, ValueError):
        raise ValueError("Informe a quantidade de dias do teste (número inteiro).")
    if d < 1 or d > MAX_DIAS:
        raise ValueError(f"A duração do teste deve estar entre 1 e {MAX_DIAS} dias.")
    return d


def validar_email(email: str) -> str:
    e = (email or "").strip().lower()
    if not _EMAIL_RE.match(e):
        raise ValueError("Informe um e-mail válido.")
    return e


def calcular_expiracao(dias: int, agora: Optional[datetime] = None) -> datetime:
    return (agora or datetime.utcnow()) + timedelta(days=validar_dias(dias))


def _naive(dt):
    """Mongo devolve datas naive; normaliza aware→naive UTC pra comparar sem TypeError."""
    if dt is not None and getattr(dt, "tzinfo", None) is not None:
        return dt.replace(tzinfo=None) - (dt.utcoffset() or timedelta(0))
    return dt


def status_trial(user: dict, agora: Optional[datetime] = None) -> dict:
    """Situação do teste de um usuário. Função PURA (não toca o banco).

    situacao ∈ nao_trial | ativo | expirado | encerrado | convertido
    """
    agora = agora or datetime.utcnow()
    em_trial = bool(user.get("trial"))
    expires = _naive(user.get("plan_expires"))
    plano = str(user.get("plan") or "")
    if not em_trial:
        return {"em_trial": False, "situacao": "nao_trial", "dias_restantes": None,
                "expira_em": expires, "expirado": False,
                "dias_contratados": user.get("trial_dias")}

    # Assinou de verdade durante/depois do teste → deixou de ser trial.
    if plano and plano != PLANO_TRIAL:
        return {"em_trial": False, "situacao": "convertido", "dias_restantes": None,
                "expira_em": expires, "expirado": False,
                "dias_contratados": user.get("trial_dias")}

    if user.get("trial_encerrado_em"):
        return {"em_trial": True, "situacao": "encerrado", "dias_restantes": 0,
                "expira_em": expires, "expirado": True,
                "dias_contratados": user.get("trial_dias")}

    restante = (expires - agora) if expires else None
    expirado = (restante is None) or (restante.total_seconds() <= 0)
    dias = 0 if expirado else max(1, -(-restante.total_seconds() // 86400).__int__())
    return {
        "em_trial": True,
        "situacao": "expirado" if expirado else "ativo",
        "dias_restantes": int(dias),
        "horas_restantes": 0 if expirado else int(restante.total_seconds() // 3600),
        "expira_em": expires,
        "expirado": expirado,
        "dias_contratados": user.get("trial_dias"),
    }


def montar_mensagem_trial(*, nome: str, email: str, senha: Optional[str], dias: int,
                          expira_em: datetime, link: Optional[str] = None) -> str:
    """Texto do WhatsApp com as credenciais do acesso de teste."""
    link = link or f"{app_url()}/login"
    primeiro = (nome or "").strip().split(" ")[0]
    saudacao = f"Olá, {primeiro}! 👋\n\n" if primeiro else "Olá! 👋\n\n"
    if senha:
        credenciais = (f"👤 *Login (e-mail):* {email}\n"
                       f"🔑 *Senha:* {senha}\n\n"
                       f"_Você pode trocar a senha depois em Configurações._\n\n")
    else:
        credenciais = (f"👤 *Login (e-mail):* {email}\n"
                       f"🔑 *Acesso:* use a mesma senha que você já cadastrou "
                       f"(se não lembrar, clique em \"Esqueci minha senha\" na tela de login).\n\n")
    return (
        f"{saudacao}"
        f"✅ *Seu acesso de teste ao AvalieImob está liberado!*\n\n"
        f"Você tem *{dias} dias* de acesso gratuito à plataforma completa:\n"
        f"• Avaliação de imóveis e PTAM em PDF\n"
        f"• Contratos, recibos e assinatura digital\n"
        f"• Topografia, georreferenciamento e propostas\n\n"
        f"{credenciais}"
        f"⏰ *Seu teste vai até:* {expira_em.strftime('%d/%m/%Y')}\n\n"
        f"👇 *Acesse agora:*\n{link}\n\n"
        f"Qualquer dúvida é só me chamar por aqui.\n"
        f"_RomaTec Consultoria Total — Açailândia/MA_"
    )


def _sanitize_user(doc: dict) -> dict:
    d = dict(doc or {})
    d.pop("_id", None)
    d.pop("password_hash", None)
    d.pop("reset_token_hash", None)
    return d


def _view(user: dict, agora: Optional[datetime] = None) -> dict:
    """Doc do usuário + campos derivados do teste, pronto pra API/tela."""
    st = status_trial(user, agora)
    d = _sanitize_user(user)
    for campo in ("plan_expires", "trial_inicio", "trial_expires", "trial_encerrado_em",
                  "created_at", "last_login_at"):
        v = d.get(campo)
        if isinstance(v, datetime):
            d[campo] = v.isoformat()
    d.update({
        "situacao": st["situacao"],
        "dias_restantes": st["dias_restantes"],
        "expirado": st["expirado"],
        "em_trial": st["em_trial"],
    })
    return d


# ── Operações ────────────────────────────────────────────────────────────────
async def criar_ou_liberar_trial(db, admin_uid: str, *, nome: str, email: str, dias,
                                 telefone: Optional[str] = None, senha: Optional[str] = None,
                                 observacao: Optional[str] = None) -> dict:
    """Cria um login novo com acesso de teste OU libera o teste para quem já é cadastrado.

    Retorna {"user": doc, "criado": bool, "senha_temporaria": str|None, "status": {...}}.
    A senha só é devolvida quando o login é NOVO (ou quando o admin definiu uma) —
    de conta existente a senha nunca é trocada nem exposta.
    """
    dias = validar_dias(dias)
    email = validar_email(email)
    agora = datetime.utcnow()
    expira = calcular_expiracao(dias, agora)

    existente = await db.users.find_one({"email": email})
    marcadores = {
        "plan": PLANO_TRIAL,
        "plan_status": "active",
        "plan_expires": expira,
        "trial": True,
        "trial_dias": dias,
        "trial_inicio": agora,
        "trial_expires": expira,
        "trial_criado_por": admin_uid,
        "trial_observacao": (observacao or "").strip() or None,
    }
    historico = {"acao": "liberado", "dias": dias, "em": agora, "por": admin_uid,
                 "expira_em": expira}

    if existente:
        st = status_trial(existente, agora)
        # Não rebaixar quem PAGA: assinatura ativa e não-trial é intocável.
        if (existente.get("plan_status") == "active"
                and not existente.get("trial")
                and str(existente.get("plan") or "") not in ("", PLANO_TRIAL)
                and (_naive(existente.get("plan_expires")) or agora) > agora):
            raise TrialError(
                f"{email} já tem assinatura ativa ({existente.get('plan')}) até "
                f"{_naive(existente['plan_expires']).strftime('%d/%m/%Y')}. "
                "Liberar teste rebaixaria o plano pago.")
        if st["situacao"] == "convertido":
            raise TrialError(f"{email} já virou assinante do plano {existente.get('plan')}.")

        upd = dict(marcadores)
        upd["trial_encerrado_em"] = None
        if nome and not (existente.get("name") or "").strip():
            upd["name"] = nome.strip()
        if telefone and not (existente.get("phone") or "").strip():
            upd["phone"] = telefone.strip()
        # Reabilita login travado por tentativas de senha (não atrapalhar o teste).
        upd["failed_logins"] = 0
        upd["lock_until"] = None
        nova_senha = None
        if senha:                       # admin definiu a senha explicitamente
            if len(senha) < 8:
                raise ValueError("A senha deve ter pelo menos 8 caracteres.")
            upd["password_hash"] = hash_password(senha)
            nova_senha = senha
        await db.users.update_one({"id": existente["id"]},
                                  {"$set": upd, "$push": {"trial_historico": historico}})
        atual = await db.users.find_one({"id": existente["id"]})
        return {"user": _view(atual, agora), "criado": False, "senha_temporaria": nova_senha,
                "status": status_trial(atual, agora)}

    # ── Login NOVO ──
    from models import User          # import tardio: evita ciclo models↔services
    if senha and len(senha) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")
    nova_senha = senha or gerar_senha_temporaria()
    user = User(name=(nome or email.split("@")[0]).strip(), email=email, role="Profissional")
    doc = user.model_dump()
    doc.update(marcadores)
    doc["password_hash"] = hash_password(nova_senha)
    doc["trial_historico"] = [historico]
    if telefone:
        doc["phone"] = telefone.strip()
    await db.users.insert_one(doc)
    return {"user": _view(doc, agora), "criado": True, "senha_temporaria": nova_senha,
            "status": status_trial(doc, agora)}


async def estender_trial(db, user_id: str, dias, admin_uid: str = "") -> dict:
    """Soma dias ao teste. Se já venceu, conta a partir de agora."""
    dias = validar_dias(dias)
    u = await db.users.find_one({"id": user_id})
    if not u:
        raise TrialError("Usuário não encontrado.")
    agora = datetime.utcnow()
    base = _naive(u.get("plan_expires")) or agora
    if base < agora:
        base = agora
    nova = base + timedelta(days=dias)
    upd = {
        "plan": PLANO_TRIAL,
        "plan_status": "active",
        "plan_expires": nova,
        "trial": True,
        "trial_expires": nova,
        "trial_dias": int(u.get("trial_dias") or 0) + dias,
        "trial_encerrado_em": None,
    }
    await db.users.update_one(
        {"id": user_id},
        {"$set": upd, "$push": {"trial_historico": {"acao": "estendido", "dias": dias,
                                                    "em": agora, "por": admin_uid,
                                                    "expira_em": nova}}})
    atual = await db.users.find_one({"id": user_id})
    return _view(atual, agora)


async def encerrar_trial(db, user_id: str, admin_uid: str = "") -> dict:
    """Corta o acesso na hora (o gate passa a barrar na próxima requisição)."""
    u = await db.users.find_one({"id": user_id})
    if not u:
        raise TrialError("Usuário não encontrado.")
    agora = datetime.utcnow()
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"plan_status": "expired", "plan_expires": agora,
                  "trial_expires": agora, "trial_encerrado_em": agora},
         "$push": {"trial_historico": {"acao": "encerrado", "em": agora, "por": admin_uid}}})
    atual = await db.users.find_one({"id": user_id})
    return _view(atual, agora)


async def redefinir_senha(db, user_id: str, senha: Optional[str] = None) -> str:
    """Gera (ou define) uma senha nova e devolve em claro UMA vez — nunca é salva em claro."""
    u = await db.users.find_one({"id": user_id})
    if not u:
        raise TrialError("Usuário não encontrado.")
    if senha and len(senha) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")
    nova = senha or gerar_senha_temporaria()
    await db.users.update_one({"id": user_id}, {"$set": {
        "password_hash": hash_password(nova), "failed_logins": 0, "lock_until": None}})
    return nova


async def listar_trials(db) -> list:
    """Todos os acessos de teste já concedidos, do mais recente ao mais antigo."""
    agora = datetime.utcnow()
    docs = await db.users.find({"trial": True}).sort("trial_inicio", -1).to_list(2000)
    return [_view(d, agora) for d in docs]
