# @module services.geo_urbano.orientacao — orientação dos lados do lote urbano.
#
# Classifica cada segmento da poligonal em FRENTE / LATERAL DIREITA / LATERAL
# ESQUERDA / FUNDO, para rotular a Descrição Perimétrica do Memorial urbano.
#
# Convenção brasileira: a RUA é a FRENTE; direita/esquerda são as de um
# observador DENTRO do lote OLHANDO PARA A RUA (visão interna → externa).
#
# Coordenadas de agrimensura: N = Northing (y, cresce p/ o norte/cima),
# E = Easting (x, cresce p/ leste/direita). Cada linha do quadro de vértices é
# um SEGMENTO `de`→`para`; após `alinhar_coords_aos_vertices`, coord_n/coord_e é
# a posição do vértice `de` — logo os pontos `de` (em `ordem`) formam o polígono.
#
# NÃO inventa a frente: se nenhum confrontante for logradouro e não houver
# `frente_idx`/override manual, devolve `frente_indefinida=True` e nenhum rótulo
# — a UI pede ao usuário para marcar a testada (lado da rua).
from __future__ import annotations

import math
import re
from typing import List, Optional, Sequence

# Chaves de lado — as MESMAS já usadas no módulo (desdobro/retificação).
LADO_FRENTE = "frente"
LADO_DIREITA = "lateral_direita"
LADO_ESQUERDA = "lateral_esquerda"
LADO_FUNDO = "fundo"

# Logradouro (via pública) no texto do confrontante → indica a FRENTE.
_RX_VIA = re.compile(
    r"\b("
    r"rua|r\.|avenida|av\.?|rodovia|rod\.?|estrada|estr\.?|travessa|tv\.?|"
    r"alameda|al\.?|viela|via|passagem|praç[ae]a?|praca|logradouro|via\s+p[úu]blica|"
    r"br[-\s]?\d|km|servid[ãa]o"
    r")\b",
    re.IGNORECASE,
)


def _pt(v: dict):
    """Ponto (E, N) do vértice `de`; None se faltar coordenada."""
    e, n = v.get("coord_e"), v.get("coord_n")
    if e is None or n is None:
        return None
    try:
        return (float(e), float(n))
    except (TypeError, ValueError):
        return None


def _centroide(pts: Sequence[tuple]) -> tuple:
    """Centroide do polígono (fórmula da área/shoelace); cai p/ média simples
    quando degenerado."""
    n = len(pts)
    A = cx = cy = 0.0
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        A += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    A *= 0.5
    if abs(A) < 1e-9:
        return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)
    return (cx / (6 * A), cy / (6 * A))


def _lado_manual(v: dict) -> Optional[str]:
    """Override manual EXPLÍCITO do lado (quadro editável), normalizado às chaves
    canônicas. Só `lado_manual` conta — o campo `lado` é o valor CALCULADO e não
    deve se auto-fixar (senão nunca reorienta ao editar o desenho)."""
    val = (v.get("lado_manual") or "").strip().lower()
    aliases = {
        "frente": LADO_FRENTE, "testada": LADO_FRENTE,
        "lateral_direita": LADO_DIREITA, "lateral direita": LADO_DIREITA,
        "direita": LADO_DIREITA, "lado_direito": LADO_DIREITA, "lado direito": LADO_DIREITA,
        "lateral_esquerda": LADO_ESQUERDA, "lateral esquerda": LADO_ESQUERDA,
        "esquerda": LADO_ESQUERDA, "lado_esquerdo": LADO_ESQUERDA, "lado esquerdo": LADO_ESQUERDA,
        "fundo": LADO_FUNDO, "fundos": LADO_FUNDO,
    }
    return aliases.get(val)


def classificar_lados(
    vertices: Sequence[dict],
    frente_idx: Optional[int] = None,
) -> dict:
    """Classifica cada segmento (na ordem de `ordem`) em frente/laterais/fundo.

    Retorna {'lados': [chave|None, ...], 'frente_indefinida': bool}. O tamanho de
    'lados' == nº de vértices ordenados. Prioridade da FRENTE:
      override manual (lado_manual=='frente') > frente_idx > confrontante logradouro.
    """
    verts = sorted(list(vertices or []), key=lambda v: v.get("ordem", 0))
    n = len(verts)
    lados: List[Optional[str]] = [None] * n
    if n == 0:
        return {"lados": lados, "frente_indefinida": True}

    # Overrides manuais entram primeiro (têm prioridade sobre o cálculo).
    manuais = {i: _lado_manual(v) for i, v in enumerate(verts)}
    for i, m in manuais.items():
        if m:
            lados[i] = m

    pts = [_pt(v) for v in verts]
    tem_geo = n >= 3 and all(p is not None for p in pts)

    # Índice(s) da FRENTE.
    frentes = [i for i, m in manuais.items() if m == LADO_FRENTE]
    if not frentes and frente_idx is not None and 0 <= frente_idx < n:
        frentes = [frente_idx]
        lados[frente_idx] = LADO_FRENTE
    if not frentes:
        auto = [i for i, v in enumerate(verts)
                if _RX_VIA.search(v.get("confrontante_lado") or "") and not manuais.get(i)]
        for i in auto:
            lados[i] = LADO_FRENTE
        frentes = auto

    if not frentes:
        # Sem frente identificável → não inventa; devolve só os overrides manuais.
        return {"lados": lados, "frente_indefinida": True}

    if not tem_geo:
        # Frente conhecida, mas sem coordenadas p/ derivar fundo/laterais.
        return {"lados": lados, "frente_indefinida": False}

    mids = [((pts[i][0] + pts[(i + 1) % n][0]) / 2,
             (pts[i][1] + pts[(i + 1) % n][1]) / 2) for i in range(n)]
    cx, cy = _centroide(pts)

    # Vetor OLHAR: do centroide → ponto médio da frente (aponta para a rua).
    fmx = sum(mids[i][0] for i in frentes) / len(frentes)
    fmy = sum(mids[i][1] for i in frentes) / len(frentes)
    ox, oy = fmx - cx, fmy - cy
    norm = math.hypot(ox, oy) or 1.0
    ox, oy = ox / norm, oy / norm

    # Segmentos ainda sem lado (não-frente e sem override).
    restantes = [i for i in range(n) if lados[i] is None]

    # FUNDO = o mais oposto ao olhar (menor projeção sobre o olhar).
    if restantes:
        def _proj(i: int) -> float:
            wx, wy = mids[i][0] - cx, mids[i][1] - cy
            return wx * ox + wy * oy
        fundo_i = min(restantes, key=_proj)
        lados[fundo_i] = LADO_FUNDO
        restantes.remove(fundo_i)

    # LATERAIS pelo sinal do produto vetorial cross(olhar, w) — E=x, N=y.
    for i in restantes:
        wx, wy = mids[i][0] - cx, mids[i][1] - cy
        cross = ox * wy - oy * wx
        lados[i] = LADO_ESQUERDA if cross > 0 else LADO_DIREITA

    return {"lados": lados, "frente_indefinida": False}


def aplicar_lados(projeto: dict) -> dict:
    """Roda a classificação e ESCREVE `lado` em cada vértice (in-place, na ordem),
    respeitando `frente_idx` do projeto. Retorna {'frente_indefinida', 'lados'}."""
    verts = sorted(projeto.get("vertices") or [], key=lambda v: v.get("ordem", 0))
    cls = classificar_lados(verts, frente_idx=projeto.get("frente_idx"))
    for v, lado in zip(verts, cls["lados"]):
        v["lado"] = lado
    return cls
