"""Migra TODAS as coleções de um MongoDB de ORIGEM (Atlas, cheio) para um de
DESTINO (Railway, com espaço). NUNCA escreve na origem — só lê. Idempotente
(pode rodar de novo sem duplicar; usa upsert por _id).

As connection strings vêm do AMBIENTE (não ficam no código):
  MONGO_ORIGEM   = connection string do Atlas   (a MONGO_URL atual do Railway)
  MONGO_DESTINO  = connection string do Mongo do Railway (a MONGO_PUBLIC_URL)
  DB_NAME        = nome do banco (padrão: railway)

Uso:
  py scripts/migrar_atlas_para_railway.py            # DRY-RUN (só conta, não copia)
  py scripts/migrar_atlas_para_railway.py --apply    # copia de verdade
"""
import os
import sys

import bson
from pymongo import MongoClient, ReplaceOne

LOTE_MAX_DOCS = 100
LOTE_MAX_BYTES = 8 * 1024 * 1024  # 8 MB por lote — evita estourar a mensagem do driver


def _tam(doc) -> int:
    # Tamanho REAL do doc (BSON), para o gate de bytes valer para qualquer coleção
    # (images tem data_b64 grande; ptam_versions/contrato_versions têm docs grandes).
    try:
        return len(bson.BSON.encode(doc))
    except Exception:
        b = doc.get("data_b64")
        return len(b) if isinstance(b, str) else 4096


def main() -> None:
    origem = os.environ.get("MONGO_ORIGEM")
    destino = os.environ.get("MONGO_DESTINO")
    db_name = os.environ.get("DB_NAME", "railway")
    if not origem or not destino:
        print("ERRO: defina MONGO_ORIGEM e MONGO_DESTINO no ambiente.")
        sys.exit(1)
    apply = "--apply" in sys.argv

    cli_o = MongoClient(origem, serverSelectionTimeoutMS=30000)
    cli_d = MongoClient(destino, serverSelectionTimeoutMS=30000)
    dbo, dbd = cli_o[db_name], cli_d[db_name]

    # Ping de conexão nos dois lados antes de começar.
    cli_o.admin.command("ping")
    cli_d.admin.command("ping")

    colls = [c for c in dbo.list_collection_names() if not c.startswith("system.")]
    print(f"Banco '{db_name}': {len(colls)} coleções na origem (Atlas).")
    print(f"Modo: {'APPLY (copiando)' if apply else 'DRY-RUN (só contando)'}\n")

    total_o = total_d = 0
    for c in sorted(colls):
        n_o = dbo[c].estimated_document_count()
        total_o += n_o
        if not apply:
            print(f"  {c:34s} origem={n_o}")
            continue

        if "--limpar" in sys.argv:
            # Zera a coleção no DESTINO antes de copiar → destino fica idêntico à
            # origem (remove os fantasmas da cópia velha do Railway). NUNCA toca a origem.
            dbd[c].drop()

        copiados = 0
        ops, bytes_lote = [], 0
        for doc in dbo[c].find({}):
            ops.append(ReplaceOne({"_id": doc["_id"]}, doc, upsert=True))
            bytes_lote += _tam(doc)
            if len(ops) >= LOTE_MAX_DOCS or bytes_lote >= LOTE_MAX_BYTES:
                dbd[c].bulk_write(ops, ordered=False)
                copiados += len(ops)
                ops, bytes_lote = [], 0
        if ops:
            dbd[c].bulk_write(ops, ordered=False)
            copiados += len(ops)

        n_d = dbd[c].count_documents({})
        total_d += n_d
        marca = "OK" if n_d >= n_o else "!! CONFERIR"
        print(f"  {c:34s} origem={n_o} copiados={copiados} destino={n_d}  {marca}")

    print(f"\nTotal origem={total_o}" + (f"   destino={total_d}" if apply else ""))
    if apply:
        print("Migração concluída. Confira: cada coleção deve ter destino >= origem.")
    else:
        print("Nada foi copiado (dry-run). Rode com --apply para copiar de verdade.")


if __name__ == "__main__":
    main()
