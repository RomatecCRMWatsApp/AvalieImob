# @module routes.uploads — Upload e recuperação de imagens/documentos.
# Os bytes vão para o Cloudflare R2 (via services.image_store); o MongoDB guarda
# só a referência (r2_key). Imagens antigas (base64 no Mongo) seguem funcionando.
import asyncio
import logging
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from db import get_db
from dependencies import get_active_subscriber
from services import image_store
from services.upload_security import detect_content_type, normalize_filename
from services.pdf_converter import (
    PdfConversionError,
    convert_pdf_to_page_pngs,
    image_bytes_to_tiff,
)

router = APIRouter(tags=["uploads"])
logger = logging.getLogger("romatec")

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "application/pdf"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/upload/image")
async def upload_image(file: UploadFile = File(...), uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    declared_content_type = (file.content_type or "").lower()
    if declared_content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de arquivo não permitido: {declared_content_type}.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio não é permitido")
    if len(data) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo muito grande. Tamanho máximo: 5MB")
    detected_content_type = detect_content_type(data)
    if detected_content_type not in {"image/jpeg", "image/png", "image/webp", "application/pdf"}:
        raise HTTPException(status_code=400, detail="Conteúdo do arquivo inválido ou não suportado")
    if detected_content_type == "application/pdf" and declared_content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="PDF deve ser enviado com content type application/pdf")

    nome = normalize_filename(file.filename)

    # ── PDF: rasteriza cada página em PNG 300 DPI (1 imagem/id por página) ──────
    # Persiste no MongoDB (db.images), igual às fotos — sobrevive a redeploys do
    # Railway (filesystem é efêmero). O PDF original é guardado para auditoria.
    # Cada página vira um card no uploader e é embutida no laudo (DocCard renderiza
    # a imagem; antes, PDF aparecia só como placeholder cinza).
    if detected_content_type == "application/pdf":
        try:
            page_pngs = convert_pdf_to_page_pngs(data)
        except PdfConversionError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except RuntimeError as exc:
            logger.exception("Falha na conversão PDF→PNG (user=%s)", uid)
            raise HTTPException(status_code=500, detail=str(exc))

        # PDF original (auditoria) — não entra na lista de cards.
        original_id = str(uuid.uuid4())
        await image_store.salvar_imagem(
            db, uid, data, "application/pdf", nome, image_id=original_id,
            extra={"is_original_pdf": True, "pdf_pages_total": len(page_pngs)},
        )

        total = len(page_pngs)
        base_nome = nome[:-4] if nome.lower().endswith(".pdf") else nome
        pages = []
        for idx, png in enumerate(page_pngs, start=1):
            pid = str(uuid.uuid4())
            await image_store.salvar_imagem(
                db, uid, png, "image/png", f"{base_nome} (p. {idx}/{total}).png",
                image_id=pid,
                extra={
                    "convertido_de_pdf": True,
                    "source_pdf_id": original_id,
                    "pdf_page": idx,
                    "pdf_pages_total": total,
                    "dpi": 300,
                },
            )
            pages.append({
                "id": pid,
                "url": f"/api/upload/image/{pid}",
                "content_type": "image/png",
                "page": idx,
            })
        logger.info("PDF convertido: user=%s paginas=%d original=%s size=%d", uid, total, original_id, len(data))
        first = pages[0]
        return {
            "id": first["id"],
            "url": first["url"],
            "content_type": "image/png",
            "convertido": True,
            "page_count": total,
            "source_pdf_id": original_id,
            "pages": pages,
        }

    # ── Imagem direta (JPG/PNG/WebP): armazena no R2 (fallback base64) ───────────
    doc = await image_store.salvar_imagem(db, uid, data, detected_content_type, nome)
    image_id = doc["id"]
    logger.info("Image uploaded: id=%s user=%s size=%d r2=%s", image_id, uid, len(data), bool(doc.get("r2_key")))
    url = f"/api/upload/image/{image_id}"
    return {
        "id": image_id,
        "url": url,
        "content_type": detected_content_type,
        "convertido": False,
        "page_count": 1,
        "pages": [{"id": image_id, "url": url, "content_type": detected_content_type, "page": 1}],
    }


@router.get("/upload/image/{image_id}")
async def get_image(image_id: str, db=Depends(get_db)):
    # Servida SEM exigir o header Authorization: tags <img src="..."> do navegador
    # não enviam o Bearer token, então qualquer dependência de auth (HTTPBearer)
    # retornaria 403 e a imagem nunca carregaria. O UUID v4 é a própria credencial
    # (capability URL, não enumerável) — coerente com a geração de DOCX/PDF, que já
    # busca a imagem só por id, e com o compartilhamento público de PTAM.
    doc = await db.images.find_one({"id": image_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    raw = await image_store.bytes_do_doc(doc)
    if raw is None:
        raise HTTPException(status_code=422, detail="Imagem corrompida ou indisponível")
    return Response(
        content=raw,
        media_type=doc.get("content_type", "image/jpeg"),
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.get("/upload/image/{image_id}/tiff")
async def get_image_tiff(image_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Baixa a imagem como TIFF 300 DPI LZW (lossless), gerado sob demanda — sem
    duplicar storage no Mongo. Útil para arquivamento de páginas de documento."""
    doc = await db.images.find_one({"id": image_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    ct = (doc.get("content_type") or "").lower()
    if ct == "application/pdf":
        raise HTTPException(status_code=422, detail="Use uma página convertida (PNG) para gerar TIFF.")
    raw = await image_store.bytes_do_doc(doc)
    if raw is None:
        raise HTTPException(status_code=422, detail="Imagem indisponível.")
    try:
        tiff = image_bytes_to_tiff(raw)
    except Exception:
        raise HTTPException(status_code=422, detail="Falha ao gerar TIFF.")
    base = (doc.get("filename") or image_id).rsplit(".", 1)[0]
    return Response(
        content=tiff,
        media_type="image/tiff",
        headers={
            "Cache-Control": "private, max-age=86400",
            "Content-Disposition": f'attachment; filename="{base}.tiff"',
        },
    )


@router.get("/upload/image/{image_id}/metadata")
async def image_metadata(image_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Extrai GPS e data/hora do EXIF da foto (quando presentes) para copiar."""
    doc = await db.images.find_one({"id": image_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    raw = await image_store.bytes_do_doc(doc)
    if raw is None:
        raise HTTPException(status_code=422, detail="Imagem indisponível")
    fonte = ""
    try:
        from services.ptam_pdf_v2 import _exif_gps_data
        gps, data_hora = _exif_gps_data(raw)
        if gps or data_hora:
            fonte = "exif"
    except Exception:
        gps, data_hora = "", ""

    # Fallback: muitas fotos perdem o EXIF (WhatsApp etc.), mas tem o overlay
    # "queimado" com GPS/data. Le via OCR (Tesseract) em thread separada.
    if not gps and not data_hora:
        try:
            from services.foto_ocr import extrair_gps_data_ocr
            g2, d2 = await asyncio.to_thread(extrair_gps_data_ocr, raw)
            if g2 or d2:
                gps, data_hora, fonte = g2, d2, "ocr"
        except Exception:
            pass

    maps_url = ""
    if gps:
        import re as _re
        m = _re.match(r"\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)", gps)
        if m:
            maps_url = f"https://www.google.com/maps?q={m.group(1)},{m.group(2)}"
    # Cacheia na imagem para o PDF reusar (sem reprocessar OCR).
    if gps or data_hora:
        try:
            await db.images.update_one(
                {"id": image_id},
                {"$set": {"meta_gps": gps, "meta_data_hora": data_hora}},
            )
        except Exception:
            pass

    partes = []
    if gps:
        partes.append(f"GPS: {gps}")
    if data_hora:
        partes.append(f"Data/Hora: {data_hora}")
    return {
        "gps": gps,
        "data_hora": data_hora,
        "maps_url": maps_url,
        "fonte": fonte,
        "tem_dados": bool(gps or data_hora),
        "texto_copia": "  |  ".join(partes),
    }


@router.delete("/upload/image/{image_id}")
async def delete_image(image_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    ok = await image_store.remover_imagem(db, image_id, uid=uid)
    if not ok:
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return {"ok": True}
