# @module routes.certificados — CRUD de Certificados Digitais ICP-Brasil A1 (.pfx)
"""
Rotas:
  POST   /api/certificados                   upload .pfx + senha + perfil + label
  GET    /api/certificados                   lista do usuário (sem .pfx/senha)
  PATCH  /api/certificados/{id}/ativar      toggle ativo
  DELETE /api/certificados/{id}              remove

A senha é validada NO MOMENTO DO UPLOAD abrindo o .pfx; se falhar, 400.
.pfx e senha são criptografados AES-256-GCM antes de gravar no MongoDB.
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models import Certificado, CertificadoPublic
from services.cert_crypto import (
    parse_pfx_metadata,
    encrypt_bytes,
)

logger = logging.getLogger("romatec")
router = APIRouter(tags=["certificados"], prefix="/certificados")


MAX_PFX_BYTES = 500 * 1024  # 500 KB — .pfx típico tem 2-10 KB


def _to_public(doc: dict) -> dict:
    """Remove campos sensíveis (.pfx, senha, nonces) antes de retornar."""
    payload = serialize_doc(doc)
    for k in ("pfx_encrypted", "password_encrypted", "nonce_pfx", "nonce_password"):
        payload.pop(k, None)
    return payload


# ── POST /certificados (multipart) ──────────────────────────────────────────

@router.post("", response_model=CertificadoPublic, status_code=201)
async def upload_certificado(
    label: str = Form(..., description="Apelido pra identificar"),
    perfil: str = Form("PF", description="PF (e-CPF) ou PJ (e-CNPJ)"),
    senha: str = Form(..., description="Senha do .pfx"),
    arquivo: UploadFile = File(..., description="Arquivo .pfx ou .p12"),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    if perfil not in ("PF", "PJ"):
        raise HTTPException(status_code=400, detail="perfil deve ser PF ou PJ")

    # Tamanho
    pfx_bytes = await arquivo.read()
    if not pfx_bytes:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    if len(pfx_bytes) > MAX_PFX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo muito grande (máximo {MAX_PFX_BYTES // 1024} KB)",
        )

    # Parsear .pfx (valida senha e extrai metadados)
    try:
        meta = parse_pfx_metadata(pfx_bytes, senha)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Erro inesperado ao parsear .pfx")
        raise HTTPException(status_code=400, detail=f"Falha ao processar certificado: {e}")

    # Verificar duplicata por fingerprint (mesmo .pfx já cadastrado)
    fingerprint = meta["fingerprint_sha256"]
    existing = await db.certificados.find_one(
        {"user_id": uid, "fingerprint_sha256": fingerprint}
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Este certificado já está cadastrado nesta conta.",
        )

    # Criptografar
    pfx_ct, pfx_nonce = encrypt_bytes(pfx_bytes)
    pwd_ct, pwd_nonce = encrypt_bytes(senha.encode("utf-8"))

    cert = Certificado(
        user_id=uid,
        label=label.strip(),
        perfil=perfil,
        titular=meta["titular"],
        documento=meta["documento"],
        valido_de=meta["valido_de"],
        valido_ate=meta["valido_ate"],
        emissor=meta["emissor"],
        serial_number=meta["serial_number"],
        fingerprint_sha256=fingerprint,
        pfx_encrypted=pfx_ct,
        password_encrypted=pwd_ct,
        nonce_pfx=pfx_nonce,
        nonce_password=pwd_nonce,
        ativo=True,
    )

    await db.certificados.insert_one(cert.model_dump())
    logger.info(
        "Certificado cadastrado: user=%s perfil=%s titular=%s validade=%s",
        uid, perfil, meta["titular"], meta["valido_ate"],
    )
    return _to_public(cert.model_dump())


# ── GET /certificados ───────────────────────────────────────────────────────

@router.get("", response_model=List[CertificadoPublic])
async def listar_certificados(
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    items = await db.certificados.find({"user_id": uid}).sort("created_at", -1).to_list(100)
    return [_to_public(i) for i in items]


# ── PATCH /certificados/{id}/ativar ─────────────────────────────────────────

class ToggleAtivoRequest(BaseModel):
    ativo: bool


@router.patch("/{cid}/ativar", response_model=CertificadoPublic)
async def toggle_ativo(
    cid: str,
    body: ToggleAtivoRequest,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    cert = await db.certificados.find_one({"id": cid, "user_id": uid})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificado não encontrado")
    await db.certificados.update_one(
        {"id": cid},
        {"$set": {"ativo": body.ativo, "updated_at": datetime.utcnow()}},
    )
    cert = await db.certificados.find_one({"id": cid})
    return _to_public(cert)


# ── DELETE /certificados/{id} ───────────────────────────────────────────────

@router.delete("/{cid}")
async def remover_certificado(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    res = await db.certificados.delete_one({"id": cid, "user_id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Certificado não encontrado")
    return {"ok": True}
