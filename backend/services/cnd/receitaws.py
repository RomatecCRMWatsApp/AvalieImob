# @module services.cnd.receitaws — CNPJ via ReceitaWS (gratuito, sem autenticação)
import asyncio
import time
import httpx

URL = "https://receitaws.com.br/v1/cnpj/{cnpj}"
TIMEOUT = 15.0


async def consultar(cpf_cnpj: str) -> dict:
    """Consulta situação cadastral de CNPJ via ReceitaWS. Somente CNPJ (14 dígitos)."""
    inicio = time.time()
    doc = cpf_cnpj.strip().replace(".", "").replace("-", "").replace("/", "")

    if len(doc) != 14:
        return {
            "provider": "receitaws",
            "resultado": "nao_aplicavel",
            "pdf_base64": None,
            "validade": None,
            "observacao": "ReceitaWS: somente para CNPJ",
            "tempo_ms": 0,
        }

    resultado = "indisponivel"
    obs = "ReceitaWS temporariamente indisponível"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                URL.format(cnpj=doc),
                headers={"Accept": "application/json"},
            )
            # Rate-limit: aguarda 2s e retenta uma vez
            if resp.status_code == 429:
                await asyncio.sleep(2)
                resp = await client.get(URL.format(cnpj=doc), headers={"Accept": "application/json"})

            if resp.status_code != 200:
                raise ValueError(f"HTTP {resp.status_code}")

            data = resp.json()
            situacao = (data.get("situacao") or "").upper()

            if situacao == "ATIVA":
                resultado = "negativa"
                obs = None
            elif situacao in ("BAIXADA", "INAPTA", "SUSPENSA", "NULA"):
                resultado = "positiva"
                obs = f"CNPJ com situação: {situacao}"
            else:
                resultado = "indisponivel"
                obs = f"Situação não reconhecida: {situacao or 'vazia'}"

    except Exception as exc:
        resultado = "indisponivel"
        obs = f"ReceitaWS: {exc}"

    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "receitaws",
        "resultado": resultado,
        "pdf_base64": None,
        "validade": None,
        "observacao": obs if resultado != "negativa" else None,
        "tempo_ms": tempo_ms,
    }
