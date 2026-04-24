# @module services.cnd.trf1 — Provider TRF1: fallback manual robusto
import time

URL_PRINCIPAL = "https://pje.trf1.jus.br/pje/ConsultaPublica/listView.seam"


async def consultar(cpf_cnpj: str) -> dict:
    """Retorna fallback manual para TRF1 por alta incidência de bloqueio/captcha."""
    inicio = time.time()
    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "trf1",
        "resultado": "indisponivel",
        "pdf_base64": None,
        "validade": None,
        "observacao": "Consulta automática indisponível no TRF1 no momento. Use consulta manual oficial.",
        "link_manual": URL_PRINCIPAL,
        "tempo_ms": tempo_ms,
    }
