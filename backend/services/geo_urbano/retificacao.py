# @module services.geo_urbano.retificacao — análise comparativa (de → para).
#
# Retificação (art. 213 Lei 6.015/73) é dirigida por COMPARAÇÃO em dois eixos:
#  • cadastral: Matrícula (registro) × BCI (cadastro municipal)
#  • geométrico: mapa atual ("como era") × mapa retificado ("como está")
from __future__ import annotations

import re

from services.geo_urbano import geometria as G


def _norm(v) -> str:
    return re.sub(r"\s+", " ", str(v or "").strip().lower()).replace(".", "")


def _norm_end(v) -> str:
    """Normaliza logradouro (expande abreviações) p/ reduzir falso-divergente."""
    s = _norm(v)
    s = re.sub(r"\br\b", "rua", s)
    s = re.sub(r"\bav\b", "avenida", s)
    s = re.sub(r"\btrav?\b", "travessa", s)
    s = re.sub(r"\brod\b", "rodovia", s)
    return s


def _norm_num(v) -> str:
    return (re.sub(r"\D", "", str(v or "")).lstrip("0")) or "0"


def _area_diverge(a, b, tol=0.5) -> bool:
    try:
        return abs(float(a) - float(b)) > tol
    except (TypeError, ValueError):
        return False


def _diff_cadastral(mat: dict, bci: dict) -> list:
    pm = mat.get("proprietario_registral") or {}
    pb = bci.get("proprietario_cadastral") or {}
    campos = [
        ("area_registral", mat.get("area_m2"), bci.get("area_terreno_m2"), "num"),
        ("endereco", mat.get("endereco"), bci.get("endereco"), "end"),
        ("titularidade", pm.get("nome") or pm.get("doc"), pb.get("nome") or pb.get("doc"), "txt"),
        ("loc_cartografica", mat.get("loc_cartografica"), bci.get("loc_cartografica"), "loc"),
        ("cod_imovel", mat.get("cod_imovel"), bci.get("cod_imovel"), "loc"),
    ]
    out = []
    for campo, vr, vb, kind in campos:
        if vr in (None, "") and vb in (None, ""):
            continue
        if kind == "num":
            div = _area_diverge(vr, vb)
        elif kind == "loc":
            div = bool(vr) and bool(vb) and _norm_num(vr) != _norm_num(vb)
        elif kind == "end":
            div = bool(vr) and bool(vb) and _norm_end(vr) != _norm_end(vb)
        else:
            div = bool(vr) and bool(vb) and _norm(vr) != _norm(vb)
        out.append({"campo": campo, "valor_registro": vr, "valor_bci": vb,
                    "valor_correto": vr, "divergente": div})  # registro é autoritativo
    return out


def _diff_geometrico(projeto: dict) -> dict:
    va = projeto.get("vertices_atual") or []
    vd = projeto.get("vertices") or []
    aa, ad = G.area_m2(va), G.area_m2(vd)
    pa, pd = G.perimetro_m(va), G.perimetro_m(vd)
    conf = []
    for i in range(max(len(va), len(vd))):
        de = va[i].get("confrontante_lado") if i < len(va) else None
        para = vd[i].get("confrontante_lado") if i < len(vd) else None
        lado = ((vd[i].get("de") if i < len(vd) else None) or
                (va[i].get("de") if i < len(va) else None) or f"segmento {i + 1}")
        conf.append({"lado": lado, "de": de, "para": para,
                     "alterado": bool(de or para) and _norm(de) != _norm(para)})
    return {"area_antes_m2": round(aa, 2), "area_depois_m2": round(ad, 2),
            "area_delta_m2": round(ad - aa, 2),
            "perimetro_antes_m": pa, "perimetro_depois_m": pd,
            "perimetro_delta_m": round(pd - pa, 2), "confrontantes_diff": conf}


def analisar(projeto: dict) -> dict:
    tipo = projeto.get("retificacao_tipo") or "mista"
    mat = (projeto.get("matriculas") or [{}])[0]
    bci = (projeto.get("bci") or [{}])[0]
    cadastral = _diff_cadastral(mat, bci) if tipo in ("cadastral", "mista") else []
    geometrico = _diff_geometrico(projeto) if tipo in ("area_perimetro", "mista") else {}
    gerou = (any(d["divergente"] for d in cadastral)
             or (bool(geometrico) and (abs(geometrico.get("area_delta_m2") or 0) > 0.5
                                       or any(c["alterado"] for c in geometrico.get("confrontantes_diff", [])))))
    return {"retificacao_tipo": tipo, "cadastral_diffs": cadastral,
            "geometrico": geometrico, "gerou_alteracao": bool(gerou)}
