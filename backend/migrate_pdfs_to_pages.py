#!/usr/bin/env python3
# @script migrate_pdfs_to_pages — converte PDFs já existentes em páginas PNG 300 DPI
"""
Migração retroativa: alinha os PDFs antigos ao novo fluxo de upload (v1.1.374+).

Procura PDFs em `db.images` (content_type application/pdf) referenciados nos campos
de documento dos PTAMs (`db.ptam_documents`) e, para cada um:
  • rasteriza cada página em PNG 300 DPI — MESMA função do endpoint /upload/image
    (services.pdf_converter.convert_pdf_to_page_pngs);
  • insere as páginas em `db.images` (1 doc por página, com source_pdf_id);
  • reescreve a referência no PTAM trocando o id do PDF pela lista de ids de página
    (1 card por página, igual ao upload novo);
  • mantém o PDF original (flags is_original_pdf + migrated_to_pages) para auditoria.

Idempotente: PDFs já migrados são reusados (não duplica páginas); PTAMs já reescritos
não voltam a ter o id do PDF, então nada é refeito.

Por padrão roda em DRY-RUN (não grava nada). Use --apply para efetivar.

Uso:
    cd backend
    python migrate_pdfs_to_pages.py                 # dry-run — mostra o que faria
    python migrate_pdfs_to_pages.py --apply         # efetiva
    python migrate_pdfs_to_pages.py --ptam <id>     # só um PTAM (dry-run)
    python migrate_pdfs_to_pages.py --ptam <id> --apply
    python migrate_pdfs_to_pages.py --limit 5 --apply

Requer as variáveis de ambiente MONGO_URL e (opcional) DB_NAME — lidas de backend/.env.
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")
# Override: arquivo conexao_migracao.txt (MONGO_URL/DB_NAME reais de produção).
_CONN = ROOT / "conexao_migracao.txt"
if _CONN.exists():
    load_dotenv(_CONN, override=True)
sys.path.insert(0, str(ROOT))

from pymongo import MongoClient  # noqa: E402

from services.pdf_converter import (  # noqa: E402
    PdfConversionError,
    convert_pdf_to_page_pngs,
)

# Campos do PTAM que guardam ids de documento (podem conter PDFs antigos).
DOC_FIELDS = [
    "fotos_documentos",
    "doc_mapa_sigef",
    "doc_memorial_descritivo",
    "doc_ccir",
    "doc_itr",
    "doc_car",
    "fotos_imovel",
]


def connect():
    """Conecta no MongoDB replicando a lógica de TLS do app (db.py)."""
    url = os.environ.get("MONGO_URL", "")
    if (not url) or ("COLE_AQUI" in url) or ("..." in url):
        print("ERRO: MONGO_URL não configurado. Edite o arquivo conexao_migracao.txt")
        print("      e cole a MONGO_URL real do serviço AvalieImob (Railway).")
        sys.exit(1)
    is_atlas = "mongodb+srv" in url or "mongodb.net" in url
    if is_atlas:
        client = MongoClient(
            url,
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
        )
    else:
        client = MongoClient(url, serverSelectionTimeoutMS=30000)
    return client[os.environ.get("DB_NAME", "railway")]


def extract_id(item) -> str | None:
    """Extrai o id da imagem a partir de um item de campo de documento.
    Aceita id puro, URL '/api/upload/image/<id>' ou dict com id/doc_id/image_id/url."""
    if isinstance(item, str):
        s = item
    elif isinstance(item, dict):
        s = item.get("id") or item.get("doc_id") or item.get("image_id") or item.get("url") or ""
    else:
        return None
    s = str(s).strip()
    if not s:
        return None
    s = s.replace("/api/upload/image/", "").split("?")[0].rstrip("/")
    return s.split("/")[-1] or None


def ensure_pages(images, pdf_doc: dict, apply: bool) -> tuple[list[str], int]:
    """Garante as páginas PNG 300 DPI de um PDF. Retorna (ids_em_ordem, paginas_geradas).
    Idempotente: se o PDF já foi migrado, reusa as páginas existentes (paginas_geradas=0)."""
    pdf_id = pdf_doc["id"]
    existing = list(images.find({"source_pdf_id": pdf_id}).sort("pdf_page", 1))
    if existing:
        return [d["id"] for d in existing], 0  # já migrado — reuso

    raw = base64.b64decode(pdf_doc["data_b64"])
    pngs = convert_pdf_to_page_pngs(raw)  # pode lançar PdfConversionError
    total = len(pngs)
    now = datetime.utcnow()
    uid = pdf_doc.get("user_id")
    base = pdf_doc.get("filename") or pdf_id
    base = base[:-4] if base.lower().endswith(".pdf") else base

    page_ids: list[str] = []
    for idx, png in enumerate(pngs, start=1):
        pid = str(uuid.uuid4())
        page_ids.append(pid)
        if apply:
            images.insert_one({
                "id": pid,
                "user_id": uid,
                "filename": f"{base} (p. {idx}/{total}).png",
                "content_type": "image/png",
                "data_b64": base64.b64encode(png).decode("utf-8"),
                "size_bytes": len(png),
                "created_at": now,
                "convertido_de_pdf": True,
                "source_pdf_id": pdf_id,
                "pdf_page": idx,
                "pdf_pages_total": total,
                "dpi": 300,
                "migrado": True,
            })
    if apply:
        images.update_one(
            {"id": pdf_id},
            {"$set": {"is_original_pdf": True, "migrated_to_pages": True, "pdf_pages_total": total}},
        )
    return page_ids, total


def run(db, apply: bool = False, ptam_id: str | None = None, limit: int = 0) -> dict:
    """Executa a migração. Retorna um resumo com as contagens."""
    images = db.images
    query = {"id": ptam_id} if ptam_id else {}
    cursor = db.ptam_documents.find(query)
    if limit:
        cursor = cursor.limit(limit)

    print("== Migração PDF→páginas — %s ==" % ("APPLY (gravando)" if apply else "DRY-RUN (sem gravar)"))
    resumo = {"ptams": 0, "pdfs": 0, "paginas": 0, "pulados": 0}

    for ptam in cursor:
        pid = ptam.get("id")
        updates: dict[str, list] = {}
        for field in DOC_FIELDS:
            items = ptam.get(field)
            if not isinstance(items, list) or not items:
                continue
            new_items: list = []
            field_changed = False
            for item in items:
                iid = extract_id(item)
                img = images.find_one({"id": iid}) if iid else None
                if not img or (img.get("content_type", "").lower() != "application/pdf"):
                    new_items.append(item)
                    continue
                try:
                    page_ids, made = ensure_pages(images, img, apply)
                except PdfConversionError as exc:
                    print("  ! PTAM %s · %s: PDF %s inválido/protegido (%s). Mantido." % (pid, field, iid, exc))
                    resumo["pulados"] += 1
                    new_items.append(item)
                    continue
                except Exception as exc:  # noqa: BLE001 — não aborta a migração inteira
                    print("  ! PTAM %s · %s: erro no PDF %s (%s). Mantido." % (pid, field, iid, exc))
                    resumo["pulados"] += 1
                    new_items.append(item)
                    continue
                new_items.extend(page_ids)
                field_changed = True
                resumo["pdfs"] += 1
                resumo["paginas"] += len(page_ids)
                tag = "reuso" if made == 0 else "%d pág. novas" % made
                print("  PTAM %s · %s: PDF %s -> %d página(s) [%s] (%s)"
                      % (pid, field, iid, len(page_ids), tag, img.get("filename", "")))
            if field_changed:
                updates[field] = new_items
        if updates:
            resumo["ptams"] += 1
            if apply:
                db.ptam_documents.update_one({"_id": ptam["_id"]}, {"$set": updates})

    print("\n== Resumo ==")
    print("PTAMs afetados:            %d" % resumo["ptams"])
    print("PDFs convertidos/reusados: %d" % resumo["pdfs"])
    print("Páginas geradas:           %d" % resumo["paginas"])
    print("PDFs pulados (erro):       %d" % resumo["pulados"])
    if not apply:
        print("\n(DRY-RUN — nada foi gravado. Rode com --apply para efetivar.)")
    return resumo


def main():
    ap = argparse.ArgumentParser(description="Converte PDFs antigos em páginas PNG 300 DPI.")
    ap.add_argument("--apply", action="store_true", help="efetiva as mudanças (padrão: dry-run)")
    ap.add_argument("--ptam", help="processa só um PTAM (id)")
    ap.add_argument("--limit", type=int, default=0, help="limita o nº de PTAMs processados")
    args = ap.parse_args()

    db = connect()
    run(db, apply=args.apply, ptam_id=args.ptam, limit=args.limit)


if __name__ == "__main__":
    main()
