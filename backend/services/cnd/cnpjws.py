# @module services.cnd.cnpjws — CNPJ via API pública cnpj.ws (sem autenticação)
import time
import httpx

URL = "https://publica.cnpj.ws/cnpj/{cnpj}"
TIMEOUT = 15.0
MANUAL_LINK = "https://servicos.receita.fazenda.gov.br/Servicos/cnpjreva/Cnpjreva_Solicitacao.asp"


async def consultar(cpf_cnpj: str) -> dict:
    inicio = time.time()
    doc = cpf_cnpj.strip().replace(".", "").replace("-", "").replace("/", "")

    if len(doc) != 14:
        return {
            "provider": "cnpjws",
            "resultado": "nao_aplicavel",
            "pdf_base64": None,
            "validade": None,
            "observacao": "Consulta cnpj.ws: somente para CNPJ",
            "link_manual": MANUAL_LINK,
            "tempo_ms": 0,
        }

    resultado = "indisponivel"
    observacao = "Serviço cnpj.ws indisponível no momento"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(
                URL.format(cnpj=doc),
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0",
                },
            )

            if resp.status_code == 404:
                resultado = "positiva"
                observacao = "CNPJ não encontrado na base pública"
            elif resp.status_code != 200:
                raise ValueError(f"HTTP {resp.status_code}")
            else:
                data = resp.json() if resp.text else {}
                status = (data.get("estabelecimento", {}).get("situacao_cadastral") or data.get("razao_social") and "ATIVA" or "").upper()
                if "ATIVA" in status:
                    resultado = "negativa"
                    observacao = None
                elif status:
                    resultado = "positiva"
                    observacao = f"Situação cadastral: {status}"
                else:
                    resultado = "indisponivel"
                    observacao = "Resposta sem situação cadastral reconhecida"
    except Exception as exc:
        resultado = "indisponivel"
        observacao = f"cnpj.ws: {exc}"

    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "cnpjws",
        "resultado": resultado,
        "pdf_base64": None,
        "validade": None,
        "observacao": observacao,
        "link_manual": MANUAL_LINK,
        "tempo_ms": tempo_ms,
    }