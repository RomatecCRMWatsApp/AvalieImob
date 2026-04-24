# @module services.cnd.tjma — Provider TJMA: fallback manual robusto
import time

LINK = "https://jurisconsult.tjma.jus.br/"


async def consultar(cpf_cnpj: str) -> dict:
    """Retorna fallback manual para TJMA por bloqueio/captcha em consulta automatizada."""
    inicio = time.time()
    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "tjma",
        "resultado": "indisponivel",
        "pdf_base64": None,
        "validade": None,
        "observacao": "Consulta automática indisponível no TJMA no momento. Use consulta manual oficial.",
        "link_manual": LINK,
        "tempo_ms": tempo_ms,
    }
