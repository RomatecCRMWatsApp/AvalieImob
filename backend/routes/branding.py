# @module routes.branding — White-label por usuário (logo, cores, rodapé, preview)
"""
Endpoints de personalização de marca (white-label) do AvalieImob.

Base efetiva: /api/branding  (montado sob o APIRouter global prefix="/api").
A marca configurada aqui é aplicada a TODOS os documentos gerados — PTAM, TVI,
Locação (ReportLab) e Contrato, Recibo, TVI/Locação DOCX (python-docx) — via
services.branding_context.BrandContext. Sem branding salvo → padrão AvalieImob.

Leitura: qualquer usuário autenticado. Escrita: assinante ativo (feature paga).
"""
import logging
import uuid as _uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

from db import get_db
from dependencies import get_active_subscriber, get_authenticated_user
from models.tenant_branding import (
    BrandingColors,
    BrandingFooter,
    BrandingTypography,
)
from services import branding_repository as repo
from services import r2_storage
from services.image_processing import LogoValidationError, process_logo
from services.pdf_branding import render_preview_png

router = APIRouter(prefix="/branding", tags=["branding"])
logger = logging.getLogger("romatec")


def _serialize(branding) -> dict:
    return branding.model_dump(mode="json")


# ── Leitura ──────────────────────────────────────────────────────────────────
@router.get("")
async def get_branding(uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    """Config completa de marca do usuário (ou padrão AvalieImob se não houver)."""
    branding = await repo.get_branding(db, uid)
    return _serialize(branding)


@router.get("/preview")
async def preview(uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    """PNG de amostra (cabeçalho + corpo + rodapé) refletindo a marca atual."""
    branding = await repo.get_branding(db, uid)
    data = render_preview_png(branding)
    media = "image/png" if data[:4] == b"\x89PNG" else "application/pdf"
    return Response(content=data, media_type=media)


# ── Logo ─────────────────────────────────────────────────────────────────────
@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """
    Upload do logo (PNG/SVG/JPG, máx 2MB). Detecta MIME real, converte para PNG
    300 DPI, sobe ao R2 e salva a URL. Remove o logo anterior, se houver.
    """
    raw = await file.read()
    try:
        processed = process_logo(raw, file.content_type)
    except LogoValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    key = f"branding/{uid}/{_uuid.uuid4().hex}.png"
    try:
        url = r2_storage.upload_bytes(processed.png_bytes, key, processed.content_type)
    except r2_storage.StorageError as exc:
        logger.error("Falha upload logo R2 (uid=%s): %s", uid, exc)
        raise HTTPException(status_code=502, detail="Falha ao armazenar o logo. Tente novamente.")

    old_url = await repo.get_logo_url(db, uid)
    branding = await repo.set_logo(
        db,
        uid,
        logo_url=url,
        original_name=file.filename or "logo",
        mime=processed.detected_mime,
        width_px=processed.width_px,
        height_px=processed.height_px,
    )
    if old_url and old_url != url:
        try:
            r2_storage.delete_object(old_url)
        except r2_storage.StorageError:
            logger.warning("Não foi possível remover logo antigo (uid=%s)", uid)

    return _serialize(branding)


@router.delete("/logo")
async def delete_logo(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Remove o logo do usuário (volta ao logo padrão AvalieImob nos documentos)."""
    old_url = await repo.get_logo_url(db, uid)
    branding = await repo.clear_logo(db, uid)
    if old_url:
        try:
            r2_storage.delete_object(old_url)
        except r2_storage.StorageError:
            logger.warning("Não foi possível remover logo do R2 (uid=%s)", uid)
    return _serialize(branding)


# ── Cores / Rodapé / Tipografia ──────────────────────────────────────────────
@router.put("/colors")
async def put_colors(
    payload: BrandingColors,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    branding = await repo.update_colors(db, uid, payload.model_dump(exclude_none=True))
    return _serialize(branding)


@router.put("/footer")
async def put_footer(
    payload: BrandingFooter,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    branding = await repo.update_footer(db, uid, payload.model_dump(exclude_none=True))
    return _serialize(branding)


@router.put("/typography")
async def put_typography(
    payload: BrandingTypography,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    branding = await repo.update_typography(db, uid, payload.model_dump(exclude_none=True))
    return _serialize(branding)


# ── Toggle padrão / Reset ────────────────────────────────────────────────────
@router.put("/use-default")
async def put_use_default(
    payload: dict,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Ativa/desativa o uso do padrão AvalieImob sem apagar a config salva."""
    value = bool(payload.get("use_default", True))
    branding = await repo.set_use_default(db, uid, value)
    return _serialize(branding)


@router.post("/reset")
async def reset(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Restaura totalmente o padrão AvalieImob (zera cores, rodapé e logo)."""
    old_url = await repo.get_logo_url(db, uid)
    branding = await repo.reset_branding(db, uid)
    if old_url:
        try:
            r2_storage.delete_object(old_url)
        except r2_storage.StorageError:
            logger.warning("Não foi possível remover logo no reset (uid=%s)", uid)
    return JSONResponse(_serialize(branding))
