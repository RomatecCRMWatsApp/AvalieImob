# @module services.cnd.tjma — Provider TJMA: Consulta processual no Tribunal de Justiça do MA
import time
import httpx

LINK = "https://esaj.tjma.jus.br/cpopg/open.do"
TIMEOUT = 15.0


async def consultar(cpf_cnpj: str) -> dict:
    """Tenta consulta no TJMA via httpx; retorna indisponivel se bloqueado/captcha."""
    inicio = time.time()
    doc = cpf_cnpj.strip().replace(".", "").replace("-", "").replace("/", "")
    resultado = "indisponivel"
    obs = None
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(
                "https://esaj.tjma.jus.br/cpopg/search.do",
                params={
                    "conversationId": "",
                    "dadosConsulta.localPesquisa.cdLocal": "-1",
                    "dadosConsulta.tipoPesquisa": "DOCPARTE",
                    "dadosConsulta.valorConsulta": doc,
                },
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code not in (200, 302):
                raise ValueError(f"status_{resp.status_code}")
            texto = resp.text.lower()
            if "captcha" in texto or "recaptcha" in texto:
                raise ValueError("captcha_detectado")
            if "não existem informações" in texto or "nenhum processo" in texto or "0 processo" in texto:
                resultado = "negativa"
            elif "processo" in texto and ("número" in texto or "classe" in texto or "numero" in texto):
                resultado = "positiva"
                obs = "Processos encontrados no TJMA"
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
        "provider": "tjma",
        "resultado": resultado,
        "pdf_base64": None,
        "validade": None,
        "observacao": obs,
        "tempo_ms": tempo_ms,
    }
