# @module services.geo_urbano.validacao_onr — Painel de validação do SIG-RI/ONR.
#
# Provimento CNJ 195/2025 (verificação de polígono fechado, precisão posicional e
# circunscrição da serventia) + ABNT NBR 17047:2022. Cada achado tem código,
# severidade (erro | warning), flag `bloqueante` e mensagem. ERRO impede gerar;
# WARNING bloqueante exige justificativa textual do RT (onr_justificativas) para
# liberar a geração; WARNING comum é informativo.
from __future__ import annotations

import re
from typing import List, Optional

from utils.cpf import limpar_cpf, validar_cpf
from services.geo_urbano import geodesia as GEO

# UF → 2 dígitos iniciais do código IBGE do município
UF_IBGE = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
    "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
    "SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35",
    "PR": "41", "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}
# Território brasileiro (lon_min, lat_min, lon_max, lat_max)
BR_BBOX = (-74.0, -34.0, -28.0, 6.0)

TOL_AREA_MEMORIAL = 0.005    # 0,5% (W-AREA-DIV — bloqueante)
TOL_AREA_MATRICULA = 0.05    # 5%  (W-AREA-MTR)
LIMITE_PRECISAO_URBANA_M = 0.50   # NBR 17047 (classe urbana, default)
DIST_DUP_M = 0.001           # vértices consecutivos coincidentes
DIST_FECHA_M = 0.01          # tolerância de fechamento


def validar_cnpj(cnpj: str) -> bool:
    c = limpar_cpf(cnpj)  # limpar_cpf apenas remove não-dígitos
    if len(c) != 14 or c == c[0] * 14:
        return False

    def _dv(base: str, pesos: List[int]) -> int:
        r = sum(int(d) * p for d, p in zip(base, pesos)) % 11
        return 0 if r < 2 else 11 - r

    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    p2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return _dv(c[:12], p1) == int(c[12]) and _dv(c[:13], p2) == int(c[13])


def doc_valido(doc: str) -> bool:
    """CPF (11) ou CNPJ (14) por dígito verificador."""
    d = limpar_cpf(doc)
    if len(d) == 11:
        return validar_cpf(d)
    if len(d) == 14:
        return validar_cnpj(d)
    return False


def _erro(cod, msg, campo=None):
    return {"codigo": cod, "severidade": "erro", "bloqueante": True, "mensagem": msg, "campo": campo}


def _warn(cod, msg, bloqueante=False, campo=None):
    return {"codigo": cod, "severidade": "warning", "bloqueante": bloqueante, "mensagem": msg, "campo": campo}


def _num(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _proprietarios(projeto: dict):
    return [p for p in (projeto.get("partes") or [])
            if p.get("papel") in ("requerente", "titular_tabular")]


def _area_matriculas(projeto: dict) -> Optional[float]:
    vals = [_num(m.get("area_m2")) for m in (projeto.get("matriculas") or [])]
    vals = [v for v in vals if v]
    return sum(vals) if vals else None


def validar(projeto: dict) -> dict:
    """Executa o painel de validação. Retorna {erros, warnings, area_calculada_m2,
    perimetro_m, fuso, hemisferio, bloqueios_pendentes, pode_gerar}."""
    erros: List[dict] = []
    warnings: List[dict] = []

    pts, fuso, hemis = GEO.pontos_lonlat(projeto.get("vertices") or [])

    # ── Geometria ────────────────────────────────────────────────────────────
    # E-DUP-VERT: vértices consecutivos coincidentes
    for i in range(1, len(pts)):
        if GEO.distancia_m(pts[i - 1], pts[i]) < DIST_DUP_M:
            erros.append(_erro("E-DUP-VERT",
                               f"Vértices consecutivos coincidentes (posições {i} e {i+1})."))
            break
    # E-CRS: fora do território brasileiro
    lon_min, lat_min, lon_max, lat_max = BR_BBOX
    if any(not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max) for (lon, lat) in pts):
        erros.append(_erro("E-CRS", "Há coordenadas fora do território brasileiro — confira o SGR/fuso."))

    ring, _f, _h = GEO.resolver_anel(projeto.get("vertices") or [])
    distintos = max(0, len(ring) - 1)   # anel fechado repete o 1º ponto
    area_m2 = perim_m = 0.0
    if distintos < 3:
        erros.append(_erro("E-VERT-MIN", "A poligonal precisa de ao menos 3 vértices distintos.",
                           campo="vertices"))
    else:
        try:
            from shapely.geometry import Polygon
            poly = Polygon(ring)
            if not poly.is_valid:
                erros.append(_erro("E-SELF-INT", "A poligonal possui auto-interseção (polígono inválido)."))
            elif poly.area == 0:
                erros.append(_erro("E-POLY-OPEN", "A poligonal não delimita área (degenerada/colinear)."))
        except Exception:
            pass
        area_m2, perim_m = GEO.area_perimetro_geodesico(ring)

    # ── Cadastro / partes ────────────────────────────────────────────────────
    # E-CPF: proprietário com CPF/CNPJ inválido
    for p in _proprietarios(projeto):
        doc = p.get("cnpj") or p.get("cpf")
        if doc and not doc_valido(doc):
            nome = p.get("razao_social") or p.get("nome") or "proprietário"
            erros.append(_erro("E-CPF", f"CPF/CNPJ inválido (dígito verificador): {nome}.", campo="partes"))

    # E-IBGE: código IBGE do município (7 dígitos + prefixo da UF)
    ibge = re.sub(r"\D", "", str(projeto.get("codigo_ibge") or ""))
    uf = (projeto.get("uf") or "").strip().upper()
    if not ibge:
        erros.append(_erro("E-IBGE", "Código IBGE do município não informado (7 dígitos).", campo="codigo_ibge"))
    elif len(ibge) != 7:
        erros.append(_erro("E-IBGE", f"Código IBGE deve ter 7 dígitos (recebido: {ibge}).", campo="codigo_ibge"))
    elif uf in UF_IBGE and not ibge.startswith(UF_IBGE[uf]):
        erros.append(_erro("E-IBGE", f"Código IBGE {ibge} não pertence à UF {uf} "
                                     f"(esperado prefixo {UF_IBGE[uf]}).", campo="codigo_ibge"))

    # E-ART: ART/TRT obrigatória
    if not (projeto.get("trt_numero") or "").strip():
        erros.append(_erro("E-ART", "ART/TRT não informada.", campo="trt_numero"))

    # ── Áreas ────────────────────────────────────────────────────────────────
    area_mem = _num(projeto.get("area_declarada_m2"))
    if area_mem and area_m2 and abs(area_m2 - area_mem) / area_mem > TOL_AREA_MEMORIAL:
        warnings.append(_warn(
            "W-AREA-DIV",
            f"Área calculada (geodésica) {area_m2:.2f} m² diverge da declarada {area_mem:.2f} m² "
            f"em mais de 0,5%.", bloqueante=True, campo="area_declarada_m2"))
    area_mat = _area_matriculas(projeto)
    if area_mat and area_m2 and area_mat != area_mem and \
            abs(area_m2 - area_mat) / area_mat > TOL_AREA_MATRICULA:
        warnings.append(_warn(
            "W-AREA-MTR",
            f"Área calculada {area_m2:.2f} m² diverge da soma das matrículas {area_mat:.2f} m² "
            f"em mais de 5% (comum em retificação).", campo="matriculas"))

    # ── Precisão / confrontantes / serventia ─────────────────────────────────
    prec = _num(projeto.get("precisao_posicional_m"))
    if prec and prec > LIMITE_PRECISAO_URBANA_M:
        warnings.append(_warn("W-PREC", f"Precisão posicional declarada ({prec:.3f} m) acima do limite "
                                        f"da classe urbana (NBR 17047).", campo="precisao_posicional_m"))
    n_confront = max(len([v for v in (projeto.get("vertices") or []) if v.get("confrontante_lado")]),
                     len(projeto.get("confrontantes") or []))
    if distintos >= 3 and n_confront < distintos:
        warnings.append(_warn("W-CONFRONT", f"Confrontantes informados ({n_confront}) menor que o número de "
                                            f"lances da poligonal ({distintos})."))
    if not re.sub(r"\D", "", (projeto.get("cartorio") or {}).get("cns") or ""):
        warnings.append(_warn("W-CNS", "CNS da serventia não informado — necessário no upload ao ONR.",
                              campo="cartorio.cns"))

    justificados = {j.get("codigo") for j in (projeto.get("onr_justificativas") or []) if j.get("texto")}
    bloqueios = [w["codigo"] for w in warnings if w["bloqueante"] and w["codigo"] not in justificados]
    return {
        "erros": erros, "warnings": warnings,
        "area_calculada_m2": round(area_m2, 2), "perimetro_m": round(perim_m, 2),
        "fuso": fuso, "hemisferio": hemis,
        "bloqueios_pendentes": bloqueios,
        "pode_gerar": not erros and not bloqueios,
    }
