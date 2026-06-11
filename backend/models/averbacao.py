# @module models.averbacao — Vistoria de Obra para Averbação (extensão do Kit TVI)
"""
Modelos + catálogos + cálculos da "Vistoria de Obra para Averbação".

Estende a collection `vistorias` (TVI) com o subdocumento `averbacao`.
Base legal: Lei 6.015/1973 (art. 167, II e art. 246) · Lei 8.212/1991 (art. 47)
· NBR 16747:2020 · NBR 12721 · Provimento CNJ 150/2023.

Os catálogos (ETAPAS_OBRA, DOCS_AVERBACAO, SISTEMAS_AVERBACAO) são a fonte única
servida por GET /api/tvi/catalogos/averbacao — o front nunca hardcoda.
Os cálculos (divergência, taxa de ocupação, conclusão geral ponderada) são SEMPRE
feitos server-side e persistidos para auditoria.
"""
from __future__ import annotations

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# ── Catálogos (fonte única) ────────────────────────────────────────────────

# Etapas com pesos NBR 12721 simplificados (somam 100).
ETAPAS_OBRA: List[dict] = [
    {"id": "servicos_preliminares", "nome": "Serviços preliminares",        "peso": 4},
    {"id": "fundacoes",             "nome": "Fundações",                     "peso": 10},
    {"id": "estrutura",             "nome": "Estrutura",                     "peso": 15},
    {"id": "alvenaria",             "nome": "Alvenaria / vedações",          "peso": 12},
    {"id": "cobertura",             "nome": "Cobertura",                     "peso": 9},
    {"id": "eletrica",              "nome": "Instalações elétricas",         "peso": 8},
    {"id": "hidrossanitaria",       "nome": "Instalações hidrossanitárias",  "peso": 8},
    {"id": "esquadrias",            "nome": "Esquadrias",                    "peso": 7},
    {"id": "revestimentos",         "nome": "Revestimentos",                 "peso": 13},
    {"id": "pisos",                 "nome": "Pisos",                         "peso": 7},
    {"id": "pintura",               "nome": "Pintura",                       "peso": 5},
    {"id": "acabamentos",           "nome": "Acabamentos finais",            "peso": 2},
]

# Checklist documental registral. `comercial=True` → só destinação ≠ residencial.
DOCS_AVERBACAO: List[dict] = [
    {"id": "requerimento",   "nome": "Requerimento de averbação assinado",        "base": "Lei 6.015/73, art. 246"},
    {"id": "habitese",       "nome": "Habite-se / Auto de conclusão",             "base": "Prefeitura"},
    {"id": "cnd_obra",       "nome": "CND de obra — INSS (via CNO/SERO)",         "base": "Lei 8.212/91, art. 47"},
    {"id": "art_trt",        "nome": "ART / TRT de execução ou conclusão",        "base": "CREA / CFT"},
    {"id": "alvara",         "nome": "Alvará de construção",                      "base": "Prefeitura"},
    {"id": "projeto",        "nome": "Projeto arquitetônico aprovado",            "base": "Prefeitura"},
    {"id": "valor_venal",    "nome": "Certidão de valor venal / caracterização",  "base": "Prefeitura"},
    {"id": "iptu",           "nome": "IPTU quitado c/ área atualizada",           "base": "Prefeitura"},
    {"id": "matricula",      "nome": "Matrícula atualizada (inteiro teor)",       "base": "CRI"},
    {"id": "avcb",           "nome": "AVCB / CLCB",                "base": "CBM/MA",        "comercial": True},
    {"id": "licenca_sanit",  "nome": "Licença sanitária (quando exigível)",       "base": "VISA",          "comercial": True},
    {"id": "acessibilidade", "nome": "Laudo de acessibilidade NBR 9050",          "base": "LBI 13.146/15", "comercial": True},
]

# Sistemas construtivos avaliados (C/NC/NA). `comercial=True` → só comercial/misto.
SISTEMAS_AVERBACAO: List[dict] = [
    {"id": "estrutura",   "nome": "Estrutura / Fundações",          "norma": "NBR 6118 · NBR 6122"},
    {"id": "vedacoes",    "nome": "Vedações / Alvenaria",           "norma": "NBR 16747"},
    {"id": "cobertura",   "nome": "Cobertura / Telhado",            "norma": "NBR 16747"},
    {"id": "imperme",     "nome": "Impermeabilização",              "norma": "NBR 9575"},
    {"id": "eletrica",    "nome": "Instalações Elétricas / QDC",    "norma": "NBR 5410"},
    {"id": "hidraulica",  "nome": "Instalações Hidráulicas",        "norma": "NBR 5626"},
    {"id": "sanitaria",   "nome": "Esgoto Sanitário",               "norma": "NBR 8160"},
    {"id": "esquadrias",  "nome": "Esquadrias / Vidros",            "norma": "NBR 10821"},
    {"id": "revest",      "nome": "Revestimentos / Fachada",        "norma": "NBR 13755"},
    {"id": "acessibilidade", "nome": "Acessibilidade",              "norma": "NBR 9050",          "comercial": True},
    {"id": "incendio",    "nome": "Combate a Incêndio / Saídas",    "norma": "NBR 17240 · CBM/MA", "comercial": True},
]

PATOLOGIAS_CATALOGO: List[str] = [
    "Fissura", "Trinca", "Rachadura", "Infiltração", "Umidade ascendente",
    "Mofo / bolor", "Eflorescência", "Descolamento cerâmico", "Desplacamento",
    "Oxidação / corrosão", "Apodrecimento", "Recalque", "Vazamento",
    "Fiação exposta", "Desgaste natural",
]

# Faixas de tolerância de divergência de área (em %). Configurável.
TOLERANCIA_DIVERGENCIA = {"verde": 2.0, "ambar": 10.0}

# Conjuntos para validação server-side.
ETAPAS_IDS = {e["id"] for e in ETAPAS_OBRA}
DOCS_IDS = {d["id"] for d in DOCS_AVERBACAO}
SISTEMAS_IDS = {s["id"] for s in SISTEMAS_AVERBACAO}
PESOS_ETAPAS = {e["id"]: e["peso"] for e in ETAPAS_OBRA}


# ── Modelos Pydantic ───────────────────────────────────────────────────────

class ConfrontoAreas(BaseModel):
    area_projeto_m2: Optional[float] = None
    area_medida_m2: Optional[float] = None
    area_matricula_m2: Optional[float] = None
    area_terreno_m2: Optional[float] = None
    detalhe_pavimentos: Optional[str] = None
    recuo_frontal_m: Optional[float] = None
    recuos_laterais: Optional[str] = None
    implantacao: Literal["conforme", "divergencia_leve", "divergencia_relevante"] = "conforme"
    # calculados server-side e persistidos para auditoria:
    divergencia_m2: Optional[float] = None
    divergencia_pct: Optional[float] = None
    taxa_ocupacao_pct: Optional[float] = None


class EtapaObra(BaseModel):
    etapa_id: str
    percentual: int = Field(ge=0, le=100)


class SistemaAverbacao(BaseModel):
    sistema_id: str
    conformidade: Literal["C", "NC", "NA", "PENDENTE"] = "PENDENTE"
    patologias: List[str] = Field(default_factory=list)
    severidade: Optional[Literal["leve", "moderada", "grave"]] = None
    observacao: Optional[str] = None


class DocumentoAverbacao(BaseModel):
    doc_id: str
    situacao: Literal["OK", "PEND", "NA", "PENDENTE_AVALIACAO"] = "PENDENTE_AVALIACAO"
    observacao: Optional[str] = None


class DadosAverbacao(BaseModel):
    destinacao: Literal["residencial", "comercial", "misto"] = "residencial"
    cno: Optional[str] = None
    alvara_numero: Optional[str] = None
    habitese_numero: Optional[str] = None
    requerente_nome: Optional[str] = None
    rt_execucao: Optional[str] = None
    tipo_edificacao: Optional[str] = None
    pavimentos: Optional[int] = None
    padrao_construtivo: Optional[str] = None
    confronto: ConfrontoAreas = Field(default_factory=ConfrontoAreas)
    etapas: List[EtapaObra] = Field(default_factory=list)
    sistemas: List[SistemaAverbacao] = Field(default_factory=list)
    documentos: List[DocumentoAverbacao] = Field(default_factory=list)
    situacao_obra: Literal["concluida", "concluida_pendencias", "em_conclusao"] = "concluida"
    compatibilidade: Literal["total", "regularizavel", "relevante"] = "total"
    parecer: Literal["apta", "apta_apos_saneamento", "inapta"] = "apta"
    necessita_asbuilt: bool = False
    recomendacoes: Optional[str] = None
    prazo_saneamento: Optional[str] = None
    emitir_trt: bool = True
    # calculado server-side:
    conclusao_geral_pct: Optional[float] = None


# ── Helpers de cálculo / classificação (fonte única) ───────────────────────

def faixa_divergencia(pct: Optional[float]) -> str:
    """Retorna a faixa da divergência: 'verde' | 'ambar' | 'vermelho'."""
    if pct is None:
        return "verde"
    ap = abs(float(pct))
    if ap <= TOLERANCIA_DIVERGENCIA["verde"]:
        return "verde"
    if ap <= TOLERANCIA_DIVERGENCIA["ambar"]:
        return "ambar"
    return "vermelho"


def frase_divergencia(pct: Optional[float]) -> str:
    """Frase condicional pela faixa de tolerância (texto do relatório)."""
    faixa = faixa_divergencia(pct)
    if faixa == "verde":
        return ("A divergência apurada situa-se dentro da tolerância técnica admitida, "
                "compatível com averbação direta da área construída na matrícula.")
    if faixa == "ambar":
        return ("A divergência apurada recomenda a verificação da exigência de levantamento "
                "as-built e eventual anuência do responsável técnico antes da averbação.")
    return ("A divergência apurada é relevante e recomenda-se a regularização prévia da "
            "construção (as-built / projeto modificativo) antes da averbação na matrícula.")


def _f(v) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def calcular_averbacao(averbacao: dict) -> dict:
    """Recalcula e persiste os campos derivados do subdocumento `averbacao`:
       confronto.divergencia_m2 / divergencia_pct / taxa_ocupacao_pct e
       conclusao_geral_pct (média ponderada das etapas pelos pesos do catálogo).
       Mutação in-place + retorno do mesmo dict. Server é a fonte da verdade."""
    if not isinstance(averbacao, dict):
        return averbacao

    conf = averbacao.get("confronto")
    if not isinstance(conf, dict):
        conf = {}
        averbacao["confronto"] = conf

    a_proj = _f(conf.get("area_projeto_m2"))
    a_med = _f(conf.get("area_medida_m2"))
    a_terr = _f(conf.get("area_terreno_m2"))

    # Divergência executado × aprovado (medida in loco × projeto aprovado).
    if a_proj and a_proj > 0 and a_med is not None:
        div_m2 = round(a_med - a_proj, 2)
        conf["divergencia_m2"] = div_m2
        conf["divergencia_pct"] = round((div_m2 / a_proj) * 100.0, 2)
    else:
        conf["divergencia_m2"] = None
        conf["divergencia_pct"] = None

    # Taxa de ocupação = projeção da edificação (área medida) / área do terreno.
    if a_terr and a_terr > 0 and a_med is not None:
        conf["taxa_ocupacao_pct"] = round((a_med / a_terr) * 100.0, 2)
    else:
        conf["taxa_ocupacao_pct"] = None

    # Conclusão geral = média ponderada das etapas pelos pesos do catálogo.
    etapas = averbacao.get("etapas") or []
    soma_peso = 0
    soma_pond = 0.0
    for e in etapas:
        if not isinstance(e, dict):
            continue
        eid = e.get("etapa_id")
        peso = PESOS_ETAPAS.get(eid)
        if not peso:
            continue
        try:
            pct = max(0, min(100, int(e.get("percentual", 0))))
        except (TypeError, ValueError):
            pct = 0
        soma_peso += peso
        soma_pond += peso * pct
    averbacao["conclusao_geral_pct"] = round(soma_pond / soma_peso, 1) if soma_peso else 0.0

    return averbacao


# ── Modelo do catálogo TVI (categoria REGULARIZAÇÃO, selo TRT) ─────────────
MODELO_AVERBACAO = {
    "id": "TVI-AVERB",
    "tipo": "obra_averbacao",
    "nome": "Vistoria de Obra para Averbação",
    "ramo": "REGULARIZACAO",
    "categoria": "Regularização",
    "modelo_especial": "averbacao",   # o front usa para renderizar o formulário próprio (6 abas)
    "selo": "TRT Obrigatória",
    "aplicacao": (
        "Vistoria de conclusão de obra (residencial, comercial ou mista) para subsidiar a "
        "averbação da construção na matrícula do imóvel, com confronto de áreas, estágio de "
        "execução por etapa e checklist documental registral."
    ),
    "normas": [
        "Lei 6.015/1973 art. 167, II e art. 246",
        "Lei 8.212/1991 art. 47 (CND/CNO)",
        "NBR 16747:2020", "NBR 12721", "Provimento CNJ 150/2023",
    ],
    "requer_art": True,
    "campos_especificos": [],
}


async def ensure_modelo_averbacao(db) -> None:
    """Garante (idempotente, sem dropar nada) o modelo de Averbação em vistoria_models."""
    from datetime import datetime
    doc = {**MODELO_AVERBACAO, "ativo": True}
    existing = await db.vistoria_models.find_one({"id": MODELO_AVERBACAO["id"]})
    if existing:
        await db.vistoria_models.update_one({"id": MODELO_AVERBACAO["id"]}, {"$set": doc})
    else:
        doc["created_at"] = datetime.utcnow()
        await db.vistoria_models.insert_one(doc)


def catalogos_averbacao() -> dict:
    """Payload do endpoint de catálogos (fonte única para o front)."""
    return {
        "etapas": ETAPAS_OBRA,
        "documentos": DOCS_AVERBACAO,
        "sistemas": SISTEMAS_AVERBACAO,
        "patologias": PATOLOGIAS_CATALOGO,
        "tolerancia_divergencia": TOLERANCIA_DIVERGENCIA,
        "destinacoes": ["residencial", "comercial", "misto"],
        "severidades": ["leve", "moderada", "grave"],
    }
