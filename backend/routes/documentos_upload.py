# @module routes.documentos_upload — Upload de documentos do imóvel com conversão PDF→TIFF 300 DPI
"""
Router dedicado ao upload de documentos anexos de um imóvel.

Regra central: arquivos PDF são automaticamente rasterizados em TIFF 300 DPI (LZW,
lossless) — uma página por arquivo — e ganham um JPEG de preview por página. O PDF
original é preservado para auditoria. Imagens (JPG/PNG/WebP) e o campo de fotografias
são armazenados sem transformação.

Storage: filesystem local em DOC_STORAGE_ROOT (default ./storage/imoveis). Os metadados
ficam embutidos no documento do imóvel (collection `properties`), no mapa
`documentos.{tipo}` (lista). Isolamento por user_id em todas as queries.

⚠️ Produção (Railway): o filesystem do container é efêmero — arquivos somem entre
deploys. Migrar DOC_STORAGE_ROOT para um bucket (S3/R2) e trocar os paths por URLs
assinadas em etapa posterior.
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from db import get_db
from dependencies import get_active_subscriber
from models.documento_anexo import DocumentoAnexo, TipoDocumento
from services.pdf_converter import PdfConversionError, convert_pdf_to_tiff_pages, is_pdf
from services.upload_security import detect_content_type, normalize_filename

router = APIRouter(prefix="/imoveis/{imovel_id}/documentos", tags=["documentos"])
logger = logging.getLogger("romatec")

# Raiz de storage (configurável; default relativo ao processo do backend).
STORAGE_ROOT = Path(os.environ.get("DOC_STORAGE_ROOT", "storage/imoveis")).resolve()

# Tipos que NUNCA são convertidos (são sempre imagens).
_TIPOS_SEM_CONVERSAO = {TipoDocumento.FOTOGRAFIAS}

# Limites por tipo (refletem a UI).
_LIMITES: dict[TipoDocumento, int] = {
    TipoDocumento.SIGEF_MAPA:          3,
    TipoDocumento.SIGEF_MEMORIAL:      3,
    TipoDocumento.CCIR:                3,
    TipoDocumento.ITR:                 1,
    TipoDocumento.CAR:                 3,
    TipoDocumento.MATRICULA:          50,
    TipoDocumento.PLANTA_PROJETO:     50,
    TipoDocumento.ESCRITURA:          50,
    TipoDocumento.FOTOGRAFIAS:        50,
    TipoDocumento.GEOREFERENCIAMENTO: 50,
    TipoDocumento.HABITE_SE:          50,
    TipoDocumento.IPTU:               50,
    TipoDocumento.OUTROS:             50,
}

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB (conforme UI)
_IMAGENS_DIRETAS = {"image/jpeg", "image/png", "image/webp"}


async def _carregar_imovel(db, imovel_id: str, uid: str) -> dict:
    """Busca o imóvel garantindo isolamento por usuário."""
    imovel = await db.properties.find_one({"id": imovel_id, "user_id": uid})
    if not imovel:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado.")
    return imovel


def _safe_full_path(rel_path: str) -> Path:
    """Resolve um path relativo dentro do STORAGE_ROOT, barrando path traversal."""
    full = (STORAGE_ROOT / rel_path).resolve()
    if not str(full).startswith(str(STORAGE_ROOT)):
        raise HTTPException(status_code=400, detail="Caminho de arquivo inválido.")
    return full


@router.post(
    "/{tipo}",
    response_model=DocumentoAnexo,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de documento com conversão automática PDF→TIFF 300 DPI",
)
async def upload_documento(
    imovel_id: str,
    tipo: TipoDocumento,
    file: UploadFile = File(..., description="PDF, JPG, PNG ou WebP (máx 5 MB)"),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
) -> DocumentoAnexo:
    imovel = await _carregar_imovel(db, imovel_id, uid)

    # Limite de arquivos por tipo.
    existentes = (imovel.get("documentos") or {}).get(tipo.value) or []
    limite = _LIMITES.get(tipo, 50)
    if len(existentes) >= limite:
        raise HTTPException(
            status_code=422,
            detail=f"Limite de {limite} arquivo(s) atingido para o campo '{tipo.value}'.",
        )

    conteudo = await file.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(conteudo) > _MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo excede o limite de 5 MB (recebido: {len(conteudo) / 1024 / 1024:.1f} MB).",
        )

    detected = detect_content_type(conteudo)
    if detected not in {"image/jpeg", "image/png", "image/webp", "application/pdf"}:
        raise HTTPException(status_code=400, detail="Conteúdo do arquivo inválido ou não suportado.")

    filename = normalize_filename(file.filename, fallback="documento")
    base_name = uuid.uuid4().hex
    output_dir = STORAGE_ROOT / imovel_id / tipo.value
    output_dir.mkdir(parents=True, exist_ok=True)

    deve_converter = detected == "application/pdf" and tipo not in _TIPOS_SEM_CONVERSAO

    if deve_converter:
        try:
            resultado = convert_pdf_to_tiff_pages(conteudo, output_dir, base_name)
        except PdfConversionError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except RuntimeError as exc:
            logger.exception("Falha de conversão PDF→TIFF (imovel=%s tipo=%s)", imovel_id, tipo.value)
            raise HTTPException(status_code=500, detail=str(exc))

        # Preserva o PDF original para auditoria.
        pdf_path = output_dir / f"{base_name}_original.pdf"
        pdf_path.write_bytes(conteudo)

        documento = DocumentoAnexo(
            id=base_name,
            tipo=tipo,
            nome_original=filename,
            paginas=resultado.total_paginas,
            arquivos_tiff=[str(p.relative_to(STORAGE_ROOT)) for p in resultado.tiff_paths],
            arquivos_preview=[str(p.relative_to(STORAGE_ROOT)) for p in resultado.preview_paths],
            arquivo_original_pdf=str(pdf_path.relative_to(STORAGE_ROOT)),
            content_type="application/pdf",
            tamanho_bytes=len(conteudo),
            convertido=True,
        )
    else:
        # Imagem direta ou fotografia — armazena sem transformação.
        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(
            detected, Path(filename).suffix.lower() or ".bin"
        )
        dest_path = output_dir / f"{base_name}{ext}"
        dest_path.write_bytes(conteudo)
        rel = str(dest_path.relative_to(STORAGE_ROOT))
        documento = DocumentoAnexo(
            id=base_name,
            tipo=tipo,
            nome_original=filename,
            paginas=1,
            arquivos_tiff=[],
            arquivos_preview=[rel],
            content_type=detected,
            tamanho_bytes=len(conteudo),
            convertido=False,
        )

    await db.properties.update_one(
        {"id": imovel_id, "user_id": uid},
        {"$push": {f"documentos.{tipo.value}": documento.model_dump(mode="json")}},
    )
    logger.info(
        "Documento anexado: imovel=%s tipo=%s id=%s paginas=%d convertido=%s",
        imovel_id, tipo.value, documento.id, documento.paginas, documento.convertido,
    )
    return documento


@router.get(
    "/{tipo}/{documento_id}/arquivo",
    summary="Serve um arquivo do documento (preview JPEG, TIFF ou PDF original)",
)
async def servir_arquivo(
    imovel_id: str,
    tipo: TipoDocumento,
    documento_id: str,
    kind: str = Query("preview", pattern="^(preview|tiff|original)$"),
    pagina: int = Query(1, ge=1),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    imovel = await _carregar_imovel(db, imovel_id, uid)
    documentos = (imovel.get("documentos") or {}).get(tipo.value) or []
    alvo = next((d for d in documentos if d.get("id") == documento_id), None)
    if not alvo:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    if kind == "original":
        rel = alvo.get("arquivo_original_pdf")
        media, fname = "application/pdf", f"{alvo.get('nome_original', documento_id)}"
    elif kind == "tiff":
        lista = alvo.get("arquivos_tiff") or []
        if not 1 <= pagina <= len(lista):
            raise HTTPException(status_code=404, detail="Página inexistente.")
        rel, media, fname = lista[pagina - 1], "image/tiff", f"{documento_id}_p{pagina:03d}.tiff"
    else:  # preview
        lista = alvo.get("arquivos_preview") or []
        if not 1 <= pagina <= len(lista):
            raise HTTPException(status_code=404, detail="Página inexistente.")
        rel = lista[pagina - 1]
        media = alvo.get("content_type") if not alvo.get("convertido") else "image/jpeg"
        if media == "application/pdf":
            media = "image/jpeg"
        fname = Path(rel).name

    if not rel:
        raise HTTPException(status_code=404, detail="Arquivo não disponível.")
    full = _safe_full_path(rel)
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Arquivo físico ausente.")
    return FileResponse(
        path=str(full),
        media_type=media,
        filename=fname,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.delete(
    "/{tipo}/{documento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um documento e todos os seus arquivos físicos",
)
async def remover_documento(
    imovel_id: str,
    tipo: TipoDocumento,
    documento_id: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    imovel = await _carregar_imovel(db, imovel_id, uid)
    documentos = (imovel.get("documentos") or {}).get(tipo.value) or []
    alvo = next((d for d in documentos if d.get("id") == documento_id), None)
    if not alvo:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    rels = list(alvo.get("arquivos_tiff") or []) + list(alvo.get("arquivos_preview") or [])
    if alvo.get("arquivo_original_pdf"):
        rels.append(alvo["arquivo_original_pdf"])
    for rel in rels:
        try:
            _safe_full_path(rel).unlink(missing_ok=True)
        except HTTPException:
            continue  # ignora paths inválidos remanescentes

    await db.properties.update_one(
        {"id": imovel_id, "user_id": uid},
        {"$pull": {f"documentos.{tipo.value}": {"id": documento_id}}},
    )
    logger.info("Documento removido: imovel=%s tipo=%s id=%s", imovel_id, tipo.value, documento_id)
