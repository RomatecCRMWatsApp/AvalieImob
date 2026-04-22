# @module services.cnd.pgfn — Provider PGFN: Dívida Ativa da União
import time
import httpx

LINK = "https://solucoes.receita.fazenda.gov.br/Servicos/certidaointer/pgfn"
TIMEOUT = 15.0


async def consultar(cpf_cnpj: str) -> dict:
    """Tenta obter certidão PGFN via HTTP; retorna indisponivel se bloqueado/captcha."""
    inicio = time.time()
    doc = cpf_cnpj.strip().replace(".", "").replace("-", "").replace("/", "")
    resultado = "indisponivel"
    obs = None
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.post(
                "https://solucoes.receita.fazenda.gov.br/Servicos/certidaointer/",
                data={"cpfcnpj": doc, "tipo": "3"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            texto = resp.text.lower()
            if "captcha" in texto or "recaptcha" in texto or resp.status_code in (403, 429):
                raise ValueError("captcha_detectado")
            if "negativa" in texto or "nada consta" in texto:
                resultado = "negativa"
            elif "positiva" in texto or "dívida" in texto or "divida" in texto:
                resultado = "positiva"
                obs = "Débito identificado na PGFN"
            else:
                raise ValueError("resposta_inesperada")
    except Exception as exc:
        resultado = "indisponivel"
        motivo = str(exc)
        if "captcha" in motivo:
            obs = f"Requer acesso manual - captcha detectado. Acesse: {LINK}"
        else:
            obs = f"Consulte manualmente: {LINK}"
    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "pgfn",
        "resultado": resultado,
        "pdf_base64": None,
        "validade": None,
        "observacao": obs,
        "tempo_ms": tempo_ms,
    }
