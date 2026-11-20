# @module services.privacidade.pedidos — Pedidos de titulares (LGPD art. 18).
#
# Canal ABERTO a quem não tem conta (cliente do avaliador, lead da calculadora,
# proprietário citado num laudo, etc.). Fluxo:
#   1. criar_pedido  → protocolo + código de 6 dígitos enviado ao e-mail informado
#                      (status `aguardando_verificacao`). A resposta é SEMPRE a mesma,
#                      exista ou não conta com aquele e-mail (sem enumeração).
#   2. verificar     → confere o código (hash, 5 tentativas, 24 h) → `recebido`
#                      e calcula o prazo interno.
#   3. admin         → muda status/responsável com trilha (`historico`).
#
# Verificação PROPORCIONAL: controle do e-mail informado. Pedidos de eliminação ou
# acesso a dados sensíveis podem exigir verificação adicional decidida pelo
# responsável (registrar no histórico) — o sistema não decide sozinho.
#
# Coleção: privacidade_pedidos. Nunca guarda o código em claro.
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional

from services.privacidade import config

TIPOS_DIREITO = {
    "confirmacao_acesso": "Confirmação da existência de tratamento / acesso aos dados",
    "correcao": "Correção de dados incompletos, inexatos ou desatualizados",
    "anonimizacao_bloqueio_eliminacao": "Anonimização, bloqueio ou eliminação",
    "portabilidade": "Portabilidade",
    "informacao_compartilhamento": "Informação sobre compartilhamento",
    "revogacao_consentimento": "Revogação de consentimento",
    "oposicao": "Oposição a tratamento",
    "revisao_decisao_automatizada": "Revisão de decisão automatizada",
    "outro": "Outro",
    # Interno (Central de Privacidade / assinatura) — não aparece no canal público
    "arrependimento_cdc": "Arrependimento da contratação (CDC art. 49) — a avaliar",
}
TIPOS_PUBLICOS = [k for k in TIPOS_DIREITO if k != "arrependimento_cdc"]

RELACOES = ("usuario", "cliente_de_usuario", "lead", "outro")

STATUS = (
    "aguardando_verificacao",
    "recebido",
    "em_analise",
    "aguardando_informacao",
    "encaminhado_controlador",
    "concluido",
    "indeferido",
)
_FINAIS = {"concluido", "indeferido"}

MAX_TENTATIVAS = 5
VALIDADE_CODIGO_H = 24

_EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[A-Za-z]{2,}$")

# Envio do código: injetável (testes trocam por um coletor; produção usa e-mail).
EnviarCodigo = Callable[[str, str, str], Awaitable[None]]


async def _enviar_codigo_email(email: str, protocolo: str, codigo: str) -> None:
    from email_service import _base_template, _send_in_background
    corpo = (
        f"<p>Recebemos uma solicitação sobre dados pessoais (protocolo <b>{protocolo}</b>).</p>"
        f"<p>Para confirmar que este e-mail é seu, informe o código: <b>{codigo}</b></p>"
        f"<p>O código vale por {VALIDADE_CODIGO_H} horas. Se você não fez esta solicitação, "
        f"ignore esta mensagem.</p>"
    )
    await _send_in_background(email, f"Confirmação do pedido {protocolo}",
                              _base_template("Pedido sobre seus dados", corpo))


enviar_codigo: EnviarCodigo = _enviar_codigo_email


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


def normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


def validar_entrada(dados: Dict[str, Any]) -> Optional[str]:
    """Devolve mensagem de erro (str) ou None se ok. Função pura."""
    nome = (dados.get("nome") or "").strip()
    email = normalizar_email(dados.get("email"))
    if not (2 <= len(nome) <= 120):
        return "Informe seu nome (2 a 120 caracteres)."
    if not _EMAIL_RE.match(email):
        return "Informe um e-mail válido para receber o código de confirmação."
    if dados.get("tipo_direito") not in TIPOS_PUBLICOS:
        return "Tipo de pedido inválido."
    if dados.get("relacao") not in RELACOES:
        return "Informe sua relação com o AvalieImob."
    if len((dados.get("descricao") or "")) > 4000:
        return "Descrição muito longa (máx. 4000 caracteres)."
    if not dados.get("declaracao_veracidade"):
        return "Confirme que as informações são verdadeiras e que o pedido é seu ou de quem você representa."
    return None


def gerar_protocolo(agora: Optional[datetime] = None) -> str:
    agora = agora or datetime.utcnow()
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    sufixo = "".join(secrets.choice(alfabeto) for _ in range(8))
    return f"PRIV-{agora:%Y%m%d}-{sufixo}"


def _evento(acao: str, por: str, detalhe: str = "", agora: Optional[datetime] = None) -> Dict[str, Any]:
    return {"em": agora or datetime.utcnow(), "acao": acao, "por": por, "detalhe": detalhe[:500]}


async def criar_pedido(db, dados: Dict[str, Any], *, origem: str = "canal_publico",
                       user_id: Optional[str] = None,
                       agora: Optional[datetime] = None) -> Dict[str, Any]:
    """Cria o pedido e envia o código. Levanta ValueError com mensagem amigável."""
    agora = agora or datetime.utcnow()
    tipo = dados.get("tipo_direito")
    if origem == "canal_publico":
        erro = validar_entrada(dados)
        if erro:
            raise ValueError(erro)
    elif tipo not in TIPOS_DIREITO:
        raise ValueError("Tipo de pedido inválido.")
    email = normalizar_email(dados.get("email"))
    protocolo = gerar_protocolo(agora)
    autenticado = user_id is not None
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    doc = {
        "id": secrets.token_hex(12),
        "protocolo": protocolo,
        "origem": origem,
        "user_id": user_id,                 # só quando aberto pela conta logada
        "nome": (dados.get("nome") or "").strip()[:120],
        "email": email,
        "relacao": dados.get("relacao") or ("usuario" if autenticado else "outro"),
        "tipo_direito": tipo,
        "descricao": (dados.get("descricao") or "")[:4000],
        # conta logada já está autenticada; canal público precisa do código
        "status": "recebido" if autenticado else "aguardando_verificacao",
        "codigo_hash": None if autenticado else _hash(protocolo + ":" + codigo),
        "codigo_expira_em": None if autenticado else agora + timedelta(hours=VALIDADE_CODIGO_H),
        "tentativas": 0,
        "verificado_em": agora if autenticado else None,
        "prazo_em": agora + timedelta(days=config.prazo_resposta_dias()) if autenticado else None,
        "responsavel": None,
        "criado_em": agora,
        "atualizado_em": agora,
        "historico": [_evento("criado", user_id or "titular", origem, agora)],
    }
    await db.privacidade_pedidos.insert_one(doc)
    if not autenticado:
        await enviar_codigo(email, protocolo, codigo)
    return doc


async def verificar(db, protocolo: str, email: str, codigo: str,
                    agora: Optional[datetime] = None) -> Dict[str, Any]:
    """Confere o código. Mensagens genéricas (não revelam se o protocolo existe)."""
    agora = agora or datetime.utcnow()
    falha = ValueError("Código inválido, expirado ou protocolo/e-mail não conferem.")
    doc = await db.privacidade_pedidos.find_one(
        {"protocolo": (protocolo or "").strip().upper(), "email": normalizar_email(email)})
    if not doc:
        raise falha
    if doc.get("status") != "aguardando_verificacao":
        return doc  # idempotente: já verificado
    if (doc.get("tentativas") or 0) >= MAX_TENTATIVAS:
        raise ValueError("Número máximo de tentativas atingido. Abra um novo pedido.")
    expira = doc.get("codigo_expira_em")
    esperado = doc.get("codigo_hash") or ""
    recebido = _hash(doc["protocolo"] + ":" + (codigo or "").strip())
    if (expira and expira < agora) or not hmac.compare_digest(esperado, recebido):
        await db.privacidade_pedidos.update_one({"id": doc["id"]}, {"$inc": {"tentativas": 1}})
        raise falha
    sets = {
        "status": "recebido",
        "verificado_em": agora,
        "prazo_em": agora + timedelta(days=config.prazo_resposta_dias()),
        "codigo_hash": None,
        "atualizado_em": agora,
    }
    await db.privacidade_pedidos.update_one(
        {"id": doc["id"]},
        {"$set": sets, "$push": {"historico": _evento("verificado", "titular", "e-mail confirmado", agora)}},
    )
    doc.update(sets)
    return doc


def visao_titular(doc: Dict[str, Any]) -> Dict[str, Any]:
    """O que o titular pode ver do próprio pedido (sem notas internas/responsável)."""
    return {
        "protocolo": doc.get("protocolo"),
        "tipo_direito": doc.get("tipo_direito"),
        "status": doc.get("status"),
        "criado_em": doc.get("criado_em"),
        "prazo_em": doc.get("prazo_em"),
    }


def visao_admin(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = {k: v for k, v in doc.items() if k not in ("_id", "codigo_hash")}
    return d


async def atualizar_admin(db, pedido_id: str, admin_uid: str, *, status: Optional[str] = None,
                          responsavel: Optional[str] = None, nota: Optional[str] = None,
                          agora: Optional[datetime] = None) -> Dict[str, Any]:
    agora = agora or datetime.utcnow()
    doc = await db.privacidade_pedidos.find_one({"id": pedido_id})
    if not doc:
        raise LookupError("Pedido não encontrado.")
    sets: Dict[str, Any] = {"atualizado_em": agora}
    eventos: List[Dict[str, Any]] = []
    if status is not None:
        if status not in STATUS or status == "aguardando_verificacao":
            raise ValueError("Status inválido.")
        if doc.get("status") == "aguardando_verificacao":
            raise ValueError("Pedido ainda não teve o e-mail confirmado pelo titular.")
        if doc.get("status") in _FINAIS and status not in _FINAIS:
            # reabrir é permitido, mas fica registrado
            eventos.append(_evento("reaberto", admin_uid, f"{doc.get('status')} → {status}", agora))
        sets["status"] = status
        if status in _FINAIS:
            sets["concluido_em"] = agora
        eventos.append(_evento("status", admin_uid, status, agora))
    if responsavel is not None:
        sets["responsavel"] = responsavel.strip()[:120] or None
        eventos.append(_evento("responsavel", admin_uid, sets["responsavel"] or "(nenhum)", agora))
    if nota:
        eventos.append(_evento("nota", admin_uid, nota, agora))
    upd: Dict[str, Any] = {"$set": sets}
    if eventos:
        upd["$push"] = {"historico": {"$each": eventos}}
    await db.privacidade_pedidos.update_one({"id": pedido_id}, upd)
    doc.update(sets)
    doc.setdefault("historico", []).extend(eventos)
    return doc
