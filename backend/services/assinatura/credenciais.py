# @module services.assinatura.credenciais — CRUD das credenciais BYOK (isolado por user_id).
# Credenciais cifradas (Fernet) no banco; nunca retornadas em claro (só máscara).
from __future__ import annotations

import uuid
from datetime import datetime

from services import crypto_service as CS
from services.assinatura.catalogo import provedor, CAMPOS_OBRIGATORIOS, CAMPOS_TODOS

COLL = "assinatura_credenciais"


class CredencialInvalida(Exception):
    """Provider desconhecido ou campos obrigatórios ausentes (HTTP 422)."""


def _mask_doc(doc: dict) -> dict:
    try:
        cred = CS.mascarar_credenciais(CS.decrypt_json(doc.get("credenciais_encrypted", "")))
    except Exception:  # noqa: BLE001 — credencial corrompida não vaza nada
        cred = {}
    return {
        "id": doc.get("id"),
        "provider": doc.get("provider"),
        "ambiente": doc.get("ambiente", "producao"),
        "padrao": bool(doc.get("padrao")),
        "ativo": doc.get("ativo", True),
        "credenciais_mascaradas": cred,
        "ultimo_teste_em": doc.get("ultimo_teste_em"),
        "ultimo_teste_ok": doc.get("ultimo_teste_ok"),
        "ultimo_teste_msg": doc.get("ultimo_teste_msg"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


async def listar(db, user_id: str) -> list:
    docs = await db[COLL].find({"user_id": user_id}).to_list(length=None)
    return [_mask_doc(d) for d in docs]


async def salvar(db, user_id: str, provider: str, ambiente: str, credenciais: dict, padrao: bool = False) -> dict:
    """Upsert por (user_id, provider). Cifra as credenciais; valida obrigatórios."""
    if not provedor(provider):
        raise CredencialInvalida(f"provider desconhecido: {provider}")
    ambiente = "sandbox" if str(ambiente) == "sandbox" else "producao"
    obrig = CAMPOS_OBRIGATORIOS[provider]
    todos = CAMPOS_TODOS[provider]
    cred = dict(credenciais or {})
    existing = await db[COLL].find_one({"user_id": user_id, "provider": provider})
    # Edição: campos não digitados (vêm mascarados/vazios) são MANTIDOS do valor atual.
    if existing:
        try:
            prev = CS.decrypt_json(existing.get("credenciais_encrypted", ""))
        except Exception:  # noqa: BLE001
            prev = {}
        for c in todos:
            if not str(cred.get(c) or "").strip() and str(prev.get(c) or "").strip():
                cred[c] = prev[c]
    faltando = [c for c in obrig if not str(cred.get(c) or "").strip()]
    if faltando:
        raise CredencialInvalida(f"campos obrigatórios ausentes: {', '.join(faltando)}")
    # cifra TODOS os campos conhecidos do provedor preenchidos (não guarda lixo)
    limpo = {k: cred[k] for k in todos if str(cred.get(k) or "").strip()}
    enc = CS.encrypt_json(limpo)
    now = datetime.utcnow()
    if existing:
        await db[COLL].update_one(
            {"user_id": user_id, "provider": provider},
            {"$set": {"credenciais_encrypted": enc, "ambiente": ambiente, "ativo": True,
                      "updated_at": now,
                      # troca de credencial invalida o teste anterior
                      "ultimo_teste_ok": None, "ultimo_teste_em": None, "ultimo_teste_msg": None}},
        )
    else:
        await db[COLL].insert_one({
            "id": str(uuid.uuid4()), "user_id": user_id, "provider": provider, "ambiente": ambiente,
            "credenciais_encrypted": enc, "padrao": False, "ativo": True,
            "ultimo_teste_em": None, "ultimo_teste_ok": None, "ultimo_teste_msg": None,
            "created_at": now, "updated_at": now,
        })

    if padrao:
        await definir_padrao(db, user_id, provider)

    doc = await db[COLL].find_one({"user_id": user_id, "provider": provider})
    return _mask_doc(doc)


async def definir_padrao(db, user_id: str, provider: str) -> bool:
    """Marca 1 provedor como padrão e desmarca os demais do MESMO usuário."""
    await db[COLL].update_many({"user_id": user_id}, {"$set": {"padrao": False}})
    r = await db[COLL].update_one(
        {"user_id": user_id, "provider": provider},
        {"$set": {"padrao": True, "updated_at": datetime.utcnow()}},
    )
    return getattr(r, "modified_count", 0) > 0


async def remover(db, user_id: str, provider: str) -> bool:
    r = await db[COLL].delete_one({"user_id": user_id, "provider": provider})
    return getattr(r, "deleted_count", 0) > 0


async def registrar_teste(db, user_id: str, provider: str, ok: bool, msg: str) -> None:
    """Grava o resultado do último teste de conexão na credencial."""
    now = datetime.utcnow()
    await db[COLL].update_one(
        {"user_id": user_id, "provider": provider},
        {"$set": {"ultimo_teste_em": now, "ultimo_teste_ok": bool(ok),
                  "ultimo_teste_msg": (msg or "")[:300], "updated_at": now}},
    )


async def obter_decifrada(db, user_id: str, provider: str):
    """(doc, credenciais_dict) p/ os adapters (PR2). None,None se não houver."""
    doc = await db[COLL].find_one({"user_id": user_id, "provider": provider})
    if not doc:
        return None, None
    return doc, CS.decrypt_json(doc.get("credenciais_encrypted", ""))
