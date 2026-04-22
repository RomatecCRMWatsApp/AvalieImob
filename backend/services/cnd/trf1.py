# @module services.cnd.trf1 — Provider TRF1: Consulta pública de processos
import time
import httpx

LINK = "https://pje.trf1.jus.br/pje/ConsultaPublica/listView.seam"
TIMEOUT = 15.0


async def consultar(cpf_cnpj: str) -> dict:
    """Tenta consulta pública no TRF1 via httpx; retorna indisponivel se bloqueado."""
    inicio = time.time()
    doc = cpf_cnpj.strip().replace(".", "").replace("-", "").replace("/", "")
    resultado = "indisponivel"
    obs = None
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(
                LINK,
                params={"txtParte": doc},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code not in (200,):
                raise ValueError(f"status_{resp.status_code}")
            texto = resp.text.lower()
            if "captcha" in texto or "recaptcha" in texto or "acesso negado" in texto:
                raise ValueError("captcha_ou_bloqueio")
            if "nenhum processo" in texto or "nenhum resultado" in texto or "0 resultado" in texto:
                resultado = "negativa"
            elif "processo" in texto and ("autos" in texto or "classe" in texto):
                resultado = "positiva"
                obs = "Processos encontrados no TRF1"
            else:
                raise ValueError("resposta_inesperada")
    except Exception as exc:
        resultado = "indisponivel"
        motivo = str(exc)
        if "captcha" in motivo or "bloqueio" in motivo:
            obs = f"Requer acesso manual - captcha/bloqueio. Acesse: {LINK}"
        else:
            obs = f"Consulte manualmente: {LINK}"
    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "trf1",
        "resultado": resultado,
        "pdf_base64": None,
        "validade": None,
        "observacao": obs,
        "tempo_ms": tempo_ms,
    }
