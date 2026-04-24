# @module services.cnd.datajud — CNJ DataJud: processos TJMA+TRF1+TST+TRT16 em paralelo (gratuito)
import asyncio
import logging
import os
import time

import httpx

logger = logging.getLogger("romatec")

BASE_URL = "https://api-publica.datajud.cnj.jus.br/{tribunal}/_search"

# Chave pública CNJ — sobrescrita via variável DATAJUD_API_KEY no Railway
DEFAULT_KEY = "cDZHYzlZa0JadVREZDJCendFbGFrOXNBN3pXRVRNandCVXp"

TRIBUNAIS = {
    "tjma": "api_publica_tjma",
    "trf1": "api_publica_trf1",
    "tst":  "api_publica_tst",
    "trt16": "api_publica_trt16",
}

TIMEOUT = 15.0
MANUAL_LINKS = {
    "TJMA": "https://jurisconsult.tjma.jus.br/",
    "TRF1": "https://pje.trf1.jus.br/pje/ConsultaPublica/listView.seam",
    "TST": "https://cndt-certidao.tst.jus.br/inicio.faces",
    "TRT16": "https://www.trt16.jus.br/",
}


def _build_query(doc: str) -> dict:
    return {
        "query": {
            "bool": {
                "should": [{"match": {"partes.documento": doc}}],
                "minimum_should_match": 1,
            }
        },
        "size": 20,
        "_source": ["numeroProcesso", "classe", "situacao", "tribunal", "dataAjuizamento"],
    }


async def _consultar_tribunal(
    client: httpx.AsyncClient,
    tribunal_key: str,
    tribunal_path: str,
    doc: str,
    api_key: str,
) -> dict:
    try:
        resp = await client.post(
            BASE_URL.format(tribunal=tribunal_path),
            headers={
                "Authorization": f"ApiKey {api_key}",
                "Content-Type": "application/json",
            },
            json=_build_query(doc),
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return {"tribunal": tribunal_key, "processos": [], "erro": f"HTTP {resp.status_code}"}

        hits = resp.json().get("hits", {}).get("hits", [])
        return {"tribunal": tribunal_key, "processos": [h.get("_source", {}) for h in hits], "erro": None}

    except Exception as exc:
        logger.debug("DataJud %s: %s", tribunal_key, exc)
        return {"tribunal": tribunal_key, "processos": [], "erro": str(exc)}


async def consultar(cpf_cnpj: str) -> dict:
    """Consulta processos em TJMA, TRF1, TST e TRT16 em paralelo via CNJ DataJud."""
    inicio = time.time()
    doc = cpf_cnpj.strip().replace(".", "").replace("-", "").replace("/", "")
    api_key = os.environ.get("DATAJUD_API_KEY", DEFAULT_KEY)

    resultado = "indisponivel"
    obs = "CNJ DataJud indisponível"

    try:
        async with httpx.AsyncClient() as client:
            tasks = [
                _consultar_tribunal(client, k, v, doc, api_key)
                for k, v in TRIBUNAIS.items()
            ]
            resultados = await asyncio.gather(*tasks, return_exceptions=True)

        total_processos = 0
        tribunais_com_processo: list[str] = []

        for r in resultados:
            if isinstance(r, Exception):
                continue
            qtd = len(r.get("processos", []))
            if qtd > 0:
                total_processos += qtd
                tribunais_com_processo.append(r["tribunal"].upper())

        if total_processos == 0:
            resultado = "negativa"
            obs = None
        else:
            resultado = "positiva"
            obs = f"Processos: {', '.join(tribunais_com_processo)} ({total_processos} encontrados)"

    except Exception as exc:
        logger.warning("DataJud falhou: %s", exc)
        resultado = "indisponivel"
        obs = f"CNJ DataJud: {exc}"

    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "datajud",
        "resultado": resultado,
        "pdf_base64": None,
        "validade": None,
        "observacao": obs,
        "link_manual": MANUAL_LINKS["TJMA"],
        "tempo_ms": tempo_ms,
    }
