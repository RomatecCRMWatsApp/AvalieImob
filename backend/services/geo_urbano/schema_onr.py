# @module services.geo_urbano.schema_onr — Esquema de atributos do SIG-RI (URBANO).
#
# Provimento CNJ 195/2025 + ABNT NBR 17047:2022. Dicionário de campos do DBF do
# shapefile enviado ao Mapa do Registro de Imóveis do Brasil (mapa.onr.org.br)
# e o gerador do LEIAME.txt. Mantido AQUI (fora do builder) para permitir ajuste
# do esquema sem tocar na geração quando o ONR revisar o manual técnico.
#
# REGRA DURA (imóvel URBANO): NÃO existem — e por isso NÃO são gerados — os
# campos rurais COD_SIGEF/SNCI/CCIR/NIRF/CAR/MÓDULO FISCAL.
from __future__ import annotations

import re
from datetime import date, datetime
from typing import List, Optional, Tuple

# Nome DBF ≤ 10 caracteres; texto ≤ 254.
ONR_URBANO_FIELDS: List[Tuple[str, str, int, int]] = [
    ("ID_IMOVEL", "C", 40, 0),
    ("TIPO_IMOV", "C", 10, 0),   # "URBANO" (fixo)
    ("NAT_ATO", "C", 30, 0),     # DESDOBRO / REMEMBRAMENTO / RETIFICACAO / USUCAPIAO / REURB-S/E
    ("MATRICULA", "C", 60, 0),   # matrículas separadas por ";"
    ("TRANSCRIC", "C", 60, 0),
    ("CNS_SERV", "C", 10, 0),
    ("SERVENTIA", "C", 120, 0),
    ("COMARCA", "C", 60, 0),
    ("MUNICIPIO", "C", 60, 0),
    ("UF", "C", 2, 0),
    ("COD_IBGE", "C", 7, 0),
    ("LOTEAMENT", "C", 100, 0),
    ("QUADRA", "C", 20, 0),
    ("LOTE", "C", 20, 0),
    ("UNIDADE", "C", 20, 0),
    ("LOGRADOUR", "C", 120, 0),
    ("NUMERO", "C", 15, 0),
    ("BAIRRO", "C", 80, 0),
    ("CEP", "C", 9, 0),
    ("CIB", "C", 20, 0),         # Cadastro Imobiliário Brasileiro (IN RFB 2.030/2021)
    ("INSC_MUNI", "C", 30, 0),   # inscrição municipal / IPTU
    ("AREA_M2", "N", 15, 2),     # área geodésica
    ("AREA_HA", "N", 12, 4),
    ("PERIMETRO", "N", 12, 2),   # perímetro geodésico
    ("N_VERTICES", "N", 5, 0),
    ("PROPRIET", "C", 254, 0),
    ("CPF_CNPJ", "C", 254, 0),
    ("N_PROPRIET", "N", 3, 0),
    ("CONFRONT", "C", 254, 0),
    ("SIST_GEOD", "C", 20, 0),   # "SIRGAS2000"
    ("EPSG_GEO", "C", 10, 0),    # "4674"
    ("HEMISF", "C", 1, 0),
    ("FUSO", "N", 2, 0),
    ("MC", "N", 4, 0),           # meridiano central
    ("PRECISAO", "N", 6, 3),     # precisão posicional declarada (m)
    ("NORMA_TEC", "C", 30, 0),   # "ABNT NBR 17047:2022"
    ("RESP_TEC", "C", 120, 0),
    ("TITULO_RT", "C", 60, 0),
    ("CONSELHO", "C", 10, 0),    # CFT / CREA
    ("REG_PROF", "C", 30, 0),
    ("ART_TRT", "C", 30, 0),
    ("DATA_LEV", "D", 8, 0),
    ("DATA_GER", "D", 8, 0),
    ("PROV_195", "C", 5, 0),     # "SIM"
    ("OBS", "C", 254, 0),
]

_NAT_ATO = {
    "remembramento": "REMEMBRAMENTO", "desdobro": "DESDOBRO",
    "retificacao": "RETIFICACAO", "usucapiao": "USUCAPIAO", "reurb": "REURB",
}
_NORMA = "ABNT NBR 17047:2022"
# IBGE dos municípios usuais (fallback quando não informado no projeto)
_IBGE_MUNICIPIO = {"açailândia": "2100055", "acailandia": "2100055"}


def _c(v, n: int) -> str:
    """Texto para campo Character: str, sem sobras, truncado a n BYTES (UTF-8),
    cortando em fronteira de caractere (evita PossibleDataLoss no pyshp)."""
    if v is None:
        return ""
    s = str(v).strip()
    b = s.encode("utf-8")
    if len(b) <= n:
        return s
    return b[:n].decode("utf-8", "ignore")


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _to_date(v) -> Optional[date]:
    """ISO/date → datetime.date; qualquer outra coisa → None."""
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if not v:
        return None
    m = re.match(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", str(v).strip())
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Extratores do projeto
# ──────────────────────────────────────────────────────────────────────────────
def _nat_ato(projeto: dict) -> str:
    ts = projeto.get("tipo_servico") or "remembramento"
    if ts == "reurb":
        mod = (projeto.get("reurb_modalidade") or "").lower()
        return "REURB-S" if mod == "reurb_s" else ("REURB-E" if mod == "reurb_e" else "REURB")
    return _NAT_ATO.get(ts, ts.upper())


def _matriculas(projeto: dict) -> str:
    return ";".join(m.get("matricula") for m in (projeto.get("matriculas") or []) if m.get("matricula"))


def _serventia(projeto: dict) -> str:
    return (projeto.get("cartorio") or {}).get("nome") or ""


def _cns(projeto: dict) -> str:
    return re.sub(r"\D", "", (projeto.get("cartorio") or {}).get("cns") or "")


def _comarca(projeto: dict) -> str:
    nome = _serventia(projeto)
    m = re.search(r"comarca de\s+([^\-–,/]+)", nome, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return projeto.get("municipio") or ""


def _codigo_ibge(projeto: dict) -> str:
    cod = re.sub(r"\D", "", str(projeto.get("codigo_ibge") or ""))
    if cod:
        return cod
    return _IBGE_MUNICIPIO.get((projeto.get("municipio") or "").strip().lower(), "")


def _proprietarios(projeto: dict) -> Tuple[str, str, int]:
    nomes, docs = [], []
    for p in projeto.get("partes") or []:
        if p.get("papel") not in ("requerente", "titular_tabular"):
            continue
        nome = p.get("razao_social") or p.get("nome")
        doc = p.get("cnpj") or p.get("cpf")
        if nome:
            nomes.append(nome)
            docs.append(doc or "")
    return ";".join(nomes), ";".join(docs), len(nomes)


def _confrontantes(projeto: dict) -> str:
    nomes = [c.get("confrontante") for c in (projeto.get("confrontantes") or []) if c.get("confrontante")]
    if not nomes:  # deriva dos lados dos vértices
        vistos, ded = set(), []
        for v in projeto.get("vertices") or []:
            c = v.get("confrontante_lado")
            if c and c not in vistos:
                vistos.add(c)
                ded.append(c)
        nomes = ded
    txt = "; ".join(nomes)
    return (txt[:251] + "...") if len(txt) > 254 else txt


def _rt(projeto: dict) -> Tuple[str, str, str, str]:
    """(nome, titulo, conselho, registro) do responsável técnico."""
    rt = projeto.get("responsavel_tecnico") or {}
    nome = rt.get("nome") or ""
    titulo = rt.get("formacao") or rt.get("titulo") or ""
    conselho_full = (rt.get("conselho") or "").strip()   # "CFT/MA 01209185369"
    conselho, registro = "", ""
    if conselho_full:
        m = re.match(r"([A-Za-z]+)", conselho_full)
        conselho = m.group(1).upper() if m else conselho_full
        registro = conselho_full[len(conselho):].strip("/ ").strip()
    return nome, titulo, conselho, registro


# ──────────────────────────────────────────────────────────────────────────────
# Registro DBF de UMA feição (polígono)
# ──────────────────────────────────────────────────────────────────────────────
def montar_registro(projeto: dict, *, rotulo: str = "", area_m2: float = 0.0,
                    perimetro_m: float = 0.0, n_vertices: int = 0,
                    fuso: Optional[int] = None, hemisferio: Optional[str] = None,
                    id_imovel: str = "", lote_label: Optional[str] = None) -> dict:
    from services.geo_urbano import geodesia as GEO  # evita import circular no topo

    nome_prop, doc_prop, n_prop = _proprietarios(projeto)
    rt_nome, rt_titulo, conselho, registro = _rt(projeto)
    f = int(fuso) if fuso else None
    hoje = date.today()
    return {
        "ID_IMOVEL": _c(id_imovel or projeto.get("id") or projeto.get("numero"), 40),
        "TIPO_IMOV": "URBANO",
        "NAT_ATO": _c(_nat_ato(projeto), 30),
        "MATRICULA": _c(_matriculas(projeto), 60),
        "TRANSCRIC": "",
        "CNS_SERV": _c(_cns(projeto), 10),
        "SERVENTIA": _c(_serventia(projeto), 120),
        "COMARCA": _c(_comarca(projeto), 60),
        "MUNICIPIO": _c(projeto.get("municipio"), 60),
        "UF": _c(projeto.get("uf"), 2).upper(),
        "COD_IBGE": _c(_codigo_ibge(projeto), 7),
        "LOTEAMENT": _c(projeto.get("loteamento"), 100),
        "QUADRA": _c(projeto.get("quadra"), 20),
        "LOTE": _c(lote_label or projeto.get("lote_resultante") or rotulo, 20),
        "UNIDADE": _c(projeto.get("unidade"), 20),
        "LOGRADOUR": _c(projeto.get("endereco"), 120),
        "NUMERO": _c(projeto.get("numero"), 15),
        "BAIRRO": _c(projeto.get("bairro"), 80),
        "CEP": _c(projeto.get("cep"), 9),
        "CIB": _c(projeto.get("cib"), 20),
        "INSC_MUNI": _c(projeto.get("inscricao_municipal"), 30),
        "AREA_M2": round(_num(area_m2), 2),
        "AREA_HA": round(_num(area_m2) / 10000.0, 4),
        "PERIMETRO": round(_num(perimetro_m), 2),
        "N_VERTICES": int(n_vertices or 0),
        "PROPRIET": _c(nome_prop, 254),
        "CPF_CNPJ": _c(doc_prop, 254),
        "N_PROPRIET": int(n_prop),
        "CONFRONT": _c(_confrontantes(projeto), 254),
        "SIST_GEOD": "SIRGAS2000",
        "EPSG_GEO": str(GEO.EPSG_SIRGAS2000_GEO),
        "HEMISF": _c(hemisferio or "S", 1).upper(),
        "FUSO": int(f) if f else 0,
        "MC": GEO.mc_de_fuso(f) if f else 0,
        "PRECISAO": round(_num(projeto.get("precisao_posicional_m") or 0.10), 3),
        "NORMA_TEC": _NORMA,
        "RESP_TEC": _c(rt_nome, 120),
        "TITULO_RT": _c(rt_titulo, 60),
        "CONSELHO": _c(conselho, 10),
        "REG_PROF": _c(registro, 30),
        "ART_TRT": _c(projeto.get("trt_numero"), 30),
        "DATA_LEV": _to_date(projeto.get("data_levantamento")) or hoje,
        "DATA_GER": hoje,
        "PROV_195": "SIM",
        "OBS": _c(projeto.get("obs_onr"), 254),
    }


# ──────────────────────────────────────────────────────────────────────────────
# LEIAME.txt (§12 do spec)
# ──────────────────────────────────────────────────────────────────────────────
def montar_leiame(projeto: dict, *, rotulo: str = "", area_m2: float = 0.0,
                  perimetro_m: float = 0.0, n_vertices: int = 0,
                  fuso: Optional[int] = None, hemisferio: Optional[str] = None,
                  sha256: str = "") -> str:
    from services.geo_urbano import geodesia as GEO

    nome_prop, _doc, _n = _proprietarios(projeto)
    rt_nome, rt_titulo, conselho, registro = _rt(projeto)
    f = int(fuso) if fuso else 0
    mc = GEO.mc_de_fuso(f) if f else 0
    hemis = (hemisferio or "S").upper()[:1]
    hoje = date.today().strftime("%d/%m/%Y")
    return "\n".join([
        "ARQUIVO GEOESPACIAL PARA ALIMENTACAO DO SIG-RI",
        "Provimento CN-CNJ n. 195/2025 - Operador Nacional do Registro de Imoveis (ONR)",
        "",
        f"Imovel..............: {projeto.get('denominacao_imovel') or rotulo or '-'}",
        "Classificacao.......: URBANO",
        f"Natureza do ato.....: {_nat_ato(projeto)}",
        f"Matricula(s)........: {_matriculas(projeto) or '-'}",
        f"Serventia (CNS).....: {_serventia(projeto) or '-'} ({_cns(projeto) or '-'})",
        f"Comarca.............: {_comarca(projeto) or '-'}",
        f"Municipio/UF (IBGE).: {projeto.get('municipio') or '-'}/{projeto.get('uf') or '-'} "
        f"({_codigo_ibge(projeto) or '-'})",
        f"Quadra/Lote.........: {projeto.get('quadra') or '-'}/{projeto.get('lote_resultante') or rotulo or '-'} "
        f"- {projeto.get('loteamento') or '-'}",
        f"Proprietario(s).....: {nome_prop or '-'}",
        f"Area................: {_num(area_m2):.2f} m2 ({_num(area_m2)/10000.0:.4f} ha)",
        f"Perimetro...........: {_num(perimetro_m):.2f} m",
        f"Vertices............: {n_vertices}",
        f"Sistema geodesico...: SIRGAS 2000 (EPSG:{GEO.EPSG_SIRGAS2000_GEO}) - Fuso {f}{hemis}, MC {mc}",
        f"Norma tecnica.......: {_NORMA}",
        f"Precisao posicional.: {_num(projeto.get('precisao_posicional_m') or 0.10):.3f} m",
        f"Responsavel tecnico.: {rt_nome or '-'} - {rt_titulo or '-'} - {conselho} {registro}".rstrip(" -"),
        f"ART/TRT.............: {projeto.get('trt_numero') or '-'}",
        f"Data de geracao.....: {hoje}",
        f"SHA-256 do pacote...: {sha256 or '-'}",
        "",
        "Observacao: por se tratar de imovel urbano, nao se aplicam os campos",
        "de cadastro rural (SIGEF, SNCI, CCIR, NIRF, CAR), conforme regra de",
        "preenchimento do Mapa do Registro de Imoveis do Brasil.",
    ])
