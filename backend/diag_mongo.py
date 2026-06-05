#!/usr/bin/env python3
# @script diag_mongo — lista bancos/coleções e contagens para achar onde estão os dados
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")
_CONN = ROOT / "conexao_migracao.txt"
if _CONN.exists():
    load_dotenv(_CONN, override=True)

from pymongo import MongoClient  # noqa: E402

url = os.environ.get("MONGO_URL", "")
if (not url) or ("COLE_AQUI" in url) or ("..." in url):
    print("ERRO: MONGO_URL não configurado. Edite conexao_migracao.txt e cole a URL real.")
    sys.exit(1)

is_atlas = "mongodb+srv" in url or "mongodb.net" in url
if is_atlas:
    client = MongoClient(url, tls=True, serverSelectionTimeoutMS=20000)
else:
    client = MongoClient(url, serverSelectionTimeoutMS=20000)

print("== Diagnóstico MongoDB ==")
print("DB_NAME no .env:", os.environ.get("DB_NAME"))
print()
print("%-22s %14s %10s %8s" % ("BANCO", "ptam_documents", "images", "PDFs"))
print("-" * 60)
for dbname in client.list_database_names():
    if dbname in ("admin", "local", "config"):
        continue
    db = client[dbname]
    cols = set(db.list_collection_names())
    ptam = db.ptam_documents.count_documents({}) if "ptam_documents" in cols else 0
    imgs = db.images.count_documents({}) if "images" in cols else 0
    pdfs = db.images.count_documents({"content_type": "application/pdf"}) if "images" in cols else 0
    print("%-22s %14d %10d %8d" % (dbname, ptam, imgs, pdfs))

print()
print("Use o banco que tiver ptam_documents/PDFs > 0. Se não for 'avalieimob',")
print("rode a migração assim (na mesma janela):")
print('   set "DB_NAME=NOME_DO_BANCO_CERTO"')
print("   migrar_pdfs.bat")
