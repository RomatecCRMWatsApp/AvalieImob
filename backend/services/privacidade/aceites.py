# @module services.privacidade.aceites — Aceite versionado (Termos/Aviso) e
# consentimentos OPCIONAIS de marketing, separados.
#
# - Aceite: grava (user_id, tipo, versao, hash, aceito_em do SERVIDOR). Não grava IP
#   nem dispositivo (minimização — a prova é usuário autenticado + versão/hash).
#   Usuário antigo SEM registro fica "aceite pendente": nada é retroagido e nenhum
#   fluxo é bloqueado (decisão de rollout fica com o dono).
# - Consentimento de marketing: histórico APPEND-ONLY de eventos concedido/revogado;
#   o estado atual é o último evento. Padrão = não consentido (nada pré-marcado).
import secrets
from datetime import datetime
from typing import Any, Dict, Optional

from services.privacidade import documentos

FINALIDADES_MARKETING = {
    "marketing_email": "Receber novidades e ofertas por e-mail",
    "marketing_whatsapp": "Receber novidades e ofertas por WhatsApp",
}


async def estado_aceites(db, uid: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for tipo in documentos.TIPOS:
        atual = documentos.carregar(tipo)
        ultimo = None
        regs = await db.privacidade_aceites.find({"user_id": uid, "tipo": tipo}).to_list(1000)
        if regs:
            ultimo = max(regs, key=lambda r: r.get("aceito_em") or datetime.min)
        pendente = (atual is not None) and (not ultimo or ultimo.get("hash") != atual["hash"])
        out[tipo] = {
            "versao_atual": atual and atual["versao"],
            "hash_atual": atual and atual["hash"],
            "aceito_versao": ultimo and ultimo.get("versao"),
            "aceito_em": ultimo and ultimo.get("aceito_em"),
            "pendente": pendente,
        }
    return out


async def registrar_aceite(db, uid: str, tipo: str, versao: str, hash_doc: str,
                           agora: Optional[datetime] = None) -> Dict[str, Any]:
    atual = documentos.carregar(tipo)
    if not atual:
        raise LookupError("Documento indisponível.")
    if versao != atual["versao"] or hash_doc != atual["hash"]:
        # o usuário só pode aceitar o texto que está sendo servido agora
        raise ValueError("A versão informada não é a vigente. Recarregue o documento.")
    agora = agora or datetime.utcnow()
    existente = await db.privacidade_aceites.find_one({"user_id": uid, "tipo": tipo, "hash": hash_doc})
    if existente:
        return existente  # idempotente
    reg = {"id": secrets.token_hex(12), "user_id": uid, "tipo": tipo, "versao": versao,
           "hash": hash_doc, "aceito_em": agora}
    await db.privacidade_aceites.insert_one(reg)
    return reg


async def estado_consentimentos(db, uid: str) -> Dict[str, Any]:
    eventos = await db.privacidade_consentimentos.find({"user_id": uid}).to_list(5000)
    out = {}
    for fin, rotulo in FINALIDADES_MARKETING.items():
        evs = sorted([e for e in eventos if e.get("finalidade") == fin],
                     key=lambda e: e.get("em") or datetime.min)
        ult = evs[-1] if evs else None
        out[fin] = {"rotulo": rotulo, "concedido": bool(ult and ult.get("concedido")),
                    "atualizado_em": ult and ult.get("em"), "eventos": len(evs)}
    return out


async def registrar_consentimento(db, uid: str, finalidade: str, concedido: bool,
                                  agora: Optional[datetime] = None) -> Dict[str, Any]:
    if finalidade not in FINALIDADES_MARKETING:
        raise ValueError("Finalidade inválida.")
    agora = agora or datetime.utcnow()
    ev = {"id": secrets.token_hex(12), "user_id": uid, "finalidade": finalidade,
          "concedido": bool(concedido), "em": agora, "origem": "central_privacidade"}
    await db.privacidade_consentimentos.insert_one(ev)
    return ev
