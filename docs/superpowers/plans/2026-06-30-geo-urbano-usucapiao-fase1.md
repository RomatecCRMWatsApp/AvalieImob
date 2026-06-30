# Geo Urbano — Usucapião Extrajudicial (Fase 1: Backend núcleo) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar o serviço de **Usucapião Extrajudicial** ao módulo Geo Urbano (backend núcleo): modelo de dados, catálogo de modalidades + validação de posse, checklist dinâmica, geradores das peças (Requerimento, Ata Notarial, Anuência, Notificação, Edital), montagem do dossiê na ordem de protocolo, fiação nas rotas e seed do caso "herdeiro", tudo coberto por testes.

**Architecture:** Serviço aditivo `tipo_servico = "usucapiao"` dentro do módulo existente (mesmo padrão de Desdobro/Retificação). Reusa a infra de geração PDF (`services.georef.generators.pdf` via alias `GP`, `services.geo_urbano.generators.textos` via `TX`), o dossiê ordenado (`dossie.gerar_dossie_ordenado`) e o despacho por `tipo_servico` em `routes/geo_urbano.py`. Nada dos serviços existentes é alterado em comportamento — só extensão.

**Tech Stack:** Python 3, FastAPI, MongoDB (Motor), Pydantic v2, ReportLab + pypdf (geração/merge PDF), pytest.

**Spec:** `docs/superpowers/specs/2026-06-30-geo-urbano-usucapiao-design.md`

**Comando de teste (sempre a partir de `backend/`):** `python -m pytest tests/test_usucapiao.py -v`

**Fora desta fase (planos próprios):** Fase 2 frontend (wizard/uploads/validação ao vivo); Fase 3 anuências ponta-a-ponta (WhatsApp + presencial) + ICP do RT.

---

## Task 1: Modelo de dados — campos e sub-models de Usucapião

**Files:**
- Modify: `backend/models/geo_urbano.py`
- Test: `backend/tests/test_usucapiao.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_usucapiao.py`:

```python
# Testes do serviço de Usucapião Extrajudicial (Geo Urbano) — modelo, modalidades,
# validação de posse, checklist dinâmica, anuentes, geradores e dossiê.
import io

import pytest
from pypdf import PdfReader

from models.geo_urbano import GeoUrbanoProjeto


def _paginas(data: bytes) -> int:
    assert data[:5] == b"%PDF-"
    return len(PdfReader(io.BytesIO(data)).pages)


def test_modelo_usucapiao_valido():
    p = GeoUrbanoProjeto(
        denominacao_imovel="Lote 12 — Quadra 8 — Vila São Francisco",
        tipo_servico="usucapiao",
        modalidade_usucapiao="extraordinaria",
        situacao_registral="nao_matriculado",
        valor_atribuido=85000.0,
        soma_posses=[
            {"possuidor_nome": "Maria das Dores", "vinculo": "de_cujus",
             "inicio": "2008", "fim": "2018"},
            {"possuidor_nome": "João Filho", "vinculo": "proprio",
             "inicio": "2018", "fim": "atual"},
        ],
        provas_posse=[{"tipo": "iptu", "ano": "2010", "descricao": "Carnê de IPTU 2010"}],
        anuentes=[{"papel": "confrontante", "nome": "Vizinho Norte",
                   "lado": "fundo", "tipo": "particular", "canal": "presencial"}],
        checklist=[{"bloco": "A", "chave": "requerimento", "label": "Requerimento",
                    "obrigatorio": True, "status": "pendente"}],
        partes=[{"papel": "advogado", "tipo_pessoa": "fisica", "nome": "Dra. Ana",
                 "oab": "OAB/MA 12345"}],
    )
    assert p.modalidade_usucapiao == "extraordinaria"
    assert p.posse.natureza.startswith("mansa")
    assert len(p.soma_posses) == 2 and p.soma_posses[0].vinculo == "de_cujus"
    assert len(p.provas_posse) == 1 and p.provas_posse[0].tipo == "iptu"
    assert p.anuentes[0].anuencia.status == "pendente"
    assert p.partes[0].oab == "OAB/MA 12345"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_usucapiao.py::test_modelo_usucapiao_valido -v`
Expected: FAIL — `ValidationError` / unexpected keyword (campos `modalidade_usucapiao`, `oab`, etc. ainda não existem).

- [ ] **Step 3: Write minimal implementation**

In `backend/models/geo_urbano.py`, after the `ViaRegularidade` Literal (around line 39), add the new Literals:

```python
ModalidadeUsucapiao = Literal[
    "extraordinaria", "ordinaria", "especial_urbana", "especial_rural",
    "familiar", "coletiva", "outra",
]
SituacaoRegistral = Literal["matriculado_terceiro", "nao_matriculado", "transcricao_antiga"]
TipoProvaPosse = Literal[
    "agua", "luz", "iptu", "telefone", "contrato", "benfeitoria",
    "comprovante_endereco", "declaracao", "foto", "outro",
]
StatusDocChecklist = Literal["pendente", "anexado", "dispensado"]
BlocoChecklist = Literal["A", "B", "C", "D", "E", "F", "G"]
VinculoPosse = Literal["proprio", "de_cujus", "cedente"]
CanalAnuencia = Literal["whatsapp", "presencial"]
PapelAnuente = Literal["confrontante", "titular_tabular"]
```

Extend `PapelParte` (around line 139) to add the new roles, and add `oab`/`uf_oab` to `Parte` (after the `cnh` field, around line 157):

```python
PapelParte = Literal[
    "requerente", "conjuge", "representante", "socio",
    "advogado", "herdeiro", "titular_tabular", "testemunha",
]
```

In class `Parte`, after `cnh: Optional[str] = None`, add:

```python
    oab: Optional[str] = None       # advogado (art. 216-A exige acompanhamento)
    uf_oab: Optional[str] = None
```

Add the new sub-models just before `class GeoUrbanoProjeto` (after `ConfrontanteRetificacao`, around line 295):

```python
# ──────────────────────────────────────────────────────────────────────────────
# Usucapião Extrajudicial (Prov. CNJ 149/2023) — sub-models embutidos no projeto
# ──────────────────────────────────────────────────────────────────────────────
class Posse(BaseModel):
    inicio: Optional[str] = None          # ano ou data ISO
    natureza: str = "mansa, pacífica, ininterrupta, com animus domini"
    origem: Optional[str] = None          # compra verbal, cessão, ocupação...
    benfeitorias: Optional[str] = None
    benfeitorias_data: Optional[str] = None
    valor_venal: Optional[float] = None
    justo_titulo: Optional[str] = None    # exigido na ordinária


class PossePeriodo(BaseModel):
    id: str = Field(default_factory=_uid)
    possuidor_nome: Optional[str] = None
    possuidor_doc: Optional[str] = None
    vinculo: VinculoPosse = "proprio"     # soma de posses (art. 1.243 CC)
    inicio: Optional[str] = None          # ano ou data ISO
    fim: Optional[str] = None             # ano/data ISO ou "atual"
    natureza: Optional[str] = None
    observacao: Optional[str] = None


class ProvaPosse(BaseModel):
    id: str = Field(default_factory=_uid)
    tipo: TipoProvaPosse = "outro"
    descricao: Optional[str] = None
    ano: Optional[str] = None             # linha do tempo: ano principal
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None
    upload_id: Optional[str] = None
    observacao: Optional[str] = None


class AnuenteUsucapiao(BaseModel):
    id: str = Field(default_factory=_uid)
    papel: PapelAnuente = "confrontante"
    nome: Optional[str] = None
    doc: Optional[str] = None
    lado: Optional[str] = None
    medida_m: Optional[float] = None
    tipo: TipoConfrontante = "particular"  # via/área pública dispensam
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    canal: CanalAnuencia = "presencial"
    anuencia: Anuencia = Field(default_factory=Anuencia)
    doc_id: Optional[str] = None           # declaração de anuência gerada


class DocChecklistItem(BaseModel):
    id: str = Field(default_factory=_uid)
    bloco: BlocoChecklist = "A"
    chave: str = ""
    label: str = ""
    obrigatorio: bool = True
    status: StatusDocChecklist = "pendente"
    upload_id: Optional[str] = None
    observacao: Optional[str] = None
```

In `class GeoUrbanoProjeto`, after the Retificação block (after `confrontantes: List[ConfrontanteRetificacao] = ...`, around line 339), add the Usucapião fields:

```python
    # Usucapião Extrajudicial (Prov. CNJ 149/2023)
    modalidade_usucapiao: ModalidadeUsucapiao = "extraordinaria"
    fundamento_legal: Optional[str] = None        # usado quando modalidade = "outra"
    valor_atribuido: Optional[float] = None
    situacao_registral: SituacaoRegistral = "nao_matriculado"
    matricula_usucapienda_id: Optional[str] = None  # aponta p/ Matricula em matriculas[]
    posse: Posse = Field(default_factory=Posse)
    soma_posses: List[PossePeriodo] = Field(default_factory=list)
    provas_posse: List[ProvaPosse] = Field(default_factory=list)
    anuentes: List[AnuenteUsucapiao] = Field(default_factory=list)
    checklist: List[DocChecklistItem] = Field(default_factory=list)
```

In `class AtualizarProjetoBody`, after the Retificação block (after `confrontantes: Optional[List[dict]] = None`, around line 419), add:

```python
    # Usucapião
    modalidade_usucapiao: Optional[ModalidadeUsucapiao] = None
    fundamento_legal: Optional[str] = None
    valor_atribuido: Optional[float] = None
    situacao_registral: Optional[SituacaoRegistral] = None
    matricula_usucapienda_id: Optional[str] = None
    posse: Optional[dict] = None
    soma_posses: Optional[List[dict]] = None
    provas_posse: Optional[List[dict]] = None
    anuentes: Optional[List[dict]] = None
    checklist: Optional[List[dict]] = None
```

Add the new models to the `model_rebuild()` block at the bottom (after `ConfrontanteRetificacao.model_rebuild()`):

```python
Posse.model_rebuild()
PossePeriodo.model_rebuild()
ProvaPosse.model_rebuild()
AnuenteUsucapiao.model_rebuild()
DocChecklistItem.model_rebuild()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_usucapiao.py::test_modelo_usucapiao_valido -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/models/geo_urbano.py backend/tests/test_usucapiao.py
git commit -m "feat(geo-urbano): modelo de dados do serviço de Usucapião"
```

---

## Task 2: Serviço `usucapiao.py` — catálogo de modalidades + `validar_posse`

**Files:**
- Create: `backend/services/geo_urbano/usucapiao.py`
- Test: `backend/tests/test_usucapiao.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_usucapiao.py`:

```python
from services.geo_urbano import usucapiao as USU


def test_modalidades_catalogo():
    assert set(USU.MODALIDADES) == {
        "extraordinaria", "ordinaria", "especial_urbana", "especial_rural",
        "familiar", "coletiva", "outra",
    }
    assert USU.MODALIDADES["extraordinaria"]["prazo_anos"] == 15
    assert USU.MODALIDADES["especial_urbana"]["area_max_m2"] == 250.0
    assert USU.MODALIDADES["ordinaria"]["exige_justo_titulo"] is True


def test_validar_posse_soma_alcanca_prazo():
    proj = {"modalidade_usucapiao": "extraordinaria",
            "soma_posses": [
                {"vinculo": "de_cujus", "inicio": "2008", "fim": "2018"},
                {"vinculo": "proprio", "inicio": "2018", "fim": "atual"}]}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["anos_cobertos"] == 18
    assert r["prazo_exigido"] == 15
    assert r["prazo_ok"] is True
    assert r["faltam_anos"] == 0


def test_validar_posse_soma_nao_alcanca():
    proj = {"modalidade_usucapiao": "extraordinaria",
            "soma_posses": [{"vinculo": "proprio", "inicio": "2018", "fim": "atual"}]}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["anos_cobertos"] == 8
    assert r["prazo_ok"] is False
    assert r["faltam_anos"] == 7


def test_validar_posse_area_excede():
    proj = {"modalidade_usucapiao": "especial_urbana", "area_declarada_m2": 320.0,
            "posse": {"inicio": "2015"}}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["area_ok"] is False
    assert r["area_max"] == 250.0


def test_validar_posse_tema_815_nao_trava_modulo_municipal():
    # STF Tema 815: especial urbana NÃO se condiciona ao módulo mínimo municipal.
    proj = {"modalidade_usucapiao": "especial_urbana", "area_declarada_m2": 120.0,
            "lote_minimo_municipal_m2": 250.0, "posse": {"inicio": "2018"}}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["area_ok"] is True
    assert r["ignora_modulo_municipal"] is True
    assert any("815" in a or "módulo" in a.lower() for a in r["avisos"])


def test_validar_posse_ordinaria_exige_justo_titulo():
    proj = {"modalidade_usucapiao": "ordinaria",
            "posse": {"inicio": "2010"}}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["exige_justo_titulo"] is True
    assert r["justo_titulo_ok"] is False
    proj["posse"]["justo_titulo"] = "Cessão de direitos hereditários, fls. 12"
    r2 = USU.validar_posse(proj, ano_ref=2026)
    assert r2["justo_titulo_ok"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_usucapiao.py::test_modalidades_catalogo -v`
Expected: FAIL — `ModuleNotFoundError: services.geo_urbano.usucapiao`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/services/geo_urbano/usucapiao.py`:

```python
# @module services.geo_urbano.usucapiao — regras do serviço de Usucapião Extrajudicial.
#
# Catálogo de modalidades (Prov. CNJ 149/2023 + CC/CF), validação do tempo de posse
# (soma de posses art. 1.243 CC) e da área-limite por modalidade, com a exceção do
# STF Tema 815 (especial urbana não se condiciona ao módulo mínimo municipal), e a
# checklist dinâmica de documentos (blocos A-G) por modalidade/situação registral.
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

# Catálogo das modalidades (define prazo, área-limite, justo título e fundamento).
MODALIDADES = {
    "extraordinaria": {
        "label": "Extraordinária", "fundamento": "art. 1.238 do Código Civil",
        "prazo_anos": 15, "prazo_reduzido": 10,
        "condicao_reducao": "moradia habitual ou obras/serviços de caráter produtivo",
        "area_max_m2": None, "exige_justo_titulo": False, "escopo": "ambos",
    },
    "ordinaria": {
        "label": "Ordinária", "fundamento": "art. 1.242 do Código Civil",
        "prazo_anos": 10, "prazo_reduzido": 5,
        "condicao_reducao": "aquisição onerosa com registro cancelado + moradia/investimentos",
        "area_max_m2": None, "exige_justo_titulo": True, "escopo": "ambos",
    },
    "especial_urbana": {
        "label": "Especial Urbana", "fundamento": "art. 183 da CF e art. 1.240 do Código Civil",
        "prazo_anos": 5, "prazo_reduzido": None, "condicao_reducao": None,
        "area_max_m2": 250.0, "exige_justo_titulo": False, "escopo": "urbano",
        "ignora_modulo_municipal": True,
    },
    "especial_rural": {
        "label": "Especial Rural", "fundamento": "art. 191 da CF e art. 1.239 do Código Civil",
        "prazo_anos": 5, "prazo_reduzido": None, "condicao_reducao": None,
        "area_max_ha": 50.0, "exige_justo_titulo": False, "escopo": "rural",
    },
    "familiar": {
        "label": "Especial Urbana Familiar", "fundamento": "art. 1.240-A do Código Civil",
        "prazo_anos": 2, "prazo_reduzido": None, "condicao_reducao": None,
        "area_max_m2": 250.0, "exige_justo_titulo": False, "escopo": "urbano",
    },
    "coletiva": {
        "label": "Coletiva", "fundamento": "art. 10 da Lei nº 10.257/2001 (Estatuto da Cidade)",
        "prazo_anos": 5, "prazo_reduzido": None, "condicao_reducao": None,
        "area_max_m2": None, "exige_justo_titulo": False, "escopo": "urbano",
    },
    "outra": {
        "label": "Outra (cartório define)", "fundamento": None,
        "prazo_anos": None, "prazo_reduzido": None, "condicao_reducao": None,
        "area_max_m2": None, "exige_justo_titulo": False, "escopo": "ambos",
    },
}


def fundamento_legal(projeto: dict) -> str:
    """Fundamento da modalidade escolhida (ou o texto livre quando 'outra')."""
    mod = projeto.get("modalidade_usucapiao") or "extraordinaria"
    info = MODALIDADES.get(mod) or {}
    return info.get("fundamento") or (projeto.get("fundamento_legal") or "").strip() or "—"


def _ano(v) -> Optional[int]:
    """Extrai o ano (int) de 2010 / '2010' / '2010-05-01'. None se vazio/atual."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    m = re.search(r"\d{4}", str(v))
    return int(m.group()) if m else None


def anos_cobertos(projeto: dict, ano_ref: Optional[int] = None) -> int:
    """Soma de posses (art. 1.243 CC): soma a duração dos períodos contíguos. Sem
    soma_posses, usa posse.inicio → ano de referência."""
    if ano_ref is None:
        ano_ref = datetime.now(timezone.utc).year
    periodos = projeto.get("soma_posses") or []
    total = 0
    if periodos:
        for p in periodos:
            ini = _ano(p.get("inicio"))
            fim = _ano(p.get("fim")) or ano_ref
            if ini is not None:
                total += max(0, fim - ini)
        return total
    ini = _ano((projeto.get("posse") or {}).get("inicio"))
    return max(0, ano_ref - ini) if ini is not None else 0


def validar_posse(projeto: dict, ano_ref: Optional[int] = None) -> dict:
    """Valida tempo de posse (vs prazo da modalidade) e área (vs limite), com a
    exceção do STF Tema 815 para a especial urbana. Retorna o relatório (não trava)."""
    mod = projeto.get("modalidade_usucapiao") or "extraordinaria"
    info = MODALIDADES.get(mod) or MODALIDADES["outra"]
    avisos = []

    cobertos = anos_cobertos(projeto, ano_ref)
    prazo = info.get("prazo_anos")
    prazo_ok = True if prazo is None else cobertos >= prazo
    faltam = 0 if (prazo is None or prazo_ok) else (prazo - cobertos)

    area = projeto.get("area_declarada_m2")
    area_max = info.get("area_max_m2")
    area_ha_max = info.get("area_max_ha")
    if area_ha_max is not None and area is not None:
        area_ok = (area / 10000.0) <= area_ha_max
    elif area_max is not None and area is not None:
        area_ok = area <= area_max
    else:
        area_ok = True
    ignora_modulo = bool(info.get("ignora_modulo_municipal"))
    if ignora_modulo:
        avisos.append("STF Tema 815 (RE 422.349): a usucapião especial urbana não se "
                      "condiciona ao módulo mínimo de área municipal.")

    exige_jt = bool(info.get("exige_justo_titulo"))
    justo_titulo_ok = (not exige_jt) or bool((projeto.get("posse") or {}).get("justo_titulo"))
    if exige_jt and not justo_titulo_ok:
        avisos.append("Modalidade ordinária exige justo título e boa-fé (art. 1.242 CC).")

    return {
        "modalidade": mod, "fundamento": fundamento_legal(projeto),
        "anos_cobertos": cobertos, "prazo_exigido": prazo, "prazo_reduzido": info.get("prazo_reduzido"),
        "prazo_ok": prazo_ok, "faltam_anos": faltam,
        "area_m2": area, "area_max": area_max, "area_max_ha": area_ha_max, "area_ok": area_ok,
        "ignora_modulo_municipal": ignora_modulo,
        "exige_justo_titulo": exige_jt, "justo_titulo_ok": justo_titulo_ok,
        "avisos": avisos,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_usucapiao.py -k "modalidades or validar_posse" -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/services/geo_urbano/usucapiao.py backend/tests/test_usucapiao.py
git commit -m "feat(geo-urbano): catálogo de modalidades + validar_posse (usucapião)"
```

---

## Task 3: Serviço `usucapiao.py` — `checklist_para` + `anuentes_de`

**Files:**
- Modify: `backend/services/geo_urbano/usucapiao.py`
- Test: `backend/tests/test_usucapiao.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_usucapiao.py`:

```python
def _chaves(items):
    return {i["chave"] for i in items}


def test_checklist_base_e_ordinaria_justo_titulo():
    base = USU.checklist_para({"modalidade_usucapiao": "extraordinaria",
                               "situacao_registral": "nao_matriculado"})
    ch = _chaves(base)
    assert {"requerimento", "ata_notarial", "procuracao_oab", "planta_memorial",
            "art_trt"} <= ch
    assert "justo_titulo" not in ch          # extraordinária dispensa
    ord_ = USU.checklist_para({"modalidade_usucapiao": "ordinaria"})
    assert "justo_titulo" in _chaves(ord_)   # ordinária exige


def test_checklist_herdeiro_adiciona_obito_partilha():
    proj = {"modalidade_usucapiao": "extraordinaria",
            "soma_posses": [{"vinculo": "de_cujus", "inicio": "2008", "fim": "2018"}]}
    ch = _chaves(USU.checklist_para(proj))
    assert {"certidao_obito", "formal_partilha"} <= ch


def test_checklist_rural_adiciona_ccir_car():
    ch = _chaves(USU.checklist_para({"modalidade_usucapiao": "especial_rural"}))
    assert {"ccir", "car", "georef_sigef"} <= ch


def test_checklist_preserva_status_existente():
    proj = {"modalidade_usucapiao": "extraordinaria",
            "checklist": [{"chave": "requerimento", "status": "anexado", "upload_id": "img-1"}]}
    item = next(i for i in USU.checklist_para(proj) if i["chave"] == "requerimento")
    assert item["status"] == "anexado" and item["upload_id"] == "img-1"


def test_anuentes_de_funde_confrontantes_e_titular():
    proj = {
        "situacao_registral": "matriculado_terceiro",
        "matriculas": [{"matricula": "12.345",
                        "proprietario_registral": {"nome": "Antigo Dono", "doc": "111"}}],
        "matricula_usucapienda_id": None,
        "confrontantes": [{"confrontante": "Vizinho Sul", "lado": "frente",
                           "tipo": "particular", "medida_m": 12.0}],
        "anuentes": [],
    }
    out = USU.anuentes_de(proj)
    papeis = {a["papel"] for a in out}
    assert "confrontante" in papeis and "titular_tabular" in papeis
    tit = next(a for a in out if a["papel"] == "titular_tabular")
    assert tit["nome"] == "Antigo Dono"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_usucapiao.py -k "checklist or anuentes" -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'checklist_para'`.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/services/geo_urbano/usucapiao.py`:

```python
# ──────────────────────────────────────────────────────────────────────────────
# Checklist dinâmica de documentos (blocos A-G), por modalidade/situação/herdeiro.
# ──────────────────────────────────────────────────────────────────────────────
# Itens base sempre presentes: (bloco, chave, label, obrigatorio)
_CHECKLIST_BASE = [
    ("A", "requerimento", "Requerimento de reconhecimento (assinado por advogado)", True),
    ("A", "procuracao_oab", "Procuração + OAB do advogado", True),
    ("A", "ata_notarial", "Ata notarial de posse (tabelião de notas)", True),
    ("B", "planta_memorial", "Planta e memorial descritivo (assinados pelos confrontantes)", True),
    ("B", "art_trt", "ART/TRT/RRT — guia paga", True),
    ("C", "doc_requerente", "Documentos do requerente e cônjuge (CPF, RG/CNH)", True),
    ("C", "comprovante_endereco", "Comprovante de endereço", True),
    ("C", "certidao_estado_civil", "Certidão de estado civil (< 90 dias)", True),
    ("E", "provas_posse", "Provas do período aquisitivo (água/luz/IPTU/contratos)", True),
    ("F", "certidao_distribuidor", "Certidões negativas dos distribuidores (comarca do imóvel + domicílio)", True),
    ("G", "anuencia_confrontantes", "Declaração de anuência dos confrontantes", True),
]


def _eh_herdeiro(projeto: dict) -> bool:
    if any((p.get("papel") == "herdeiro") for p in (projeto.get("partes") or [])):
        return True
    return any((p.get("vinculo") == "de_cujus") for p in (projeto.get("soma_posses") or []))


def checklist_para(projeto: dict) -> list:
    """Monta a checklist dinâmica (blocos A-G). Preserva status/upload já marcados
    (casados por `chave`)."""
    mod = projeto.get("modalidade_usucapiao") or "extraordinaria"
    info = MODALIDADES.get(mod) or {}
    sit = projeto.get("situacao_registral") or "nao_matriculado"
    itens = list(_CHECKLIST_BASE)

    # D) Imóvel — varia pela situação registral
    if sit == "nao_matriculado":
        itens.append(("D", "negativa_propriedade", "Certidão negativa de propriedade (RI competente)", True))
    else:
        itens.append(("D", "certidao_matricula", "Certidão de inteiro teor da matrícula (atualizada)", True))
    itens += [
        ("D", "certidao_confrontante", "Certidões dos confrontantes (inteiro teor/negativas)", True),
        ("D", "certidao_negativa_onus", "Certidões negativas de ônus e ações reais", True),
        ("D", "iptu_valor_venal", "Carnê de IPTU/ITR + comprovante de valor venal", True),
        ("G", "anuencia_titular", "Anuência dos titulares de direitos da matrícula",
         sit != "nao_matriculado"),
    ]

    # Ordinária: exige justo título
    if info.get("exige_justo_titulo"):
        itens.append(("A", "justo_titulo", "Justo título (contrato/cessão de direitos)", True))

    # Caso herdeiro: óbito, partilha, certidões dos demais herdeiros, posse exclusiva
    if _eh_herdeiro(projeto):
        itens += [
            ("C", "certidao_obito", "Certidão de óbito do de cujus", True),
            ("C", "formal_partilha", "Formal de partilha / escritura de inventário", False),
            ("C", "certidao_herdeiros", "Certidões de nascimento/casamento dos demais herdeiros", True),
            ("C", "prova_posse_exclusiva", "Prova da posse exclusiva (rompimento da composse)", True),
        ]

    # Rural: georreferenciamento certificado + CCIR + CAR
    if info.get("escopo") == "rural":
        itens += [
            ("B", "georef_sigef", "Georreferenciamento certificado INCRA/SIGEF", True),
            ("B", "ccir", "CCIR", True),
            ("B", "car", "CAR (Cadastro Ambiental Rural)", True),
        ]

    # Preserva status/upload já marcados (por chave).
    atual = {i.get("chave"): i for i in (projeto.get("checklist") or [])}
    out = []
    for (bloco, chave, label, obrig) in itens:
        prev = atual.get(chave) or {}
        out.append({
            "bloco": bloco, "chave": chave, "label": label, "obrigatorio": bool(obrig),
            "status": prev.get("status") or "pendente",
            "upload_id": prev.get("upload_id"), "observacao": prev.get("observacao"),
        })
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Anuentes (planta/memorial) — confrontantes + titular tabular da matrícula.
# ──────────────────────────────────────────────────────────────────────────────
def _matricula_usucapienda(projeto: dict) -> dict:
    mid = projeto.get("matricula_usucapienda_id")
    mats = projeto.get("matriculas") or []
    if mid:
        for m in mats:
            if m.get("id") == mid:
                return m
    return mats[0] if mats else {}


def anuentes_de(projeto: dict) -> list:
    """Deriva os anuentes de `confrontantes` (lados) + titular tabular da matrícula,
    fundindo com os anuentes já cadastrados (por nome+doc)."""
    existentes = {((a.get("nome") or "").strip().lower(), (a.get("doc") or "")): a
                  for a in (projeto.get("anuentes") or [])}

    def _merge(base: dict) -> dict:
        chave = ((base.get("nome") or "").strip().lower(), (base.get("doc") or ""))
        prev = existentes.get(chave)
        if prev:
            merged = dict(base)
            merged.update({k: v for k, v in prev.items() if v not in (None, "")})
            return merged
        return base

    out = []
    for c in (projeto.get("confrontantes") or []):
        out.append(_merge({
            "papel": "confrontante", "nome": c.get("confrontante"), "doc": c.get("doc"),
            "lado": c.get("lado"), "medida_m": c.get("medida_m"),
            "tipo": c.get("tipo") or "particular", "endereco": c.get("endereco"),
            "telefone": c.get("telefone"), "canal": "presencial",
            "anuencia": {"status": "pendente"},
        }))

    if (projeto.get("situacao_registral") or "nao_matriculado") != "nao_matriculado":
        mat = _matricula_usucapienda(projeto)
        tit = (mat.get("proprietario_registral") or {}) if mat else {}
        if tit.get("nome"):
            out.append(_merge({
                "papel": "titular_tabular", "nome": tit.get("nome"), "doc": tit.get("doc"),
                "tipo": "particular", "canal": "presencial", "anuencia": {"status": "pendente"},
            }))

    # anuentes manuais que não vieram de confrontante/titular
    vistos = {((a.get("nome") or "").strip().lower(), (a.get("doc") or "")) for a in out}
    for a in (projeto.get("anuentes") or []):
        chave = ((a.get("nome") or "").strip().lower(), (a.get("doc") or ""))
        if chave not in vistos:
            out.append(a)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_usucapiao.py -k "checklist or anuentes" -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/services/geo_urbano/usucapiao.py backend/tests/test_usucapiao.py
git commit -m "feat(geo-urbano): checklist dinâmica + anuentes_de (usucapião)"
```

---

## Task 4: Gerador — Requerimento de Usucapião

**Files:**
- Modify: `backend/services/geo_urbano/generators/textos.py`
- Modify: `backend/services/geo_urbano/generators/pdf.py`
- Test: `backend/tests/test_usucapiao.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_usucapiao.py`:

```python
from services.geo_urbano.generators import pdf as GPDF


def _pdf_text(data: bytes) -> str:
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)


def _proj_usucapiao():
    return {
        "denominacao_imovel": "Lote 12 — Quadra 8 — Vila São Francisco",
        "tipo_servico": "usucapiao", "modalidade_usucapiao": "extraordinaria",
        "situacao_registral": "nao_matriculado", "municipio": "Açailândia", "uf": "MA",
        "tema": "prime_i", "endereco": "Rua Safira, nº 147, Vila São Francisco",
        "area_declarada_m2": 360.0, "valor_atribuido": 85000.0,
        "posse": {"inicio": "2008", "origem": "ocupação para moradia",
                  "natureza": "mansa, pacífica, ininterrupta, com animus domini"},
        "soma_posses": [
            {"possuidor_nome": "Maria das Dores", "vinculo": "de_cujus", "inicio": "2008", "fim": "2018"},
            {"possuidor_nome": "João Filho", "vinculo": "proprio", "inicio": "2018", "fim": "atual"}],
        "partes": [
            {"papel": "requerente", "tipo_pessoa": "fisica", "nome": "João Filho",
             "cpf": "012.345.678-90", "estado_civil": "solteiro", "profissao": "lavrador"},
            {"papel": "advogado", "tipo_pessoa": "fisica", "nome": "Dra. Ana Souza",
             "oab": "OAB/MA 12345"}],
        "confrontantes": [
            {"confrontante": "Vizinho Norte", "lado": "fundo", "tipo": "particular", "medida_m": 12.0}],
        "cartorio": {"nome": "Cartório do 1º Ofício Extrajudicial da Comarca de Açailândia/MA",
                     "endereco": "Rua Bom Jesus, 236 — Centro — Açailândia/MA"},
    }


def test_requerimento_usucapiao_render():
    data = GPDF.gerar_pdf("requerimento_usucapiao", _proj_usucapiao(), "prime_i")
    assert _paginas(data) >= 1
    txt = _pdf_text(data)
    assert "USUCAPIÃO" in txt.upper()
    assert "1.238" in txt                      # fundamento da extraordinária
    assert "Maria das Dores" in txt            # possuidor somado
    assert "OAB/MA 12345" in txt               # advogado
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_usucapiao.py::test_requerimento_usucapiao_render -v`
Expected: FAIL — `ValueError: tipo de documento desconhecido: requerimento_usucapiao`.

- [ ] **Step 3: Write minimal implementation**

In `backend/services/geo_urbano/generators/textos.py`, append text helpers at the end:

```python
# ──────────────────────────────────────────────────────────────────────────────
# Usucapião Extrajudicial — textos auxiliares
# ──────────────────────────────────────────────────────────────────────────────
def soma_posses_texto(projeto: dict) -> str:
    """Descreve a soma de posses (art. 1.243 CC): possuidores anteriores + períodos."""
    periodos = projeto.get("soma_posses") or []
    if not periodos:
        return ""
    partes = []
    for p in periodos:
        per = " a ".join(x for x in (p.get("inicio"), p.get("fim")) if x)
        vinc = {"de_cujus": " (de cujus, posse somada)", "cedente": " (cedente)",
                "proprio": ""}.get(p.get("vinculo") or "proprio", "")
        partes.append(f"{p.get('possuidor_nome') or '—'}{vinc}: {per or '—'}")
    return ("Para o cômputo do prazo, soma-se a posse dos antecessores (art. 1.243 do "
            "Código Civil): " + "; ".join(partes) + ".")


def valor_atribuido_texto(projeto: dict) -> str:
    v = projeto.get("valor_atribuido")
    return f"R$ {_n_br(v)}" if v is not None else "—"
```

In `backend/services/geo_urbano/generators/pdf.py`, add the render function just before the `gerar_pdf` dispatcher (after `confrontantes_para_drl`, around line 588). Note `USU` import is added at module top:

At the top of `pdf.py`, after `from services.geo_urbano.generators import croqui as CROQUI` (line 21), add:

```python
from services.geo_urbano import usucapiao as USU
```

Update `_partes_assinatura` (around line 246) so papéis NÃO signatários do bloco do requerente (advogado/herdeiro/testemunha/titular_tabular) não saiam rotulados como "Requerente" — só requerente/cônjuge (e representante/sócio para PJ) assinam esse bloco. Replace the loop body's `papel` mapping + add a skip:

```python
def _partes_assinatura(projeto: dict):
    """Linhas de assinatura das partes (requerente PJ → representante; ou PF + cônjuge)."""
    _LABEL = {"requerente": "Requerente", "representante": "Representante legal",
              "socio": "Sócio", "conjuge": "Cônjuge anuente"}
    out = []
    for p in projeto.get("partes") or []:
        if p.get("papel") == "requerente" and p.get("tipo_pessoa") == "juridica":
            continue  # PJ assina via representante
        if p.get("papel") not in _LABEL:   # advogado/herdeiro/testemunha/titular: bloco próprio
            continue
        nome = p.get("nome") or p.get("razao_social") or ""
        if nome:
            out.append((nome, _LABEL[p.get("papel")]))
    if not out:
        out = [("", "Requerente")]
    return out
```

Add an advogado signature helper (used pelo Requerimento de Usucapião — art. 216-A exige advogado), e a render function, before `def gerar_pdf(`:

```python
def _bloco_advogado(projeto: dict, st, L):
    """Bloco de assinatura do ADVOGADO (com OAB) — exigido no usucapião (art. 216-A)."""
    from reportlab.platypus import KeepTogether
    adv = next((p for p in (projeto.get("partes") or []) if p.get("papel") == "advogado"), None)
    if not adv or not adv.get("nome"):
        return []
    oab = adv.get("oab") or ""
    if oab and adv.get("uf_oab") and adv["uf_oab"] not in oab:
        oab = f"OAB/{adv['uf_oab']} {oab}"
    linhas = [(adv["nome"], True), (f"Advogado(a) — {oab}".rstrip(" —"), False)]
    b = [Spacer(1, 42),
         Table([[""]], colWidths=[L * 0.6], style=[("LINEABOVE", (0, 0), (-1, -1), 0.8, black)])]
    for txt, bold in linhas:
        b.append(Paragraph(f"<b>{GP._esc(txt)}</b>" if bold else GP._esc(txt), st["assina"]))
    b.append(Spacer(1, 14))
    return [KeepTogether(b)]
```

Add the render function before `def gerar_pdf(`:

```python
# ──────────────────────────────────────────────────────────────────────────────
# Usucapião Extrajudicial — Requerimento, Ata Notarial, Anuência, Notificação, Edital
# ──────────────────────────────────────────────────────────────────────────────
def requerimento_usucapiao(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    d = projeto.get("cartorio") or {}
    story = []
    for ln in [f"Ao Ilustríssimo Senhor Oficial do {d.get('nome') or 'Cartório de Registro de Imóveis'}",
               d.get("endereco") or ""]:
        if ln:
            story.append(Paragraph(GP._esc(ln), st["corpo"]))
    story.append(Spacer(1, 16))
    story += GP._titulo("REQUERIMENTO DE USUCAPIÃO EXTRAJUDICIAL", cfg, st, L)

    info = USU.MODALIDADES.get(projeto.get("modalidade_usucapiao") or "extraordinaria") or {}
    fund = USU.fundamento_legal(projeto)
    intro = (TX.bloco_requerentes(projeto)
             + "por seu advogado adiante assinado (art. 216-A da Lei nº 6.015/1973), vem REQUERER "
             + f"o RECONHECIMENTO EXTRAJUDICIAL DE USUCAPIÃO, na modalidade {info.get('label') or '—'} "
             + f"({fund}), do imóvel adiante descrito:")
    story += GP._paras(intro, st["corpo"])

    # Descrição do imóvel (matrícula ou pedido de abertura de matrícula).
    sit = projeto.get("situacao_registral") or "nao_matriculado"
    mats = projeto.get("matriculas") or []
    if sit == "nao_matriculado" or not mats:
        desc = (f"Imóvel urbano denominado {projeto.get('denominacao_imovel') or '—'}, situado em "
                f"{projeto.get('endereco') or '—'}, no Município de {projeto.get('municipio') or ''}/"
                f"{projeto.get('uf') or ''}, com área de {TX.m2(projeto.get('area_declarada_m2'))}, "
                f"SEM REGISTRO ANTERIOR, requerendo-se a ABERTURA DE MATRÍCULA.")
    else:
        desc = TX.transcricao_matricula(mats[0], projeto.get("municipio") or "", projeto.get("uf") or "")
    story += GP._secao("DO IMÓVEL", cfg, st, L)
    story += GP._paras(desc, st["corpo"])

    # Da posse + soma de posses.
    posse = projeto.get("posse") or {}
    pcorpo = (f"O requerente exerce posse {posse.get('natureza') or 'mansa, pacífica e ininterrupta'} "
              f"sobre o imóvel desde {posse.get('inicio') or '—'}"
              + (f", com origem em {posse['origem']}" if posse.get("origem") else "") + ". "
              + TX.soma_posses_texto(projeto))
    if posse.get("benfeitorias"):
        pcorpo += (f" Existem as seguintes benfeitorias: {posse['benfeitorias']}"
                   + (f" (desde {posse['benfeitorias_data']})" if posse.get("benfeitorias_data") else "") + ".")
    story += GP._secao("DA POSSE", cfg, st, L)
    story += GP._paras(pcorpo, st["corpo"])

    # Confrontantes + valor atribuído.
    confs = projeto.get("confrontantes") or []
    if confs:
        rol = "; ".join(f"{(c.get('lado') or '').replace('_', ' ')}: {c.get('confrontante') or '—'}"
                        for c in confs)
        story += GP._secao("DOS CONFRONTANTES", cfg, st, L)
        story += GP._paras("O imóvel confronta com: " + rol + ".", st["corpo"])
    story += GP._paras(f"Valor atribuído ao imóvel: {TX.valor_atribuido_texto(projeto)}.", st["corpo"])

    story += GP._paras("Nestes termos,\nPede deferimento.", st["corpo"])
    story.append(Spacer(1, 4))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    story += _bloco_assinaturas_partes(projeto, st, L)
    story += _bloco_advogado(projeto, st, L)
    return _build(story, cfg, "Requerimento de Usucapião", logo_bytes)
```

In `gerar_pdf`, add the dispatch branch (before `raise ValueError(...)`):

```python
    if tipo == "requerimento_usucapiao":
        return requerimento_usucapiao(projeto, tema, logo_bytes)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_usucapiao.py::test_requerimento_usucapiao_render -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/geo_urbano/generators/textos.py backend/services/geo_urbano/generators/pdf.py backend/tests/test_usucapiao.py
git commit -m "feat(geo-urbano): gerador do Requerimento de Usucapião"
```

---

## Task 5: Geradores — Ata Notarial + Edital

**Files:**
- Modify: `backend/services/geo_urbano/generators/pdf.py`
- Test: `backend/tests/test_usucapiao.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_usucapiao.py`:

```python
def test_ata_notarial_render():
    data = GPDF.gerar_pdf("ata_notarial", _proj_usucapiao(), "prime_i")
    assert _paginas(data) >= 1
    txt = _pdf_text(data).upper()
    assert "ATA NOTARIAL" in txt
    assert "POSSE" in txt


def test_edital_usucapiao_render():
    data = GPDF.gerar_pdf("edital_usucapiao", _proj_usucapiao(), "prime_i")
    assert _paginas(data) >= 1
    assert "EDITAL" in _pdf_text(data).upper()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_usucapiao.py -k "ata_notarial or edital" -v`
Expected: FAIL — `ValueError: tipo de documento desconhecido: ata_notarial`.

- [ ] **Step 3: Write minimal implementation**

In `backend/services/geo_urbano/generators/pdf.py`, add after `requerimento_usucapiao` (before `gerar_pdf`):

```python
def ata_notarial(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    story = GP._titulo("MINUTA DE ATA NOTARIAL DE POSSE", cfg, st, L)
    story += GP._paras(
        "SAIBAM quantos esta virem que, perante o Tabelionato de Notas da circunscrição do imóvel, "
        "comparece o requerente abaixo qualificado, a fim de que seja lavrada ATA NOTARIAL atestando, "
        "com fé pública, o tempo, a natureza e as condições da posse exercida (art. 216-A da Lei nº "
        "6.015/1973; Provimento CNJ nº 149/2023).", st["corpo"])
    story += GP._paras(TX.bloco_requerentes(projeto), st["corpo"])
    posse = projeto.get("posse") or {}
    story += GP._secao("DA POSSE DECLARADA", cfg, st, L)
    story += GP._paras(
        f"O requerente declara exercer posse {posse.get('natureza') or 'mansa, pacífica e ininterrupta'} "
        f"sobre o imóvel denominado {projeto.get('denominacao_imovel') or '—'}, situado em "
        f"{projeto.get('endereco') or '—'}, {projeto.get('municipio') or ''}/{projeto.get('uf') or ''}, "
        f"desde {posse.get('inicio') or '—'}. {TX.soma_posses_texto(projeto)}", st["corpo"])
    testemunhas = [p for p in (projeto.get("partes") or []) if p.get("papel") == "testemunha"]
    if testemunhas:
        story += GP._secao("DAS TESTEMUNHAS", cfg, st, L)
        story += GP._paras("Ouvidas as testemunhas: "
                           + "; ".join(t.get("nome") or "—" for t in testemunhas) + ".", st["corpo"])
    story += GP._paras("Documentos apresentados e demais declarações são consignados pelo Tabelião no "
                       "ato da lavratura. Esta minuta serve de subsídio ao Tabelionato de Notas.", st["small"])
    story.append(Spacer(1, 6))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    story += _bloco_assinaturas_partes(projeto, st, L)
    return _build(story, cfg, "Minuta de Ata Notarial", logo_bytes)


def edital_usucapiao(projeto: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    info = USU.MODALIDADES.get(projeto.get("modalidade_usucapiao") or "extraordinaria") or {}
    story = GP._titulo("EDITAL DE RECONHECIMENTO EXTRAJUDICIAL DE USUCAPIÃO", cfg, st, L)
    story += GP._paras(
        "O Oficial de Registro de Imóveis FAZ SABER, para conhecimento de eventuais interessados "
        "incertos e não sabidos, que tramita pedido de reconhecimento extrajudicial de usucapião "
        f"(art. 216-A da Lei nº 6.015/1973; Provimento CNJ nº 149/2023), na modalidade "
        f"{info.get('label') or '—'} ({USU.fundamento_legal(projeto)}), referente ao imóvel "
        f"{projeto.get('denominacao_imovel') or '—'}, situado em {projeto.get('endereco') or '—'}, "
        f"{projeto.get('municipio') or ''}/{projeto.get('uf') or ''}, com área de "
        f"{TX.m2(projeto.get('area_declarada_m2'))}, requerido por "
        f"{TX.bloco_requerentes(projeto).rstrip(', ')}.", st["corpo"])
    story += GP._paras(
        "Ficam INTIMADOS eventuais interessados a se manifestarem no prazo de 15 (quinze) dias. "
        "Decorrido o prazo sem impugnação fundamentada, presumir-se-á a concordância (art. 216-A, "
        "§ 4º, da Lei nº 6.015/1973, com a redação da Lei nº 13.465/2017).", st["corpo"])
    story.append(Spacer(1, 6))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    return _build(story, cfg, "Edital de Usucapião", logo_bytes)
```

In `gerar_pdf`, add the branches (before `raise ValueError(...)`):

```python
    if tipo == "ata_notarial":
        return ata_notarial(projeto, tema, logo_bytes)
    if tipo == "edital_usucapiao":
        return edital_usucapiao(projeto, tema, logo_bytes)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_usucapiao.py -k "ata_notarial or edital" -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/services/geo_urbano/generators/pdf.py backend/tests/test_usucapiao.py
git commit -m "feat(geo-urbano): geradores Ata Notarial e Edital de Usucapião"
```

---

## Task 6: Geradores por-anuente — Declaração de Anuência + Notificação

**Files:**
- Modify: `backend/services/geo_urbano/generators/pdf.py`
- Test: `backend/tests/test_usucapiao.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_usucapiao.py`:

```python
def test_declaracao_anuencia_render():
    proj = _proj_usucapiao()
    anuente = {"papel": "confrontante", "nome": "Vizinho Norte", "lado": "fundo",
               "medida_m": 12.0, "doc": "CPF 111.222.333-44"}
    data = GPDF.declaracao_anuencia(proj, anuente, "prime_i")
    assert _paginas(data) >= 1
    txt = _pdf_text(data)
    assert "ANUÊNCIA" in txt.upper() and "Vizinho Norte" in txt


def test_notificacao_render():
    proj = _proj_usucapiao()
    anuente = {"papel": "confrontante", "nome": "Vizinho Norte", "lado": "fundo"}
    data = GPDF.notificacao(proj, anuente, "prime_i")
    assert _paginas(data) >= 1
    assert "NOTIFICA" in _pdf_text(data).upper()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_usucapiao.py -k "declaracao_anuencia or notificacao" -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'declaracao_anuencia'`.

- [ ] **Step 3: Write minimal implementation**

In `backend/services/geo_urbano/generators/pdf.py`, add after `edital_usucapiao` (before `gerar_pdf`):

```python
def declaracao_anuencia(projeto: dict, anuente: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    nome = anuente.get("nome") or "—"
    papel = "TITULAR DE DIREITOS" if anuente.get("papel") == "titular_tabular" else "CONFRONTANTE"
    story = GP._titulo("DECLARAÇÃO DE ANUÊNCIA", cfg, st, L)
    qual = []
    if anuente.get("doc"):
        qual.append(f"inscrito(a) sob o nº {anuente['doc']}")
    if anuente.get("endereco"):
        qual.append(f"residente e domiciliado(a) em {anuente['endereco']}")
    lado_txt = ""
    if anuente.get("lado"):
        lado_txt = (f", especialmente quanto ao lado {(anuente.get('lado') or '').replace('_', ' ').upper()}"
                    f", medindo {TX.metros(anuente.get('medida_m'))}")
    corpo = (
        f"Eu, {nome}{(', ' + ', '.join(qual)) if qual else ''}, na qualidade de {papel} do imóvel "
        f"objeto do pedido de reconhecimento extrajudicial de usucapião — {projeto.get('denominacao_imovel') or '—'}, "
        f"situado em {projeto.get('endereco') or '—'}, {projeto.get('municipio') or ''}/{projeto.get('uf') or ''} —, "
        f"DECLARO, para os fins do art. 216-A da Lei nº 6.015/1973, RECONHECER e ANUIR com os limites e "
        f"confrontações constantes da Planta e do Memorial Descritivo do referido imóvel{lado_txt}, nada "
        f"tendo a opor ao presente pedido."
    )
    story += GP._paras(corpo, st["corpo"])
    story.append(Spacer(1, 6))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    story += GP._bloco_assinaturas([(nome, papel.title() + " anuente")], st, L)
    return _build(story, cfg, f"Anuência — {nome}", logo_bytes)


def notificacao(projeto: dict, anuente: dict, tema: str, logo_bytes=None) -> bytes:
    cfg = GP._cfg(tema)
    st = GP._styles(cfg)
    L = _largura()
    nome = anuente.get("nome") or "—"
    story = GP._titulo("NOTIFICAÇÃO DE CONFRONTANTE", cfg, st, L)
    story += GP._paras(
        f"Prezado(a) Sr.(a) {nome},", st["corpo"])
    story += GP._paras(
        "Fica V.Sa. NOTIFICADO(A), na qualidade de confrontante/titular de direitos, acerca do pedido "
        f"de reconhecimento extrajudicial de usucapião do imóvel {projeto.get('denominacao_imovel') or '—'}, "
        f"situado em {projeto.get('endereco') or '—'}, {projeto.get('municipio') or ''}/{projeto.get('uf') or ''}, "
        "para que se manifeste no prazo de 15 (quinze) dias. O silêncio será interpretado como CONCORDÂNCIA "
        "(art. 216-A, § 4º, da Lei nº 6.015/1973, com a redação da Lei nº 13.465/2017).", st["corpo"])
    story.append(Spacer(1, 6))
    story.append(Paragraph(GP._esc(_data_extenso(projeto.get("municipio") or "Açailândia",
                                                 projeto.get("uf") or "MA")), st["corpo_c"]))
    return _build(story, cfg, f"Notificação — {nome}", logo_bytes)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_usucapiao.py -k "declaracao_anuencia or notificacao" -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/services/geo_urbano/generators/pdf.py backend/tests/test_usucapiao.py
git commit -m "feat(geo-urbano): geradores Declaração de Anuência e Notificação (usucapião)"
```

---

## Task 7: Seed do caso "herdeiro" + dossiê de Usucapião

**Files:**
- Modify: `backend/services/geo_urbano/seed.py`
- Modify: `backend/services/geo_urbano/generators/dossie.py`
- Test: `backend/tests/test_usucapiao.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_usucapiao.py`:

```python
from services.geo_urbano.seed import build_seed_usucapiao
from services.geo_urbano.generators import dossie as DOSSIE


def test_seed_usucapiao_valido():
    doc = build_seed_usucapiao("u-test")
    m = GeoUrbanoProjeto(**doc)
    assert m.tipo_servico == "usucapiao"
    assert m.modalidade_usucapiao == "extraordinaria"
    assert any(p.vinculo == "de_cujus" for p in m.soma_posses)   # caso herdeiro
    # a soma de posses alcança o prazo da extraordinária (15 anos)
    r = USU.validar_posse(doc, ano_ref=2026)
    assert r["prazo_ok"] is True


def test_dossie_usucapiao_ordem_e_render():
    assert DOSSIE.ORDEM_DOSSIE_USUCAPIAO[0][0] == "requerimento_usucapiao"
    doc = build_seed_usucapiao("u-test")
    secoes = [
        ("Requerimento de Usucapião", [GPDF.gerar_pdf("requerimento_usucapiao", doc, "prime_i")]),
        ("Minuta de Ata Notarial", [GPDF.gerar_pdf("ata_notarial", doc, "prime_i")]),
        ("Memorial Descritivo", [GPDF.gerar_pdf("memorial_descritivo", doc, "prime_i")]),
        ("Edital", [GPDF.gerar_pdf("edital_usucapiao", doc, "prime_i")]),
    ]
    doss = DOSSIE.gerar_dossie_ordenado(doc, secoes)
    assert _paginas(doss) >= 6   # capa + sumário + 4 peças
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_usucapiao.py -k "seed_usucapiao or dossie_usucapiao" -v`
Expected: FAIL — `ImportError: cannot import name 'build_seed_usucapiao'`.

- [ ] **Step 3: Write minimal implementation**

In `backend/services/geo_urbano/generators/dossie.py`, add the ordering constant after `ORDEM_DOSSIE` (around line 41):

```python
# Ordem de protocolo do dossiê de USUCAPIÃO (art. 216-A LRP / Prov. CNJ 149/2023).
ORDEM_DOSSIE_USUCAPIAO = [
    ("requerimento_usucapiao", "Requerimento de Usucapião (advogado)"),
    ("ata_notarial", "Ata Notarial de Posse"),
    ("planta_mapa", "Planta / Mapa Georreferenciado"),
    ("memorial_descritivo", "Memorial Descritivo"),
    ("art_trt", "ART / TRT / RRT"),
    ("certidao_matricula", "Certidão da Matrícula / Negativa de Propriedade"),
    ("declaracoes_anuencia", "Declarações de Anuência (confrontantes/titulares)"),
    ("certidoes_confrontantes", "Certidões dos Confrontantes"),
    ("certidoes_negativas", "Certidões Negativas (ônus / ações reais)"),
    ("iptu_valor_venal", "IPTU / Valor Venal"),
    ("provas_posse", "Provas de Posse (linha do tempo)"),
    ("relatorio_fotografico", "Relatório Fotográfico"),
    ("docs_herdeiro", "Documentos do Herdeiro (óbito / partilha)"),
    ("justo_titulo", "Justo Título"),
    ("certidoes_distribuidores", "Certidões dos Distribuidores"),
    ("notificacoes_edital", "Notificações / Edital"),
    ("docs_requerente", "Documentos Pessoais do Requerente"),
]
```

In `backend/services/geo_urbano/seed.py`, add at the end of the file:

```python
def build_seed_usucapiao(user_id: str = "") -> dict:
    """Caso-teste do HERDEIRO: usucapião extraordinária com soma da posse do de cujus
    (2008–2018) + posse própria do herdeiro (2018–atual) sobre lote urbano em
    Açailândia/MA, imóvel sem registro (pede abertura de matrícula)."""
    from models.geo_urbano import (
        GeoUrbanoProjeto, Parte, Posse, PossePeriodo, ProvaPosse,
        AnuenteUsucapiao, Confrontacao, Vertice, calcular_completude,
    )
    partes = [
        Parte(papel="requerente", tipo_pessoa="fisica", nome="João Filho da Silva",
              cpf="012.345.678-90", rg="0123456 SSP/MA", nacionalidade="brasileiro",
              estado_civil="solteiro", profissao="lavrador",
              filiacao="filho de José da Silva e Maria das Dores da Silva",
              endereco="Rua Safira, nº 147, Vila São Francisco, Açailândia/MA"),
        Parte(papel="advogado", tipo_pessoa="fisica", nome="Dra. Ana Souza",
              oab="12345", uf_oab="MA",
              endereco="Av. Central, nº 100, Centro, Açailândia/MA"),
        Parte(papel="herdeiro", tipo_pessoa="fisica", nome="Pedro da Silva",
              cpf="098.765.432-10", nacionalidade="brasileiro", estado_civil="casado"),
        Parte(papel="testemunha", tipo_pessoa="fisica", nome="Carlos Pereira"),
    ]
    confs = [
        Confrontacao(lado="frente", medida_m=12.0, confrontante="Rua Safira"),
        Confrontacao(lado="lateral_direita", medida_m=30.0, confrontante="Lote 13"),
        Confrontacao(lado="lateral_esquerda", medida_m=30.0, confrontante="Lote 11"),
        Confrontacao(lado="fundo", medida_m=12.0, confrontante="Lote 20 (Vizinho Norte)"),
    ]
    proj = GeoUrbanoProjeto(
        user_id=user_id,
        denominacao_imovel="Lote 12 — Quadra 8 — Vila São Francisco",
        tipo_servico="usucapiao", tema="prime_i", status="conferencia",
        modalidade_usucapiao="extraordinaria", situacao_registral="nao_matriculado",
        municipio="Açailândia", uf="MA", bairro="Vila São Francisco", quadra="8",
        lote_resultante="12",
        endereco="Rua Safira, nº 147, Quadra 8, Lote 12, Vila São Francisco, Açailândia/MA",
        area_declarada_m2=360.00, perimetro_m=84.00, valor_atribuido=85000.00,
        posse=Posse(inicio="2008", origem="ocupação para moradia da família",
                    benfeitorias="casa de alvenaria com 3 cômodos", benfeitorias_data="2009"),
        soma_posses=[
            PossePeriodo(possuidor_nome="Maria das Dores da Silva", vinculo="de_cujus",
                         inicio="2008", fim="2018",
                         observacao="posse da genitora (de cujus), somada por sucessão"),
            PossePeriodo(possuidor_nome="João Filho da Silva", vinculo="proprio",
                         inicio="2018", fim="atual",
                         observacao="posse exclusiva do herdeiro (rompimento da composse)"),
        ],
        provas_posse=[
            ProvaPosse(tipo="iptu", ano="2010", descricao="Carnê de IPTU 2010"),
            ProvaPosse(tipo="luz", ano="2014", descricao="Fatura de energia 2014"),
            ProvaPosse(tipo="agua", ano="2020", descricao="Fatura de água 2020"),
        ],
        confrontantes=[],   # preenchidos como dicts logo após o model_dump (abaixo)
        anuentes=[AnuenteUsucapiao(papel="confrontante", nome="Vizinho Norte",
                                   lado="fundo", medida_m=12.0, tipo="particular",
                                   canal="presencial")],
        partes=partes,
    )
    doc = proj.model_dump(mode="json")
    # confrontantes da poligonal (usados pela anuência/requerimento)
    doc["confrontantes"] = [
        {"id": c.lado, "lado": c.lado, "confrontante": c.confrontante, "medida_m": c.medida_m,
         "tipo": "particular"} for c in confs]
    doc["completude"] = calcular_completude(doc)
    return doc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_usucapiao.py -k "seed_usucapiao or dossie_usucapiao" -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the FULL usucapião suite + the existing geo_urbano suite (no regressions)**

Run: `python -m pytest tests/test_usucapiao.py tests/test_geo_urbano.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/services/geo_urbano/seed.py backend/services/geo_urbano/generators/dossie.py backend/tests/test_usucapiao.py
git commit -m "feat(geo-urbano): seed do caso herdeiro + ordem do dossiê de usucapião"
```

---

## Task 8: Fiação nas rotas — geração, dossiê, persistência, validação/checklist, seed

**Files:**
- Modify: `backend/routes/geo_urbano.py`
- Test: smoke de import (rotas não têm test client no módulo) + suíte existente.

- [ ] **Step 1: Add the usucapião generated doc-types + upload tipos**

In `backend/routes/geo_urbano.py`, add to `_DOCS_GERAVEIS` (around line 73):

```python
_DOCS_GERAVEIS = {"requerimento_cartorio", "requerimento_superintendencia",
                  "memorial_descritivo", "cadeia_dominical", "oficio_aprovacao",
                  "quadro_retificacao",
                  # usucapião
                  "requerimento_usucapiao", "ata_notarial", "edital_usucapiao"}
```

Add the usucapião upload tipos to `_TIPOS_UPLOAD` (inside the set, around line 52):

```python
    # usucapião
    "planta_usucapiao", "ata_notarial_assinada", "certidao_matricula", "negativa_propriedade",
    "certidao_confrontante", "certidao_negativa", "iptu_usucapiao", "justo_titulo",
    "certidao_obito", "formal_partilha", "certidao_estado_civil", "procuracao_oab",
    "certidao_distribuidor", "prova_posse", "doc_requerente", "foto_imovel",
```

- [ ] **Step 2: Persist usucapião fields in `atualizar_projeto`**

In `atualizar_projeto` (around line 197), extend the `escalares` tuple with the usucapião scalars:

```python
                 # retificação
                 "retificacao_tipo",
                 # usucapião
                 "modalidade_usucapiao", "fundamento_legal", "valor_atribuido",
                 "situacao_registral", "matricula_usucapienda_id")
```

Add `posse` to the dict-merge groups loop (around line 216):

```python
    for grupo in ("cartorio", "superintendencia", "responsavel_tecnico", "posse"):
```

Add the usucapião arrays to the array-persist loop (around line 221):

```python
    for grupo in ("matriculas", "bci", "vertices", "partes", "iptu", "lotes_resultantes",
                  "vertices_atual", "confrontantes",
                  "soma_posses", "provas_posse", "anuentes", "checklist"):
```

- [ ] **Step 3: Add the usucapião branch to `_montar_dossie`**

In `_montar_dossie` (around line 694, after the `if tipo in ("remembramento", "desdobro"):` block, before the Retificação fallback), add:

```python
    # ── Usucapião Extrajudicial: ordem de protocolo do art. 216-A LRP
    if tipo == "usucapiao":
        req = assinadas.get("requerimento_usucapiao") \
            or await asyncio.to_thread(PDF.gerar_pdf, "requerimento_usucapiao", doc, tema, logo)
        memorial = assinadas.get("memorial_descritivo") \
            or await asyncio.to_thread(PDF.gerar_pdf, "memorial_descritivo", doc, tema, logo)
        ata = await asyncio.to_thread(PDF.gerar_pdf, "ata_notarial", doc, tema, logo)
        edital = await asyncio.to_thread(PDF.gerar_pdf, "edital_usucapiao", doc, tema, logo)
        from services.geo_urbano import usucapiao as USU
        anuentes = USU.anuentes_de(doc)
        decls = [await asyncio.to_thread(PDF.declaracao_anuencia, doc, a, tema, logo)
                 for a in anuentes if a.get("nome")]
        notifs = [await asyncio.to_thread(PDF.notificacao, doc, a, tema, logo)
                  for a in anuentes if a.get("nome")]
        secoes = [
            ("Requerimento de Usucapião (advogado)", [req]),
            ("Ata Notarial de Posse", (await _ub(doc, "ata_notarial_assinada")) or [ata]),
            ("Planta / Mapa Georreferenciado", await _ub(doc, "planta_usucapiao")),
            ("Memorial Descritivo", [memorial]),
            ("ART / TRT / RRT", await _ub(doc, "art_trt")),
            ("Certidão da Matrícula / Negativa de Propriedade",
             (await _ub(doc, "certidao_matricula")) + (await _ub(doc, "negativa_propriedade"))),
            ("Declarações de Anuência", decls),
            ("Certidões dos Confrontantes", await _ub(doc, "certidao_confrontante")),
            ("Certidões Negativas (ônus / ações reais)", await _ub(doc, "certidao_negativa")),
            ("IPTU / Valor Venal", await _ub(doc, "iptu_usucapiao")),
            ("Provas de Posse (linha do tempo)", await _ub(doc, "prova_posse")),
            ("Relatório Fotográfico", await _ub(doc, "foto_imovel")),
            ("Documentos do Herdeiro (óbito / partilha)",
             (await _ub(doc, "certidao_obito")) + (await _ub(doc, "formal_partilha"))),
            ("Justo Título", await _ub(doc, "justo_titulo")),
            ("Certidões dos Distribuidores", await _ub(doc, "certidao_distribuidor")),
            ("Notificações / Edital", notifs + [edital]),
            ("Documentos Pessoais do Requerente",
             (await _ub(doc, "doc_requerente")) + (await _ub(doc, "certidao_estado_civil"))
             + (await _ub(doc, "procuracao_oab"))),
        ]
        return await asyncio.to_thread(DOSSIE.gerar_dossie_ordenado, doc, secoes, capa_pdf)
```

- [ ] **Step 4: Add validation, checklist, anuência-PDF and seed endpoints**

Find the existing `seed` endpoint and the retificação endpoints (around line 394) to match the router style. Add these endpoints near them (use the same `router`, `_get`, `get_active_subscriber`, `Response`, `_PDF` already imported in the file):

```python
@router.get("/projetos/{pid}/usucapiao/validacao")
async def usucapiao_validacao(pid: str, ano_ref: int = Query(None),
                              uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    from services.geo_urbano import usucapiao as USU
    doc = await _get(db, pid, uid)
    return USU.validar_posse(doc, ano_ref)


@router.get("/projetos/{pid}/usucapiao/checklist")
async def usucapiao_checklist(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    from services.geo_urbano import usucapiao as USU
    doc = await _get(db, pid, uid)
    return {"checklist": USU.checklist_para(doc), "anuentes": USU.anuentes_de(doc)}


@router.get("/projetos/{pid}/usucapiao/anuencia/{aid}")
async def usucapiao_anuencia_pdf(pid: str, aid: str, modo: str = Query("declaracao"),
                                 tema: str = Query(None),
                                 uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    from services.geo_urbano import usucapiao as USU
    doc = await _get(db, pid, uid)
    await _injetar_logo(db, uid, doc)
    logo = doc.get("_brand_logo_bytes")
    tema = tema or doc.get("tema") or "prime_i"
    anuente = next((a for a in USU.anuentes_de(doc) if a.get("id") == aid or a.get("nome") == aid), None)
    if not anuente:
        raise HTTPException(status_code=404, detail="Anuente não encontrado.")
    fn = PDF.notificacao if modo == "notificacao" else PDF.declaracao_anuencia
    data = await asyncio.to_thread(fn, doc, anuente, tema, logo)
    nome = f"{modo}_{(anuente.get('nome') or aid)}.pdf"
    return Response(content=data, media_type=_PDF,
                    headers={"Content-Disposition": f'inline; filename="{nome}"'})
```

Find the existing `POST /projetos/seed` endpoint (search `def seed` / `build_seed`) and add a sibling that accepts a `tipo` query, or add a dedicated endpoint:

```python
@router.post("/projetos/seed-usucapiao")
async def criar_seed_usucapiao(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    from services.geo_urbano.seed import build_seed_usucapiao
    doc = build_seed_usucapiao(uid)
    doc["numero"] = await _numero(db)
    await db.geo_urbano_projetos.insert_one(doc)
    return serialize_doc(doc)
```

- [ ] **Step 5: Verify imports + the route serves the usucapião dossiê without DB**

Run (from `backend/`):

```bash
python -c "import routes; from routes import all_routers; print('routers:', len(all_routers))"
python -c "from services.geo_urbano.seed import build_seed_usucapiao; from services.geo_urbano.generators import pdf as P; d=build_seed_usucapiao('u'); print('dossie OK' if P.gerar_pdf('requerimento_usucapiao', d, 'prime_i')[:5]==b'%PDF-' else 'FAIL')"
```

Expected: prints `routers: <N>` (no import error) and `dossie OK`.

- [ ] **Step 6: Run the full suite (no regressions)**

Run: `python -m pytest tests/test_usucapiao.py tests/test_geo_urbano.py -v`
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add backend/routes/geo_urbano.py
git commit -m "feat(geo-urbano): fiação das rotas de usucapião (geração, dossiê, validação, checklist, seed)"
```

---

## Task 9: Bump de versão + verificação final

**Files:**
- Modify: `frontend/build-number.txt`
- Modify: `CLAUDE.md` (linha de estado atual)

- [ ] **Step 1: Incrementar o build-number**

Ler o valor atual de `frontend/build-number.txt` e incrementar +1. (Regra obrigatória do `CLAUDE.md` antes de qualquer deploy.)

- [ ] **Step 2: Atualizar a linha "Estado atual" no `CLAUDE.md`**

Adicionar uma linha de release no topo do bloco de versões descrevendo a Fase 1 do Usucapião (modelo + `usucapiao.py` modalidades/validação/checklist + geradores Requerimento/Ata/Anuência/Notificação/Edital + dossiê + rotas + seed do herdeiro + testes), referenciando que é backend-only e que Fases 2 (frontend) e 3 (anuências ponta-a-ponta) seguem em planos próprios.

- [ ] **Step 3: Verificação final — suíte completa do módulo**

Run: `python -m pytest tests/test_usucapiao.py tests/test_geo_urbano.py -q`
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/build-number.txt CLAUDE.md
git commit -m "chore(geo-urbano): usucapião Fase 1 (backend) — bump versão + changelog"
```

---

## Notas de implementação

- **`GP._bloco_assinaturas`** existe (usado por `drl`); **`_bloco_assinaturas_partes`** é local do `pdf.py` (usado por `requerimento`). Use cada um como mostrado.
- **`GP._cfg/_styles/_titulo/_secao/_paras/_esc`** vêm de `services.georef.generators.pdf`. Não reimplemente.
- **Import circular:** `usucapiao.py` NÃO importa `pdf.py`; `pdf.py` importa `usucapiao` (catálogo/fundamento). No `_montar_dossie` o import de `usucapiao` é local (dentro da função) para espelhar o padrão já usado com `RET`.
- **Determinismo dos testes:** `validar_posse(projeto, ano_ref=...)` sempre recebe `ano_ref` explícito nos testes (não depende da data atual).
- **Sem alteração de comportamento** em Remembramento/Desdobro/Retificação: todas as mudanças em `pdf.py`/`dossie.py`/`routes` são branches/itens novos.
- **Refinamento conhecido (Fase 2):** o `memorial()` compartilhado renderiza um bloco "Superintendência — Aprovação municipal" e o marcador "(X) Urbano" fixos — corretos para os serviços municipais, mas inadequados para usucapião (sem Superintendência; pode ser rural). Não quebra a Fase 1 (o memorial gera PDF válido), mas o bloco do RT/aprovação do memorial deve ser tornado `tipo_servico`-aware na Fase 2.
- **`_partes_assinatura` agora filtra** papéis não-signatários (advogado/herdeiro/testemunha/titular_tabular) — isso é inócuo para Remembramento/Desdobro/Retificação (cujas `partes` só têm requerente/representante/sócio), e necessário para o usucapião não poluir o bloco do requerente.
```
