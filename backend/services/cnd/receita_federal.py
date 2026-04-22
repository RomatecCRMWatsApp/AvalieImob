# @module services.cnd.receita_federal — Provider Receita Federal: situação cadastral CPF/CNPJ
import time
import httpx

LINK = "https://solucoes.receita.fazenda.gov.br/Servicos/certidaointer/"
TIMEOUT = 15.0


async def consultar(cpf_cnpj: str) -> dict:
    """Tenta obter certidão da Receita Federal via HTTP; retorna indisponivel se bloqueado."""
    inicio = time.time()
    doc = cpf_cnpj.strip().replace(".", "").replace("-", "").replace("/", "")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(
                LINK,
                params={"tipo": "2" if len(doc) == 14 else "1"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            texto = resp.text.lower()
            if "captcha" in texto or "recaptcha" in texto or resp.status_code == 403:
                raise ValueError("captcha_detectado")
            if "negativa" in texto or "nada consta" in texto:
                resultado = "negativa"
                obs = None
            elif "positiva" in texto or "dívida" in texto or "divida" in texto:
                resultado = "positiva"
                obs = "Débito identificado na Receita Federal"
            else:
                raise ValueError("resposta_inesperada")
    except Exception as exc:
        resultado = "indisponivel"
        motivo = str(exc)
        if "captcha" in motivo:
            obs = f"Requer acesso manual - captcha detectado. Acesse: {LINK}"
        elif "timeout" in motivo.lower() or "ConnectError" in motivo:
            obs = f"Timeout ou sem conexão. Consulte manualmente: {LINK}"
        else:
            obs = f"Consulte manualmente: {LINK}"
    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "receita",
        "resultado": resultado,
        "pdf_base64": None,
        "validade": None,
        "observacao": obs if resultado == "indisponivel" else None,
        "tempo_ms": tempo_ms,
    }
