# @module routes.perfil_avaliador — CRUD do perfil profissional do avaliador
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from db import get_db
from dependencies import serialize_doc
from services.auth_service import get_current_user_id
from models import PerfilAvaliadorBase, PerfilAvaliador

router = APIRouter(tags=["perfil-avaliador"])


class CartaoRegularidadeBody(BaseModel):
    cartao_regularidade_b64: Optional[str] = None
    cartao_regularidade_link: Optional[str] = None
    cartao_regularidade_anexar: Optional[bool] = None


class CertidaoRegularidadeBody(BaseModel):
    certidao_regularidade_b64: Optional[str] = None
    certidao_regularidade_validade: Optional[str] = None
    certidao_regularidade_link: Optional[str] = None
    certidao_regularidade_anexar: Optional[bool] = None


class CertificadoCnaiBody(BaseModel):
    certificado_cnai_b64: Optional[str] = None
    certificado_cnai_anexar: Optional[bool] = None


def _campos_arquivo_regularidade(prefix: str, b64) -> dict:
    """Converte o arquivo recebido (imagem OU PDF) nos campos de armazenamento do perfil.
    PDF → páginas-imagem em {prefix}_paginas_b64; imagem → {prefix}_b64; "" remove ambos."""
    from services.cartao_regularidade import is_pdf_b64, pdf_b64_to_paginas_png_b64
    if b64 == "":
        return {f"{prefix}_b64": "", f"{prefix}_paginas_b64": []}
    if is_pdf_b64(b64):
        return {f"{prefix}_paginas_b64": pdf_b64_to_paginas_png_b64(b64), f"{prefix}_b64": ""}
    return {f"{prefix}_b64": b64, f"{prefix}_paginas_b64": []}


@router.get("/perfil-avaliador")
async def get_perfil_avaliador(uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    doc = await db.perfil_avaliador.find_one({"user_id": uid})
    if not doc:
        return PerfilAvaliador(user_id=uid).model_dump(mode="json")
    return serialize_doc(doc)


@router.put("/perfil-avaliador")
async def update_perfil_avaliador(body: PerfilAvaliadorBase, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    now = datetime.utcnow()
    data = body.model_dump(mode="json")
    data["user_id"] = uid
    data["updated_at"] = now
    existing = await db.perfil_avaliador.find_one({"user_id": uid})
    if existing:
        await db.perfil_avaliador.update_one({"user_id": uid}, {"$set": data})
        doc = await db.perfil_avaliador.find_one({"user_id": uid})
    else:
        data["id"] = str(uuid.uuid4())
        data["created_at"] = now
        await db.perfil_avaliador.insert_one(data)
        doc = await db.perfil_avaliador.find_one({"user_id": uid})
    return serialize_doc(doc)


@router.put("/perfil-avaliador/cartao-regularidade")
async def set_cartao_regularidade(body: CartaoRegularidadeBody,
                                  uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    """Salva SÓ o Cartão de Regularidade (CRECI) no perfil — sem mexer no resto.
    Aceita IMAGEM (PNG/JPG/WEBP) ou PDF — o PDF é convertido em páginas-imagem (frente/verso)."""
    upd = {"updated_at": datetime.utcnow()}
    if body.cartao_regularidade_link is not None:
        upd["cartao_regularidade_link"] = body.cartao_regularidade_link
    if body.cartao_regularidade_anexar is not None:
        upd["cartao_regularidade_anexar"] = body.cartao_regularidade_anexar
    if body.cartao_regularidade_b64 is not None:
        upd.update(_campos_arquivo_regularidade("cartao_regularidade", body.cartao_regularidade_b64))
    await db.perfil_avaliador.update_one(
        {"user_id": uid},
        {"$set": upd, "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": datetime.utcnow()}},
        upsert=True,
    )
    doc = await db.perfil_avaliador.find_one({"user_id": uid})
    return serialize_doc(doc)


@router.put("/perfil-avaliador/assinatura-tecnico")
async def set_assinatura_tecnico(body: dict, uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    """Salva a assinatura GRÁFICA do responsável técnico (PNG transparente). É carimbada
    automaticamente no Memorial do Geo Urbano ao gerar/enviar às partes (o ICP sela depois).
    Aceita dataURL ou base64 puro; "" remove."""
    raw = (body or {}).get("assinatura_b64")
    val = "" if not raw else str(raw).split(",")[-1]
    await db.perfil_avaliador.update_one(
        {"user_id": uid},
        {"$set": {"assinatura_tecnico_b64": val, "updated_at": datetime.utcnow()},
         "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": datetime.utcnow()}},
        upsert=True,
    )
    doc = await db.perfil_avaliador.find_one({"user_id": uid})
    return serialize_doc(doc)


@router.put("/perfil-avaliador/certidao-regularidade")
async def set_certidao_regularidade(body: CertidaoRegularidadeBody,
                                    uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    """Salva SÓ a Certidão de Regularidade (CRECI) no perfil — gerada on-line, com validade.
    Aceita IMAGEM ou PDF (convertido em páginas-imagem)."""
    upd = {"updated_at": datetime.utcnow()}
    if body.certidao_regularidade_validade is not None:
        upd["certidao_regularidade_validade"] = body.certidao_regularidade_validade
    if body.certidao_regularidade_link is not None:
        upd["certidao_regularidade_link"] = body.certidao_regularidade_link
    if body.certidao_regularidade_anexar is not None:
        upd["certidao_regularidade_anexar"] = body.certidao_regularidade_anexar
    if body.certidao_regularidade_b64 is not None:
        upd.update(_campos_arquivo_regularidade("certidao_regularidade", body.certidao_regularidade_b64))
    await db.perfil_avaliador.update_one(
        {"user_id": uid},
        {"$set": upd, "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": datetime.utcnow()}},
        upsert=True,
    )
    doc = await db.perfil_avaliador.find_one({"user_id": uid})
    return serialize_doc(doc)


@router.put("/perfil-avaliador/certificado-cnai")
async def set_certificado_cnai(body: CertificadoCnaiBody,
                               uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    """Salva o Certificado CNAI (miniatura no currículo do PTAM). Aceita IMAGEM ou PDF."""
    upd = {"updated_at": datetime.utcnow()}
    if body.certificado_cnai_anexar is not None:
        upd["certificado_cnai_anexar"] = body.certificado_cnai_anexar
    if body.certificado_cnai_b64 is not None:
        upd.update(_campos_arquivo_regularidade("certificado_cnai", body.certificado_cnai_b64))
    await db.perfil_avaliador.update_one(
        {"user_id": uid},
        {"$set": upd, "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": datetime.utcnow()}},
        upsert=True,
    )
    doc = await db.perfil_avaliador.find_one({"user_id": uid})
    return serialize_doc(doc)
