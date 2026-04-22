# @module services.cnd.rfb_cadastro — Provider RFB: situação cadastral CPF na Receita Federal
import time
import httpx

LINK_CPF = "https://www.receita.fazenda.gov.br/Aplicacoes/SSL/ATBHE/ConsultaSituacaoCPF.app/consultarSituacao.asp"
LINK_CNPJ = "https://www.receita.fazenda.gov.br/Aplicacoes/SSL/ATBHE/CNPJREVA/Interfaces/ResultadoInteface.asp"
TIMEOUT = 15.0


async def consultar(cpf_cnpj: str) -> dict:
    """Tenta consultar situação cadastral CPF/CNPJ na RFB; fallback indisponivel."""
    inicio = time.time()
    doc = cpf_cnpj.strip().replace(".", "").replace("-", "").replace("/", "")
    eh_cnpj = len(doc) == 14
    link = LINK_CNPJ if eh_cnpj else LINK_CPF
    resultado = "indisponivel"
    obs = None
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            if eh_cnpj:
                resp = await client.post(
                    link,
                    data={"cnpj": doc},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
            else:
                resp = await client.post(
                    link,
                    data={"cpf": doc, "txtTexto_captcha_serpro_gov_br": ""},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
            texto = resp.text.lower()
            if "captcha" in texto or "recaptcha" in texto or resp.status_code in (403, 429):
                raise ValueError("captcha_detectado")
            if "regular" in texto or "ativo" in texto:
                resultado = "negativa"
                obs = "Situação cadastral: Regular"
            elif "suspensa" in texto or "cancelada" in texto or "nula" in texto:
                resultado = "positiva"
                obs = "Situação cadastral irregular"
            else:
                raise ValueError("resposta_inesperada")
    except Exception as exc:
        resultado = "indisponivel"
        motivo = str(exc)
        if "captcha" in motivo:
            obs = f"Requer acesso manual - captcha detectado. Acesse: {link}"
        else:
            obs = f"Consulte manualmente: {link}"
    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "rfb_cadastro",
        "resultado": resultado,
        "pdf_base64": None,
        "validade": None,
        "observacao": obs,
        "tempo_ms": tempo_ms,
    }
