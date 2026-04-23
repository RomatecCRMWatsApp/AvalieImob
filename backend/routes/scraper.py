"""
Módulo de scraping de amostras de mercado de portais imobiliários.
Integra ZAP Imóveis, VivaReal e OLX para busca automática de amostras.
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, status
from fake_useragent import UserAgent

from services.auth_service import get_current_user_id

router = APIRouter(prefix="/api/scraper", tags=["scraper"])

# Cache simples em memória com TTL
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 1800  # 30 minutos

# Rate limiting simples
_rate_limit: Dict[str, List[float]] = {}
RATE_LIMIT = 10  # requests per minute

ua = UserAgent()


def _get_cache_key(params: Dict[str, Any]) -> str:
    """Gera chave única para cache baseada nos parâmetros."""
    key_data = json.dumps(params, sort_keys=True)
    return hashlib.md5(key_data.encode()).hexdigest()


def _get_from_cache(key: str) -> Optional[List[Dict[str, Any]]]:
    """Recupera dados do cache se ainda válidos."""
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["timestamp"] < CACHE_TTL:
            return entry["data"]
        del _cache[key]
    return None


def _save_to_cache(key: str, data: List[Dict[str, Any]]) -> None:
    """Salva dados no cache."""
    _cache[key] = {"data": data, "timestamp": time.time()}


def _check_rate_limit(user_id: str) -> bool:
    """Verifica se usuário está dentro do rate limit."""
    now = time.time()
    if user_id not in _rate_limit:
        _rate_limit[user_id] = []
    # Limpa entradas antigas
    _rate_limit[user_id] = [t for t in _rate_limit[user_id] if now - t < 60]
    if len(_rate_limit[user_id]) >= RATE_LIMIT:
        return False
    _rate_limit[user_id].append(now)
    return True


def _map_tipo_imovel(tipo: str) -> str:
    """Mapeia tipo de imóvel para formato dos portais."""
    mapping = {
        "casa": "Casa",
        "apartamento": "Apartamento",
        "terreno": "Terreno",
        "sala_comercial": "Sala/Conjunto",
        "galpao": "Galpão/Depósito/Armazém",
        "chacara": "Chácara",
        "fazenda": "Fazenda",
    }
    return mapping.get(tipo, "Casa")


def _map_tipo_unidade(tipo: str) -> str:
    """Mapeia tipo para formato de unidade dos portais."""
    mapping = {
        "casa": "Casa",
        "apartamento": "Apartamento",
        "terreno": "Terreno",
        "sala_comercial": "Sala",
        "galpao": "Galpão",
        "chacara": "Chácara",
        "fazenda": "Fazenda",
    }
    return mapping.get(tipo, "Casa")


async def _scrape_zap(
    cidade: str,
    estado: str,
    tipo: str,
    area_min: int,
    area_max: int,
    valor_max: int,
    finalidade: str = "venda",
    limite: int = 20,
) -> List[Dict[str, Any]]:
    """Scraping do ZAP Imóveis via API interna."""
    amostras = []
    
    try:
        business = "SALE" if finalidade == "venda" else "RENTAL"
        tipo_unidade = _map_tipo_unidade(tipo)
        
        url = (
            f"https://glue-api.zapimoveis.com.br/v3/listings"
            f"?business={business}"
            f"&categoryPage=USED"
            f"&size={min(limite, 50)}"
            f"&from=0"
            f"&q={cidade.replace(' ', '%20')}%20{estado}"
            f"&tipoUnidade=RESIDENCIAL_{tipo_unidade.upper()}"
        )
        
        if area_min > 0:
            url += f"&areaMin={area_min}"
        if area_max > 0:
            url += f"&areaMax={area_max}"
        if valor_max > 0:
            url += f"&priceMax={valor_max}"
        
        headers = {
            "User-Agent": ua.random,
            "Accept": "application/json",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "x-domain": "www.zapimoveis.com.br",
            "Referer": "https://www.zapimoveis.com.br/",
        }
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                listings = data.get("search", {}).get("result", {}).get("listings", [])
                
                for item in listings:
                    try:
                        listing = item.get("listing", {})
                        address = listing.get("address", {})
                        
                        # Extrair dados
                        endereco = address.get("street", "")
                        bairro = address.get("neighborhood", "")
                        cidade_resp = address.get("city", cidade)
                        
                        # Área
                        area = 0
                        if "usableAreas" in listing and listing["usableAreas"]:
                            area = listing["usableAreas"][0]
                        elif "totalAreas" in listing and listing["totalAreas"]:
                            area = listing["totalAreas"][0]
                        
                        # Valor
                        valor = 0
                        if "pricingInfos" in listing and listing["pricingInfos"]:
                            pricing = listing["pricingInfos"][0]
                            if finalidade == "venda":
                                valor = pricing.get("price", 0)
                            else:
                                valor = pricing.get("rentalPrice", 0) or pricing.get("price", 0)
                        
                        # Foto
                        foto = ""
                        if "medias" in listing and listing["medias"]:
                            for media in listing["medias"]:
                                if media.get("type") == "IMAGE":
                                    foto = media.get("url", "")
                                    break
                        
                        # Descrição
                        descricao = listing.get("description", "")[:200]
                        
                        # Quartos/banheiros
                        quartos = listing.get("bedrooms", [0])[0] if listing.get("bedrooms") else 0
                        banheiros = listing.get("bathrooms", [0])[0] if listing.get("bathrooms") else 0
                        
                        if area > 0 and valor > 0:
                            amostra = {
                                "address": f"{endereco}, {bairro}" if endereco else f"{bairro}, {cidade_resp}",
                                "neighborhood": bairro or cidade_resp,
                                "area": float(area),
                                "value": float(valor),
                                "value_per_sqm": round(valor / area, 2) if area > 0 else 0,
                                "source": "ZAP Imóveis",
                                "source_url": f"https://www.zapimoveis.com.br/imovel/{listing.get('id', '')}",
                                "collection_date": datetime.now().strftime("%Y-%m-%d"),
                                "contact_phone": "",
                                "notes": f"{quartos} quarto(s), {banheiros} banheiro(s). {descricao}" if descricao else f"{quartos} quarto(s), {banheiros} banheiro(s)",
                                "tipo_amostra": "oferta",
                                "thumbnail": foto,
                            }
                            amostras.append(amostra)
                    except Exception:
                        continue
                        
    except Exception as e:
        print(f"[ZAP] Erro: {e}")
        
    return amostras[:limite]


async def _scrape_vivareal(
    cidade: str,
    estado: str,
    tipo: str,
    area_min: int,
    area_max: int,
    valor_max: int,
    finalidade: str = "venda",
    limite: int = 20,
) -> List[Dict[str, Any]]:
    """Scraping do VivaReal via API interna."""
    amostras = []
    
    try:
        business = "SALE" if finalidade == "venda" else "RENTAL"
        tipo_unidade = _map_tipo_unidade(tipo)
        
        url = (
            f"https://glue-api.vivareal.com.br/v3/listings"
            f"?business={business}"
            f"&size={min(limite, 50)}"
            f"&from=0"
            f"&q={cidade.replace(' ', '%20')}%20{estado}"
            f"&tipoUnidade=RESIDENCIAL_{tipo_unidade.upper()}"
        )
        
        if area_min > 0:
            url += f"&areaMin={area_min}"
        if area_max > 0:
            url += f"&areaMax={area_max}"
        if valor_max > 0:
            url += f"&priceMax={valor_max}"
        
        headers = {
            "User-Agent": ua.random,
            "Accept": "application/json",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "x-domain": "www.vivareal.com.br",
            "Referer": "https://www.vivareal.com.br/",
        }
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                listings = data.get("search", {}).get("result", {}).get("listings", [])
                
                for item in listings:
                    try:
                        listing = item.get("listing", {})
                        address = listing.get("address", {})
                        
                        endereco = address.get("street", "")
                        bairro = address.get("neighborhood", "")
                        cidade_resp = address.get("city", cidade)
                        
                        area = 0
                        if "usableAreas" in listing and listing["usableAreas"]:
                            area = listing["usableAreas"][0]
                        elif "totalAreas" in listing and listing["totalAreas"]:
                            area = listing["totalAreas"][0]
                        
                        valor = 0
                        if "pricingInfos" in listing and listing["pricingInfos"]:
                            pricing = listing["pricingInfos"][0]
                            if finalidade == "venda":
                                valor = pricing.get("price", 0)
                            else:
                                valor = pricing.get("rentalPrice", 0) or pricing.get("price", 0)
                        
                        foto = ""
                        if "medias" in listing and listing["medias"]:
                            for media in listing["medias"]:
                                if media.get("type") == "IMAGE":
                                    foto = media.get("url", "")
                                    break
                        
                        descricao = listing.get("description", "")[:200]
                        quartos = listing.get("bedrooms", [0])[0] if listing.get("bedrooms") else 0
                        banheiros = listing.get("bathrooms", [0])[0] if listing.get("bathrooms") else 0
                        
                        if area > 0 and valor > 0:
                            amostra = {
                                "address": f"{endereco}, {bairro}" if endereco else f"{bairro}, {cidade_resp}",
                                "neighborhood": bairro or cidade_resp,
                                "area": float(area),
                                "value": float(valor),
                                "value_per_sqm": round(valor / area, 2) if area > 0 else 0,
                                "source": "VivaReal",
                                "source_url": f"https://www.vivareal.com.br/imovel/{listing.get('id', '')}",
                                "collection_date": datetime.now().strftime("%Y-%m-%d"),
                                "contact_phone": "",
                                "notes": f"{quartos} quarto(s), {banheiros} banheiro(s). {descricao}" if descricao else f"{quartos} quarto(s), {banheiros} banheiro(s)",
                                "tipo_amostra": "oferta",
                                "thumbnail": foto,
                            }
                            amostras.append(amostra)
                    except Exception:
                        continue
                        
    except Exception as e:
        print(f"[VivaReal] Erro: {e}")
        
    return amostras[:limite]


async def _scrape_olx(
    cidade: str,
    estado: str,
    tipo: str,
    finalidade: str = "venda",
    limite: int = 20,
) -> List[Dict[str, Any]]:
    """Scraping do OLX Imóveis via HTML (fallback)."""
    amostras = []
    
    try:
        uf = estado.lower()
        tipo_busca = "imoveis/venda" if finalidade == "venda" else "imoveis/aluguel"
        
        url = f"https://www.olx.com.br/{tipo_busca}/estado-{uf}?q={cidade.replace(' ', '+')}+{tipo}"
        
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }
        
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")
                
                # Buscar cards de anúncios
                cards = soup.find_all("div", {"data-ds-component": "DS-AdCard"})
                
                for card in cards[:limite]:
                    try:
                        # Título/endereço
                        titulo_elem = card.find("h2", {"data-ds-component": "DS-Text"})
                        titulo = titulo_elem.text.strip() if titulo_elem else ""
                        
                        # Preço
                        preco_elem = card.find("span", {"data-ds-component": "DS-Text"}, string=lambda x: x and "R$" in x)
                        preco_texto = preco_elem.text.strip() if preco_elem else ""
                        valor = 0
                        if preco_texto:
                            valor_str = preco_texto.replace("R$", "").replace(".", "").replace(",", ".").strip()
                            try:
                                valor = float(valor_str.split()[0])
                            except ValueError:
                                pass
                        
                        # Link
                        link_elem = card.find("a", href=True)
                        link = link_elem["href"] if link_elem else ""
                        if link and not link.startswith("http"):
                            link = f"https://www.olx.com.br{link}"
                        
                        # Foto
                        img_elem = card.find("img")
                        foto = img_elem.get("src", "") if img_elem else ""
                        
                        if titulo and valor > 0:
                            amostra = {
                                "address": titulo[:100],
                                "neighborhood": cidade,
                                "area": 0.0,  # OLX não mostra área diretamente
                                "value": float(valor),
                                "value_per_sqm": 0.0,
                                "source": "OLX Imóveis",
                                "source_url": link,
                                "collection_date": datetime.now().strftime("%Y-%m-%d"),
                                "contact_phone": "",
                                "notes": "Verificar área no anúncio",
                                "tipo_amostra": "oferta",
                                "thumbnail": foto,
                            }
                            amostras.append(amostra)
                    except Exception:
                        continue
                        
    except Exception as e:
        print(f"[OLX] Erro: {e}")
        
    return amostras[:limite]


@router.post("/amostras")
async def buscar_amostras(
    payload: Dict[str, Any],
    uid: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    """
    Busca amostras de mercado em portais imobiliários.
    Ordem: ZAP → VivaReal → OLX (fallback)
    """
    # Rate limiting
    if not _check_rate_limit(uid):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite de requisições excedido. Máximo 10 por minuto.",
        )
    
    # Extrair parâmetros
    cidade = payload.get("cidade", "").strip()
    estado = payload.get("estado", "").strip()
    tipo = payload.get("tipo_imovel", "casa")
    area_min = int(payload.get("area_min", 0) or 0)
    area_max = int(payload.get("area_max", 0) or 0)
    valor_max = int(payload.get("valor_max", 0) or 0)
    finalidade = payload.get("finalidade", "venda")
    limite = min(int(payload.get("limite", 20) or 20), 50)
    
    if not cidade or not estado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cidade e estado são obrigatórios.",
        )
    
    # Verificar cache
    cache_params = {
        "cidade": cidade,
        "estado": estado,
        "tipo": tipo,
        "area_min": area_min,
        "area_max": area_max,
        "valor_max": valor_max,
        "finalidade": finalidade,
        "limite": limite,
    }
    cache_key = _get_cache_key(cache_params)
    cached = _get_from_cache(cache_key)
    
    if cached:
        return {
            "amostras": cached,
            "total": len(cached),
            "fonte": "Cache",
            "cache_hit": True,
        }
    
    # Buscar em paralelo nos portais
    fontes_usadas = []
    todas_amostras = []
    
    # Tentar ZAP primeiro
    zap_result = await _scrape_zap(
        cidade, estado, tipo, area_min, area_max, valor_max, finalidade, limite
    )
    if zap_result:
        todas_amostras.extend(zap_result)
        fontes_usadas.append("ZAP Imóveis")
    
    # Tentar VivaReal
    vivareal_result = await _scrape_vivareal(
        cidade, estado, tipo, area_min, area_max, valor_max, finalidade, limite
    )
    if vivareal_result:
        # Evitar duplicatas (mesmo endereço)
        enderecos_existentes = {a["address"] for a in todas_amostras}
        for amostra in vivareal_result:
            if amostra["address"] not in enderecos_existentes:
                todas_amostras.append(amostra)
        fontes_usadas.append("VivaReal")
    
    # Fallback OLX se poucos resultados
    if len(todas_amostras) < 5:
        olx_result = await _scrape_olx(cidade, estado, tipo, finalidade, limite)
        if olx_result:
            enderecos_existentes = {a["address"] for a in todas_amostras}
            for amostra in olx_result:
                if amostra["address"] not in enderecos_existentes:
                    todas_amostras.append(amostra)
            fontes_usadas.append("OLX Imóveis")
    
    # Ordenar por valor/m² (mais relevantes primeiro)
    todas_amostras.sort(key=lambda x: x.get("value_per_sqm", 0), reverse=True)
    
    # Limitar resultado
    resultado = todas_amostras[:limite]
    
    # Salvar no cache
    _save_to_cache(cache_key, resultado)
    
    return {
        "amostras": resultado,
        "total": len(resultado),
        "fonte": " + ".join(fontes_usadas) if fontes_usadas else "Nenhuma fonte",
        "cache_hit": False,
    }


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Endpoint de health check."""
    return {"status": "ok", "service": "scraper"}
