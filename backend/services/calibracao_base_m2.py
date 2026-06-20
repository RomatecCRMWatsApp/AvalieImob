# @module services.calibracao_base_m2 — Calibra a base R$/m² da Calculadora pública
# a partir dos PTAMs REAIS já emitidos (concluídos/assinados) do dono da conta.
"""Dá credibilidade defensável à estimativa: em vez de valor-semente, usa a MEDIANA
do R$/m² (valor final ÷ área considerada) das avaliações reais por cidade/UF.

- Só conta PTAM concluído/assinado (utils.ptam_status.calcular_status_ptam).
- R$/m² = resultado_valor_total ÷ área (imovel_area_a_considerar / property_area_sqm /
  imovel_area_construida — 1ª positiva). Filtra faixa sã (200–60000) p/ excluir
  rural-por-ha e outliers. MEDIANA (robusta) por região, mínimo 3 amostras.
- Persiste em `avaliacao_base_m2` e mantém cache em processo (lido pelo /estimar, sync).
"""
import logging
from datetime import datetime, timezone
from statistics import median

logger = logging.getLogger("romatec")

_ACENTOS = str.maketrans("ÁÀÂÃÉÊÍÓÔÕÚÇ", "AAAAEEIOOOUC")
VM2_MIN, VM2_MAX = 200.0, 60000.0
N_MINIMO = 3
COL = "avaliacao_base_m2"

# Cache em processo: {regiao_key: {"media_m2": float, "n": int, "escopo": "cidade"|"uf"}}
_CACHE: dict = {}


def _norm(t: str) -> str:
    return (t or "").strip().upper().translate(_ACENTOS)


def _num(v) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def base_calibrada(uf: str, cidade: str):
    """(media_m2, n, label) da base REAL calibrada, ou None. Lê o cache (sync)."""
    ck = f"{uf}:{_norm(cidade)}"
    if ck in _CACHE:
        c = _CACHE[ck]
        return c["media_m2"], c["n"], f"{(cidade or '').strip().title()}/{uf}"
    if uf in _CACHE:
        c = _CACHE[uf]
        return c["media_m2"], c["n"], f"{uf} — base estadual"
    return None


async def carregar_cache(db) -> int:
    global _CACHE
    novo: dict = {}
    try:
        async for d in db[COL].find({}):
            if d.get("regiao_key") and d.get("media_m2"):
                novo[d["regiao_key"]] = {"media_m2": d["media_m2"], "n": d.get("n", 0), "escopo": d.get("escopo")}
        _CACHE = novo
    except Exception as e:  # noqa: BLE001
        logger.error("calibracao_base_m2: erro ao carregar cache: %s", e)
    return len(_CACHE)


async def recalibrar(db, owner_uid: str) -> dict:
    """Reagrega os PTAMs do owner → base R$/m² por cidade/UF. Substitui a coleção e o cache."""
    from utils.ptam_status import calcular_status_ptam

    por_cidade: dict = {}
    por_uf: dict = {}
    total, usados = 0, 0
    try:
        cursor = db.ptam_documents.find({"user_id": owner_uid})
        async for p in cursor:
            total += 1
            try:
                if calcular_status_ptam(p) not in ("concluido", "assinado"):
                    continue
                valor = _num(p.get("resultado_valor_total"))
                area = 0.0
                for k in ("imovel_area_a_considerar", "property_area_sqm", "imovel_area_construida"):
                    a = _num(p.get(k))
                    if a > 0:
                        area = a
                        break
                if valor <= 0 or area <= 0:
                    continue
                vm2 = valor / area
                if not (VM2_MIN <= vm2 <= VM2_MAX):
                    continue
                uf = (p.get("property_state") or "").strip().upper()
                if len(uf) != 2:
                    continue
                cidade = p.get("property_city") or ""
                por_uf.setdefault(uf, []).append(vm2)
                if cidade.strip():
                    por_cidade.setdefault(f"{uf}:{_norm(cidade)}", []).append(vm2)
                usados += 1
            except Exception:  # noqa: BLE001 — um doc ruim não derruba a calibração
                continue
    except Exception as e:  # noqa: BLE001
        logger.error("calibracao_base_m2: erro ao varrer PTAMs: %s", e)
        return {"erro": str(e), "total": total, "usados": usados, "regioes": 0}

    agora = datetime.now(timezone.utc)
    docs = []
    for key, vals in por_cidade.items():
        if len(vals) >= N_MINIMO:
            docs.append({"regiao_key": key, "escopo": "cidade", "media_m2": round(median(vals), 2), "n": len(vals), "atualizado_em": agora})
    for uf, vals in por_uf.items():
        if len(vals) >= N_MINIMO:
            docs.append({"regiao_key": uf, "escopo": "uf", "media_m2": round(median(vals), 2), "n": len(vals), "atualizado_em": agora})

    try:
        await db[COL].delete_many({})
        if docs:
            await db[COL].insert_many(docs)
    except Exception as e:  # noqa: BLE001
        logger.error("calibracao_base_m2: erro ao gravar: %s", e)

    await carregar_cache(db)
    return {
        "total_ptams": total, "ptams_usados": usados,
        "regioes": len(docs),
        "cidades": sum(1 for d in docs if d["escopo"] == "cidade"),
        "ufs": sum(1 for d in docs if d["escopo"] == "uf"),
        "minimo_amostras": N_MINIMO,
    }
