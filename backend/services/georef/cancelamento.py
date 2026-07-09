# @module services.georef.cancelamento — Requerimento de Cancelamento de Parcela SIGEF
# Base normativa: OFÍCIO CIRCULAR Nº 814/2026/DF/SEDE/INCRA (Processo SEI 54000.080781/2026-84)
# — "Evoluções nos Requerimentos de CANCELAMENTO no Sistema de Gestão Fundiária (SIGEF)".
"""Catálogo das Justificativas Pré-estabelecidas + geração do checklist do requerimento
de cancelamento de parcela georreferenciada (glebas rurais) junto ao INCRA/SIGEF."""
from __future__ import annotations

REFERENCIA_NORMATIVA = (
    "Ofício Circular nº 814/2026/DF/SEDE/INCRA — Processo SEI nº 54000.080781/2026-84"
)

# ──────────────────────────────────────────────────────────────────────────────
# Justificativas Pré-estabelecidas (item 2.1 do Ofício Circular 814/2026) — I a X.
# Cada uma traz os documentos EXIGIDOS pelo INCRA e quem deve assinar o requerimento.
# ──────────────────────────────────────────────────────────────────────────────
JUSTIFICATIVAS = [
    {
        "id": "alteracao_rt", "num": "I",
        "titulo": "Alteração de Responsável Técnico",
        "descricao": "Um novo credenciado será responsável pelo georreferenciamento do "
                     "imóvel rural no SIGEF, independentemente de haver retificação de perímetro.",
        "assinante": "Detentor", "exige_ods": True,
        "documentos": [
            "Documento de responsabilidade técnica do serviço (ART/TRT/RRT)",
            "Requerimento de cancelamento assinado pelo detentor",
            "Arquivos do levantamento e obtenção das coordenadas",
            "Cópia da certidão de matrícula atualizada",
            "Outros documentos que o credenciado entender necessários",
        ],
    },
    {
        "id": "unificacao", "num": "II",
        "titulo": "Unificação / Remembramento",
        "descricao": "Unificar duas ou mais parcelas já existentes no SIGEF, cadastradas em "
                     "nome de um mesmo detentor, em uma única certificação.",
        "assinante": "Detentor", "exige_ods": True,
        "documentos": [
            "Documento de responsabilidade técnica do serviço (ART/TRT/RRT)",
            "Requerimento de cancelamento assinado pelo detentor",
            "Cópia(s) da(s) certidão(ões) de matrícula",
            "Relação das parcelas a serem unificadas/remembradas",
            "Arquivos do levantamento e obtenção das coordenadas (caso não seja o RT da parcela)",
        ],
    },
    {
        "id": "erro_tecnico", "num": "III",
        "titulo": "Erro técnico",
        "descricao": "Quando um terceiro relata a existência de erro técnico em parcela "
                     "inserida no SIGEF que impede a certificação pretendida. Se houver "
                     "sobreposição real entre matrículas com litígio dominial, use \"Litígio Dominial\".",
        "assinante": "Detentor", "exige_ods": True,
        "documentos": [
            "Informação técnica caracterizando que a sobreposição ou o afastamento se deu por erro técnico",
            "Reconstituição de matrícula",
            "Cópia das certidões de matrículas envolvidas",
            "Documento de responsabilidade técnica (ART/TRT/RRT)",
            "Arquivos do levantamento e obtenção das coordenadas",
            "Outros documentos que o credenciado entender necessários",
        ],
    },
    {
        "id": "correcao_perimetro", "num": "IV",
        "titulo": "Correção de Perímetro",
        "descricao": "Correção de geometria de parcela no SIGEF a pedido do Responsável Técnico.",
        "assinante": "Detentor", "exige_ods": True,
        "documentos": [
            "Justificativa para a correção",
            "Documento de responsabilidade técnica (ART/TRT/RRT)",
            "Requerimento de cancelamento assinado pelo detentor",
            "Cópia da certidão de matrícula",
            "Arquivos do levantamento e obtenção das coordenadas",
        ],
    },
    {
        "id": "individualizacao_rt", "num": "V",
        "titulo": "Individualização de Responsabilidade Técnica",
        "descricao": "Separar certificações de um mesmo profissional credenciado que possuem "
                     "diferentes documentos de responsabilidade técnica.",
        "assinante": "Detentor (se o documento de RT não estiver por ele assinado)", "exige_ods": True,
        "documentos": [
            "Justificativa técnica para a individualização",
            "Documento de responsabilidade técnica (ART/TRT/RRT)",
            "Requerimento de cancelamento assinado pelo detentor (caso o documento de RT não esteja por ele assinado)",
        ],
    },
    {
        "id": "divisao_geometria", "num": "VI",
        "titulo": "Divisão de Geometria",
        "descricao": "Fracionamento que não se relaciona com desmembramento — ex.: separação "
                     "de estrada, divisa municipal, usucapião/estremação/Gleba Legal, "
                     "certificação com matrículas preexistentes, entre outros.",
        "assinante": "Detentor", "exige_ods": True,
        "documentos": [
            "Documento de responsabilidade técnica do serviço (ART/TRT/RRT)",
            "Requerimento de cancelamento assinado pelo detentor",
            "Cópia das certidões de matrícula",
            "Arquivos do levantamento e obtenção das coordenadas",
            "Cópia dos documentos que justifiquem a divisão (caso o interessado não seja o detentor cadastrado)",
            "Outros documentos que o credenciado entender necessários",
        ],
    },
    {
        "id": "litigio_dominial", "num": "VII",
        "titulo": "Litígio Dominial",
        "descricao": "Sobreposição entre matrículas, total ou parcial. A conclusão do "
                     "requerimento se dará por determinação judicial ou acordo entre as partes.",
        "assinante": "Proprietário do imóvel prejudicado pela certificação", "exige_ods": True,
        "documentos": [
            "Documento de responsabilidade técnica do serviço (ART/TRT/RRT)",
            "Requerimento de cancelamento assinado pelo proprietário do imóvel prejudicado pela certificação",
            "Arquivos do levantamento e obtenção das coordenadas",
            "Cópias das certidões de matrícula envolvidas",
            "Arquivo gráfico com a plotagem das matrículas envolvidas",
            "Outros documentos que o credenciado entender necessários",
        ],
    },
    {
        "id": "impedimento_registro", "num": "VIII",
        "titulo": "Parcela com Impedimento de Registro",
        "descricao": "Exclusão de parcelas que representam estradas, corpos hídricos, processo "
                     "de usucapião não concluído e outros não passíveis de registro.",
        "assinante": "Detentor", "exige_ods": False,
        "documentos": [
            "Justificativa demonstrando a impossibilidade de prosseguimento do registro",
            "Documento de responsabilidade técnica do serviço (ART/TRT/RRT)",
            "Requerimento de cancelamento assinado pelo detentor",
        ],
    },
    {
        "id": "distrato", "num": "IX",
        "titulo": "Distrato",
        "descricao": "Distrato entre responsável técnico e proprietário do imóvel.",
        "assinante": "Proprietário e credenciado", "exige_ods": False,
        "documentos": [
            "Documento assinado pelo proprietário e pelo credenciado, OU",
            "Cancelamento do documento de responsabilidade técnica",
        ],
    },
    {
        "id": "publicas_regularizacao", "num": "X",
        "titulo": "Parcelas Públicas ou de Regularização Fundiária",
        "descricao": "Exclusão de parcelas referentes a Assentamentos Rurais, Glebas Públicas "
                     "e regularização fundiária.",
        "assinante": "Órgão público responsável (ou detentor, na regularização por destinação particular)",
        "exige_ods": True,
        "documentos": [
            "Requerimento de cancelamento emitido pelo órgão público responsável, citando o código da parcela SIGEF a ser cancelada",
            "Requerimento de cancelamento assinado pelo detentor ou procuração (regularização por destinação particular ou Serfal)",
            "Documento de responsabilidade técnica (nos casos de destinação particular)",
            "Arquivos do levantamento e obtenção das coordenadas e Planilha ODS (nos casos de destinação particular)",
        ],
    },
]

_JUST_BY_ID = {j["id"]: j for j in JUSTIFICATIVAS}

# Condições de DEFERIMENTO AUTOMÁTICO (item 1 do Ofício — i a viii).
CONDICOES_AUTO = [
    ("requerente_e_rt", "O requerente é o responsável técnico pela certificação."),
    ("natureza_particular", "A natureza da parcela objeto do cancelamento é particular."),
    ("sem_registro_sigef", "A parcela objeto do cancelamento não tem registro confirmado no SIGEF."),
    ("ods_uma_aba", "A Planilha ODS associada tem apenas uma aba de perímetro."),
    ("diff_pct_ok", "A área da parcela na Planilha ODS difere menos de 10% da parcela objeto do cancelamento."),
    ("diff_abs_ok", "A área da parcela na Planilha ODS difere menos de 25 hectares da parcela objeto do cancelamento."),
    ("nao_oriunda_auto", "A parcela objeto do cancelamento não é oriunda de cancelamento deferido automaticamente."),
    ("sncr_nao_inibido", "O código SNCR do imóvel não está inibido."),
]


def justificativa(jid):
    """Devolve o dict da justificativa por id (ou None)."""
    return _JUST_BY_ID.get((jid or "").strip())


def _num(v):
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        s = str(v).strip().replace(".", "").replace(",", ".") if "," in str(v) else str(v).strip()
        import re
        s = re.sub(r"[^\d.\-]", "", s)
        return float(s) if s not in ("", "-", ".") else None
    except Exception:
        return None


def _diff_areas(canc):
    """(diff_pct, diff_abs_ha) entre a área da parcela e a da Planilha ODS. None se faltar dado."""
    a, b = _num(canc.get("area_parcela_ha")), _num(canc.get("area_ods_ha"))
    if a is None or b is None or a == 0:
        return None, None
    d_abs = abs(a - b)
    return (d_abs / a * 100.0), d_abs


def _canc(projeto):
    return dict(projeto.get("cancelamento") or {})


def exige_ods(projeto) -> bool:
    """Planilha ODS obrigatória no campo 'nova certificação' (item 2.2), exceto quando a
    justificativa é distrato/impedimento de registro ou a parcela é oriunda de contrato/destinação
    particular (marcado pelo credenciado)."""
    canc = _canc(projeto)
    j = justificativa(canc.get("justificativa"))
    if j and not j.get("exige_ods", True):
        return False
    if canc.get("origem_contrato_destinacao_particular"):
        return False
    return True


def condicoes_automaticas(projeto) -> list:
    """Avalia as 8 condições de deferimento automático a partir dos dados do projeto.
    ok=True (atendida) / False (não atendida) / None (a verificar — faltam dados)."""
    canc = _canc(projeto)
    d_pct, d_abs = _diff_areas(canc)
    valores = {
        "requerente_e_rt": canc.get("requerente_e_rt", True),
        "natureza_particular": (canc.get("natureza") or "particular") == "particular",
        "sem_registro_sigef": not canc.get("registro_confirmado", False),
        "ods_uma_aba": canc.get("ods_uma_aba", True),
        "diff_pct_ok": (None if d_pct is None else d_pct < 10.0),
        "diff_abs_ok": (None if d_abs is None else d_abs < 25.0),
        "nao_oriunda_auto": not canc.get("oriunda_cancelamento_auto", False),
        "sncr_nao_inibido": not canc.get("sncr_inibido", False),
    }
    detalhes = {
        "diff_pct_ok": (f"Diferença de {d_pct:.2f}%".replace(".", ",") if d_pct is not None
                        else "Informe as áreas da parcela e da Planilha ODS"),
        "diff_abs_ok": (f"Diferença de {d_abs:.4f} ha".replace(".", ",") if d_abs is not None
                        else "Informe as áreas da parcela e da Planilha ODS"),
    }
    out = []
    for key, texto in CONDICOES_AUTO:
        out.append({"chave": key, "texto": texto, "ok": valores.get(key),
                    "detalhe": detalhes.get(key, "")})
    return out


def documentos_checklist(projeto) -> list:
    """Documentos exigidos pela justificativa selecionada + status marcado pelo credenciado."""
    canc = _canc(projeto)
    j = justificativa(canc.get("justificativa"))
    status = dict(canc.get("docs_status") or {})
    if not j:
        return []
    out = []
    for i, label in enumerate(j["documentos"]):
        key = f"{j['id']}_{i}"
        out.append({"chave": key, "label": label, "status": status.get(key, "pendente")})
    if exige_ods(projeto):
        out.append({"chave": f"{j['id']}_ods",
                    "label": "Planilha ODS associada no campo \"nova certificação\" (obrigatória)",
                    "status": status.get(f"{j['id']}_ods", "pendente")})
    return out


def deferimento_automatico(projeto) -> bool:
    """True quando TODAS as 8 condições estão atendidas (deferimento automático do SIGEF)."""
    return all(c["ok"] is True for c in condicoes_automaticas(projeto))


AVISOS = [
    "Após o protocolo com a Planilha ODS associada, o status ficará \"EM VERIFICAÇÃO\": confira "
    "se o protocolo está conforme seus objetivos. Requerimentos \"EM VERIFICAÇÃO\" há mais de 24 "
    "horas são indeferidos automaticamente pelo SIGEF (item 2.4).",
    "Validações: ERRO indefere automaticamente; ALERTA direciona à análise do INCRA (se protocolado); "
    "INFO apenas registra informação e não impede o protocolo (item 2.5).",
    "É possível alterar código de vértices ou coordenadas na Planilha ODS apenas se estiverem "
    "somente na parcela objeto do cancelamento — não, se também pertencerem a parcela confrontante (item 2.3).",
]


def checklist(projeto) -> dict:
    """Checklist completo do requerimento de cancelamento para o front/PDF."""
    canc = _canc(projeto)
    j = justificativa(canc.get("justificativa"))
    condicoes = condicoes_automaticas(projeto)
    docs = documentos_checklist(projeto)
    total = len(docs)
    ok = sum(1 for d in docs if d["status"] == "ok")
    return {
        "referencia": REFERENCIA_NORMATIVA,
        "justificativa": j,
        "justificativas": [{"id": x["id"], "num": x["num"], "titulo": x["titulo"]} for x in JUSTIFICATIVAS],
        "documentos": docs,
        "condicoes_auto": condicoes,
        "exige_ods": exige_ods(projeto),
        "deferimento_automatico": all(c["ok"] is True for c in condicoes) if j else False,
        "progresso": {"ok": ok, "total": total, "pct": (round(ok * 100 / total) if total else 0)},
        "avisos": AVISOS,
    }
