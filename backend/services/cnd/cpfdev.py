# @module services.cnd.cpfdev — CPF situação cadastral via cpf.dev (requer CPF_DEV_API_KEY)
import os
import time

import httpx

URL = "https://api.cpf.dev/v1/{cpf}"
TIMEOUT = 15.0


async def consultar(cpf_cnpj: str) -> dict:
    """Consulta situação cadastral de CPF via cpf.dev. Somente CPF (11 dígitos)."""
    inicio = time.time()
    doc = cpf_cnpj.strip().replace(".", "").replace("-", "").replace("/", "")

    if len(doc) != 11:
        return {
            "provider": "cpfdev",
            "resultado": "nao_aplicavel",
            "pdf_base64": None,
            "validade": None,
            "observacao": "cpf.dev: somente para CPF físico",
            "tempo_ms": 0,
        }

    api_key = os.environ.get("CPF_DEV_API_KEY", "")
    if not api_key:
        return {
            "provider": "cpfdev",
            "resultado": "indisponivel",
            "pdf_base64": None,
            "validade": None,
            "observacao": "Configure CPF_DEV_API_KEY no Railway para consulta de CPF",
            "tempo_ms": 0,
        }

    resultado = "indisponivel"
    obs = "cpf.dev temporariamente indisponível"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                URL.format(cpf=doc),
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code != 200:
                raise ValueError(f"HTTP {resp.status_code}")

            data = resp.json()
            situacao = (data.get("situacao") or "").lower()

            if "regular" in situacao:
                resultado = "negativa"
                obs = None
            else:
                resultado = "positiva"
                obs = f"CPF com situação: {situacao.upper() or 'não regular'}"

    except Exception as exc:
        resultado = "indisponivel"
        obs = f"cpf.dev: {exc}"

    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "cpfdev",
        "resultado": resultado,
        "pdf_base64": None,
        "validade": None,
        "observacao": obs if resultado != "negativa" else None,
        "tempo_ms": tempo_ms,
    }
