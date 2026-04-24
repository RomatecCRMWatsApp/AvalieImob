# @module routes.sigef — Endpoints de consulta SIGEF/INCRA para laudos rurais
"""Rotas para consulta automatica ao SIGEF (INCRA) e preenchimento de PTAMs rurais."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from typing import Optional
import json
import re
from datetime import datetime
import xml.etree.ElementTree as ET

from dependencies import get_active_subscriber
from db import get_db
from services.sigef_service import (
    consulta_completa_rural,
    buscar_modulo_fiscal,
    calcular_modulos_fiscais,
    parsear_arquivo_sigef,
    _validar_ccir,
    _formatar_ccir,
)

router = APIRouter(prefix="/sigef", tags=["sigef"])


def _validate_sigef_file_structure(filename: str, content: bytes) -> str:
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio não é permitido")

    lowered_name = (filename or "").lower().strip()
    text = content.decode("utf-8", errors="replace").lstrip("\ufeff \t\r\n")

    if lowered_name.endswith((".json", ".geojson")):
        try:
            data = json.loads(text)
        except Exception:
            raise HTTPException(status_code=400, detail="JSON/GeoJSON inválido")
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="Estrutura JSON inválida para arquivo SIGEF")
        if not any(key in data for key in ("features", "geometry", "coordinates", "type")):
            raise HTTPException(status_code=400, detail="GeoJSON sem estrutura geométrica reconhecida")
        return text

    if not text.startswith("<"):
        raise HTTPException(status_code=400, detail="Arquivo SIGEF XML/KML/GML inválido")

    try:
        root = ET.fromstring(text)
    except Exception:
        raise HTTPException(status_code=400, detail="XML/KML/GML inválido")

    root_tag = root.tag.split("}")[-1].lower() if "}" in root.tag else root.tag.lower()
    tags = {
        (el.tag.split("}")[-1].lower() if "}" in el.tag else el.tag.lower())
        for el in root.iter()
    }

    if lowered_name.endswith(".kml") and "kml" not in tags and root_tag != "kml":
        raise HTTPException(status_code=400, detail="KML inválido: raiz/namespace não reconhecidos")

    if lowered_name.endswith(".gml"):
        has_gml_structure = any(tag in tags for tag in {"featurecollection", "featuremember", "poslist", "polygon", "surface"})
        if not has_gml_structure:
            raise HTTPException(status_code=400, detail="GML inválido: estrutura geoespacial não reconhecida")

    expected_sigef_tags = {
        "coordinates", "poslist", "coord", "ccir", "codigo", "parcela_codigo",
        "denominacao", "municipio", "estado", "uf", "area", "area_ha",
    }
    if not tags.intersection(expected_sigef_tags):
        raise HTTPException(status_code=400, detail="Arquivo SIGEF sem campos estruturais reconhecidos")

    return text


# ── Schemas ───────────────────────────────────────────────────────────────────

class ConsultaSIGEFRequest(BaseModel):
    ccir: Optional[str] = None
    sigef_codigo: Optional[str] = None
    estado: Optional[str] = "MA"


class VincularPtamRequest(BaseModel):
    ccir_numero: Optional[str] = None
    sigef_codigo: Optional[str] = None
    denominacao: Optional[str] = None
    property_city: Optional[str] = None
    property_state: Optional[str] = None
    property_area_ha: Optional[float] = None
    sigef_situacao: Optional[str] = None
    sigef_data_certificacao: Optional[str] = None
    sigef_area_ha: Optional[float] = None
    sigef_perimetro_m: Optional[float] = None
    sigef_vertices: Optional[int] = None
    sigef_datum: Optional[str] = None
    modulo_fiscal_ha: Optional[float] = None
    numero_modulos_fiscais: Optional[float] = None
    dados_incra_automaticos: Optional[bool] = True
    dados_incra_data_consulta: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/consultar")
async def consultar_sigef(
    body: ConsultaSIGEFRequest,
    current_user: dict = Depends(get_active_subscriber),
):
    """Consulta dados do imovel rural no SIGEF/INCRA.
    
    Aceita CCIR (15 digitos) ou codigo UUID SIGEF.
    Retorna dados normalizados prontos para preencher o PTAM.
    """
    ccir = (body.ccir or "").strip()
    sigef_codigo = (body.sigef_codigo or "").strip()
    estado = (body.estado or "MA").upper().strip()

    if not ccir and not sigef_codigo:
        raise HTTPException(status_code=400, detail="Informe o CCIR ou o codigo SIGEF.")

    # Valida CCIR se fornecido
    if ccir and not sigef_codigo:
        digits = re.sub(r"\D", "", ccir)
        if len(digits) != 15:
            raise HTTPException(
                status_code=422,
                detail=f"CCIR invalido: '{ccir}'. Deve ter exatamente 15 digitos numericos."
            )

    resultado = await consulta_completa_rural(
        ccir=ccir or None,
        sigef_codigo=sigef_codigo or None,
        estado=estado,
    )

    # Monta resposta normalizada
    sigef = resultado.get("sigef")
    modulo_fiscal = resultado.get("modulo_fiscal_ha")
    n_modulos = resultado.get("numero_modulos_fiscais")
    erros = resultado.get("erros", [])

    if not sigef and erros:
        # Ainda retorna 200 com dados parciais — frontend decide fallback
        return {
            "encontrado": False,
            "erros": erros,
            "modulo_fiscal_ha": modulo_fiscal,
            "fonte": "erro_api",
            "data_consulta": resultado.get("data_consulta"),
        }

    if not sigef:
        return {
            "encontrado": False,
            "erros": ["Imovel nao localizado no SIGEF/INCRA com os dados fornecidos."],
            "modulo_fiscal_ha": modulo_fiscal,
            "fonte": "nao_encontrado",
            "data_consulta": resultado.get("data_consulta"),
        }

    area_ha = sigef.get("area_ha")
    municipio = sigef.get("municipio", "")
    uf = sigef.get("uf", "") or estado

    return {
        "encontrado": True,
        "fonte": resultado.get("fonte"),
        "data_consulta": resultado.get("data_consulta"),
        "erros": erros,
        # Dados SIGEF
        "sigef_codigo": sigef.get("codigo"),
        "sigef_situacao": sigef.get("situacao"),
        "sigef_data_certificacao": sigef.get("data_certificacao"),
        "sigef_area_ha": area_ha,
        "sigef_perimetro_m": sigef.get("perimetro_m"),
        "sigef_vertices": sigef.get("vertices"),
        "sigef_datum": sigef.get("datum", "SIRGAS 2000"),
        # Imovel
        "denominacao": sigef.get("denominacao"),
        "municipio": municipio,
        "uf": uf,
        # Modulos fiscais
        "modulo_fiscal_ha": modulo_fiscal,
        "numero_modulos_fiscais": n_modulos,
        # CCIR formatado
        "ccir_numero": _formatar_ccir(ccir) if ccir else None,
    }


@router.get("/validar-ccir/{ccir}")
async def validar_ccir(
    ccir: str,
    current_user: dict = Depends(get_active_subscriber),
):
    """Valida formato do CCIR (deve ter 15 digitos numericos)."""
    digits = re.sub(r"\D", "", ccir or "")
    valido = len(digits) == 15
    return {
        "ccir": ccir,
        "valido": valido,
        "digits": len(digits),
        "formatado": _formatar_ccir(ccir) if valido else None,
        "mensagem": "CCIR valido" if valido else f"CCIR invalido: {len(digits)} digitos encontrados, esperado 15.",
    }


@router.post("/vincular-ptam/{ptam_id}")
async def vincular_ptam(
    ptam_id: str,
    body: VincularPtamRequest,
    current_user: dict = Depends(get_active_subscriber),
):
    """Atualiza campos rurais de um PTAM com dados do SIGEF/INCRA."""
    db = await get_db()
    ptam = await db["ptams"].find_one({"id": ptam_id, "user_id": current_user["id"]})
    if not ptam:
        raise HTTPException(status_code=404, detail="PTAM nao encontrado.")

    update_fields = {}
    data = body.model_dump(exclude_none=True)

    # Campos mapeados diretamente
    campo_map = {
        "ccir_numero": "ccir_numero",
        "sigef_codigo": "sigef_codigo",
        "denominacao": "denominacao",
        "property_city": "property_city",
        "property_state": "property_state",
        "property_area_ha": "property_area_ha",
        "sigef_situacao": "sigef_situacao",
        "sigef_data_certificacao": "sigef_data_certificacao",
        "sigef_area_ha": "sigef_area_ha",
        "sigef_perimetro_m": "sigef_perimetro_m",
        "sigef_vertices": "sigef_vertices",
        "sigef_datum": "sigef_datum",
        "modulo_fiscal_ha": "modulo_fiscal_ha",
        "numero_modulos_fiscais": "numero_modulos_fiscais",
        "dados_incra_automaticos": "dados_incra_automaticos",
        "dados_incra_data_consulta": "dados_incra_data_consulta",
    }

    for src, dst in campo_map.items():
        if src in data:
            update_fields[dst] = data[src]

    if not update_fields:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar.")

    update_fields["updated_at"] = datetime.utcnow()

    await db["ptams"].update_one(
        {"id": ptam_id},
        {"$set": update_fields}
    )

    campos_atualizados = len(update_fields) - 1  # desconta updated_at
    return {
        "ok": True,
        "ptam_id": ptam_id,
        "campos_atualizados": campos_atualizados,
        "mensagem": f"{campos_atualizados} campos rurais atualizados via SIGEF/INCRA.",
    }


@router.post("/importar-arquivo")
async def importar_arquivo_sigef(
    file: UploadFile = File(...),
    ptam_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_active_subscriber),
):
    """Faz parse de arquivo KML/XML/GML/JSON exportado pelo SIGEF.
    
    Tipos aceitos: .kml, .xml, .gml, .json, .geojson
    Retorna dados normalizados prontos para preencher o PTAM.
    """
    nome = file.filename or ""
    extensoes_validas = (".kml", ".xml", ".gml", ".json", ".geojson")
    if not any(nome.lower().endswith(ext) for ext in extensoes_validas):
        raise HTTPException(
            status_code=415,
            detail=f"Formato nao suportado. Aceitos: KML, XML, GML, JSON, GeoJSON."
        )

    conteudo = await file.read()
    if len(conteudo) > 10 * 1024 * 1024:  # 10 MB max
        raise HTTPException(status_code=413, detail="Arquivo muito grande (max 10 MB).")

    _validate_sigef_file_structure(nome, conteudo)

    resultado = parsear_arquivo_sigef(conteudo, nome)

    if resultado.get("erro"):
        return {
            "encontrado": False,
            "erro": resultado["erro"],
            "arquivo": nome,
        }

    # Calcula modulos fiscais a partir dos dados extraidos
    area_ha = resultado.get("area_ha")
    municipio = resultado.get("municipio", "")
    uf = resultado.get("uf", "MA")
    modulos = calcular_modulos_fiscais(area_ha, municipio, uf) if area_ha else {}

    sigef_situacao = resultado.get("situacao") or "certificado"
    ccir_raw = resultado.get("ccir_raw") or ""
    ccir_fmt = _formatar_ccir(ccir_raw) if ccir_raw else None

    return {
        "encontrado": True,
        "fonte": resultado.get("fonte", "arquivo_sigef"),
        "arquivo": nome,
        "data_consulta": datetime.now().strftime("%d/%m/%Y %H:%M"),
        # Dados extraidos
        "sigef_codigo": resultado.get("codigo"),
        "denominacao": resultado.get("denominacao"),
        "municipio": municipio,
        "uf": uf,
        "sigef_situacao": sigef_situacao,
        "sigef_data_certificacao": resultado.get("data_certificacao"),
        "sigef_area_ha": area_ha,
        "sigef_perimetro_m": resultado.get("perimetro_m"),
        "sigef_vertices": resultado.get("vertices"),
        "sigef_datum": resultado.get("datum", "SIRGAS 2000"),
        "ccir_numero": ccir_fmt,
        # Modulos fiscais calculados
        "modulo_fiscal_ha": modulos.get("modulo_fiscal_ha"),
        "numero_modulos_fiscais": modulos.get("numero_modulos_fiscais"),
        "classificacao_fundiaria": modulos.get("classificacao_fundiaria"),
        "ptam_id": ptam_id,
    }


@router.get("/modulo-fiscal")
async def get_modulo_fiscal(
    municipio: str = Query(..., description="Nome do municipio"),
    uf: str = Query("MA", description="Sigla do estado (UF)"),
    area_ha: Optional[float] = Query(None, description="Area em ha para calcular n de modulos"),
    current_user: dict = Depends(get_active_subscriber),
):
    """Retorna modulo fiscal e classificacao fundiaria para um municipio/UF."""
    if area_ha is not None and area_ha > 0:
        return calcular_modulos_fiscais(area_ha, municipio, uf)
    modulo_ha = buscar_modulo_fiscal(municipio, uf)
    return {
        "municipio": municipio,
        "uf": uf.upper(),
        "modulo_fiscal_ha": modulo_ha,
        "numero_modulos_fiscais": None,
        "classificacao_fundiaria": None,
    }

