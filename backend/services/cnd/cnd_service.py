# @module services.cnd.cnd_service — Orquestrador CND: dispara providers em paralelo
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from services.cnd import receita_federal, pgfn, tst, trf1, tjma, cnib, rfb_cadastro
from models.cnd import CNDConsulta, CNDCertidao, CNDLog

logger = logging.getLogger("romatec")

PROVIDERS = [
    receita_federal.consultar,
    pgfn.consultar,
    tst.consultar,
    trf1.consultar,
    tjma.consultar,
    cnib.consultar,
    rfb_cadastro.consultar,
]


async def _run_provider(fn, cpf_cnpj: str) -> dict:
    """Executa um provider com proteção total contra exceções."""
    try:
        return await asyncio.wait_for(fn(cpf_cnpj), timeout=20)
    except asyncio.TimeoutError:
        provider = fn.__module__.split(".")[-1]
        return {"provider": provider, "resultado": "indisponivel", "pdf_base64": None,
                "validade": None, "observacao": "Timeout de 20s excedido", "tempo_ms": 20000}
    except Exception as exc:
        provider = fn.__module__.split(".")[-1]
        logger.warning("Provider %s falhou: %s", provider, exc)
        return {"provider": provider, "resultado": "indisponivel", "pdf_base64": None,
                "validade": None, "observacao": f"Erro inesperado: {exc}", "tempo_ms": 0}


async def consultar_cnd(
    db,
    user_id: str,
    cpf_cnpj: str,
    nome_parte: str,
    tipo_parte: str,
    finalidade: str,
    ptam_id: Optional[str] = None,
    data_nascimento: Optional[str] = None,
    ip: Optional[str] = None,
) -> str:
    """Orquestra consulta CND: log LGPD → cache → providers paralelos → persistência."""
    # 1. Log LGPD
    log = CNDLog(user_id=user_id, cpf_cnpj=cpf_cnpj, finalidade=finalidade, ip=ip)
    await db.cnd_logs.insert_one(log.model_dump())

    # 2. Verifica cache (mesma parte nas últimas 24h)
    cache_limite = datetime.utcnow() - timedelta(hours=24)
    consulta_cache = await db.cnd_consultas.find_one({
        "user_id": user_id,
        "cpf_cnpj": cpf_cnpj,
        "status": "concluido",
        "created_at": {"$gte": cache_limite},
    })
    if consulta_cache:
        logger.info("CND cache hit para %s user=%s", cpf_cnpj, user_id)
        return consulta_cache["id"]

    # 3. Cria documento de consulta (status: processando)
    consulta = CNDConsulta(
        user_id=user_id,
        cpf_cnpj=cpf_cnpj,
        nome_parte=nome_parte,
        tipo_parte=tipo_parte,
        ptam_id=ptam_id,
        status="processando",
    )
    await db.cnd_consultas.insert_one(consulta.model_dump())

    # 4. Dispara todos os providers em paralelo
    tasks = [_run_provider(fn, cpf_cnpj) for fn in PROVIDERS]
    resultados = await asyncio.gather(*tasks, return_exceptions=True)

    # 5. Persiste cada certidão
    for res in resultados:
        if isinstance(res, Exception):
            logger.error("Provider retornou exceção não capturada: %s", res)
            continue
        cert = CNDCertidao(
            consulta_id=consulta.id,
            provider=res.get("provider", "desconhecido"),
            resultado=res.get("resultado", "erro"),
            pdf_base64=res.get("pdf_base64"),
            validade=res.get("validade"),
            observacao=res.get("observacao"),
            tempo_ms=res.get("tempo_ms", 0),
        )
        await db.cnd_certidoes.insert_one(cert.model_dump())

    # 6. Atualiza status da consulta
    await db.cnd_consultas.update_one(
        {"id": consulta.id},
        {"$set": {"status": "concluido"}},
    )

    return consulta.id
