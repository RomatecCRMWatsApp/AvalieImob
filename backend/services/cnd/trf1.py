# @module services.cnd.trf1 — Provider TRF1: Consulta pública de processos
import asyncio
import time
import httpx

URL_PRINCIPAL  = "https://pje.trf1.jus.br/pje/ConsultaPublica/listView.seam"
URL_ALTERNATIVA = "https://processual.trf1.jus.br/consultaProcessual/processo.faces"

TIMEOUT = httpx.Timeout(15.0, connect=5.0)
FALLBACK_OBS = "TRF1 indisponível — consultar em pje.trf1.jus.br"


def _resultado_indisponivel(obs: str, tempo_ms: int) -> dict:
    return {
        "provider": "trf1",
        "resultado": "indisponivel",
        "pdf_base64": None,
        "validade": None,
        "observacao": obs,
        "tempo_ms": tempo_ms,
    }


async def _tentar_url(client: httpx.AsyncClient, url: str, params: dict) -> httpx.Response:
    """Tenta a URL com retry (máx 2 tentativas) e backoff de 2s."""
    for tentativa in range(2):
        try:
            resp = await client.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
            return resp
        except (httpx.TimeoutException, httpx.ConnectError):
            if tentativa == 1:
                raise
            await asyncio.sleep(2)


async def consultar(cpf_cnpj: str) -> dict:
    """Tenta consulta pública no TRF1 via httpx; retorna indisponivel se bloqueado/timeout."""
    inicio = time.time()
    doc = cpf_cnpj.strip().replace(".", "").replace("-", "").replace("/", "")
    resultado = "indisponivel"
    obs = FALLBACK_OBS

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            # Tenta URL principal com retry
            try:
                resp = await _tentar_url(client, URL_PRINCIPAL, {"txtParte": doc})
            except (httpx.TimeoutException, httpx.ConnectError):
                # Fallback para URL alternativa
                try:
                    resp = await _tentar_url(client, URL_ALTERNATIVA, {"nrProcesso": doc})
                except (httpx.TimeoutException, httpx.ConnectError):
                    tempo_ms = int((time.time() - inicio) * 1000)
                    return _resultado_indisponivel(FALLBACK_OBS, tempo_ms)

            if resp.status_code not in (200,):
                raise ValueError(f"status_{resp.status_code}")

            texto = resp.text.lower()
            if "captcha" in texto or "recaptcha" in texto or "acesso negado" in texto:
                raise ValueError("captcha_ou_bloqueio")

            if "nenhum processo" in texto or "nenhum resultado" in texto or "0 resultado" in texto:
                resultado = "negativa"
                obs = None
            elif "processo" in texto and ("autos" in texto or "classe" in texto):
                resultado = "positiva"
                obs = "Processos encontrados no TRF1"
            else:
                raise ValueError("resposta_inesperada")

    except Exception as exc:
        resultado = "indisponivel"
        motivo = str(exc)
        if "captcha" in motivo or "bloqueio" in motivo:
            obs = f"Requer acesso manual — captcha/bloqueio. Acesse: {URL_PRINCIPAL}"
        else:
            obs = FALLBACK_OBS

    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "trf1",
        "resultado": resultado,
        "pdf_base64": None,
        "validade": None,
        "observacao": obs,
        "tempo_ms": tempo_ms,
    }
