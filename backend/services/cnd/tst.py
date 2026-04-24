# @module services.cnd.tst — Provider TST: fallback manual robusto (captcha pesado)
import time

LINK = "https://cndt-certidao.tst.jus.br/inicio.faces"


async def consultar(cpf_cnpj: str) -> dict:
    """Retorna fallback manual para TST por bloqueios anti-bot/captcha recorrentes."""
    inicio = time.time()
    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "tst",
        "resultado": "indisponivel",
        "pdf_base64": None,
        "validade": None,
        "observacao": "Consulta automática indisponível no TST no momento. Use consulta manual oficial.",
        "link_manual": LINK,
        "tempo_ms": tempo_ms,
    }
