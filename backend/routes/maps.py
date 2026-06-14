# @module routes/maps — Geocoding via Nominatim + comparativos do PTAM com coordenadas
"""Maps routes: geocode e comparativos com coordenadas."""
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId

from db import get_db
from dependencies import get_active_subscriber

router = APIRouter(prefix="/maps", tags=["maps"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_HEADERS = {"User-Agent": "AvalieImob/1.0 (romatec@romatec.com.br)"}


def _montar_endereco_br(addr: dict) -> str:
    """Compõe um endereço BR legível a partir do `address` do Nominatim."""
    rua = addr.get("road") or addr.get("pedestrian") or addr.get("residential") or ""
    num = addr.get("house_number") or ""
    bairro = addr.get("suburb") or addr.get("neighbourhood") or addr.get("city_district") or ""
    cidade = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality") or ""
    uf = addr.get("state") or ""
    cep = addr.get("postcode") or ""
    p1 = ", ".join([x for x in [rua, (f"nº {num}" if num else ""), bairro] if x])
    p2 = ", ".join([x for x in [cidade, uf] if x])
    out = ", ".join([x for x in [p1, p2] if x])
    if cep:
        out = f"{out}, CEP {cep}" if out else f"CEP {cep}"
    return out


@router.get("/reverse")
async def reverse(lat: float = Query(...), lng: float = Query(...)):
    """Reverse-geocode (coordenadas → endereço) via Nominatim. Best-effort."""
    params = {"lat": lat, "lon": lng, "format": "jsonv2", "addressdetails": 1, "zoom": 18}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(NOMINATIM_REVERSE_URL, params=params, headers=NOMINATIM_HEADERS)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Nominatim indisponível: {exc}")
    if not data or "error" in data:
        raise HTTPException(status_code=404, detail="Endereço não encontrado para as coordenadas")
    addr = data.get("address") or {}
    return {
        "endereco": _montar_endereco_br(addr) or data.get("display_name", ""),
        "display_name": data.get("display_name", ""),
        "address": addr,
    }


@router.get("/geocode")
async def geocode(endereco: str = Query(..., min_length=3)):
    """Geocodifica endereço usando Nominatim (OpenStreetMap) — gratuito e sem chave."""
    params = {"q": endereco, "format": "json", "limit": 1, "countrycodes": "br"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(NOMINATIM_URL, params=params, headers=NOMINATIM_HEADERS)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Nominatim indisponível: {exc}")

    if not data:
        raise HTTPException(status_code=404, detail="Endereço não encontrado")

    r = data[0]
    return {
        "lat": float(r["lat"]),
        "lng": float(r["lon"]),
        "display_name": r.get("display_name", ""),
    }


@router.get("/comparativos/{ptam_id}")
async def comparativos(
    ptam_id: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Retorna amostras do PTAM com coordenadas geocodificadas."""
    try:
        oid = ObjectId(ptam_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ptam_id inválido")

    ptam = await db["ptams"].find_one({"_id": oid, "user_id": uid})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM não encontrado")

    imovel_addr = " ".join(filter(None, [
        ptam.get("property_address", ""),
        ptam.get("property_neighborhood", ""),
        ptam.get("property_city", ""),
        ptam.get("property_state", ""),
    ]))

    imovel_coords = None
    lat_raw = ptam.get("property_gps_lat")
    lng_raw = ptam.get("property_gps_lng")
    if lat_raw and lng_raw:
        try:
            imovel_coords = {"lat": float(lat_raw), "lng": float(lng_raw)}
        except ValueError:
            pass

    if not imovel_coords and imovel_addr.strip():
        try:
            params = {"q": imovel_addr, "format": "json", "limit": 1, "countrycodes": "br"}
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(NOMINATIM_URL, params=params, headers=NOMINATIM_HEADERS)
                data = resp.json()
            if data:
                imovel_coords = {"lat": float(data[0]["lat"]), "lng": float(data[0]["lon"])}
        except Exception:
            pass

    samples_raw = ptam.get("market_samples", [])
    samples = []
    for i, s in enumerate(samples_raw):
        addr = " ".join(filter(None, [s.get("address", ""), s.get("neighborhood", ""), ptam.get("property_city", "")]))
        coords = None
        if addr.strip():
            try:
                params = {"q": addr, "format": "json", "limit": 1, "countrycodes": "br"}
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.get(NOMINATIM_URL, params=params, headers=NOMINATIM_HEADERS)
                    d = resp.json()
                if d:
                    coords = {"lat": float(d[0]["lat"]), "lng": float(d[0]["lon"])}
            except Exception:
                pass
        samples.append({
            "idx": i + 1,
            "address": s.get("address", ""),
            "neighborhood": s.get("neighborhood", ""),
            "value_per_sqm": s.get("value_per_sqm", 0),
            "area": s.get("area", 0),
            "value": s.get("value", 0),
            "coords": coords,
        })

    return {
        "imovel": {"address": imovel_addr, "coords": imovel_coords},
        "samples": samples,
    }
