# @module routes.dashboard — Estatísticas do dashboard do usuário
from datetime import datetime
from collections import defaultdict
from fastapi import APIRouter, Depends
from db import get_db
from services.auth_service import get_current_user_id

router = APIRouter(tags=["dashboard"])

_MONTHS_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _f(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _as_dt(v):
    if isinstance(v, datetime):
        return v
    if isinstance(v, str) and v:
        try:
            return datetime.fromisoformat(v.replace("Z", ""))
        except ValueError:
            return None
    return None


@router.get("/dashboard/stats")
async def dashboard_stats(uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    # Laudos reais = PTAMs (collection ptam_documents), não a legada `evaluations`.
    ptams = await db.ptam_documents.find({"user_id": uid}).to_list(5000)
    clients_count = await db.clients.count_documents({"user_id": uid})

    # Imóveis: soma properties (legado) + nº de PTAMs com imóvel identificado.
    props_count = await db.properties.count_documents({"user_id": uid})
    if props_count == 0:
        props_count = sum(1 for p in ptams if (p.get("property_address") or p.get("property_label") or p.get("denominacao")))

    # Volume avaliado = soma do valor total dos laudos.
    total_val = sum(_f(p.get("resultado_valor_total") or p.get("total_indemnity")) for p in ptams)

    # Laudos por mês (últimos 6 meses) pela data de criação.
    monthly = defaultdict(int)
    for p in ptams:
        dt = _as_dt(p.get("created_at"))
        if dt:
            monthly[_MONTHS_PT[dt.month - 1]] += 1
    now_month = datetime.utcnow().month
    order = [_MONTHS_PT[(now_month - 6 + i) % 12] for i in range(6)]
    monthly_list = [{"month": m, "count": monthly.get(m, 0)} for m in order]

    return {
        "evaluations": len(ptams),
        "clients": clients_count,
        "properties": props_count,
        "revenue": round(total_val, 2),
        "monthly": monthly_list,
    }
