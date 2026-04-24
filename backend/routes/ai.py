# @module routes.ai — Roma_IA com cascata de provedores: Groq -> Gemini -> Claude Haiku -> OpenAI
import os
import asyncio
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
    "Voce e a Roma_IA, especialista senior em avaliacao imobiliaria brasileira, com dominio pleno da ABNT NBR 14653 "
    "(partes 1 a 7), da Resolucao COFECI 957/2006, das normas CREA/CONFEA e do CPC art. 156. "
    "Responda sempre em portugues-BR, em tom tecnico-juridico, objetivo e profissional.\n\n"
    "COMPETENCIA NORMATIVA:\n"
    "- ABNT NBR 14653-1: Procedimentos gerais de avaliacao de bens\n"
    "- ABNT NBR 14653-2: Imoveis urbanos - Metodo Comparativo Direto de Dados de Mercado (item 8.2)\n"
    "- ABNT NBR 14653-3: Imoveis rurais - avaliacoes agronomicas (safra, rebanho, gleba)\n"
    "- Resolucao COFECI 957/2006: habilitacao do Corretor para PTAM mercadologico\n"
    "- Lei 5.194/1966 e Lei 6.530/1978: regulamentacao profissional CREA e CRECI\n"
    "- Resolucao CONFEA 345/90: responsabilidade tecnica ART\n"
    "- Lei 13.786/2018: patrimonio de afetacao e laudos de incorporacao\n"
    "- CPC art. 156: perito judicial cadastrado no tribunal\n\n"
    "Ao responder, cite a norma ou dispositivo legal pertinente. Use formatacao tecnico-juridica formal."
)


# ---------- Provedores individuais ----------

async def _call_groq(messages: list, max_tokens: int) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY nao configurada")
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    resp = await asyncio.wait_for(
        client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=messages,
            max_tokens=max_tokens,
        ),
        timeout=15,
    )
    return resp.choices[0].message.content or ""


async def _call_gemini(messages: list, max_tokens: int) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY nao configurada")
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=next((m["content"] for m in messages if m["role"] == "system"), None),
    )
    history_gemini = []
    for m in messages:
        if m["role"] == "system":
            continue
        role = "user" if m["role"] == "user" else "model"
        history_gemini.append({"role": role, "parts": [m["content"]]})
    # Split last user turn to send as actual prompt
    if history_gemini and history_gemini[-1]["role"] == "user":
        last_prompt = history_gemini[-1]["parts"][0]
        chat_history = history_gemini[:-1]
    else:
        last_prompt = ""
        chat_history = history_gemini
    chat = model.start_chat(history=chat_history)
    resp = await asyncio.wait_for(
        asyncio.to_thread(
            chat.send_message,
            last_prompt,
            generation_config={"max_output_tokens": max_tokens},
        ),
        timeout=20,
    )
    return resp.text or ""


async def _call_claude(messages: list, max_tokens: int) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY nao configurada")
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=api_key)
    system_content = next((m["content"] for m in messages if m["role"] == "system"), None)
    non_system = [m for m in messages if m["role"] != "system"]
    resp = await asyncio.wait_for(
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            system=system_content or "",
            messages=non_system,
        ),
        timeout=25,
    )
    return resp.content[0].text if resp.content else ""


async def _call_openai(messages: list, max_tokens: int) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY nao configurada")
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)
    resp = await asyncio.wait_for(
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=max_tokens,
        ),
        timeout=30,
    )
    return resp.choices[0].message.content or ""


# ---------- Cascata principal ----------

_PROVIDERS = [
    ("groq", _call_groq),
    ("gemini", _call_gemini),
    ("claude", _call_claude),
    ("openai", _call_openai),
]


async def _roma_ia_cascata(messages: list, max_tokens: int = 2000):
    """Tenta provedores em ordem. Retorna (reply, provedor_usado)."""
    last_error = None
    for name, fn in _PROVIDERS:
        try:
            reply = await fn(messages, max_tokens)
            if reply:
                logger.info("Roma_IA respondeu via provedor: %s", name)
                return reply, name
        except ValueError as e:
            logger.debug("Provedor %s ignorado (nao configurado): %s", name, e)
            last_error = e
        except asyncio.TimeoutError:
            logger.warning("Provedor %s timeout, tentando proximo", name)
            last_error = asyncio.TimeoutError(f"{name} timeout")
        except Exception as e:
            logger.warning("Provedor %s falhou (%s: %s), tentando proximo", name, type(e).__name__, str(e)[:120])
            last_error = e
    raise HTTPException(
        status_code=503,
        detail=f"Nenhum provedor de IA disponivel. Ultimo erro: {str(last_error)[:200]}",
    )


# ---------- Endpoints ----------

@router.post("/ai/chat", response_model=AIMessageResponse)
@limiter.limit("20/minute")
async def ai_chat(
    request: Request,
    data: AIMessage,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    # Salva mensagem do usuario
    await db.ai_messages.insert_one({
        "user_id": uid,
        "session_id": data.session_id,
        "role": "user",
        "content": data.message,
        "ts": datetime.utcnow(),
    })

    # Busca historico (ultimas 20 mensagens)
    history = await db.ai_messages.find(
        {"user_id": uid, "session_id": data.session_id}
    ).sort("ts", 1).to_list(20)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})

    reply, provider = await _roma_ia_cascata(messages)

    if not reply:
        raise HTTPException(status_code=500, detail="Resposta vazia da IA")

    # Salva resposta com metadado do provedor
    await db.ai_messages.insert_one({
        "user_id": uid,
        "session_id": data.session_id,
        "role": "assistant",
        "content": reply,
        "provider": provider,
        "ts": datetime.utcnow(),
    })

    return AIMessageResponse(session_id=data.session_id, reply=reply, provider=provider)


@router.get("/ai/history/{session_id}")
async def ai_history(
    session_id: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    items = await db.ai_messages.find(
        {"user_id": uid, "session_id": session_id}
    ).sort("ts", 1).to_list(1000)
    return [
        {
            "role": i["role"],
            "content": i["content"],
            "ts": i["ts"].isoformat(),
            "provider": i.get("provider"),
        }
        for i in items
    ]


@router.get("/ai/status")
async def ai_status(uid: str = Depends(get_active_subscriber)):
    """Retorna quais provedores estao configurados."""
    return {
        "groq": bool(os.environ.get("GROQ_API_KEY")),
        "gemini": bool(os.environ.get("GEMINI_API_KEY")),
        "claude": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
    }
