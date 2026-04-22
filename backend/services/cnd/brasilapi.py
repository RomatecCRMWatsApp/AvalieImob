# @module services.cnd.brasilapi — CNPJ fallback via BrasilAPI (gratuito, sem chave)
import time
import httpx

URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
TIMEOUT = 15.0


async def consultar(cpf_cnpj: str) -> dict:
    """Consulta CNPJ via BrasilAPI — fallback gratuito sem rate-limit documentado."""
    inicio = time.time()
    doc = cpf_cnpj.strip().replace(".", "").replace("-", "").replace("/", "")

    if len(doc) != 14:
        return {
            "provider": "brasilapi",
            "resultado": "nao_aplicavel",
            "pdf_base64": None,
            "validade": None,
            "observacao": "BrasilAPI: somente para CNPJ",
            "tempo_ms": 0,
        }

    resultado = "indisponivel"
    obs = "BrasilAPI temporariamente indisponível"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(URL.format(cnpj=doc))

            if resp.status_code == 404:
                resultado = "positiva"
                obs = "CNPJ não encontrado na base da Receita Federal"
            elif resp.status_code != 200:
                raise ValueError(f"HTTP {resp.status_code}")
            else:
                data = resp.json()
                situacao = (data.get("descricao_situacao_cadastral") or "").lower()

                if "ativa" in situacao:
                    resultado = "negativa"
                    obs = None
                elif any(s in situacao for s in ("baixada", "inapta", "suspensa", "nula")):
                    resultado = "positiva"
                    obs = f"CNPJ: {situacao.upper()}"
                else:
                    resultado = "indisponivel"
                    obs = f"Situação: {situacao or 'não informada'}"

    except Exception as exc:
        resultado = "indisponivel"
        obs = f"BrasilAPI: {exc}"

    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "brasilapi",
        "resultado": resultado,
        "pdf_base64": None,
        "validade": None,
        "observacao": obs if resultado != "negativa" else None,
        "tempo_ms": tempo_ms,
    }
