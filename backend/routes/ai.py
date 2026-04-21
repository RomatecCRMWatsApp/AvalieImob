# @module routes.ai — Chat IA (OpenAI) e histórico de sessão
import os
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db
from dependencies import get_active_subscriber
from models import AIMessage, AIMessageResponse

router = APIRouter(tags=["ai"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("romatec")

SYSTEM_PROMPT = (
    "Você é um especialista sênior em avaliação imobiliária brasileira, com domínio pleno da ABNT NBR 14653 "
    "(partes 1 a 7), da Resolução COFECI 957/2006, das normas CREA/CONFEA e do CPC art. 156. "
    "Responda sempre em português-BR, em tom técnico-jurídico, objetivo e profissional.\n\n"
    "COMPETÊNCIA NORMATIVA:\n"
    "• ABNT NBR 14653-1: Procedimentos gerais de avaliação de bens\n"
    "• ABNT NBR 14653-2: Imóveis urbanos — Método Comparativo Direto de Dados de Mercado (item 8.2)\n"
    "• ABNT NBR 14653-3: Imóveis rurais — avaliações agronômicas (safra, rebanho, gleba)\n"
    "• Resolução COFECI 957/2006: habilitação do Corretor para PTAM mercadológico\n"
    "• Lei 5.194/1966 e Lei 6.530/1978: regulamentação profissional CREA e CRECI\n"
    "• Resolução CONFEA 345/90: responsabilidade técnica ART\n"
    "• Lei 13.786/2018: patrimônio de afetação e laudos de incorporação\n"
    "• CPC art. 156: perito judicial cadastrado no tribunal\n\n"
    "Ao responder, cite a norma ou dispositivo legal pertinente. Use formatação técnico-jurídica formal."
)


@router.post("/ai/chat", response_model=AIMessageResponse)
@limiter.limit("10/minute")
async def ai_chat(request: Request, data: AIMessage, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    from openai import AsyncOpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM não configurado")
    await db.ai_messages.insert_one({"user_id": uid, "session_id": data.session_id, "role": "user", "content": data.message, "ts": datetime.utcnow()})
    history = await db.ai_messages.find({"user_id": uid, "session_id": data.session_id}).sort("ts", 1).to_list(50)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    try:
        client_ai = AsyncOpenAI(api_key=api_key)
        resp = await client_ai.chat.completions.create(model="gpt-4o-mini", messages=messages, max_tokens=2000)
        reply = resp.choices[0].message.content or ""
    except Exception as e:
        logger.exception("AI error")
        raise HTTPException(status_code=500, detail=f"Erro na IA: {str(e)[:200]}")
    if not reply:
        raise HTTPException(status_code=500, detail="Resposta vazia da IA")
    await db.ai_messages.insert_one({"user_id": uid, "session_id": data.session_id, "role": "assistant", "content": reply, "ts": datetime.utcnow()})
    return AIMessageResponse(session_id=data.session_id, reply=reply)


@router.get("/ai/history/{session_id}")
async def ai_history(session_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    items = await db.ai_messages.find({"user_id": uid, "session_id": session_id}).sort("ts", 1).to_list(1000)
    return [{"role": i["role"], "content": i["content"], "ts": i["ts"].isoformat()} for i in items]
