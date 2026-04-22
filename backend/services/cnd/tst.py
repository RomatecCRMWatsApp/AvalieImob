# @module services.cnd.tst — Provider TST: Certidão Negativa de Débitos Trabalhistas (CNDT)
import time
import httpx

LINK = "https://cndt-certidao.tst.jus.br/inicio.faces"
TIMEOUT = 15.0


async def consultar(cpf_cnpj: str) -> dict:
    """Tenta obter CNDT via POST form no TST; retorna indisponivel se captcha/erro."""
    inicio = time.time()
    doc = cpf_cnpj.strip().replace(".", "").replace("-", "").replace("/", "")
    resultado = "indisponivel"
    obs = None
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            # Primeira requisição para obter viewstate/cookies
            get_resp = await client.get(LINK, headers={"User-Agent": "Mozilla/5.0"})
            if get_resp.status_code not in (200, 302):
                raise ValueError(f"status_{get_resp.status_code}")
            texto = get_resp.text.lower()
            if "captcha" in texto or "recaptcha" in texto:
                raise ValueError("captcha_detectado")
            # Extrai viewstate se presente
            import re
            vs_match = re.search(r'name="javax\.faces\.ViewState"\s+value="([^"]+)"', get_resp.text)
            viewstate = vs_match.group(1) if vs_match else ""
            post_resp = await client.post(
                LINK,
                data={
                    "formulario:cpfCnpj": doc,
                    "javax.faces.ViewState": viewstate,
                    "formulario:pesquisar": "Pesquisar",
                },
                headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"},
            )
            texto_post = post_resp.text.lower()
            if "captcha" in texto_post or "recaptcha" in texto_post:
                raise ValueError("captcha_detectado")
            if "negativa" in texto_post or "nada consta" in texto_post:
                resultado = "negativa"
            elif "positiva" in texto_post or "débito" in texto_post or "debito" in texto_post:
                resultado = "positiva"
                obs = "Débito trabalhista identificado no TST"
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
        "provider": "tst",
        "resultado": resultado,
        "pdf_base64": None,
        "validade": None,
        "observacao": obs,
        "tempo_ms": tempo_ms,
    }
