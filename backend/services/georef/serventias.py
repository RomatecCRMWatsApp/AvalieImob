# @module services.georef.serventias — Lookup CNS → serventia (cartório) + município/UF.
#
# Tabela oficial das serventias extrajudiciais (CNJ), 3.703 cartórios, indexada por
# CNS. Resolve automaticamente o nome correto da serventia e a comarca a partir do
# CNS lido do Memorial SIGEF (ex.: 03.169-0 → "Serventia Extrajudicial de São
# Francisco do Maranhão — Ofício Único", São Francisco do Maranhão/MA).
import json
import os
import re
from functools import lru_cache

_JSON = os.path.join(os.path.dirname(__file__), "..", "..", "data", "serventias_cns.json")

_CONECTORES = {"de", "da", "do", "das", "dos", "e", "di", "du", "à", "a"}


@lru_cache(maxsize=1)
def _tabela() -> dict:
    try:
        with open(_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def _norm(cns: str) -> str:
    return re.sub(r"\D", "", cns or "")


def _title_br(s: str) -> str:
    if not s:
        return s
    palavras = str(s).lower().split()
    return " ".join(w if w in _CONECTORES else (w[:1].upper() + w[1:]) for w in palavras)


def buscar_serventia(cns: str) -> dict | None:
    """Retorna {cns, denominacao, cidade, uf} para o CNS, ou None se não houver."""
    reg = _tabela().get(_norm(cns))
    if not reg:
        return None
    return {
        "cns": reg.get("cns") or cns,
        "denominacao": (reg.get("denominacao") or "").strip(),
        "cidade": _title_br(reg.get("cidade") or ""),
        "uf": (reg.get("uf") or "").strip(),
    }


def enriquecer_cartorio(imovel: dict, editados: dict | None = None) -> dict:
    """Preenche cartorio_nome / cartorio_municipio / cartorio_uf a partir do CNS.

    Respeita campos editados manualmente (não sobrescreve `imovel.<campo>` marcado).
    """
    editados = editados or {}
    cns = imovel.get("cartorio_cns")
    if not cns:
        return imovel
    s = buscar_serventia(cns)
    if not s:
        return imovel
    if not editados.get("imovel.cartorio_nome"):
        imovel["cartorio_nome"] = s["denominacao"]
    if not editados.get("imovel.cartorio_municipio") and s["cidade"]:
        imovel["cartorio_municipio"] = s["cidade"]
    if not editados.get("imovel.cartorio_uf") and s["uf"]:
        imovel["cartorio_uf"] = s["uf"]
    return imovel
