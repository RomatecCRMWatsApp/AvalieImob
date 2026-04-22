# @module services.cnd.receita_federal — Provider Receita Federal: situação cadastral CPF/CNPJ
import time
import httpx

# URLs oficiais atualizadas (Receita Federal migrou o portal em 2024)
URL_CPF  = "https://servicos.receita.fazenda.gov.br/Servicos/CPF/ConsultaSituacao/ConsultaPublica.asp"
URL_CNPJ = "https://servicos.receita.fazenda.gov.br/Servicos/cnpjreva/Cnpjreva_Solicitacao.asp"
URL_CND  = "https://solucoes.receita.fazenda.gov.br/Servicos/certidaointer/default.aspx"

TIMEOUT = 15.0
FALLBACK_OBS = (
    "Receita Federal temporariamente indisponível — "
    "consultar manualmente em gov.br/receitafederal"
)


async def consultar(cpf_cnpj: str) -> dict:
    """Tenta obter certidão da Receita Federal via HTTP; retorna indisponivel se bloqueado."""
    inicio = time.time()
    doc = cpf_cnpj.strip().replace(".", "").replace("-", "").replace("/", "")
    resultado = "indisponivel"
    obs = FALLBACK_OBS

    is_cnpj = len(doc) == 14
    url_cadastro = URL_CNPJ if is_cnpj else URL_CPF

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            # 1ª tentativa: URL de consulta cadastral (CPF ou CNPJ)
            resp = await client.get(
                url_cadastro,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            texto = resp.text.lower()

            if "captcha" in texto or "recaptcha" in texto or resp.status_code == 403:
                raise ValueError("captcha_detectado")

            if resp.status_code == 404:
                raise ValueError("url_404")

            if "negativa" in texto or "nada consta" in texto or "regular" in texto:
                resultado = "negativa"
                obs = None
            elif "positiva" in texto or "dívida" in texto or "divida" in texto or "pendente" in texto:
                resultado = "positiva"
                obs = "Débito identificado na Receita Federal"
            else:
                # 2ª tentativa: endpoint CND (GET, não POST)
                resp2 = await client.get(
                    URL_CND,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                texto2 = resp2.text.lower()
                if resp2.status_code == 404:
                    raise ValueError("cnd_url_404")
                if "negativa" in texto2 or "nada consta" in texto2:
                    resultado = "negativa"
                    obs = None
                elif "positiva" in texto2 or "dívida" in texto2 or "divida" in texto2:
                    resultado = "positiva"
                    obs = "Débito identificado na Receita Federal"
                else:
                    raise ValueError("resposta_inesperada")

    except Exception as exc:
        resultado = "indisponivel"
        motivo = str(exc)
        if "captcha" in motivo:
            obs = f"Requer acesso manual — captcha detectado. Acesse: {URL_CND}"
        elif "url_404" in motivo or "cnd_url_404" in motivo:
            obs = FALLBACK_OBS
        elif "timeout" in motivo.lower() or "connecterror" in motivo.lower():
            obs = f"Timeout ou sem conexão. {FALLBACK_OBS}"
        else:
            obs = FALLBACK_OBS

    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "receita",
        "resultado": resultado,
        "pdf_base64": None,
        "validade": None,
        "observacao": obs if resultado == "indisponivel" else None,
        "tempo_ms": tempo_ms,
    }
