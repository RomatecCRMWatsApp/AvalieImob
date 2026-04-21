# @module routes.imoveis_crm — Proxy público para imóveis do CRM Romatec com cache 5 min
import asyncio
import logging
import time as _time
from fastapi import APIRouter

router = APIRouter(tags=["crm"])
logger = logging.getLogger("romatec")

_crm_cache: dict = {"data": None, "ts": 0.0}
_CRM_CACHE_TTL = 300
_CRM_TRPC_URL = "https://romateccrm.com/api/trpc/properties.list"


def _fetch_crm_imoveis() -> list:
    import requests as _req
    resp = _req.get(_CRM_TRPC_URL, timeout=10, headers={"Accept": "application/json"})
    resp.raise_for_status()
    payload = resp.json()
    raw_items = payload.get("result", {}).get("data", {}).get("json", [])
    result = []
    for item in raw_items:
        images = item.get("images") or []
        slug = item.get("publicSlug") or ""
        area_construida = item.get("areaConstruida") or item.get("areaCasa")
        try:
            area_val = float(area_construida) if area_construida else None
        except (ValueError, TypeError):
            area_val = None
        try:
            terreno_val = float(item.get("areaTerreno") or 0) or None
        except (ValueError, TypeError):
            terreno_val = None
        try:
            preco_val = float(item.get("price") or 0)
        except (ValueError, TypeError):
            preco_val = 0.0
        quartos = item.get("bedrooms")
        banheiros = item.get("bathrooms")
        vagas = item.get("garageSpaces")
        result.append({
            "id": item.get("id"),
            "nome": item.get("denomination", ""),
            "tipo": item.get("propertyType") or "Imóvel",
            "preco": preco_val,
            "endereco": ", ".join(filter(None, [item.get("address", ""), item.get("city", ""), item.get("state", "")])),
            "quartos": int(quartos) if quartos else None,
            "banheiros": int(banheiros) if banheiros else None,
            "vagas": int(vagas) if vagas else None,
            "area": area_val,
            "terreno": terreno_val,
            "imagem": images[0] if images else None,
            "fotos": len(images),
            "status": "Disponível" if item.get("status") == "available" else (item.get("status") or ""),
            "link": f"https://romateccrm.com/imovel/{slug}" if slug else "https://romateccrm.com/properties",
        })
    return result


@router.get("/imoveis-crm")
async def get_imoveis_crm():
    now = _time.time()
    if _crm_cache["data"] is not None and (now - _crm_cache["ts"]) < _CRM_CACHE_TTL:
        return {"imoveis": _crm_cache["data"], "cached": True, "cache_age_s": int(now - _crm_cache["ts"])}
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _fetch_crm_imoveis)
        _crm_cache["data"] = data
        _crm_cache["ts"] = _time.time()
        logger.info("CRM Romatec: %d imóveis carregados", len(data))
        return {"imoveis": data, "cached": False, "cache_age_s": 0}
    except Exception as exc:
        logger.warning("Falha ao buscar CRM Romatec: %s", exc)
        fallback = _crm_cache["data"] or []
        return {"imoveis": fallback, "cached": True, "error": str(exc)[:200], "cache_age_s": int(now - _crm_cache["ts"]) if _crm_cache["data"] else -1}
