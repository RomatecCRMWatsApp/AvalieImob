# @module services.origem_trafego — de onde veio cada cadastro (Google, Bing, direto…).
#
# O dado bruto JÁ existe: `routes/auth.register` grava utm_source/utm_medium/
# utm_campaign/page_origin/**referrer** no doc do usuário desde o cadastro (o
# frontend captura em App.js + Register.jsx). Até agora só a ZAYRA usava isso,
# no resumo semanal por WhatsApp. Aqui classificamos e agregamos para o painel.
#
# Tudo é função PURA sobre o doc do usuário — sem I/O, fácil de testar.
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

# Domínios próprios: navegação interna não é "canal de aquisição".
_PROPRIOS = ("romatecavalieimob.com.br", "avalieimob", "localhost", "127.0.0.1")

# host (substring) → (canal, tipo)
_HOSTS = [
    ("google.", "google", "organico"),
    ("bing.", "bing", "organico"),
    ("duckduckgo", "duckduckgo", "organico"),
    ("yahoo.", "yahoo", "organico"),
    ("ecosia.", "ecosia", "organico"),
    ("instagram", "instagram", "social"),
    ("facebook", "facebook", "social"),
    ("fb.com", "facebook", "social"),
    ("whatsapp", "whatsapp", "social"),
    ("wa.me", "whatsapp", "social"),
    ("t.me", "telegram", "social"),
    ("telegram", "telegram", "social"),
    ("linkedin", "linkedin", "social"),
    ("youtube", "youtube", "social"),
    ("youtu.be", "youtube", "social"),
    ("tiktok", "tiktok", "social"),
]

_LABEL = {
    "google": "Google", "bing": "Bing", "duckduckgo": "DuckDuckGo", "yahoo": "Yahoo",
    "ecosia": "Ecosia", "instagram": "Instagram", "facebook": "Facebook",
    "whatsapp": "WhatsApp", "telegram": "Telegram", "linkedin": "LinkedIn",
    "youtube": "YouTube", "tiktok": "TikTok", "direto": "Direto", "email": "E-mail",
    # Canais das nossas próprias peças de divulgação (ver DivulgacaoPage).
    "qrcode": "QR Code", "link": "Link compartilhado",
}

_MEDIUM_PAGO = {"cpc", "ppc", "paid", "ads", "paid_social", "display"}
_MEDIUM_SOCIAL = {"social", "social_paid", "post", "stories", "bio"}
_MEDIUM_EMAIL = {"email", "e-mail", "newsletter", "mail"}


def _host(url: str) -> str:
    if not url:
        return ""
    u = str(url).strip()
    if not u:
        return ""
    if "//" not in u:
        u = "//" + u
    try:
        h = (urlparse(u).hostname or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def _rotular(canal: str, tipo: str, detalhe: str = "") -> str:
    if canal == "referral":
        return f"Site parceiro ({detalhe})" if detalhe else "Site parceiro"
    base = _LABEL.get(canal, canal.title() if canal else "Direto")
    if tipo == "organico" and canal in ("google", "bing", "duckduckgo", "yahoo", "ecosia"):
        return f"{base} (orgânico)"
    if tipo == "pago":
        return f"{base} Ads"
    return base


def classificar(doc: dict) -> dict:
    """De onde veio este cadastro/lead.

    Ordem: UTM (campanha marcada por nós) vence o referrer; sem os dois, é direto.
    Retorna {canal, label, tipo, detalhe, campanha, pagina_entrada}.
    """
    doc = doc or {}
    campanha = (doc.get("utm_campaign") or "").strip() or None
    pagina = (doc.get("page_origin") or "").strip() or None
    utm_source = (doc.get("utm_source") or "").strip().lower()
    utm_medium = (doc.get("utm_medium") or "").strip().lower()

    if utm_source:
        canal = utm_source.replace("www.", "").split(".")[0]
        if utm_medium in _MEDIUM_PAGO:
            tipo = "pago"
        elif utm_medium in _MEDIUM_EMAIL or canal == "email":
            tipo = "email"
        elif utm_medium in _MEDIUM_SOCIAL or canal in ("instagram", "facebook", "whatsapp",
                                                       "telegram", "linkedin", "tiktok"):
            tipo = "social"
        elif utm_medium in ("organic", "organico"):
            tipo = "organico"
        else:
            tipo = "campanha"
        return {"canal": canal, "label": _rotular(canal, tipo), "tipo": tipo,
                "detalhe": utm_medium or None, "campanha": campanha, "pagina_entrada": pagina}

    host = _host(doc.get("referrer") or "")
    if host and not any(p in host for p in _PROPRIOS):
        for chave, canal, tipo in _HOSTS:
            if chave in host:
                return {"canal": canal, "label": _rotular(canal, tipo), "tipo": tipo,
                        "detalhe": host, "campanha": campanha, "pagina_entrada": pagina}
        return {"canal": "referral", "label": _rotular("referral", "referral", host),
                "tipo": "referral", "detalhe": host, "campanha": campanha,
                "pagina_entrada": pagina}

    return {"canal": "direto", "label": "Direto", "tipo": "direto", "detalhe": None,
            "campanha": campanha, "pagina_entrada": pagina}


def _naive(dt):
    if dt is not None and getattr(dt, "tzinfo", None) is not None:
        return dt.replace(tzinfo=None) - (dt.utcoffset() or timedelta(0))
    return dt


def situacao_do_cadastro(doc: dict) -> str:
    """assinante | em_teste | teste_expirado | cadastrado (nunca ativou)."""
    plano = str(doc.get("plan") or "")
    ativo = doc.get("plan_status") == "active"
    if doc.get("trial") and plano in ("", "trial"):
        return "em_teste" if ativo else "teste_expirado"
    if ativo:
        return "assinante"
    return "expirado" if doc.get("plan_status") == "expired" else "cadastrado"


def resumo_por_canal(docs: list, dias: Optional[int] = None,
                     agora: Optional[datetime] = None) -> list:
    """Ranking de canais: total de cadastros, assinantes pagantes, em teste e conversão."""
    agora = agora or datetime.utcnow()
    corte = (agora - timedelta(days=dias)) if dias else None
    acc: dict = {}
    for d in docs or []:
        criado = _naive(d.get("created_at"))
        if corte and criado and criado < corte:
            continue
        c = classificar(d)
        item = acc.setdefault(c["canal"], {
            "canal": c["canal"], "label": c["label"], "tipo": c["tipo"],
            "total": 0, "assinantes": 0, "em_teste": 0, "conversao": 0.0,
        })
        item["total"] += 1
        sit = situacao_do_cadastro(d)
        if sit == "assinante":
            item["assinantes"] += 1
        elif sit == "em_teste":
            item["em_teste"] += 1
    saida = sorted(acc.values(), key=lambda x: (-x["total"], x["canal"]))
    for item in saida:
        item["conversao"] = round(100.0 * item["assinantes"] / item["total"], 1) if item["total"] else 0.0
    return saida


def view_cadastro(doc: dict) -> dict:
    """Linha da tabela de cadastros (sem dados sensíveis)."""
    c = classificar(doc)
    criado = _naive(doc.get("created_at"))
    ultimo = _naive(doc.get("last_login_at"))
    return {
        "id": doc.get("id") or "",
        "nome": doc.get("name") or "",
        "email": doc.get("email") or "",
        "telefone": doc.get("phone") or "",
        "canal": c["canal"],
        "canal_label": c["label"],
        "tipo": c["tipo"],
        "campanha": c["campanha"],
        "pagina_entrada": c["pagina_entrada"],
        "referrer": doc.get("referrer") or None,
        "situacao": situacao_do_cadastro(doc),
        "plan": doc.get("plan") or "",
        "plan_status": doc.get("plan_status") or "inactive",
        "cadastrado_em": criado.isoformat() if isinstance(criado, datetime) else None,
        "ultimo_acesso": ultimo.isoformat() if isinstance(ultimo, datetime) else None,
        "nunca_acessou": not ultimo,
    }
