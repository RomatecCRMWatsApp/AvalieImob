# @module services.cnd.pgfn — Provider PGFN: fallback manual robusto
import time

LINK = "https://solucoes.receita.fazenda.gov.br/Servicos/certidaointernet/PF/Emitir"


async def consultar(cpf_cnpj: str) -> dict:
    """Retorna fallback manual para PGFN por bloqueios recorrentes em emissão automatizada."""
    inicio = time.time()
    tempo_ms = int((time.time() - inicio) * 1000)
    return {
        "provider": "pgfn",
        "resultado": "indisponivel",
        "pdf_base64": None,
        "validade": None,
        "observacao": "Consulta automática indisponível na PGFN no momento. Use o portal oficial.",
        "link_manual": LINK,
        "tempo_ms": tempo_ms,
    }
