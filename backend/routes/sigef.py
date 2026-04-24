# @module routes.sigef — Endpoints de consulta SIGEF/INCRA para laudos rurais
"""Rotas para consulta automatica ao SIGEF (INCRA) e preenchimento de PTAMs rurais.

Credenciais INCRA: FQNS / CFTMA 12-091-853-69
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import re
from datetime import datetime

from dependencies import get_current_user
from db import get_db
from services.sigef_service import (
    consulta_completa_rural,
    buscar_modulo_fiscal,
    _validar_ccir,
    _formatar_ccir,
)

router = APIRouter(prefix="/sigef", tags=["sigef"])


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
    current_user: dict = Depends(get_current_user),
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
    current_user: dict = Depends(get_current_user),
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
    current_user: dict = Depends(get_current_user),
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
