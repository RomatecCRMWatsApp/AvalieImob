# @module migrate_ptam_status — Backfill do status_calculado nos PTAMs existentes.
"""
Recalcula e persiste `status_calculado` em todos os PTAMs (coleção ptam_documents).
Idempotente. Usa as MESMAS env vars do app: MONGO_URL e DB_NAME.

Rodar de dentro de backend/ (pra achar utils.ptam_status):

    cd backend
    # PowerShell:  $env:MONGO_URL="..."; $env:DB_NAME="railway"
    # CMD:         set MONGO_URL=...  &&  set DB_NAME=railway
    python migrate_ptam_status.py            # aplica
    python migrate_ptam_status.py --dry-run  # mostra mudanças, não grava
    python migrate_ptam_status.py --inspect  # diagnóstico de seções, não grava

No Railway (recomendado, já tem env + Mongo): rode no shell do serviço backend.
"""
import argparse
import asyncio
import os
import sys
from collections import Counter
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

from utils.ptam_status import calcular_status_ptam, diagnostico_status

# Carrega a connection string do mesmo jeito que diag_mongo.py:
#   .env (backend e raiz) e, com prioridade, conexao_migracao.txt
try:
    from dotenv import load_dotenv
    ROOT = Path(__file__).resolve().parent
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT.parent / ".env")
    _CONN = ROOT / "conexao_migracao.txt"
    if _CONN.exists():
        load_dotenv(_CONN, override=True)
except ImportError:
    pass

COLLECTION = "ptam_documents"


def _connect():
    mongo_url = os.environ.get("MONGO_URL", "")
    if (not mongo_url) or ("COLE_AQUI" in mongo_url) or ("..." in mongo_url) or (mongo_url == "sua_connection_string"):
        print("ERRO: MONGO_URL não configurado. Edite backend/conexao_migracao.txt "
              "e cole a URL real (a mesma do Railway).", file=sys.stderr)
        sys.exit(1)
    is_atlas = "mongodb+srv" in mongo_url or "mongodb.net" in mongo_url
    kwargs = dict(serverSelectionTimeoutMS=30000) if not is_atlas else dict(
        tls=True, tlsAllowInvalidCertificates=False,
        serverSelectionTimeoutMS=30000, connectTimeoutMS=30000, socketTimeoutMS=30000,
    )
    client = AsyncIOMotorClient(mongo_url, **kwargs)
    db = client[os.environ.get("DB_NAME", "railway")]
    print(f"[migração] banco: {os.environ.get('DB_NAME', 'railway')}")
    return client, db


async def migrar(dry_run=False, inspect=False):
    client, db = _connect()
    try:
        col = db[COLLECTION]
        total = await col.count_documents({})
        if total == 0:
            print(f"[migração] coleção '{COLLECTION}' vazia. Nada a fazer.")
            return

        modo = "INSPECT" if inspect else "DRY-RUN" if dry_run else "APLICANDO"
        print(f"[migração] {total} PTAMs em {COLLECTION} ({modo})")

        contagem = Counter()
        alterados = 0

        async for ptam in col.find({}):
            numero = ptam.get("numero_ptam") or ptam.get("number") or ptam.get("id")

            if inspect:
                d = diagnostico_status(ptam)
                contagem[d["status"]] += 1
                print(f"  {numero}: {d['status']} (valor={d['valor_final']}, "
                      f"assinado={d['assinado']}, faltando={d['secoes_faltando']})")
                continue

            novo = calcular_status_ptam(ptam)
            contagem[novo] += 1
            if ptam.get("status_calculado") != novo:
                alterados += 1
                print(f"  {numero}: {ptam.get('status_calculado')!r} -> {novo!r}")
                if not dry_run:
                    await col.update_one({"id": ptam["id"]}, {"$set": {"status_calculado": novo}})

        print("\n[migração] distribuição:")
        for s, q in sorted(contagem.items()):
            print(f"  {s:10s}: {q}")

        if inspect:
            print("\n[migração] INSPECT — nada gravado.")
        elif dry_run:
            print(f"\n[migração] DRY-RUN — {alterados} mudariam (nada gravado).")
        else:
            print(f"\n[migração] OK — {alterados} PTAMs atualizados.")
    finally:
        client.close()


def main():
    ap = argparse.ArgumentParser(description="Backfill status_calculado dos PTAMs.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--inspect", action="store_true")
    args = ap.parse_args()
    try:
        asyncio.run(migrar(dry_run=args.dry_run, inspect=args.inspect))
    except Exception as exc:  # noqa: BLE001
        print(f"[migração] ERRO: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
