# @module services.cnd.cnib — Provider CNIB: sempre indisponivel (requer credenciamento)
import time

LINK = "https://www.cnib.com.br"


async def consultar(cpf_cnpj: str) -> dict:
    """CNIB requer credenciamento especial. Retorna sempre indisponivel com link."""
    inicio = time.time()
    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "cnib",
        "resultado": "indisponivel",
        "pdf_base64": None,
        "validade": None,
        "observacao": f"CNIB requer acesso credenciado — consultar manualmente em {LINK}",
        "tempo_ms": tempo_ms,
    }
