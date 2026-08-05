# @module services.geo_urbano.georref_urbano — Fase 6 (Georref. de lote urbano).
#
# Serviço de CAMPO PURO: o lote urbano já existe e é regular — não há ato
# registral de alteração de perímetro. O cliente (banco financiador, proprietário
# ou advogado) quer saber ONDE o lote está e em QUE SITUAÇÃO está na quadra.
#
# Núcleo (tudo função PURA, testável sem I/O):
#   • catálogo de finalidades / peças / presets / memoriais / uploads
#   • composição do dossiê montada pelo usuário (matriz de peças + presets)
#   • validação (bloqueios + avisos §13 — nada obrigatório exceto mapa/coords +
#     memorial + ART/TRT; o resto é aviso informativo, nunca bloqueia)
#   • import de coordenadas (CSV/TXT/KML/KMZ → quadro de vértices)
#
# NÃO usa `from __future__ import annotations` (mantém compat com o resto do módulo).
import io
import re
import zipfile
from typing import List, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# Finalidade (§2) — alimenta o subtítulo da capa e o cabeçalho das peças.
# ──────────────────────────────────────────────────────────────────────────────
FINALIDADES = [
    ("financiamento_bancario", "Financiamento bancário"),
    ("averbacao_construcao", "Averbação de construção"),
    ("regularizacao_municipal", "Regularização municipal"),
    ("processo_judicial", "Processo judicial"),
    ("licenciamento_obra", "Licenciamento de obra"),
    ("uso_particular", "Uso particular"),
    ("outra", "Outra"),
]
# Texto do "...para fins de {X}" (subtítulo da capa / cabeçalho).
_FINALIDADE_TEXTO = {
    "financiamento_bancario": "financiamento bancário",
    "averbacao_construcao": "averbação de construção",
    "regularizacao_municipal": "regularização municipal",
    "processo_judicial": "instrução de processo judicial",
    "licenciamento_obra": "licenciamento de obra",
    "uso_particular": "uso particular",
    "outra": "",
}
INSTITUICOES = [
    "CAIXA ECONÔMICA FEDERAL", "BANCO DO BRASIL", "BRADESCO", "ITAÚ UNIBANCO",
    "SANTANDER", "SICOOB", "SICREDI", "BANCO DA AMAZÔNIA", "OUTRA",
]

# ──────────────────────────────────────────────────────────────────────────────
# Peças do dossiê (§4.1) — ordem canônica (é a ordem no PDF; arrastável no front,
# persistida em composicao.ordem).
# ──────────────────────────────────────────────────────────────────────────────
PECAS = [
    "capa", "sumario", "apresentacao", "imagem_localizacao", "mapa_lote",
    "quadro_vertices", "memorial_perimetrico", "memorial_situacao",
    "memorial_sucinto", "memorial_area_construida", "planta_quadra",
    "relatorio_fotografico", "art_trt", "matricula_anexa", "docs_proprietario",
    "anexos_diversos",
]
PECA_LABEL = {
    "capa": "Capa",
    "sumario": "Sumário",
    "apresentacao": "Apresentação",
    "imagem_localizacao": "Imagem de Localização",
    "mapa_lote": "Mapa do Lote (planta com coordenadas)",
    "quadro_vertices": "Quadro de Vértices",
    "memorial_perimetrico": "Memorial Descritivo Perimétrico (MD-PER)",
    "memorial_situacao": "Memorial de Localização e Situação (MD-SIT)",
    "memorial_sucinto": "Descrição Sucinta (MD-SUC)",
    "memorial_area_construida": "Memorial de Área Construída (MD-CON)",
    "planta_quadra": "Planta de Quadra",
    "relatorio_fotografico": "Relatório Fotográfico",
    "art_trt": "ART / TRT",
    "matricula_anexa": "Matrícula (anexo)",
    "docs_proprietario": "Documentos do Proprietário",
    "anexos_diversos": "Anexos Diversos",
}
# peça de memorial ↔ código do memorial (multi-seleção §6)
PECA_MEMORIAL = {
    "memorial_perimetrico": "MD-PER",
    "memorial_situacao": "MD-SIT",
    "memorial_sucinto": "MD-SUC",
    "memorial_area_construida": "MD-CON",
}

# Catálogo de memoriais (§6) — multi-seleção (mínimo 1).
MEMORIAIS = [
    {"codigo": "MD-PER", "nome": "Memorial Descritivo Perimétrico", "peca": "memorial_perimetrico",
     "descricao": "Descrição vértice a vértice: azimutes, distâncias, confrontantes por segmento, "
                  "quadro de áreas e perímetro (SIRGAS 2000/UTM, NBR 13133)."},
    {"codigo": "MD-SIT", "nome": "Memorial de Localização e Situação", "peca": "memorial_situacao",
     "descricao": "Descrição cartorial: quadra, loteamento, formato do lote, distância até a "
                  "esquina, confrontantes da quadra, logradouro de frente."},
    {"codigo": "MD-SUC", "nome": "Descrição Sucinta (resumo técnico)", "peca": "memorial_sucinto",
     "descricao": "1 página: identificação, endereço, área, perímetro, coordenada de amarração, "
                  "finalidade — formato exigido por correspondentes bancários."},
    {"codigo": "MD-CON", "nome": "Memorial de Área Construída", "peca": "memorial_area_construida",
     "descricao": "Quadro de áreas edificadas por pavimento/bloco, área total construída, "
                  "taxa de ocupação e coeficiente de aproveitamento (só com benfeitoria)."},
]

# Presets (§4.2). COMPLETO é resolvido dinamicamente (todas as peças habilitadas).
_PRESET_BANCO = {
    "capa", "apresentacao", "imagem_localizacao", "mapa_lote", "quadro_vertices",
    "memorial_perimetrico", "memorial_situacao", "art_trt",
}
_PRESET_SIMPLIFICADO = {"mapa_lote", "memorial_perimetrico", "art_trt"}
PRESETS = ["COMPLETO", "BANCO", "SIMPLIFICADO", "PERSONALIZADO"]

# Definições da capa (§7.2) — combobox editável; default derivado da finalidade.
DEFINICOES_CAPA = [
    "Para fins de localização e situação",
    "Para fins de financiamento bancário — localização e situação",
    "Para fins de averbação de construção",
    "Para fins de regularização municipal",
    "Para instrução de processo judicial",
    "Planta de quadra e localização do lote",
]
_DEFINICAO_POR_FINALIDADE = {
    "financiamento_bancario": "Para fins de financiamento bancário — localização e situação",
    "averbacao_construcao": "Para fins de averbação de construção",
    "regularizacao_municipal": "Para fins de regularização municipal",
    "processo_judicial": "Para instrução de processo judicial",
    "licenciamento_obra": "Para fins de licenciamento de obra",
    "uso_particular": "Para fins de localização e situação",
    "outra": "Para fins de localização e situação",
}

# Tipos de upload (§3) — quase tudo OPCIONAL (só mapa_coordenadas é obrigatório
# p/ gerar). {chave: (rótulo, obrigatorio, multiplo)}.
TIPOS_UPLOAD = [
    ("mapa_coordenadas", "Mapa/planta do lote com coordenadas", True),
    ("memorial_coordenadas", "Memorial Descritivo de Coordenadas (extrair vértices)", False),
    ("memorial_situacao", "Memorial de Localização e Situação (extrair quadra)", False),
    ("imagem_localizacao", "Imagem de localização (satélite/aérea)", False),
    ("foto_imovel", "Foto do imóvel/fachada", False),
    ("planta_quadra", "Planta de quadra", False),
    ("matricula_imovel", "Certidão/matrícula do imóvel", False),
    ("doc_proprietario_pf", "Documento do proprietário — PF (CPF, RG ou CNH)", False),
    ("doc_proprietario_pj", "Documento do proprietário — PJ (contrato social ou cartão CNPJ)", False),
    ("art_trt_pdf", "ART/TRT emitida", False),
    ("art_trt_boleto", "Boleto/comprovante da ART/TRT", False),
    ("iptu_bci", "BCI / IPTU / CND (facultativo)", False),
    ("outros", "Outros documentos", False),
]
# tipos de upload NOVOS deste serviço (os que ainda não existem em _TIPOS_UPLOAD
# do routes; foto_imovel/art_trt_boleto já existem no módulo).
UPLOADS_NOVOS = {
    "mapa_coordenadas", "memorial_coordenadas", "memorial_situacao",
    "imagem_localizacao", "planta_quadra", "matricula_imovel",
    "doc_proprietario_pf", "doc_proprietario_pj", "art_trt_pdf", "iptu_bci", "outros",
}


# ──────────────────────────────────────────────────────────────────────────────
# Composição do dossiê
# ──────────────────────────────────────────────────────────────────────────────
def definicao_capa_default(finalidade: Optional[str]) -> str:
    return _DEFINICAO_POR_FINALIDADE.get(finalidade or "", DEFINICOES_CAPA[0])


def finalidade_texto(projeto: dict) -> str:
    """Texto do subtítulo da capa: '...para fins de {X}[ junto à {instituição}]'."""
    fin = projeto.get("finalidade")
    if fin == "outra":
        return (projeto.get("finalidade_livre") or "").strip()
    base = _FINALIDADE_TEXTO.get(fin or "", "")
    inst = (projeto.get("instituicao_financeira") or "").strip()
    if fin == "financiamento_bancario" and inst and inst != "OUTRA":
        base = f"{base} junto à {inst}"
    return base


def preset_pecas(preset: str) -> dict:
    """{chave: bool} de um preset. COMPLETO = todas ligadas (a habilitação por
    insumo é aplicada depois em resolver_composicao)."""
    preset = (preset or "").upper()
    if preset == "BANCO":
        ligadas = _PRESET_BANCO
    elif preset == "SIMPLIFICADO":
        ligadas = _PRESET_SIMPLIFICADO
    else:  # COMPLETO / PERSONALIZADO (base = tudo)
        ligadas = set(PECAS)
    return {p: (p in ligadas) for p in PECAS}


def composicao_default(finalidade: Optional[str]) -> dict:
    """Composição inicial. Financiamento bancário → preset BANCO (§2)."""
    preset = "BANCO" if finalidade == "financiamento_bancario" else "COMPLETO"
    return {
        "preset": preset,
        "pecas": preset_pecas(preset),
        "ordem": list(PECAS),
        "definicao_capa": definicao_capa_default(finalidade),
    }


def _uploads(projeto: dict, tipo: str) -> list:
    return (projeto.get("uploads") or {}).get(tipo) or []


def _memoriais(projeto: dict) -> set:
    return set(projeto.get("memoriais_selecionados") or [])


def _insumo_status(projeto: dict, peca: str) -> Tuple[bool, Optional[str]]:
    """(habilitada, motivo_se_bloqueada). Peça sem insumo → desabilitada com tooltip."""
    verts = [v for v in (projeto.get("vertices") or [])]
    tem_poligono = len(verts) >= 3
    if peca in ("capa", "sumario", "apresentacao", "art_trt"):
        return True, None  # sempre disponíveis (art_trt pode gerar placeholder)
    if peca == "imagem_localizacao":
        return (bool(_uploads(projeto, "imagem_localizacao")),
                "envie a imagem de localização para habilitar")
    if peca == "mapa_lote":
        ok = tem_poligono or bool(_uploads(projeto, "mapa_coordenadas"))
        return ok, "importe coordenadas ou envie o mapa/planta para habilitar"
    if peca == "quadro_vertices":
        return tem_poligono, "importe ao menos 3 vértices para habilitar"
    if peca in PECA_MEMORIAL:
        cod = PECA_MEMORIAL[peca]
        sel = cod in _memoriais(projeto)
        if peca == "memorial_area_construida":
            ok = sel and bool(projeto.get("possui_benfeitoria"))
            return ok, "selecione MD-CON e marque 'possui benfeitoria'"
        return sel, f"selecione o memorial {cod} para habilitar"
    if peca == "planta_quadra":
        qd = projeto.get("quadra_dados") or {}
        ok = (bool(_uploads(projeto, "planta_quadra"))
              or bool(qd.get("lotes"))
              or qd.get("modo_planta") == "gerada")
        return ok, "anexe a planta de quadra ou informe os lotes vizinhos"
    if peca == "relatorio_fotografico":
        return bool(_uploads(projeto, "foto_imovel")), "envie fotos do imóvel para habilitar"
    if peca == "matricula_anexa":
        return bool(_uploads(projeto, "matricula_imovel")), "anexe a certidão/matrícula"
    if peca == "docs_proprietario":
        ok = bool(_uploads(projeto, "doc_proprietario_pf") or _uploads(projeto, "doc_proprietario_pj"))
        return ok, "anexe os documentos do proprietário"
    if peca == "anexos_diversos":
        return bool(_uploads(projeto, "outros")), "envie 'outros documentos' para habilitar"
    return True, None


_PAGINAS_FIXAS = {  # estimativa grosseira por peça
    "capa": 1, "sumario": 1, "apresentacao": 1, "imagem_localizacao": 1,
    "mapa_lote": 1, "quadro_vertices": 1, "memorial_perimetrico": 2,
    "memorial_situacao": 1, "memorial_sucinto": 1, "memorial_area_construida": 1,
    "planta_quadra": 1, "art_trt": 2,
}


def _paginas_peca(projeto: dict, peca: str) -> int:
    if peca in _PAGINAS_FIXAS:
        return _PAGINAS_FIXAS[peca]
    if peca == "relatorio_fotografico":
        return max(1, (len(_uploads(projeto, "foto_imovel")) + 1) // 2)
    if peca == "matricula_anexa":
        return len(_uploads(projeto, "matricula_imovel")) or 1
    if peca == "docs_proprietario":
        return (len(_uploads(projeto, "doc_proprietario_pf"))
                + len(_uploads(projeto, "doc_proprietario_pj"))) or 1
    if peca == "anexos_diversos":
        return len(_uploads(projeto, "outros")) or 1
    return 1


def resolver_composicao(projeto: dict) -> dict:
    """Resolve a composição: por peça {ligada, habilitada, motivo}, ordem efetiva,
    estimativa de páginas e memoriais selecionados. Usado pelo preview do front
    (peças desabilitadas com tooltip; contagem de páginas)."""
    comp = projeto.get("composicao") or composicao_default(projeto.get("finalidade"))
    ligadas = comp.get("pecas") or {}
    ordem = [p for p in (comp.get("ordem") or PECAS) if p in PECA_LABEL]
    ordem += [p for p in PECAS if p not in ordem]  # garante todas presentes
    itens, paginas = [], 0
    for p in ordem:
        hab, motivo = _insumo_status(projeto, p)
        lig = bool(ligadas.get(p, True))
        no_pdf = lig and hab
        itens.append({
            "chave": p, "label": PECA_LABEL[p], "ligada": lig,
            "habilitada": hab, "motivo": None if hab else motivo, "no_pdf": no_pdf,
        })
        if no_pdf:
            paginas += _paginas_peca(projeto, p)
    return {
        "preset": comp.get("preset", "PERSONALIZADO"),
        "definicao_capa": comp.get("definicao_capa") or definicao_capa_default(projeto.get("finalidade")),
        "pecas": itens,
        "ordem": ordem,
        "paginas_estimadas": paginas,
        "memoriais_selecionados": sorted(_memoriais(projeto)),
    }


def pecas_no_dossie(projeto: dict) -> List[str]:
    """Ordem das peças que EFETIVAMENTE entram no PDF (ligadas + habilitadas)."""
    res = resolver_composicao(projeto)
    return [i["chave"] for i in res["pecas"] if i["no_pdf"]]


# ──────────────────────────────────────────────────────────────────────────────
# Validação (§13) — nada obrigatório exceto mapa/coords + memorial + ART/TRT.
# Bloqueios impedem gerar; avisos só informam (aparecem no painel e no LEIAME).
# ──────────────────────────────────────────────────────────────────────────────
def _area_declarada(projeto: dict) -> Optional[float]:
    for k in ("area_declarada", "area_declarada_m2"):
        v = projeto.get(k)
        if v:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def validar(projeto: dict) -> dict:
    bloqueios, avisos = [], []
    verts = projeto.get("vertices") or []
    # distintos por (coord_e, coord_n) quando houver; senão por id/ordem
    distintos = {(v.get("coord_e"), v.get("coord_n")) for v in verts}
    if len([v for v in verts]) < 3 or len(distintos) < 3:
        bloqueios.append({"codigo": "E-POLIGONO",
                          "msg": "polígono inválido — mínimo 3 vértices distintos e fechamento."})
    if not _memoriais(projeto):
        bloqueios.append({"codigo": "E-MEMORIAL",
                          "msg": "selecione ao menos um tipo de memorial."})
    if not (projeto.get("denominacao_imovel") or "").strip():
        bloqueios.append({"codigo": "E-DENOM", "msg": "informe a denominação do imóvel."})

    comp = resolver_composicao(projeto)
    ligadas = {i["chave"] for i in comp["pecas"] if i["ligada"]}
    sel = _memoriais(projeto)

    art = projeto.get("art_trt") or {}
    if "art_trt" in ligadas and not (art.get("numero") or _uploads(projeto, "art_trt_pdf")):
        avisos.append({"codigo": "art_pendente",
                       "msg": "peça ART/TRT ligada sem número informado nem documento anexado."})
    ad = _area_declarada(projeto)
    ac = projeto.get("area_calculada_m2")
    if ad and ac:
        try:
            if abs(float(ac) - ad) / ad > 0.005:
                avisos.append({"codigo": "divergencia_area",
                               "msg": f"divergência de área — calculada {float(ac):.2f} m² × "
                                      f"declarada {ad:.2f} m² (> 0,5%); considerar retificação "
                                      f"(art. 213, Lei 6.015/73)."})
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    if not _uploads(projeto, "matricula_imovel"):
        avisos.append({"codigo": "sem_matricula",
                       "msg": "matrícula não anexada (relevante para finalidade bancária)."})
    if "imagem_localizacao" in ligadas and not _uploads(projeto, "imagem_localizacao"):
        avisos.append({"codigo": "sem_imagem_localizacao",
                       "msg": "a capa será gerada sem o bloco de imagem de localização."})
    if verts and any(not (v.get("confrontante_lado") or v.get("confrontante")) for v in verts):
        avisos.append({"codigo": "confrontantes_incompletos",
                       "msg": "algum segmento da poligonal está sem confrontante nomeado."})
    esq = (projeto.get("quadra_dados") or {}).get("esquina") or {}
    if "MD-SIT" in sel and not (esq.get("is_esquina") or esq.get("distancia_m")):
        avisos.append({"codigo": "esquina_nao_informada",
                       "msg": "MD-SIT selecionado sem distância de esquina nem marcação de esquina."})

    return {"ok": not bloqueios, "bloqueios": bloqueios, "avisos": avisos}


# ──────────────────────────────────────────────────────────────────────────────
# Catálogo estático p/ o frontend (picker de composição no topo do "Novo projeto")
# ──────────────────────────────────────────────────────────────────────────────
def opcoes() -> dict:
    return {
        "finalidades": [{"codigo": c, "label": l} for c, l in FINALIDADES],
        "instituicoes": INSTITUICOES,
        "pecas": [{"chave": p, "label": PECA_LABEL[p]} for p in PECAS],
        "presets": PRESETS,
        "memoriais": MEMORIAIS,
        "definicoes_capa": DEFINICOES_CAPA,
        "uploads": [{"chave": c, "label": l, "obrigatorio": o} for c, l, o in TIPOS_UPLOAD],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Import de coordenadas (§5) — CSV/TXT/KML/KMZ → lista de vértices.
# Colunas aceitas: vertice,E,N | vertice,lat,long | P,X,Y. Delimitador
# auto-detectado (, ; \t espaço). Detecção de sistema por magnitude.
# ──────────────────────────────────────────────────────────────────────────────
def _num(s) -> Optional[float]:
    """Número BR ('9.453.766,07') ou US ('223012.5')."""
    if s is None:
        return None
    t = str(s).strip().replace(" ", "")
    if not t:
        return None
    if "," in t and "." in t:          # BR: ponto=milhar, vírgula=decimal
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:                      # só vírgula = decimal
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _eh_utm(a: float, b: float) -> bool:
    """Par (X/E, Y/N) parece UTM no Brasil? E ~10^5-6, N ~10^6-7."""
    mags = sorted(abs(x) for x in (a, b))
    return mags[0] >= 1_000 and mags[1] >= 1_000_000


def _split(linha: str) -> list:
    for d in ("\t", ";", ","):
        if d in linha:
            return [c.strip() for c in linha.split(d)]
    return [c for c in re.split(r"\s+", linha.strip()) if c]


def _parse_csv_txt(texto: str) -> Tuple[list, str, list]:
    vertices, avisos = [], []
    sistema = None
    linhas = [ln for ln in texto.splitlines() if ln.strip()]
    ordem = 0
    for ln in linhas:
        cols = _split(ln)
        if len(cols) < 2:
            continue
        # descarta cabeçalho (linha sem par numérico)
        nums = [(_num(c), c) for c in cols]
        numeric = [n for n, _ in nums if n is not None]
        if len(numeric) < 2:
            continue
        rotulo = None
        # rótulo = 1ª coluna não-numérica (ou vazia)
        for n, raw in nums:
            if n is None and raw:
                rotulo = raw
                break
        # os 2 últimos numéricos são as coordenadas (X/E, Y/N) ou (lat, long)
        a, b = numeric[-2], numeric[-1]
        ordem += 1
        de = rotulo or f"P-{ordem:02d}"
        if _eh_utm(a, b):
            # define qual é E e qual é N pela magnitude (N é o maior no Brasil)
            e, n = (a, b) if abs(b) >= abs(a) else (b, a)
            vertices.append({"ordem": ordem, "de": de, "coord_e": e, "coord_n": n})
            sistema = sistema or "utm"
        else:
            # geográficas: uma em [-90,90] (lat) e outra em [-180,180] (long)
            lat, lon = (a, b) if abs(a) <= 90 else (b, a)
            vertices.append({"ordem": ordem, "de": de, "_lat": lat, "_lon": lon})
            sistema = sistema or "geo"
    return vertices, (sistema or "desconhecido"), avisos


def _parse_kml(texto: str) -> Tuple[list, str, list]:
    """Extrai o 1º bloco <coordinates> (lon,lat[,alt] separados por espaço)."""
    m = re.search(r"<coordinates>(.*?)</coordinates>", texto, re.DOTALL | re.IGNORECASE)
    if not m:
        return [], "desconhecido", ["KML sem <coordinates>"]
    vertices = []
    ordem = 0
    for tok in m.group(1).replace("\n", " ").split():
        parts = tok.split(",")
        if len(parts) < 2:
            continue
        lon, lat = _num(parts[0]), _num(parts[1])
        if lon is None or lat is None:
            continue
        ordem += 1
        vertices.append({"ordem": ordem, "de": f"P-{ordem:02d}", "_lat": lat, "_lon": lon})
    # KML costuma fechar o anel (último == primeiro) → remove duplicata final
    if len(vertices) >= 2 and abs(vertices[0]["_lat"] - vertices[-1]["_lat"]) < 1e-9 \
            and abs(vertices[0]["_lon"] - vertices[-1]["_lon"]) < 1e-9:
        vertices.pop()
    return vertices, "geo", []


def _parse_gpx(texto: str) -> Tuple[list, str, list]:
    """GPX → vértices geográficos. Prioriza <wpt> (marcos), depois <rtept> (rota),
    depois <trkpt> (trilha). lat/lon nos atributos; <name> opcional. Fecha o anel."""
    pat = re.compile(r"<(wpt|rtept|trkpt)\b([^>]*?)(?:/>|>(.*?)</\1>)", re.DOTALL | re.IGNORECASE)
    grupos = {"wpt": [], "rtept": [], "trkpt": []}
    for m in pat.finditer(texto):
        tag, attrs, inner = m.group(1).lower(), m.group(2) or "", m.group(3) or ""
        mlat = re.search(r'\blat\s*=\s*"([^"]+)"', attrs, re.IGNORECASE)
        mlon = re.search(r'\blon\s*=\s*"([^"]+)"', attrs, re.IGNORECASE)
        if not mlat or not mlon:
            continue
        lat, lon = _num(mlat.group(1)), _num(mlon.group(1))
        if lat is None or lon is None:
            continue
        mnome = re.search(r"<name>\s*(.*?)\s*</name>", inner, re.DOTALL | re.IGNORECASE)
        nome = (mnome.group(1).strip() if mnome else "") or None
        grupos[tag].append((lat, lon, nome))
    pts = grupos["wpt"] or grupos["rtept"] or grupos["trkpt"]
    if not pts:
        return [], "desconhecido", ["GPX sem <wpt>/<rtept>/<trkpt>"]
    vertices = [{"ordem": i, "de": nome or f"P-{i:02d}", "_lat": lat, "_lon": lon}
                for i, (lat, lon, nome) in enumerate(pts, 1)]
    # GPX de polígono costuma fechar o anel (último == primeiro) → remove duplicata final
    if len(vertices) >= 2 and abs(vertices[0]["_lat"] - vertices[-1]["_lat"]) < 1e-9 \
            and abs(vertices[0]["_lon"] - vertices[-1]["_lon"]) < 1e-9:
        vertices.pop()
    return vertices, "geo", []


def _geo_para_utm(vertices: list) -> list:
    """Converte vértices geográficos (_lat/_lon) em UTM (coord_e/coord_n) via
    geodesia (fuso auto pelo centroide). Import lazy — pyproj só carrega aqui."""
    geo = [v for v in vertices if v.get("_lon") is not None]
    if not geo:
        return vertices
    try:
        from services.geo_urbano import geodesia as G
    except Exception:  # noqa: BLE001 — sem pyproj: mantém lat/long crus
        return vertices
    lon_c = sum(v["_lon"] for v in geo) / len(geo)
    fuso = G.fuso_de_longitude(lon_c)
    for v in vertices:
        if v.get("_lon") is None:
            continue
        e, n, _fuso, _hemi = G.geo_para_utm(v["_lon"], v["_lat"], fuso=fuso)
        v["coord_e"], v["coord_n"] = round(e, 3), round(n, 3)
    return vertices


def importar_coordenadas(conteudo: bytes, filename: str = "") -> dict:
    """CSV/TXT/KML/KMZ/GPX → {vertices:[{ordem,de,coord_e,coord_n}], sistema, avisos}.
    Geográficas são convertidas para UTM (SIRGAS 2000, fuso pelo centroide)."""
    nome = (filename or "").lower()
    avisos = []
    if nome.endswith(".kmz"):
        try:
            with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
                kml_name = next((n for n in z.namelist() if n.lower().endswith(".kml")), None)
                texto = z.read(kml_name).decode("utf-8", "ignore") if kml_name else ""
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"KMZ inválido: {e}")
        vertices, sistema, av = _parse_kml(texto)
    else:
        texto = conteudo.decode("utf-8", "ignore")
        low = texto.lower()
        if nome.endswith(".gpx") or "<gpx" in low or "<wpt" in low or "<trkpt" in low or "<rtept" in low:
            vertices, sistema, av = _parse_gpx(texto)
        elif nome.endswith(".kml") or "<coordinates>" in low:
            vertices, sistema, av = _parse_kml(texto)
        else:
            vertices, sistema, av = _parse_csv_txt(texto)
    avisos += av
    if sistema == "geo":
        _geo_para_utm(vertices)
    # limpa chaves auxiliares (_lat/_lon) mantendo latitude/longitude opcionais
    for v in vertices:
        v.pop("_lat", None)
        v.pop("_lon", None)
    if len(vertices) < 3:
        avisos.append("menos de 3 vértices reconhecidos — confira o arquivo.")
    return {"vertices": vertices, "sistema": sistema, "avisos": avisos}
