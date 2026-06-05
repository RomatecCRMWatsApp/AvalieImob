#!/usr/bin/env python3
# @script diag_pdfs — mostra os PDFs do db.images e onde (se) estão referenciados nos PTAMs
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

# Banco: usa DB_NAME, mas ignora placeholders de exemplo setados por engano.
dbname = os.environ.get("DB_NAME") or "avalieimob"
if dbname in ("NOME_DO_BANCO_CERTO", "", None):
    dbname = "avalieimob"

is_atlas = "mongodb+srv" in url or "mongodb.net" in url
client = MongoClient(url, tls=True, serverSelectionTimeoutMS=20000) if is_atlas \
    else MongoClient(url, serverSelectionTimeoutMS=20000)
db = client[dbname]
print("Banco:", db.name)

FIELDS = [
    "fotos_documentos", "doc_mapa_sigef", "doc_memorial_descritivo",
    "doc_ccir", "doc_itr", "doc_car", "fotos_imovel",
]

print("\n== PDFs em db.images (content_type = application/pdf) ==")
pdf_ids = []
for d in db.images.find({"content_type": "application/pdf"}):
    pid = d.get("id")
    pdf_ids.append(pid)
    print("  id=%s | file=%s | is_original_pdf=%s | migrated=%s | user=%s"
          % (pid, d.get("filename"), d.get("is_original_pdf"), d.get("migrated_to_pages"), d.get("user_id")))

print("\n== ptam_documents — campos de documento (valor cru) ==")
ptams = list(db.ptam_documents.find({}))
for p in ptams:
    print("\n  PTAM id=%s  user_id=%s" % (p.get("id"), p.get("user_id")))
    achou_campo = False
    for f in FIELDS:
        v = p.get(f)
        if v:
            achou_campo = True
            print("    %s = %r" % (f, v))
    # procura ids de PDF em QUALQUER campo (mesmo fora da lista padrão)
    for k, v in p.items():
        s = str(v)
        for pid in pdf_ids:
            if pid and pid in s and k not in FIELDS:
                print("    [!] PDF %s aparece no campo NÃO-padrão '%s'" % (pid, k))
    if not achou_campo:
        print("    (nenhum dos campos de documento padrão preenchido)")

print("\n== Cada PDF está referenciado onde? ==")
for pid in pdf_ids:
    hits = []
    for p in ptams:
        for k, v in p.items():
            if pid and pid in str(v):
                hits.append("ptam %s.%s" % (p.get("id"), k))
    print("  PDF %s -> %s" % (pid, hits or "NÃO referenciado em nenhum ptam_documents"))
