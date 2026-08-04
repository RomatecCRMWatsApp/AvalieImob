"""Migra as imagens JÁ existentes de base64-no-Mongo para o Cloudflare R2.

Para cada doc de `db.images` que tem `data_b64`: sobe os bytes no R2, grava
`r2_key` e remove o `data_b64` do Mongo — liberando o espaço já ocupado.
Idempotente: pula quem já tem `r2_key`. Roda depois que o app já usa o R2.

Ambiente (Railway Variables):
  MONGO_URL   = banco de produção (o Mongo do Railway)
  DB_NAME     = avalieimob
  R2_ENDPOINT, R2_BUCKET, R2_ACCESS_KEY, R2_SECRET_KEY

Uso (a partir de backend/):
  py scripts/migrar_imagens_para_r2.py            # DRY-RUN (só conta)
  py scripts/migrar_imagens_para_r2.py --apply    # migra de verdade
"""
import base64
import os
import sys

from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/
from services import r2_storage  # noqa: E402

_EXT = {
    "image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
    "image/webp": "webp", "application/pdf": "pdf",
}


def main() -> None:
    url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "avalieimob")
    if not url:
        print("ERRO: defina MONGO_URL (o Mongo do Railway).")
        sys.exit(1)
    for v in ("R2_ENDPOINT", "R2_BUCKET", "R2_ACCESS_KEY", "R2_SECRET_KEY"):
        if not os.environ.get(v):
            print(f"ERRO: variável do R2 ausente: {v}")
            sys.exit(1)
    apply = "--apply" in sys.argv

    db = MongoClient(url, serverSelectionTimeoutMS=30000)[db_name]
    q = {"data_b64": {"$exists": True, "$ne": None}, "r2_key": {"$exists": False}}
    total = db.images.count_documents(q)
    print(f"Imagens com data_b64 (ainda não no R2): {total}")
    print(f"Modo: {'APPLY (migrando)' if apply else 'DRY-RUN (só conta)'}\n")

    migrados = erros = 0
    liberado = 0
    for doc in db.images.find(q):
        iid = doc.get("id")
        uid = doc.get("user_id", "_")
        b64 = doc.get("data_b64")
        if not iid or not b64:
            continue
        try:
            raw = base64.b64decode(b64)
        except Exception:
            erros += 1
            print(f"  {iid}: data_b64 corrompido — pulado")
            continue
        ct = (doc.get("content_type") or "image/jpeg").lower()
        key = f"images/{uid}/{iid}.{_EXT.get(ct, 'bin')}"
        if not apply:
            continue
        try:
            r2_storage.upload_bytes(raw, key, ct)
            db.images.update_one(
                {"id": iid}, {"$set": {"r2_key": key}, "$unset": {"data_b64": ""}}
            )
            migrados += 1
            liberado += len(b64)
            if migrados % 25 == 0:
                print(f"  ... {migrados} migrados")
        except Exception as exc:
            erros += 1
            print(f"  {iid}: falha ao subir no R2: {exc}")

    print(f"\nMigrados: {migrados}   Erros: {erros}   "
          f"Espaço liberado no Mongo: ~{liberado / 1024 / 1024:.1f} MB")
    if not apply:
        print("(dry-run — rode com --apply para migrar de verdade)")


if __name__ == "__main__":
    main()
