# @module routes.admin_ia — painel "Uso da IA": provedor, modelo, tempo e falhas por chamada.
# Só metadados (o texto das conversas não é gravado em ia_uso). Restrito a administradores.
import os

from fastapi import APIRouter, Depends, Query

from db import get_db
from dependencies import get_admin_user
from services import ia_uso

router = APIRouter(prefix="/admin/ia", tags=["admin-ia"])

_PROJ = {"_id": 0, "id": 1, "ts": 1, "origem": 1, "sucesso": 1, "provedor": 1, "modelo": 1,
         "ms_total": 1, "tentativas": 1, "chars_entrada": 1, "chars_saida": 1}


@router.get("/uso")
async def uso_ia(dias: int = Query(7, ge=1, le=365), _admin: str = Depends(get_admin_user),
                 db=Depends(get_db)):
    desde = ia_uso.janela(dias)
    docs = await db[ia_uso.COLECAO].find({"ts": {"$gte": desde}}, _PROJ).to_list(20000)
    docs.sort(key=lambda d: d.get("ts"), reverse=True)
    recentes = [{**d, "ts": d["ts"].isoformat() if hasattr(d.get("ts"), "isoformat") else d.get("ts")}
                for d in docs[:60]]
    return {
        "dias": dias,
        "resumo": ia_uso.resumo(docs),
        "configurados": {
            "groq": bool(os.environ.get("GROQ_API_KEY")),
            "gemini": bool(os.environ.get("GEMINI_API_KEY")),
            "claude": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "openai": bool(os.environ.get("OPENAI_API_KEY")),
        },
        "modelos": {p: ia_uso.modelo_de(p) for p in ("groq", "gemini", "claude", "openai")},
        "recentes": recentes,
        "retencao_dias": ia_uso.RETENCAO_DIAS,
    }
