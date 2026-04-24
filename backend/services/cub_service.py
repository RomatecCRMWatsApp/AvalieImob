# @module services.cub_service – CUB automático SINDUSCON + Método Evolutivo NBR 14.653-2
"""
Scraping mensal do CUB (Custo Unitário Básico) do SINDUSCON-SP e outros estados.
Implementa cache em memória + cache MongoDB (TTL 30 dias) + fallback hardcoded.
Fórmula do Método Evolutivo conforme NBR 14.653-2:2011, item 8.2.1.2.
"""
import re
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Fallback: valores médios nacionais por tipo (R$/m²) ──────────────────────
# Fonte: médias SINDUSCON-SP/IBGE – referência Fev/2024
CUB_FALLBACK = {
    "R1-B":  2_650.00,   # Residencial 1 pavimento – Baixo padrão
    "R1-N":  3_120.00,   # Residencial 1 pavimento – Normal
    "R1-A":  3_980.00,   # Residencial 1 pavimento – Alto padrão
    "PP-B":  2_450.00,   # Prédio popular – Baixo
    "PP-N":  2_820.00,   # Prédio popular – Normal
    "RP1Q-B": 2_580.00,  # Residencial 1 quarto – Baixo
    "RP1Q-N": 3_050.00,  # Residencial 1 quarto – Normal
    "RP1Q-A": 3_880.00,  # Residencial 1 quarto – Alto
    "R8-B":  2_710.00,   # Residencial 8 pavimentos – Baixo
    "R8-N":  3_230.00,   # Residencial 8 pavimentos – Normal
    "R8-A":  4_100.00,   # Residencial 8 pavimentos – Alto
    "R16-N": 3_310.00,   # Residencial 16 pavimentos – Normal
    "R16-A": 4_250.00,   # Residencial 16 pavimentos – Alto
    "CSL-8": 3_150.00,   # Comercial salas e lojas – 8 pav
    "CSL-16": 3_380.00,  # Comercial salas e lojas – 16 pav
    "GI":    1_980.00,   # Galpão industrial
    "PIS":   2_150.00,   # Projeto de Interesse Social
}

CUB_TIPOS_DESCRICAO = {
    "R1-B":   "Residencial 1 pavimento – Baixo padrão",
    "R1-N":   "Residencial 1 pavimento – Normal",
    "R1-A":   "Residencial 1 pavimento – Alto padrão",
    "PP-B":   "Prédio popular – Baixo padrão",
    "PP-N":   "Prédio popular – Normal",
    "RP1Q-B": "Residencial 1 quarto – Baixo padrão",
    "RP1Q-N": "Residencial 1 quarto – Normal",
    "RP1Q-A": "Residencial 1 quarto – Alto padrão",
    "R8-B":   "Residencial 8 pavimentos – Baixo padrão",
    "R8-N":   "Residencial 8 pavimentos – Normal",
    "R8-A":   "Residencial 8 pavimentos – Alto padrão",
    "R16-N":  "Residencial 16 pavimentos – Normal",
    "R16-A":  "Residencial 16 pavimentos – Alto padrão",
    "CSL-8":  "Comercial salas e lojas – 8 pav. Normal",
    "CSL-16": "Comercial salas e lojas – 16 pav. Normal",
    "GI":     "Galpão industrial",
    "PIS":    "Projeto de Interesse Social",
}

# URLs de scraping por estado
SINDUSCON_URLS = {
    "SP": "https://www.sindusconsp.com.br/cub/",
    "MG": "https://www.sinduscon-mg.org.br/cub-mg/",
    "RJ": "https://www.sindusconrj.com.br/cub/",
    "RS": "https://www.sinduscon-rs.com.br/cub",
    "PR": "https://www.sinduscon-pr.com.br/",
    "SC": "https://sindusconsc.com.br/",
    "BA": "https://www.sinduscon-ba.org.br/",
    "PE": "https://www.sinduscon-pe.com.br/",
    "CE": "https://sinduscon-ce.org.br/",
    "GO": "https://www.sinduscon-go.com.br/",
    "DF": "https://www.sinduscondf.org.br/",
    "ES": "https://www.sinduscon-es.com.br/",
    "MA": "https://www.sinduscon-sp.com.br/cub/",  # MA usa SP como fallback
}

# Cache em memória: { "chave": { "cub": {tipo: valor}, "fonte": str, "referencia": str, "ts": float } }
_memoria_cache: dict = {}


def _chave_cache(estado: str) -> str:
    mes = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"cub_{estado}_{mes}"


def _parse_valor_cub(texto: str) -> Optional[float]:
    """Extrai float de texto como '3.234,56' ou '3234.56'."""
    if not texto:
        return None
    texto = texto.strip().replace(" ", "")
    # Formato brasileiro: 3.234,56
    m = re.search(r"\d{1,3}(?:\.\d{3})*,\d{2}", texto)
    if m:
        return float(m.group().replace(".", "").replace(",", "."))
    # Formato americano: 3234.56
    m = re.search(r"\d{3,6}\.\d{2}", texto)
    if m:
        return float(m.group())
    # Número inteiro simples
    m = re.search(r"\d{3,6}", texto)
    if m:
        val = float(m.group())
        if val > 500:
            return val
    return None


def buscar_cub_sinduscon_sp() -> dict:
    """
    Scraping SINDUSCON-SP (https://www.sindusconsp.com.br/cub/).
    Retorna dict {tipo: valor} ou {} em caso de falha.
    """
    url = SINDUSCON_URLS["SP"]
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("SINDUSCON-SP scraping falhou: %s", exc)
        return {}

    soup = BeautifulSoup(resp.text, "lxml")
    resultados = {}

    # Estratégia 1: procurar tabela com tipos CUB
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                tipo_texto = cells[0].get_text(strip=True)
                valor_texto = cells[-1].get_text(strip=True)
                # Mapear tipo encontrado para chave padronizada
                tipo_norm = tipo_texto.upper().replace(" ", "-")
                for tipo_key in CUB_FALLBACK:
                    if tipo_key.replace("-", "") in tipo_norm.replace("-", "") or \
                       tipo_norm.replace("-", "") in tipo_key.replace("-", ""):
                        val = _parse_valor_cub(valor_texto)
                        if val and 800 < val < 15_000:
                            resultados[tipo_key] = val
                        break

    # Estratégia 2: procurar spans/divs com valor > 800
    if not resultados:
        for tag in soup.find_all(["td", "span", "div", "p"]):
            texto = tag.get_text(strip=True)
            val = _parse_valor_cub(texto)
            if val and 1_000 < val < 10_000:
                # Tenta identificar o tipo pelo contexto anterior
                prev = tag.find_previous_sibling()
                if prev:
                    tipo_prev = prev.get_text(strip=True).upper()
                    for tipo_key in CUB_FALLBACK:
                        if tipo_key.replace("-", "") in tipo_prev.replace("-", ""):
                            resultados[tipo_key] = val
                            break

    logger.info("SINDUSCON-SP scraping retornou %d tipos", len(resultados))
    return resultados


def buscar_cub_estado(estado: str) -> dict:
    """
    Tenta scraping do estado. Se falhar ou estado não tiver URL dedicada, usa SP.
    Retorna dict {tipo: valor}.
    """
    estado = estado.upper()
    if estado not in SINDUSCON_URLS or estado == "SP":
        return buscar_cub_sinduscon_sp()

    url = SINDUSCON_URLS[estado]
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("Scraping %s falhou (%s), usando SP como fallback", estado, exc)
        return buscar_cub_sinduscon_sp()

    soup = BeautifulSoup(resp.text, "lxml")
    resultados = {}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                tipo_texto = cells[0].get_text(strip=True).upper()
                valor_texto = cells[-1].get_text(strip=True)
                for tipo_key in CUB_FALLBACK:
                    if tipo_key.replace("-", "") in tipo_texto.replace("-", ""):
                        val = _parse_valor_cub(valor_texto)
                        if val and 800 < val < 15_000:
                            resultados[tipo_key] = val
                        break

    if not resultados:
        logger.info("Scraping %s retornou vazio, usando SP", estado)
        return buscar_cub_sinduscon_sp()

    return resultados


async def get_cub(estado: str, db=None) -> dict:
    """
    Retorna CUB atual na ordem: cache memória → cache MongoDB → scraping → fallback.
    NUNCA falha: sempre retorna valores.

    Retorno:
    {
        "estado": str,
        "mes_referencia": str,   # "YYYY-MM"
        "fonte": str,            # descrição da fonte
        "is_fallback": bool,
        "valores": {tipo: valor},
        "atualizado_em": str (ISO),
    }
    """
    estado = estado.upper()
    chave = _chave_cache(estado)
    mes_ref = datetime.now(timezone.utc).strftime("%Y-%m")
    agora = datetime.now(timezone.utc)

    # 1. Cache memória
    if chave in _memoria_cache:
        entry = _memoria_cache[chave]
        logger.debug("CUB %s: cache memória hit", estado)
        return entry

    # 2. Cache MongoDB
    if db is not None:
        try:
            doc = await db.cub_cache.find_one({"chave": chave})
            if doc:
                entry = {
                    "estado": estado,
                    "mes_referencia": mes_ref,
                    "fonte": doc.get("fonte", "Cache MongoDB"),
                    "is_fallback": doc.get("is_fallback", False),
                    "valores": doc.get("valores", {}),
                    "atualizado_em": doc.get("criado_em", agora).isoformat(),
                }
                _memoria_cache[chave] = entry
                logger.debug("CUB %s: cache MongoDB hit", estado)
                return entry
        except Exception as exc:
            logger.warning("Erro ao ler cub_cache MongoDB: %s", exc)

    # 3. Scraping
    valores_scraped = {}
    fonte = "Scraping não disponível"
    is_fallback = True

    try:
        valores_scraped = buscar_cub_estado(estado)
        if valores_scraped:
            fonte = f"SINDUSCON-{'SP' if estado not in SINDUSCON_URLS else estado} (scraping)"
            is_fallback = False
            logger.info("CUB %s: scraping bem-sucedido (%d tipos)", estado, len(valores_scraped))
    except Exception as exc:
        logger.warning("Scraping CUB %s falhou: %s", estado, exc)

    # 4. Fallback hardcoded (sempre completo)
    valores_finais = {**CUB_FALLBACK, **valores_scraped}  # scraped sobrescreve fallback quando disponível
    if not valores_scraped:
        fonte = "Referência nacional (SP) – valores médios SINDUSCON"
        is_fallback = True

    entry = {
        "estado": estado,
        "mes_referencia": mes_ref,
        "fonte": fonte,
        "is_fallback": is_fallback,
        "valores": valores_finais,
        "atualizado_em": agora.isoformat(),
    }

    # Salvar no MongoDB
    if db is not None:
        try:
            await db.cub_cache.replace_one(
                {"chave": chave},
                {
                    "chave": chave,
                    "estado": estado,
                    "fonte": fonte,
                    "is_fallback": is_fallback,
                    "valores": valores_finais,
                    "criado_em": agora,
                },
                upsert=True,
            )
        except Exception as exc:
            logger.warning("Erro ao salvar cub_cache MongoDB: %s", exc)

    _memoria_cache[chave] = entry
    return entry


def calcular_metodo_evolutivo(
    cub_valor: float,
    area_construida: float,
    valor_terreno: float,
    fator_obsolescencia: float = 0.0,   # 0–80 (%)
    fator_adequacao: float = 1.0,
    benfeitoria_extra: float = 0.0,
    tipo_cub: str = "R1-N",
    fonte_cub: str = "",
) -> dict:
    """
    Método Evolutivo conforme NBR 14.653-2:2011, item 8.2.1.2.

    Fórmula:
        Valor Benfeitorias = CUB × Área × Fator Adequação × (1 − Depreciação%)
        Valor Total = Valor Terreno + Valor Benfeitorias + Benfeitorias Extras

    Parâmetros:
        cub_valor           R$/m² do CUB do tipo selecionado
        area_construida     m² da área construída
        valor_terreno       R$ valor de mercado do terreno
        fator_obsolescencia % de depreciação (0–80)
        fator_adequacao     fator de adequação ao uso (padrão 1.0)
        benfeitoria_extra   R$ de benfeitorias extras (piscina, etc.)
        tipo_cub            código do tipo CUB
        fonte_cub           texto descritivo da fonte
    """
    fator_dep = max(0.0, min(80.0, fator_obsolescencia)) / 100.0
    fator_adequacao = max(0.1, fator_adequacao)

    custo_reproducao = cub_valor * area_construida * fator_adequacao
    depreciacao_valor = custo_reproducao * fator_dep
    valor_benfeitoria = custo_reproducao - depreciacao_valor
    valor_total = valor_terreno + valor_benfeitoria + benfeitoria_extra

    return {
        "tipo_cub": tipo_cub,
        "cub_valor": round(cub_valor, 2),
        "area_construida": round(area_construida, 2),
        "fator_adequacao": round(fator_adequacao, 4),
        "fator_obsolescencia_pct": round(fator_obsolescencia, 2),
        "custo_reproducao": round(custo_reproducao, 2),
        "depreciacao_valor": round(depreciacao_valor, 2),
        "valor_benfeitoria": round(valor_benfeitoria, 2),
        "valor_terreno": round(valor_terreno, 2),
        "benfeitoria_extra": round(benfeitoria_extra, 2),
        "valor_total": round(valor_total, 2),
        "fonte_cub": fonte_cub,
        "base_legal": "NBR 14.653-2:2011, item 8.2.1.2",
        "calculado_em": datetime.now(timezone.utc).isoformat(),
        "formula": (
            f"VT = VTe + [CUB({cub_valor:.2f}) × {area_construida:.2f}m² × "
            f"Fa({fator_adequacao:.2f}) × (1 − {fator_obsolescencia:.1f}%)] + BE({benfeitoria_extra:.2f})"
        ),
    }
