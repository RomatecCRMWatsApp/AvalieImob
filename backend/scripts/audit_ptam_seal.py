"""scripts/audit_ptam_seal.py — AUDITORIA (somente leitura) do selo "A" nos PTAMs.

Neste sistema o PDF do PTAM é gerado SOB DEMANDA a partir dos dados (não há PDF
congelado para PTAM sem assinatura). Logo:
  - PTAM "concluido" SEM ICP/D4Sign  -> já sai com o selo ao regerar (nada a migrar).
  - PTAM "assinado" (ICP/D4Sign)      -> PDF congelado, NÃO recebe overlay (intocável).

Este script NÃO grava nada. Só conta/lista e, opcionalmente, gera amostras de PDF
(regeradas, já com o selo) numa pasta local para conferência visual.

Uso (rodar de dentro de backend/):
    python -m scripts.audit_ptam_seal
    python -m scripts.audit_ptam_seal --samples 3 --out ./_ptam_seal_samples
"""
import os
import sys
import argparse
from collections import Counter

from pymongo import MongoClient

from utils.ptam_status import calcular_status_ptam

COLLECTION = "ptam_documents"


def _conn():
    uri = os.environ.get("MONGO_URL") or os.environ.get("MONGODB_URI")
    if not uri:
        print("ERRO: defina MONGO_URL (ou MONGODB_URI) no ambiente.")
        sys.exit(2)
    db_name = os.environ.get("DB_NAME", "railway")
    return MongoClient(uri)[db_name]


def _assinado(d):
    return d.get("icp_status") == "assinado" or d.get("d4sign_status") == "assinado"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=0,
                    help="gera N PDFs de amostra (concluido sem ICP) p/ conferir o selo")
    ap.add_argument("--out", default="./_ptam_seal_samples")
    args = ap.parse_args()

    db = _conn()
    col = db[COLLECTION]

    total = 0
    por_status = Counter()
    icp = d4 = 0
    concluido_sem_assin = []  # (numero, _id) — já saem com selo ao regerar

    for d in col.find({}, {
        "numero_ptam": 1, "icp_status": 1, "d4sign_status": 1,
        # campos que o calcular_status_ptam usa
        "valor_final": 1, "valor_total": 1, "conclusion_value": 1,
        "etapas_concluidas": 1, "conclusion_text": 1,
    }):
        total += 1
        st = calcular_status_ptam(d)
        por_status[st] += 1
        if _assinado(d):
            if d.get("icp_status") == "assinado":
                icp += 1
            if d.get("d4sign_status") == "assinado":
                d4 += 1
        elif st == "concluido":
            concluido_sem_assin.append((d.get("numero_ptam") or str(d.get("_id")), d.get("_id")))

    print("\n===== AUDITORIA SELO 'A' — PTAM (somente leitura) =====")
    print(f"  Total de PTAMs            : {total}")
    for st in ("assinado", "concluido", "rascunho"):
        print(f"  status '{st}'".ljust(28) + f": {por_status.get(st, 0)}")
    print(f"  -> assinados ICP          : {icp}")
    print(f"  -> assinados D4Sign       : {d4}")
    print(f"\n  Concluídos SEM assinatura : {len(concluido_sem_assin)}")
    print("    (estes já saem com o selo 'A' automaticamente no próximo download —")
    print("     o PDF é regenerado a partir dos dados, não há migração a fazer.)")
    print("  Assinados (ICP/D4Sign)    : intocáveis (PDF congelado; overlay quebraria a assinatura).")

    if args.samples and concluido_sem_assin:
        _gerar_amostras(db, concluido_sem_assin[:args.samples], args.out)

    MongoClient  # noqa — só leitura; nenhum update/insert foi chamado


def _gerar_amostras(db, itens, out_dir):
    """Regenera alguns PDFs (concluido sem ICP) p/ conferir o selo a olho. Read-only."""
    from services.ptam_pdf_v2 import generate_ptam_pdf_v2
    os.makedirs(out_dir, exist_ok=True)
    print(f"\n  Gerando {len(itens)} amostra(s) em {out_dir} ...")
    for numero, _id in itens:
        try:
            doc = db[COLLECTION].find_one({"_id": _id})
            perfil = db["perfil_avaliador"].find_one({"user_id": doc.get("user_id")}) or {}
            perfil.pop("_id", None)
            # amostra simples: sem resolver bytes de fotos/anexos (placeholders),
            # o que importa aqui é o SELO na capa/conclusão.
            doc["fotos_imovel"] = []
            doc["market_samples"] = []
            pdf = generate_ptam_pdf_v2(doc, perfil)
            nome = f"PTAM_{str(numero).replace('/', '-')}_SELO.pdf"
            with open(os.path.join(out_dir, nome), "wb") as f:
                f.write(pdf)
            print(f"    ✓ {nome} ({len(pdf)} bytes)")
        except Exception as e:
            print(f"    ✗ {numero}: {e!r}")


if __name__ == "__main__":
    main()
