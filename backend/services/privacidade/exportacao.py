# @module services.privacidade.exportacao — Exportação dos dados da PRÓPRIA conta.
#
# Escopo (deliberadamente restrito, ver docs/privacidade/retencao-e-direitos.md):
#   - dados da conta do usuário (sem hash de senha, tokens de reset, contadores de
#     bloqueio, segredos);
#   - perfil profissional (sem imagens em base64 — só a indicação de que existem);
#   - aceites, consentimentos, pedidos de privacidade e pagamentos do próprio usuário;
#   - CONTAGEM dos registros de negócio (laudos, clientes, contratos...).
# NÃO inclui o conteúdo da carteira (clientes, proprietários, partes de contratos):
# são dados de TERCEIROS, dos quais o assinante tende a ser controlador. Exportar a
# carteira é decisão de produto/jurídica pendente (portabilidade da carteira).
#
# Todas as consultas filtram pelo user_id DA SESSÃO — nunca por id vindo do cliente.
import csv
import hashlib
import io
import json
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from services.privacidade import config

_CAMPOS_PROIBIDOS_USER = {
    "_id", "password_hash", "reset_token_hash", "reset_token_expires", "failed_logins",
    "lock_until", "romatec_crm_id_secret",
}
_CONTAGENS = (
    "ptam_documents", "clients", "properties", "contratos", "recibos", "propostas",
    "vistorias", "garantias", "georef_projetos", "geo_urbano_projetos", "amostras_mercado",
    "documentos_externos", "evaluations", "locacoes",
)


def _limpar(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _limpar(x) for k, x in v.items() if k != "_id"}
    if isinstance(v, list):
        return [_limpar(x) for x in v]
    if isinstance(v, (bytes, bytearray)):
        return f"<binário: {len(v)} bytes>"
    return v


def _sem_b64(d: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in d.items():
        if k == "_id" or k == "user_id":
            continue
        if k.endswith("_b64") or k.endswith("_paginas_b64"):
            out[k] = "<imagem armazenada — disponível no aplicativo>" if v else None
        else:
            out[k] = v
    return out


async def _lista(db, nome: str, filtro: Dict[str, Any], limite: int = 1000) -> List[Dict[str, Any]]:
    col = getattr(db, nome)
    return await col.find(filtro).to_list(limite)


async def coletar(db, uid: str) -> Dict[str, Any]:
    """Monta o pacote de dados do usuário `uid` (função de leitura, sem efeitos)."""
    user = await db.users.find_one({"id": uid}) or {}
    conta = {k: v for k, v in user.items() if k not in _CAMPOS_PROIBIDOS_USER}
    perfil = await db.perfil_avaliador.find_one({"user_id": uid})
    pacote: Dict[str, Any] = {
        "gerado_em": datetime.utcnow(),
        "aviso": ("Exportação dos dados da sua conta. Registros de clientes e outras pessoas "
                  "cadastradas por você aparecem só como contagem."),
        "conta": conta,
        "perfil_profissional": _sem_b64(perfil) if perfil else None,
        "aceites": await _lista(db, "privacidade_aceites", {"user_id": uid}),
        "consentimentos": await _lista(db, "privacidade_consentimentos", {"user_id": uid}),
        "pedidos_privacidade": [
            {k: v for k, v in p.items() if k not in ("codigo_hash",)}
            for p in await _lista(db, "privacidade_pedidos", {"user_id": uid})
        ],
        "pagamentos": [
            {k: p.get(k) for k in ("mp_payment_id", "plan_id", "status", "amount", "created_at")}
            for p in await _lista(db, "transactions", {"user_id": uid})
        ],
        "contagem_registros": {},
    }
    for nome in _CONTAGENS:
        try:
            pacote["contagem_registros"][nome] = await getattr(db, nome).count_documents({"user_id": uid})
        except Exception:  # noqa: BLE001 — coleção ausente não derruba a exportação
            pacote["contagem_registros"][nome] = None
    return _limpar(pacote)


_PERIGOSOS = ("=", "+", "-", "@", "\t", "\r")


def celula_segura(valor: Any) -> str:
    """Neutraliza injeção de fórmula em planilhas (CSV injection)."""
    s = "" if valor is None else str(valor)
    if s and s[0] in _PERIGOSOS:
        return "'" + s
    return s


def _achatar(prefixo: str, v: Any, linhas: List[Tuple[str, str]]) -> None:
    if isinstance(v, dict):
        for k, x in v.items():
            _achatar(f"{prefixo}.{k}" if prefixo else k, x, linhas)
    elif isinstance(v, list):
        if not v:
            linhas.append((prefixo, ""))
        for i, x in enumerate(v):
            _achatar(f"{prefixo}[{i}]", x, linhas)
    else:
        linhas.append((prefixo, "" if v is None else str(v)))


def para_csv(pacote: Dict[str, Any]) -> bytes:
    linhas: List[Tuple[str, str]] = []
    _achatar("", pacote, linhas)
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL)
    w.writerow(["campo", "valor"])
    for campo, valor in linhas:
        w.writerow([celula_segura(campo), celula_segura(valor)])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def para_json(pacote: Dict[str, Any]) -> bytes:
    return json.dumps(pacote, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def _hash_token(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


async def criar(db, uid: str, formato: str, agora: Optional[datetime] = None) -> Dict[str, Any]:
    """Gera o arquivo e um link privado de curta duração (token de uso único)."""
    if formato not in ("json", "csv"):
        raise ValueError("Formato inválido (use json ou csv).")
    agora = agora or datetime.utcnow()
    pacote = await coletar(db, uid)
    conteudo = para_json(pacote) if formato == "json" else para_csv(pacote)
    token = secrets.token_urlsafe(32)
    expira = agora + timedelta(minutes=config.validade_exportacao_minutos())
    await db.privacidade_exportacoes.insert_one({
        "id": secrets.token_hex(12),
        "user_id": uid,
        "token_hash": _hash_token(token),
        "formato": formato,
        "conteudo": conteudo,
        "criado_em": agora,
        "expira_em": expira,
        "baixado_em": None,
    })
    return {"token": token, "expira_em": expira, "formato": formato}


class ExportacaoIndisponivel(Exception):
    """404: não existe / é de outro usuário (não revela qual)."""


class ExportacaoExpirada(Exception):
    """410: expirou ou já foi baixada."""


async def baixar(db, uid: str, token: str, agora: Optional[datetime] = None) -> Tuple[bytes, str]:
    agora = agora or datetime.utcnow()
    doc = await db.privacidade_exportacoes.find_one({"token_hash": _hash_token(token or ""), "user_id": uid})
    if not doc:
        raise ExportacaoIndisponivel()
    if doc.get("baixado_em") or doc.get("conteudo") is None or doc["expira_em"] < agora:
        # descarta o conteúdo se ainda estiver guardado
        await db.privacidade_exportacoes.update_one({"id": doc["id"]}, {"$set": {"conteudo": None}})
        raise ExportacaoExpirada()
    await db.privacidade_exportacoes.update_one(
        {"id": doc["id"]}, {"$set": {"baixado_em": agora, "conteudo": None}})
    return doc["conteudo"], doc["formato"]
