# @module services.ia_uso — rastreio das chamadas de IA (provedor, modelo, tempo, resultado).
#
# Guarda SÓ metadados: nunca o texto da pergunta nem o da resposta (só o tamanho em
# caracteres). Um registro por chamada da cascata, com cada tentativa de provedor.
# A gravação é best-effort: se o banco falhar, a resposta da IA segue normalmente.
import asyncio
import logging
import os
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timedelta

from fastapi import HTTPException

logger = logging.getLogger("romatec")

COLECAO = "ia_uso"
RETENCAO_DIAS = 365  # índice TTL no startup; metadados apenas (ver docs/privacidade)

_uid_atual: ContextVar = ContextVar("ia_uso_uid", default=None)


def definir_usuario(uid) -> None:
    """Chamado pelas dependências de autenticação: a cascata sabe de quem é a chamada."""
    try:
        _uid_atual.set(uid)
    except Exception:  # noqa: BLE001
        pass


def modelo_de(provedor: str) -> str:
    """Modelo efetivamente usado por cada provedor (mesmas regras dos _call_*)."""
    return {
        "groq": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        "gemini": os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest"),
        "claude": "claude-haiku-4-5-20251001",
        "openai": "gpt-4o-mini",
    }.get(provedor, "")


def classificar_erro(exc: BaseException) -> str:
    if isinstance(exc, ValueError):
        return "nao_configurado"
    if isinstance(exc, asyncio.TimeoutError):
        return "timeout"
    return f"erro:{type(exc).__name__}"


def _chars(messages: list) -> int:
    total = 0
    for m in messages or []:
        c = m.get("content") if isinstance(m, dict) else None
        if isinstance(c, str):
            total += len(c)
    return total


def montar_registro(*, origem, uid, tentativas, provedor, ms_total, messages, reply, max_tokens) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "ts": datetime.utcnow(),
        "user_id": uid,
        "origem": origem or "desconhecida",
        "sucesso": provedor is not None,
        "provedor": provedor,
        "modelo": modelo_de(provedor) if provedor else None,
        "ms_total": ms_total,
        "max_tokens": max_tokens,
        "chars_entrada": _chars(messages),
        "chars_saida": len(reply) if isinstance(reply, str) else 0,
        "tentativas": tentativas,
    }


def _db_atual():
    from db import get_db
    return get_db()


async def registrar(doc: dict) -> None:
    try:
        db = _db_atual()
        if db is None:
            return
        await db[COLECAO].insert_one(dict(doc))
    except Exception as e:  # noqa: BLE001
        logger.debug("ia_uso: não registrou (%s)", type(e).__name__)


async def cascata(providers, messages: list, max_tokens: int, *, origem: str, rotulo: str = "Roma_IA"):
    """Tenta os provedores em ordem. Devolve (resposta, provedor). Registra a chamada.

    Mesmo comportamento das cascatas antigas: provedor sem chave é pulado, timeout/erro
    passa ao próximo, resposta vazia passa ao próximo; nenhum responde → HTTP 503.
    """
    uid = _uid_atual.get()
    tentativas = []
    inicio = time.perf_counter()
    last_error = None
    for name, fn in providers:
        t0 = time.perf_counter()
        try:
            reply = await fn(messages, max_tokens)
            ms = int((time.perf_counter() - t0) * 1000)
            if reply:
                tentativas.append({"provedor": name, "modelo": modelo_de(name), "resultado": "ok", "ms": ms})
                logger.info("%s respondeu via provedor: %s (%d ms)", rotulo, name, ms)
                await registrar(montar_registro(
                    origem=origem, uid=uid, tentativas=tentativas, provedor=name,
                    ms_total=int((time.perf_counter() - inicio) * 1000),
                    messages=messages, reply=reply, max_tokens=max_tokens))
                return reply, name
            tentativas.append({"provedor": name, "modelo": modelo_de(name), "resultado": "vazio", "ms": ms})
        except Exception as e:  # noqa: BLE001
            ms = int((time.perf_counter() - t0) * 1000)
            resultado = classificar_erro(e)
            if resultado != "nao_configurado":
                tentativas.append({"provedor": name, "modelo": modelo_de(name), "resultado": resultado, "ms": ms})
                logger.warning("Provedor %s falhou (%s), tentando próximo", name, resultado)
            last_error = asyncio.TimeoutError(f"{name} timeout") if resultado == "timeout" else e
    await registrar(montar_registro(
        origem=origem, uid=uid, tentativas=tentativas, provedor=None,
        ms_total=int((time.perf_counter() - inicio) * 1000),
        messages=messages, reply=None, max_tokens=max_tokens))
    raise HTTPException(
        status_code=503,
        detail=f"Nenhum provedor de IA disponivel. Ultimo erro: {str(last_error)[:200]}",
    )


# ── resumo para o painel ─────────────────────────────────────────────────────
def _p95(valores):
    if not valores:
        return None
    v = sorted(valores)
    return v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))]


def resumo(docs: list) -> dict:
    total = len(docs)
    ok = sum(1 for d in docs if d.get("sucesso"))
    por_prov = {}
    por_origem = {}
    for d in docs:
        o = d.get("origem") or "desconhecida"
        po = por_origem.setdefault(o, {"origem": o, "chamadas": 0, "falhas": 0})
        po["chamadas"] += 1
        if not d.get("sucesso"):
            po["falhas"] += 1
        for t in d.get("tentativas") or []:
            p = por_prov.setdefault(t["provedor"], {
                "provedor": t["provedor"], "modelo": t.get("modelo"), "tentativas": 0,
                "respondeu": 0, "falhas": {}, "_ms": []})
            p["tentativas"] += 1
            if t.get("resultado") == "ok":
                p["respondeu"] += 1
                p["_ms"].append(t.get("ms") or 0)
            else:
                p["falhas"][t["resultado"]] = p["falhas"].get(t["resultado"], 0) + 1
    provedores = []
    for p in por_prov.values():
        ms = p.pop("_ms")
        p["ms_medio"] = int(sum(ms) / len(ms)) if ms else None
        p["ms_p95"] = _p95(ms)
        provedores.append(p)
    tot_ms = [d.get("ms_total") or 0 for d in docs if d.get("sucesso")]
    return {
        "chamadas": total,
        "respondidas": ok,
        "sem_resposta": total - ok,
        "taxa_sucesso": round(100 * ok / total, 1) if total else None,
        "ms_medio": int(sum(tot_ms) / len(tot_ms)) if tot_ms else None,
        "ms_p95": _p95(tot_ms),
        "com_reserva": sum(1 for d in docs if d.get("sucesso") and len(d.get("tentativas") or []) > 1),
        "provedores": sorted(provedores, key=lambda x: -x["tentativas"]),
        "origens": sorted(por_origem.values(), key=lambda x: -x["chamadas"]),
    }


def janela(dias: int) -> datetime:
    return datetime.utcnow() - timedelta(days=max(1, min(int(dias or 7), 365)))
