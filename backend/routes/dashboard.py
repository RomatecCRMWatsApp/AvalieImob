# @module routes.dashboard — Estatísticas do dashboard do usuário
from datetime import datetime
from collections import defaultdict
from fastapi import APIRouter, Depends
from db import get_db
from services.auth_service import get_current_user_id

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats")
async def dashboard_stats(uid: str = Depends(get_current_user_id), db=Depends(get_db)):
    clients_count = await db.clients.count_documents({"user_id": uid})
    props_count = await db.properties.count_documents({"user_id": uid})
    evals = await db.evaluations.find({"user_id": uid}).to_list(1000)
    total_val = sum((e.get("value") or 0) for e in evals if e.get("status") == "Emitido")
    monthly = defaultdict(int)
    months_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    for e in evals:
        try:
            d = datetime.fromisoformat(e.get("date", ""))
            monthly[months_pt[d.month - 1]] += 1
        except Exception:
            pass
    now_month = datetime.utcnow().month
    order = [months_pt[(now_month - 6 + i) % 12] for i in range(6)]
    monthly_list = [{"month": m, "count": monthly.get(m, 0)} for m in order]
    return {
        "evaluations": len(evals),
        "clients": clients_count,
        "properties": props_count,
        "revenue": round(total_val * 0.01, 2),
        "monthly": monthly_list,
    }
