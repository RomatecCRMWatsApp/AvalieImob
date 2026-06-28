# @module services.geo_urbano.generators.textos — conteúdo dos documentos (texto/dados).
#
# Builders consumidos pelo renderer PDF. O núcleo é a TRANSCRIÇÃO FIEL, matrícula
# por matrícula, das certidões (Requerimento §7.2) e a descrição perimétrica do
# imóvel resultante a partir dos vértices do mapa (Memorial §7.3).
from __future__ import annotations

import re
from typing import List, Optional


def cim_completo(projeto: dict) -> str:
    """CIM com o dígito de controle: '01.10.041.0001.00001-111'. O controle (3 díg.,
    informado pela prefeitura/BCI) é zero-padded; sem controle, retorna só a base."""
    base = (projeto.get("cmi_resultante") or "").strip()
    ctrl = re.sub(r"\D", "", str(projeto.get("cmi_controle") or ""))
    return f"{base}-{ctrl.zfill(3)[-3:]}" if (base and ctrl) else base

_LADO_LABEL = {
    "frente": "FRENTE", "lateral_direita": "LATERAL DIREITA",
    "lateral_esquerda": "LATERAL ESQUERDA", "fundo": "FUNDOS", "fundos": "FUNDOS",
}
_ORDEM_LADO = ["frente", "lateral_direita", "lateral_esquerda", "fundo", "fundos"]


def _n_br(v: Optional[float], casas: int = 2) -> str:
    if v is None:
        return ""
    s = f"{float(v):,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def m2(v) -> str:
    return f"{_n_br(v)} m²" if v is not None else "—"


def metros(v) -> str:
    return f"{_n_br(v)} m" if v is not None else "—"


# ──────────────────────────────────────────────────────────────────────────────
# Qualificação das partes
# ──────────────────────────────────────────────────────────────────────────────
def _juntar(partes: List[str]) -> str:
    return ", ".join(p for p in partes if p and str(p).strip())


def qualificar_parte(p: dict) -> str:
    if (p.get("tipo_pessoa") or "juridica") == "juridica":
        seg = [p.get("razao_social") or "",
               "pessoa jurídica de direito privado"]
        if p.get("cnpj"):
            seg.append(f"inscrita no CNPJ sob o nº {p['cnpj']}")
        if p.get("nire"):
            seg.append(f"NIRE {p['nire']}")
        if p.get("junta"):
            seg.append(f"registro na {p['junta']}")
        if p.get("sede"):
            seg.append(f"com sede na {p['sede']}")
        return _juntar(seg)
    seg = [p.get("nome") or ""]
    seg += [x for x in (p.get("nacionalidade"), p.get("estado_civil"), p.get("profissao")) if x]
    if p.get("rg"):
        seg.append(f"portador do RG nº {p['rg']}")
    if p.get("cpf"):
        seg.append(f"inscrito no CPF sob o nº {p['cpf']}")
    if p.get("cnh"):
        seg.append(f"CNH nº {p['cnh']}")
    if p.get("filiacao"):
        seg.append(p["filiacao"])
    if p.get("endereco"):
        seg.append(f"residente e domiciliado na {p['endereco']}")
    return _juntar(seg)


def bloco_requerentes(projeto: dict) -> str:
    """Qualificação completa dos requerentes (PJ + representante; ou PF + cônjuge)."""
    partes = projeto.get("partes") or []
    requerentes = [p for p in partes if p.get("papel") in ("requerente", None)]
    reps = [p for p in partes if p.get("papel") in ("representante", "socio")]
    blocos = []
    for r in requerentes:
        txt = qualificar_parte(r)
        if r.get("tipo_pessoa") == "juridica" and reps:
            txt += ", neste ato representada por " + "; ".join(qualificar_parte(x) for x in reps)
        blocos.append(txt)
    if not requerentes and reps:
        blocos = [qualificar_parte(x) for x in reps]
    return ";\n\n".join(blocos) + (", " if blocos else "")


# ──────────────────────────────────────────────────────────────────────────────
# Transcrição item por item das matrículas (FIEL à certidão) — §7.2
# ──────────────────────────────────────────────────────────────────────────────
def _confr_por_lado(mat: dict) -> dict:
    out = {}
    for c in mat.get("confrontacoes") or []:
        out.setdefault((c.get("lado") or "").lower(), c)
    return out


def transcricao_matricula(mat: dict, municipio: str, uf: str) -> str:
    porlado = _confr_por_lado(mat)
    cab = [f"Matrícula nº {mat.get('matricula') or '—'}"]
    if mat.get("livro"):
        cab.append(f"Livro {mat['livro']}")
    if mat.get("folhas"):
        cab.append(f"fls. {mat['folhas']}")
    cab.append(f"{mat.get('natureza') or 'UM TERRENO'}")
    linha = ", ".join(cab) + f", nesta cidade de {municipio}/{uf}"
    if mat.get("endereco"):
        linha += f", situado na {mat['endereco']}"
    cons = []
    if mat.get("quadra"):
        cons.append(f"Quadra nº {mat['quadra']}")
    if mat.get("lote_origem"):
        cons.append(f"Lote {mat['lote_origem']}")
    if mat.get("loteamento"):
        cons.append(mat["loteamento"])
    if cons:
        linha += ", constituído da " + ", ".join(cons)
    if mat.get("area_m2") is not None:
        linha += f". Área de {m2(mat['area_m2'])}"
    cmi = " / ".join(x for x in (mat.get("cod_imovel"), mat.get("loc_cartografica")) if x)
    if cmi:
        linha += f". CMI/Cód.: {cmi}"
    # confrontações fiéis
    medidas = []
    for lado in _ORDEM_LADO:
        c = porlado.get(lado)
        if c:
            medidas.append(f"{_LADO_LABEL.get(lado, lado.upper())}: "
                           f"{metros(c.get('medida_m'))} com {c.get('confrontante') or '—'}")
    if medidas:
        linha += ". Medindo de " + "; ".join(medidas)
    if mat.get("registro_anterior"):
        linha += f". Registro anterior: {mat['registro_anterior']}"
    return linha + "."


def lista_transcricoes(projeto: dict) -> List[str]:
    municipio = projeto.get("municipio") or ""
    uf = projeto.get("uf") or ""
    mats = sorted(projeto.get("matriculas") or [], key=lambda m: m.get("ordem", 0))
    return [f"{i+1}- {transcricao_matricula(m, municipio, uf)}" for i, m in enumerate(mats)]


# ──────────────────────────────────────────────────────────────────────────────
# Descrição perimétrica do imóvel resultante (a partir dos vértices) — §7.3/§7.2
# ──────────────────────────────────────────────────────────────────────────────
def descricao_perimetrica(projeto: dict) -> str:
    verts = sorted(projeto.get("vertices") or [], key=lambda v: v.get("ordem", 0))
    if not verts:
        return ""
    partes = [f"Inicia-se a descrição no vértice {verts[0].get('de')}"]
    for v in verts:
        partes.append(
            f"deste, segue com azimute {v.get('azimute') or '—'} e distância de "
            f"{metros(v.get('distancia_m'))} até o vértice {v.get('para') or '—'}, "
            f"confrontando neste segmento com {v.get('confrontante_lado') or '—'}"
        )
    return "; ".join(partes) + ", fechando o polígono."


_EXTENSO = {1: "uma", 2: "duas", 3: "três", 4: "quatro", 5: "cinco", 6: "seis",
           7: "sete", 8: "oito", 9: "nove", 10: "dez"}

# Título e ação do requerimento por tipo de serviço.
TITULO_REQUERIMENTO = {
    "remembramento": "REQUERIMENTO DE REMEMBRAMENTO", "desdobro": "REQUERIMENTO DE DESDOBRO",
    "retificacao": "REQUERIMENTO DE RETIFICAÇÃO", "reurb": "REQUERIMENTO DE REURB",
    "usucapiao": "REQUERIMENTO DE USUCAPIÃO",
}
ACAO_REQUERIMENTO = {
    "remembramento": "o REMEMBRAMENTO (unificação) dos imóveis", "desdobro": "o DESDOBRO do imóvel",
    "retificacao": "a RETIFICAÇÃO do imóvel", "reurb": "a REGULARIZAÇÃO FUNDIÁRIA (REURB) do imóvel",
    "usucapiao": "o RECONHECIMENTO DE USUCAPIÃO do imóvel",
}


def descricao_lotes_resultantes(projeto: dict) -> str:
    """Desdobro: descreve os N lotes resultantes (denominação/área/confrontações)."""
    lotes = sorted(projeto.get("lotes_resultantes") or [], key=lambda l: l.get("ordem", 0))
    n = len(lotes)
    if not n:
        return ""
    cab = f"ficando o imóvel desdobrado em {n} ({_EXTENSO.get(n, str(n))}) lotes, a saber:"
    partes = [cab]
    for l in lotes:
        seg = f"Lote nº {l.get('denominacao') or l.get('ordem')}"
        if projeto.get("quadra"):
            seg += f" da Quadra nº {projeto['quadra']}"
        if projeto.get("loteamento"):
            seg += f", {projeto['loteamento']}"
        if l.get("area_declarada_m2") is not None:
            seg += f", com área de {m2(l['area_declarada_m2'])}"
        porlado = {(c.get("lado") or "").lower(): c for c in (l.get("confrontacoes") or [])}
        medidas = []
        for lado in _ORDEM_LADO:
            c = porlado.get(lado)
            if c:
                medidas.append(f"{_LADO_LABEL.get(lado, lado.upper())}: "
                               f"{metros(c.get('medida_m'))} com {c.get('confrontante') or '—'}")
        if medidas:
            seg += ". Medindo de " + "; ".join(medidas)
        partes.append(seg + ".")
    via = projeto.get("area_via_doacao_m2")
    if via:
        partes.append(f"Destina-se a área de {m2(via)} à abertura de via pública / doação ao Município.")
    return "\n\n".join(partes)


def relacao_retificacao(projeto: dict) -> str:
    """Retificação: relação 'de → para' (cadastral + geométrico) do `retificacao_analise`."""
    an = projeto.get("retificacao_analise") or {}
    linhas = []
    for d in an.get("cadastral_diffs") or []:
        if d.get("divergente"):
            linhas.append(f'onde consta "{d.get("valor_registro")}", retifique-se para '
                          f'"{d.get("valor_correto")}" (campo {d.get("campo")});')
    g = an.get("geometrico") or {}
    if g.get("area_antes_m2") is not None and g.get("area_depois_m2") is not None:
        linhas.append(f"a área de {m2(g.get('area_antes_m2'))} passa a {m2(g.get('area_depois_m2'))} "
                      f"(Δ {m2(g.get('area_delta_m2'))});")
    if g.get("perimetro_antes_m") is not None and g.get("perimetro_depois_m") is not None:
        linhas.append(f"o perímetro de {metros(g.get('perimetro_antes_m'))} passa a "
                      f"{metros(g.get('perimetro_depois_m'))};")
    for c in g.get("confrontantes_diff") or []:
        if c.get("alterado"):
            linhas.append(f'a confrontação do lado {c.get("lado")} passa de "{c.get("de")}" '
                          f'para "{c.get("para")}";')
    if not linhas:
        return "Não foram identificadas divergências a retificar no presente requerimento."
    return "Procede-se às seguintes retificações: " + " ".join(linhas)


# Ação por tipo de serviço (usada no Ofício de aprovação ao Cartório).
ACAO_SERVICO = {
    "remembramento": "o remembramento (unificação) dos lotes",
    "desdobro": "o desdobro (fracionamento) do imóvel",
    "retificacao": "a retificação de área/registro do imóvel",
    "reurb": "a regularização fundiária urbana (REURB) do imóvel",
    "usucapiao": "o reconhecimento extrajudicial de usucapião do imóvel",
}


def lista_matriculas_str(projeto: dict) -> str:
    mats = sorted(projeto.get("matriculas") or [], key=lambda m: m.get("ordem", 0))
    nums = [m.get("matricula") for m in mats if m.get("matricula")]
    return ", ".join(nums)


def descricao_resultante(projeto: dict) -> str:
    lotes = sorted(projeto.get("matriculas") or [], key=lambda m: m.get("ordem", 0))
    nums = [m.get("lote_origem") for m in lotes if m.get("lote_origem")]
    lista = ", ".join(nums[:-1]) + (" e " + nums[-1] if len(nums) > 1 else (nums[0] if nums else ""))
    seg = [f"Um TERRENO urbano resultante do remembramento dos Lotes {lista}"]
    if projeto.get("lote_resultante"):
        seg.append(f"constituindo o Lote nº {projeto['lote_resultante']}")
    if projeto.get("quadra"):
        seg.append(f"da Quadra nº {projeto['quadra']}")
    if projeto.get("loteamento"):
        seg.append(projeto["loteamento"])
    txt = ", ".join(seg)
    if projeto.get("area_declarada_m2") is not None:
        txt += f", com área total de {m2(projeto['area_declarada_m2'])}"
    if projeto.get("perimetro_m") is not None:
        txt += f" e perímetro de {metros(projeto['perimetro_m'])}"
    desc = descricao_perimetrica(projeto)
    if desc:
        txt += ". " + desc
    return txt
