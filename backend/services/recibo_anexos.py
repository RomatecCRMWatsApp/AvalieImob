# @module services.recibo_anexos — Upload/armazenamento/envio de anexos de recibo
"""
Anexos do recibo (documentos comprobatórios): até 5 arquivos, 10MB cada,
nos formatos PDF/JPG/PNG/WebP.

Os bytes ficam em db.images (mesma coleção das fotos do PTAM — sobrevive a
redeploys), e a metadata fica no array `anexos` do recibo:
    {id, url, name, content_type, size_bytes}
"""
import base64
import logging
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger("romatec")

MAX_ANEXOS = 5
MAX_ANEXO_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_ANEXO_TYPES = {"application/pdf", "image/jpeg", "image/jpg", "image/png", "image/webp"}


async def salvar_anexo(db, *, uid: str, filename: str, content_type: str, data: bytes) -> dict:
    """Persiste o anexo em db.images e devolve a metadata p/ o array do recibo."""
    ct = (content_type or "").lower()
    if ct == "image/jpg":
        ct = "image/jpeg"
    if ct not in ALLOWED_ANEXO_TYPES:
        raise ValueError(f"Tipo de arquivo não permitido: {content_type}")
    if not data:
        raise ValueError("Arquivo vazio não é permitido")
    if len(data) > MAX_ANEXO_BYTES:
        raise ValueError("Arquivo muito grande. Tamanho máximo: 10MB")

    anexo_id = str(uuid.uuid4())
    await db.images.insert_one({
        "id": anexo_id,
        "user_id": uid,
        "filename": filename or f"anexo-{anexo_id}",
        "content_type": ct,
        "data_b64": base64.b64encode(data).decode("utf-8"),
        "size_bytes": len(data),
        "created_at": datetime.utcnow(),
        "is_recibo_anexo": True,
    })
    return {
        "id": anexo_id,
        "url": f"/api/upload/image/{anexo_id}",
        "name": filename or f"anexo-{anexo_id}",
        "content_type": ct,
        "size_bytes": len(data),
    }


def _imagem_para_pdf_page(raw: bytes) -> Optional[bytes]:
    """Converte uma imagem (jpg/png/webp) em uma página PDF A4 (imagem centralizada)."""
    try:
        import io as _io
        from PIL import Image
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader

        im = Image.open(_io.BytesIO(raw))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        W, H = A4
        margin = 36  # ~0,5 polegada
        max_w, max_h = W - 2 * margin, H - 2 * margin
        iw, ih = im.size
        scale = min(max_w / iw, max_h / ih)
        dw, dh = iw * scale, ih * scale
        x, y = (W - dw) / 2, (H - dh) / 2
        buf = _io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.drawImage(ImageReader(im), x, y, width=dw, height=dh,
                    preserveAspectRatio=True, mask="auto")
        c.showPage()
        c.save()
        return buf.getvalue()
    except Exception as e:
        logger.warning("anexo imagem->pdf falhou: %s", e)
        return None


async def anexar_anexos_ao_pdf(db, recibo: dict, pdf_bytes: bytes) -> bytes:
    """Mescla os anexos (PDF e imagens) ao final do PDF do recibo.
       Best-effort: se algo falhar, devolve o PDF original sem anexos."""
    anexos = recibo.get("anexos") or []
    if not anexos:
        return pdf_bytes
    try:
        import io as _io
        from pypdf import PdfReader, PdfWriter

        writer = PdfWriter()
        for p in PdfReader(_io.BytesIO(pdf_bytes)).pages:
            writer.add_page(p)

        for ax in anexos:
            carregado = await carregar_anexo_bytes(db, ax)
            if not carregado:
                continue
            raw, name, ct = carregado
            ct = (ct or "").lower()
            try:
                if ct == "application/pdf":
                    for p in PdfReader(_io.BytesIO(raw)).pages:
                        writer.add_page(p)
                elif ct.startswith("image/"):
                    page_pdf = _imagem_para_pdf_page(raw)
                    if page_pdf:
                        for p in PdfReader(_io.BytesIO(page_pdf)).pages:
                            writer.add_page(p)
            except Exception as e:
                logger.warning("Falha ao anexar anexo %s ao PDF: %s", name, e)

        out = _io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception as e:
        logger.warning("Falha ao mesclar anexos no PDF do recibo: %s", e)
        return pdf_bytes


async def carregar_anexo_bytes(db, anexo: dict) -> Optional[tuple[bytes, str, str]]:
    """Devolve (bytes, filename, content_type) de um anexo, ou None se sumiu."""
    anexo_id = anexo.get("id")
    if not anexo_id:
        return None
    img = await db.images.find_one({"id": anexo_id})
    if not img or not img.get("data_b64"):
        return None
    try:
        raw = base64.b64decode(img["data_b64"])
    except Exception:
        return None
    return (
        raw,
        anexo.get("name") or img.get("filename") or f"{anexo_id}",
        anexo.get("content_type") or img.get("content_type") or "application/octet-stream",
    )
