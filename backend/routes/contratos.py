# @module routes.contratos — CRUD Contratos Imobiliarios, versionamento com diff/SHA-256
import hashlib
import io
import json
import logging
import uuid as _uuid_module
from datetime import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pymongo import ReturnDocument
from pydantic import BaseModel
from bson import ObjectId
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

from db import get_db
from dependencies import get_active_subscriber, get_authenticated_user, serialize_doc
from models.contrato import (
    ContratoBase, Contrato, ContratoVersion, ContratoVersionDiff,
    TIPOS_CONTRATO,
)
from services.contrato_ia_service import (
    gerar_clausulas_contrato,
    gerar_clausulas_corretor,
    gerar_clausulas_exclusividade,
    validar_alertas_juridicos,
    calcular_penalidades,
    gerar_checklist,
)

router = APIRouter(tags=["contratos"])
logger = logging.getLogger("romatec")


# ──────────────────────────────────────────────────────────────────────────────
# Schemas auxiliares
# ──────────────────────────────────────────────────────────────────────────────

class ContratoCreate(BaseModel):
    tipo_contrato: str
    numero_contrato: Optional[str] = None
    cidade_assinatura: Optional[str] = None
    data_assinatura: Optional[str] = None
    foro_eleito: Optional[str] = None
    vendedores: Optional[List[Any]] = None
    compradores: Optional[List[Any]] = None
    corretor: Optional[Any] = None
    objeto: Optional[Any] = None
    pagamento: Optional[Any] = None
    procuracao: Optional[Any] = None
    etapas_concluidas: Optional[Any] = None
    etapas_concluidas_em: Optional[Any] = None
    config: Optional[Any] = None


class ContratoUpdate(BaseModel):
    tipo_contrato: Optional[str] = None
    status: Optional[str] = None
    cidade_assinatura: Optional[str] = None
    data_assinatura: Optional[str] = None
    foro_eleito: Optional[str] = None
    vendedores: Optional[List[Any]] = None
    compradores: Optional[List[Any]] = None
    corretor: Optional[Any] = None
    objeto: Optional[Any] = None
    pagamento: Optional[Any] = None
    procuracao: Optional[Any] = None
    etapas_concluidas: Optional[Any] = None
    etapas_concluidas_em: Optional[Any] = None
    clausulas: Optional[List[Any]] = None
    alertas_juridicos: Optional[List[Any]] = None
    testemunha_1: Optional[Any] = None
    testemunha_2: Optional[Any] = None
    incluir_logo: Optional[bool] = None
    incluir_recibo_arras: Optional[bool] = None
    incluir_checklist: Optional[bool] = None
    template_pdf: Optional[str] = None   # prime1 | prime2 | tradicional


class GerarClausulasRequest(BaseModel):
    tipo: Optional[str] = None  # sobreescreve o tipo do contrato se fornecido


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _strip_html_inline(s) -> str:
    """Remove HTML do editor rich text -> texto inline (p/ campos onus/benfeitorias no PDF)."""
    import re as _re
    if not s:
        return ""
    t = str(s)
    t = _re.sub(r"(?i)<br\s*/?>", " ", t)
    t = _re.sub(r"(?i)</(div|p|li|ul|ol|tr)>", " ", t)
    t = _re.sub(r"<[^>]+>", "", t)
    t = (t.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    return _re.sub(r"\s{2,}", " ", t).strip()


def _calculate_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _deep_diff(old: dict, new: dict, path: str = "") -> List[dict]:
    diffs = []
    all_keys = set(old.keys()) | set(new.keys())
    for key in all_keys:
        old_val = old.get(key)
        new_val = new.get(key)
        current_path = f"{path}.{key}" if path else key
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            diffs.extend(_deep_diff(old_val, new_val, current_path))
        elif isinstance(old_val, list) and isinstance(new_val, list):
            if old_val != new_val:
                diffs.append({"campo": current_path, "de": old_val, "para": new_val})
        elif old_val != new_val:
            diffs.append({"campo": current_path, "de": old_val, "para": new_val})
    return diffs


def _create_version(
    contrato_id: str,
    user_id: str,
    numero_versao: int,
    tipo: str,
    hash_sha256: str,
    diffs: List[dict],
    snapshot: Optional[dict] = None,
    numero_lacre: Optional[str] = None,
) -> dict:
    return {
        "id": str(_uuid_module.uuid4()),
        "contrato_id": contrato_id,
        "user_id": user_id,
        "numero_versao": numero_versao,
        "tipo": tipo,
        "hash_sha256": hash_sha256,
        "diffs": diffs,
        "snapshot": snapshot,
        "numero_lacre": numero_lacre,
        "created_at": datetime.utcnow(),
    }


def _contrato_query_by_cid(cid: str, uid: str) -> dict:
    query = {"user_id": uid}
    if ObjectId.is_valid(cid):
        query["$or"] = [{"id": cid}, {"_id": ObjectId(cid)}]
    else:
        query["id"] = cid
    return query


def _format_numero_cont(doc: dict) -> str:
    """Exibe a numeração no padrão CONT NNNN/AAAA derivada do numero_contrato
    armazenado (ex.: 'CV-2026-0001' -> 'CONT 0001/2026'). Não altera o dado salvo."""
    numero = (doc.get("numero_contrato") or "").strip()
    if not numero:
        return ""
    partes = numero.replace("CV-", "").replace("CONT-", "").split("-")
    if len(partes) >= 2 and partes[0].isdigit():
        ano, seq = partes[0], partes[1]
        return f"CONT {seq}/{ano}"
    if len(partes) >= 2 and partes[1].isdigit():
        seq, ano = partes[0], partes[1]
        return f"CONT {seq}/{ano}"
    return f"CONT {numero}"


def _parse_dt(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(value)[:len(fmt) + 2], fmt)
        except Exception:
            continue
    return None


def _compute_status_card(doc: dict) -> str:
    """Status do círculo do card (espelha o ciclo de vida do PTAM/spec PR-4):
    rascunho | concluido | assinado | ativo | denunciado | encerrado | rescindido.
    Derivado dos campos existentes, sem mutar o status armazenado."""
    status = (doc.get("status") or "").lower()
    assinado = (
        doc.get("icp_status") == "assinado"
        or doc.get("d4sign_status") == "assinado"
        or status == "assinado"
    )
    if doc.get("rescindido_em") or status in ("distratado", "rescindido"):
        return "rescindido"
    if assinado:
        fim = _parse_dt(doc.get("data_vigencia_fim"))
        if fim and datetime.utcnow() > fim:
            return "encerrado"
        if doc.get("denunciado_em"):
            return "denunciado"
        return "ativo" if fim else "assinado"
    if status in ("definitivo", "concluido", "em_revisao"):
        return "concluido"
    return "rascunho"


def _normalize_contrato_doc(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return doc
    raw_id = doc.get("_id")
    payload = serialize_doc(doc)
    if not payload.get("id") and raw_id is not None:
        payload["id"] = str(raw_id)
    payload["numero_display"] = _format_numero_cont(payload)
    payload["status_card"] = _compute_status_card(payload)
    return payload


_BLANK = "_______________"
_BLANK_BRL = "R$ _______________"
_BLANK_DATE = "___/___/______"
_BLANK_EXT = "_" * 45

_UNIDADES = [
    "", "um", "dois", "tres", "quatro", "cinco", "seis", "sete", "oito", "nove",
    "dez", "onze", "doze", "treze", "quatorze", "quinze", "dezesseis", "dezessete",
    "dezoito", "dezenove",
]
_DEZENAS = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
_CENTENAS = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos",
             "seiscentos", "setecentos", "oitocentos", "novecentos"]


def _centenas_ext(n: int) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "cem"
    parts = []
    c, r = divmod(n, 100)
    if c:
        parts.append(_CENTENAS[c])
    if r < 20:
        if r:
            parts.append(_UNIDADES[r])
    else:
        d, u = divmod(r, 10)
        parts.append(_DEZENAS[d])
        if u:
            parts.append(_UNIDADES[u])
    return " e ".join(parts)


def _extenso(valor: Any) -> str:
    """Converte valor monetario para extenso em portugues."""
    try:
        raw = str(valor).replace("R$", "").replace("\xa0", "").strip()
        raw = raw.replace(".", "").replace(",", ".")
        n = float(raw)
        if n <= 0:
            return _BLANK_EXT
    except Exception:
        return _BLANK_EXT

    inteiro = int(n)
    centavos = round((n - inteiro) * 100)

    parts: list[str] = []
    bi, resto = divmod(inteiro, 1_000_000_000)
    mi, resto = divmod(resto, 1_000_000)
    mil, u = divmod(resto, 1_000)

    if bi:
        parts.append(_centenas_ext(bi) + (" bilhao" if bi == 1 else " bilhoes"))
    if mi:
        parts.append(_centenas_ext(mi) + (" milhao" if mi == 1 else " milhoes"))
    if mil:
        s = "mil" if mil == 1 else (_centenas_ext(mil) + " mil")
        parts.append(s)
    if u:
        parts.append(_centenas_ext(u))

    if not parts:
        parts = ["zero"]

    reais_str = " e ".join(parts)
    reais_str += " real" if inteiro == 1 else " reais"

    if centavos:
        reais_str += " e " + _centenas_ext(centavos)
        reais_str += " centavo" if centavos == 1 else " centavos"

    return reais_str


def _safe_text(value: Any) -> str:
    """Codifica string para cp1252 (WinAnsiEncoding — Helvetica no PDF)."""
    text = str(value) if value is not None else ""
    return text.encode("cp1252", errors="replace").decode("cp1252")


def _s(value: Any, fallback: str = _BLANK) -> str:
    """Retorna valor formatado ou fallback se vazio."""
    if value is None or value == "" or value == 0:
        return fallback
    return _safe_text(str(value))


def _brl(value: Any) -> str:
    """Formata valor BRL ou retorna blank."""
    try:
        n = float(str(value).replace("R$", "").replace(".", "").replace(",", ".").strip())
        if n == 0:
            return _BLANK_BRL
        s = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except Exception:
        return _BLANK_BRL


def _fmt_brl(value: Any) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "R$ 0,00"
    s = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def _fmt_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, str) and value:
        return value
    return _BLANK_DATE


def _qualifica_pf(p: dict, role: str = "") -> str:
    """Formata qualificacao completa de pessoa fisica para o contrato."""
    nome = _s(p.get("nome"), _BLANK)
    cpf = _s(p.get("cpf"), _BLANK)
    rg = p.get("rg") or ""
    rg_orgao = p.get("rg_orgao") or ""
    nascimento = _fmt_date(p.get("nascimento"))
    estado_civil = _s(p.get("estado_civil"), _BLANK)
    profissao = _s(p.get("profissao"), _BLANK)
    nacionalidade = _s(p.get("nacionalidade"), "brasileiro(a)")
    endereco = _s(p.get("endereco"), _BLANK)
    cidade = _s(p.get("cidade"), _BLANK)
    uf = _s(p.get("uf"), _BLANK)
    cep = p.get("cep") or ""

    rg_part = f", RG {rg}" if rg else ""
    if rg and rg_orgao:
        rg_part = f", RG {rg} {rg_orgao}"

    # CNH (documento de habilitação) — opcional
    cnh = p.get("cnh") or ""
    cnh_cat = p.get("cnh_categoria") or ""
    cnh_orgao = p.get("cnh_orgao") or ""
    cnh_validade = _fmt_date(p.get("cnh_validade")) if p.get("cnh_validade") else ""
    cnh_part = ""
    if cnh:
        cnh_part = f", portador(a) da CNH n. {cnh}"
        if cnh_cat:
            cnh_part += f" categoria {cnh_cat}"
        if cnh_orgao:
            cnh_part += f" expedida pelo {cnh_orgao}"
        if cnh_validade:
            cnh_part += f", válida até {cnh_validade}"

    # Filiação — opcional
    mae = (p.get("filiacao_mae") or "").strip()
    pai = (p.get("filiacao_pai") or "").strip()
    filiacao_part = ""
    if mae and pai:
        filiacao_part = f", filho(a) de {_safe_text(pai)} e {_safe_text(mae)}"
    elif mae:
        filiacao_part = f", filho(a) de {_safe_text(mae)}"
    elif pai:
        filiacao_part = f", filho(a) de {_safe_text(pai)}"

    cep_part = f", CEP {cep}" if cep else ""
    loc = f"{endereco}, {cidade}-{uf}{cep_part}"

    qualif = (
        f"{nome}, {nacionalidade}, {estado_civil}, {profissao}, "
        f"portador(a) do CPF n. {cpf}{rg_part}{cnh_part}{filiacao_part}, "
        f"nascido(a) em {nascimento}, "
        f"residente em {loc}"
    )

    conjuge = p.get("conjuge_nome") or ""
    if conjuge:
        cjcpf = _s(p.get("conjuge_cpf"), _BLANK)
        cj = f"; conjuge: {_safe_text(conjuge)}, CPF {cjcpf}"
        cj_rg = p.get("conjuge_rg") or ""
        cj_rg_org = p.get("conjuge_rg_orgao") or ""
        if cj_rg:
            cj += f", RG {cj_rg}" + (f" {cj_rg_org}" if cj_rg_org else "")
        cj_cnh = p.get("conjuge_cnh") or ""
        if cj_cnh:
            cj += f", CNH n. {cj_cnh}"
            if p.get("conjuge_cnh_categoria"):
                cj += f" categoria {p['conjuge_cnh_categoria']}"
            if p.get("conjuge_cnh_orgao"):
                cj += f" expedida pelo {p['conjuge_cnh_orgao']}"
            if p.get("conjuge_cnh_validade"):
                cj += f", válida até {_fmt_date(p.get('conjuge_cnh_validade'))}"
        cj_mae = (p.get("conjuge_filiacao_mae") or "").strip()
        cj_pai = (p.get("conjuge_filiacao_pai") or "").strip()
        if cj_mae and cj_pai:
            cj += f", filho(a) de {_safe_text(cj_pai)} e {_safe_text(cj_mae)}"
        elif cj_mae:
            cj += f", filho(a) de {_safe_text(cj_mae)}"
        elif cj_pai:
            cj += f", filho(a) de {_safe_text(cj_pai)}"
        qualif += cj

    return _safe_text(qualif)


def _qualifica_pj(p: dict, role: str = "") -> str:
    """Formata qualificacao completa de pessoa juridica para o contrato."""
    razao = _s(p.get("razao_social") or p.get("nome"), _BLANK)
    cnpj = _s(p.get("cnpj"), _BLANK)
    endereco = _s(p.get("endereco"), _BLANK)
    cidade = _s(p.get("cidade"), _BLANK)
    uf = _s(p.get("uf"), _BLANK)
    rep_nome = _s(p.get("representante_nome") or p.get("nome"), _BLANK)
    rep_cpf = _s(p.get("representante_cpf"), _BLANK)
    rep_cargo = p.get("representante_cargo") or "representante legal"

    return _safe_text(
        f"{razao}, inscrita no CNPJ/MF sob n. {cnpj}, "
        f"com sede em {endereco}, {cidade}-{uf}, "
        f"neste ato representada por {rep_nome}, CPF {rep_cpf}, na qualidade de {rep_cargo}"
    )


def _nome_parte(parte: dict) -> str:
    if not isinstance(parte, dict):
        return ""
    return (
        parte.get("nome")
        or parte.get("razao_social")
        or (parte.get("pf") or {}).get("nome")
        or (parte.get("pj") or {}).get("razao_social")
        or (parte.get("pj") or {}).get("nome_fantasia")
        or ""
    )


def _extract_corpo_contrato(doc: dict) -> List[str]:
    # Prioridade: cláusulas estruturadas, depois campos textuais livres.
    clausulas = doc.get("clausulas")
    linhas: List[str] = []

    if isinstance(clausulas, list) and clausulas:
        for i, item in enumerate(clausulas, 1):
            if isinstance(item, dict):
                titulo = item.get("titulo") or item.get("nome") or f"Cláusula {i}"
                texto = item.get("texto") or item.get("conteudo") or ""
                if texto:
                    linhas.append(f"{titulo}: {texto}")
                else:
                    linhas.append(str(titulo))
            elif isinstance(item, str) and item.strip():
                linhas.append(item.strip())

    for key in ("corpo", "texto", "texto_contrato", "clausulas_texto"):
        value = doc.get(key)
        if isinstance(value, str) and value.strip():
            linhas.extend([p.strip() for p in value.split("\n") if p.strip()])

    if not linhas:
        linhas.append("Contrato sem cláusulas textuais cadastradas.")

    return linhas


def _pdf_styles() -> dict:
    ss = getSampleStyleSheet()
    verde = colors.HexColor("#1a4731")
    cinza = colors.HexColor("#4a4a4a")

    return {
        "titulo": ParagraphStyle("titulo", parent=ss["Heading1"], fontSize=14,
                                 textColor=verde, spaceAfter=4, leading=18),
        "subtitulo": ParagraphStyle("subtitulo", parent=ss["Heading2"], fontSize=11,
                                    textColor=verde, spaceAfter=3, spaceBefore=10, leading=14),
        "secao": ParagraphStyle("secao", parent=ss["Normal"], fontSize=9,
                                textColor=verde, fontName="Helvetica-Bold",
                                spaceAfter=2, spaceBefore=6, leading=12),
        "corpo": ParagraphStyle("corpo", parent=ss["Normal"], fontSize=9,
                                textColor=cinza, spaceAfter=3, leading=13),
        "clausula_titulo": ParagraphStyle("clausula_titulo", parent=ss["Normal"], fontSize=9,
                                          fontName="Helvetica-Bold", textColor=cinza,
                                          spaceAfter=2, spaceBefore=5, leading=12),
        "clausula_texto": ParagraphStyle("clausula_texto", parent=ss["Normal"], fontSize=9,
                                         textColor=cinza, spaceAfter=4, leading=13,
                                         leftIndent=10),
        "rodape": ParagraphStyle("rodape", parent=ss["Normal"], fontSize=7,
                                 textColor=colors.grey, alignment=1),
        "assinatura": ParagraphStyle("assinatura", parent=ss["Normal"], fontSize=9,
                                     textColor=cinza, alignment=1, spaceAfter=2, leading=13),
    }


def _xml_safe(text: str) -> str:
    """Escapa &, <, > soltos PRESERVANDO tags inline (b/i/u/br/strong/em) e entidades
    (&nbsp; etc.). Evita 'not well-formed' do ReportLab Paragraph quando o conteúdo
    tem caracteres especiais vindos dos dados do contrato (ônus, nomes, ficha...)."""
    import re as _re
    keep = _re.compile(
        r'(</?(?:b|i|u|br|strong|em)\s*/?>|&(?:[a-zA-Z][a-zA-Z0-9]{0,8}|#\d{1,6});)',
        _re.IGNORECASE,
    )
    parts = keep.split(str(text))
    for i in range(0, len(parts), 2):  # segmentos fora de tag/entidade permitida
        parts[i] = parts[i].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return "".join(parts)


def _p(text: str, style) -> Paragraph:
    return Paragraph(_safe_text(_xml_safe(text)), style)


def _generate_contrato_pdf_bytes(doc: dict, uid: str, empresa: str, raise_on_error: bool = False) -> bytes:
    contrato_id = str(doc.get("id") or doc.get("_id") or "-")
    styles = _pdf_styles()
    buffer = io.BytesIO()

    try:
        pdf = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
            topMargin=2 * cm, bottomMargin=2.5 * cm,
            title=f"Contrato {contrato_id}",
        )

        elems: list = []
        verde = colors.HexColor("#1a4731")

        # ── Cabeçalho ────────────────────────────────────────────────────────
        empresa_safe = _safe_text(empresa or "AvalieImob / Romatec")
        elems.append(_p(f"<b>{empresa_safe}</b>", styles["subtitulo"]))

        tipo_raw = doc.get("tipo_contrato") or ""
        TIPOS_LABEL = {
            "compra_venda": "COMPRA E VENDA DE IMOVEL",
            "promessa_compra_venda": "PROMESSA DE COMPRA E VENDA DE IMOVEL",
            "locacao_residencial": "LOCACAO RESIDENCIAL",
            "locacao_comercial": "LOCACAO COMERCIAL",
            "arras": "RECIBO DE ARRAS / SINAL",
            "permuta": "PERMUTA DE IMOVEIS",
            "intermediacao": "INTERMEDIACAO IMOBILIARIA",
            "cessao_direitos": "CESSAO DE DIREITOS",
            "comodato": "COMODATO",
            "distrato": "DISTRATO",
            "exclusividade": "EXCLUSIVIDADE DE INTERMEDIACAO",
            "locacao_rural": "LOCACAO RURAL",
            "arrendamento_rural": "ARRENDAMENTO RURAL",
            "compra_venda_veiculo": "COMPRA E VENDA DE VEICULO",
        }
        tipo_label = TIPOS_LABEL.get(tipo_raw, _safe_text(tipo_raw).upper() or "CONTRATO PARTICULAR")
        elems.append(_p(f"CONTRATO PARTICULAR DE {tipo_label}", styles["titulo"]))

        numero = _s(doc.get("numero_contrato"), "s/n")
        data_ass = _fmt_date(doc.get("data_assinatura"))
        cidade_ass = _s(doc.get("cidade_assinatura"), _BLANK)
        status = _s(doc.get("status"), "MINUTA")
        elems.append(_p(
            f"<b>Numero:</b> {numero} &nbsp;&nbsp; <b>Status:</b> {status} &nbsp;&nbsp; "
            f"<b>Data de assinatura:</b> {data_ass} &nbsp;&nbsp; <b>Foro:</b> {cidade_ass}",
            styles["corpo"]
        ))
        elems.append(HRFlowable(width="100%", thickness=1.2, color=verde, spaceAfter=8))

        # ── Das Partes ────────────────────────────────────────────────────────
        labels = doc.get("_labels", {})
        parte1_label = _safe_text(labels.get("parte1", "Vendedor"))
        parte2_label = _safe_text(labels.get("parte2", "Comprador"))

        elems.append(_p("DAS PARTES", styles["secao"]))

        vendedores = doc.get("vendedores") or []
        if not vendedores:
            elems.append(_p(f"<b>{parte1_label}(es):</b> {_BLANK}", styles["corpo"]))
        else:
            for i, v in enumerate(vendedores, 1):
                prefix = f"<b>{parte1_label} {i}:</b> " if len(vendedores) > 1 else f"<b>{parte1_label}:</b> "
                if isinstance(v, dict):
                    qualif = _qualifica_pj(v) if v.get("tipo") == "pj" else _qualifica_pf(v)
                else:
                    qualif = _safe_text(str(v))
                elems.append(_p(prefix + qualif + ".", styles["corpo"]))

        elems.append(Spacer(1, 4))

        compradores = doc.get("compradores") or []
        if not compradores:
            elems.append(_p(f"<b>{parte2_label}(es):</b> {_BLANK}", styles["corpo"]))
        else:
            for i, c in enumerate(compradores, 1):
                prefix = f"<b>{parte2_label} {i}:</b> " if len(compradores) > 1 else f"<b>{parte2_label}:</b> "
                if isinstance(c, dict):
                    qualif = _qualifica_pj(c) if c.get("tipo") == "pj" else _qualifica_pf(c)
                else:
                    qualif = _safe_text(str(c))
                elems.append(_p(prefix + qualif + ".", styles["corpo"]))

        # Corretor
        cor = doc.get("corretor") or {}
        if isinstance(cor, dict) and cor.get("incluir"):
            elems.append(Spacer(1, 4))
            cor_nome = _s(cor.get("nome"), _BLANK)
            cor_creci = _s(cor.get("creci"), _BLANK)
            cor_cpf = _s(cor.get("cpf_cnpj"), _BLANK)
            elems.append(_p(
                f"<b>Corretor(a):</b> {cor_nome}, CRECI {cor_creci}, CPF/CNPJ {cor_cpf}.",
                styles["corpo"]
            ))

        elems.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

        # ── Do Imóvel / Objeto ────────────────────────────────────────────────
        obj = doc.get("objeto") or {}
        if isinstance(obj, dict) and any(obj.values()):
            elems.append(_p("DO OBJETO DO CONTRATO", styles["secao"]))
            tipo_bem = obj.get("tipo_bem", "imovel_urbano")

            if tipo_bem == "veiculo":
                desc = _s(obj.get("descricao_veiculo"), _BLANK)
                placa = _s(obj.get("placa"), _BLANK)
                renavam = _s(obj.get("renavam"), _BLANK)
                chassi = _s(obj.get("chassi"), _BLANK)
                ano = _s(obj.get("ano_fabricacao"), _BLANK)
                cor_v = _s(obj.get("cor"), _BLANK)
                elems.append(_p(
                    f"Veiculo: <b>{desc}</b>, placa <b>{placa}</b>, RENAVAM {renavam}, "
                    f"chassi {chassi}, ano {ano}, cor {cor_v}.",
                    styles["corpo"]
                ))
            else:
                endereco = _s(obj.get("endereco"), _BLANK)
                bairro = _s(obj.get("bairro"), "")
                cidade = _s(obj.get("cidade"), _BLANK)
                uf = _s(obj.get("uf"), _BLANK)
                cep = obj.get("cep") or ""
                matricula = _s(obj.get("matricula"), _BLANK)
                reg_imovel = _s(obj.get("registro_imovel"), _BLANK)
                area_total = _s(obj.get("area_total"), _BLANK)
                area_construida = _s(obj.get("area_construida"), "")
                ccir = _s(obj.get("ccir"), "")
                car = _s(obj.get("car"), "")

                loc = f"{endereco}, {bairro + ', ' if bairro else ''}{cidade}-{uf}"
                if cep:
                    loc += f", CEP {cep}"

                unidade = "ha" if tipo_bem == "imovel_rural" else "m2"
                area_txt = f"{area_total} {unidade}"
                if area_construida:
                    area_txt += f" (construida: {area_construida} m2)"

                tipo_bem_label = "Imovel Urbano" if tipo_bem == "imovel_urbano" else "Imovel Rural"
                elems.append(_p(
                    f"{tipo_bem_label} situado em <b>{loc}</b>, "
                    f"com area total de <b>{area_txt}</b>, "
                    f"matricula n. <b>{matricula}</b>, registrado no <b>{reg_imovel}</b>.",
                    styles["corpo"]
                ))

                if ccir:
                    elems.append(_p(f"CCIR: {ccir}" + (f"  |  CAR: {car}" if car else ""), styles["corpo"]))

                situacao = obj.get("situacao_ocupacao") or ""
                SITUACAO_LABEL = {
                    "desocupado": "desocupado e livre",
                    "ocupado_vendedor": "ocupado pelo Vendedor, com imissao na posse no ato",
                    "ocupado_terceiros": "ocupado por terceiros",
                    "locado": "locado a terceiros",
                }
                if situacao:
                    elems.append(_p(f"Situacao de ocupacao: {SITUACAO_LABEL.get(situacao, situacao)}.", styles["corpo"]))

                onus = _strip_html_inline(_s(obj.get("onus"), ""))
                if onus and onus != _BLANK:
                    elems.append(_p(f"Onus/Gravames: {onus}", styles["corpo"]))

                benf = _strip_html_inline(_s(obj.get("benfeitorias"), ""))
                if benf and benf != _BLANK:
                    elems.append(_p(f"Benfeitorias incluidas: {benf}", styles["corpo"]))

            elems.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

        # ── Do Preço e Pagamento ──────────────────────────────────────────────
        pag = doc.get("pagamento") or {}
        if isinstance(pag, dict):
            elems.append(_p("DO PRECO E FORMA DE PAGAMENTO", styles["secao"]))

            valor_total = pag.get("valor_total") or 0
            valor_brl = _brl(valor_total)
            valor_ext = _extenso(valor_total)

            elems.append(_p(
                f"O preco total da presente negociacao e de <b>{valor_brl}</b> "
                f"(<i>{valor_ext}</i>).",
                styles["corpo"]
            ))

            # Arras
            arras_val = pag.get("arras_valor") or 0
            arras_data = _fmt_date(pag.get("arras_data"))
            arras_tipo = pag.get("arras_tipo") or "confirmatorias"
            if arras_val:
                elems.append(_p(
                    f"Arras {arras_tipo}: <b>{_brl(arras_val)}</b>, pagos em {arras_data}.",
                    styles["corpo"]
                ))

            # Formas de pagamento
            formas = pag.get("formas") or []
            if formas:
                TIPO_FORMA = {
                    "dinheiro": "Dinheiro/PIX", "financiamento": "Financiamento",
                    "parcelado": "Parcelado", "cheque": "Cheque",
                    "permuta": "Permuta", "fgts": "FGTS", "consorcio": "Consorcio", "outro": "Outro",
                }
                rows = [["Forma", "Valor", "Vencimento", "Descricao"]]
                for f in formas:
                    if not isinstance(f, dict):
                        continue
                    rows.append([
                        TIPO_FORMA.get(f.get("tipo", ""), _s(f.get("tipo"), "-")),
                        _brl(f.get("valor")),
                        _fmt_date(f.get("data")),
                        _s(f.get("descricao") or f.get("banco"), "-"),
                    ])
                tbl = Table(rows, colWidths=[3.5 * cm, 3.5 * cm, 3 * cm, 5.5 * cm])
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), verde),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]))
                elems.append(Spacer(1, 4))
                elems.append(tbl)

            # Penalidades
            pen = pag.get("penalidades") or {}
            if isinstance(pen, dict) and pen:
                elems.append(Spacer(1, 6))
                elems.append(_p("PENALIDADES", styles["secao"]))
                vd = pen.get("vendedor_desiste") or ""
                cd = pen.get("comprador_desiste") or ""
                if vd:
                    elems.append(_p(f"Desistencia do {parte1_label}: {_safe_text(str(vd))}", styles["corpo"]))
                if cd:
                    elems.append(_p(f"Desistencia do {parte2_label}: {_safe_text(str(cd))}", styles["corpo"]))

            elems.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

        # ── Corretagem ────────────────────────────────────────────────────────
        if isinstance(cor, dict) and cor.get("incluir"):
            elems.append(_p("DA CORRETAGEM", styles["secao"]))
            pct = _s(cor.get("comissao_percentual"), _BLANK)
            valor_cor = ""
            try:
                vc = float(str(cor.get("comissao_percentual") or 0))
                vt = float(str((doc.get("pagamento") or {}).get("valor_total") or 0))
                if vc and vt:
                    valor_cor = f" = {_brl(vc * vt / 100)}"
            except Exception:
                pass

            resp = cor.get("comissao_responsavel") or "vendedor"
            RESP_LABEL = {"vendedor": parte1_label, "comprador": parte2_label, "ambos": "ambas as partes (50/50)"}
            elems.append(_p(
                f"Comissao de corretagem: <b>{pct}%{valor_cor}</b>, de responsabilidade do(a) {RESP_LABEL.get(resp, resp)}.",
                styles["corpo"]
            ))

            # Parcelas comissão
            p1 = cor.get("comissao_parcela1_pct") or 50
            p2 = cor.get("comissao_parcela2_pct") or 50
            elems.append(_p(f"Pagamento: {p1}% no ato do sinal e {p2}% na quitacao.", styles["corpo"]))

            # Dados bancários
            banco = cor.get("banco") or ""
            agencia = cor.get("agencia") or ""
            conta = cor.get("conta") or ""
            pix = cor.get("banco_pix") or ""
            cnpj_banco = cor.get("banco_cnpj") or ""
            if any([banco, agencia, conta, pix]):
                dados = []
                if banco:
                    dados.append(f"Banco: {_safe_text(banco)}")
                if agencia:
                    dados.append(f"Ag. {_safe_text(agencia)}")
                if conta:
                    dados.append(f"CC {_safe_text(conta)}")
                if cnpj_banco:
                    dados.append(f"CNPJ {_safe_text(cnpj_banco)}")
                if pix:
                    dados.append(f"PIX: {_safe_text(pix)}")
                elems.append(_p("Dados bancarios: " + " | ".join(dados), styles["corpo"]))

            elems.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

        # ── Cláusulas ─────────────────────────────────────────────────────────
        # Exclusividade: texto canônico (mesmo builder dos templates Prime); demais
        # tipos: cláusulas livres do documento. Garante paridade de texto nos 3 layouts.
        _is_excl = "exclusiv" in (doc.get("tipo_contrato") or "").lower()
        _clausulas_canon = []
        if _is_excl:
            try:
                from pdf.templates.contrato_base import (
                    montar_clausulas, preambulo_exclusividade, fecho_exclusividade,
                )
                _clausulas_canon = montar_clausulas(doc)
            except Exception:
                _clausulas_canon = []
        clausulas = doc.get("clausulas") or []
        if _clausulas_canon:
            try:
                for par in preambulo_exclusividade(doc):
                    elems.append(_p(par, styles["clausula_texto"]))
            except Exception:
                logger.warning("Falha no preâmbulo de exclusividade.", exc_info=True)
            elems.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))
            for cl in _clausulas_canon:
                elems.append(_p(f"<b>{cl.titulo}</b>", styles["clausula_titulo"]))
                for item in cl.itens:
                    elems.append(_p(item, styles["clausula_texto"]))
            try:
                elems.append(_p(fecho_exclusividade(doc), styles["clausula_texto"]))
            except Exception:
                logger.warning("Falha no fecho de exclusividade.", exc_info=True)
            elems.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))
        elif clausulas:
            elems.append(_p("CLAUSULAS E CONDICOES", styles["secao"]))
            for i, cl in enumerate(clausulas, 1):
                if isinstance(cl, dict):
                    titulo = _s(cl.get("titulo") or cl.get("nome"), f"Clausula {i}")
                    texto = _s(cl.get("texto") or cl.get("conteudo"), "")
                    elems.append(_p(f"<b>Clausula {i}a — {titulo}</b>", styles["clausula_titulo"]))
                    if texto:
                        elems.append(_p(texto, styles["clausula_texto"]))
                elif isinstance(cl, str) and cl.strip():
                    elems.append(_p(cl.strip(), styles["clausula_texto"]))

            elems.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))
        else:
            # Cláusula de foro padrão
            foro = _s(doc.get("foro_eleito"), "Comarca de Acailandia - Estado do Maranhao")
            elems.append(_p("DO FORO", styles["secao"]))
            elems.append(_p(
                f"Fica eleito o foro da {foro} para dirimir quaisquer controversias "
                f"oriundas do presente instrumento.",
                styles["corpo"]
            ))
            elems.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

        # ── Testemunhas ───────────────────────────────────────────────────────
        test1 = doc.get("testemunha_1") or {}
        test2 = doc.get("testemunha_2") or {}
        if isinstance(test1, dict) and test1.get("nome"):
            elems.append(_p("DAS TESTEMUNHAS", styles["secao"]))
            for t in [test1, test2]:
                if isinstance(t, dict) and t.get("nome"):
                    tnome = _s(t.get("nome"), _BLANK)
                    tcpf = _s(t.get("cpf"), _BLANK)
                    elems.append(_p(f"{tnome} — CPF {tcpf}", styles["corpo"]))

        # ── Local e Assinaturas ────────────────────────────────────────────────
        elems.append(PageBreak())
        cidade_ass = _s(doc.get("cidade_assinatura"), _BLANK)
        data_ass = _fmt_date(doc.get("data_assinatura"))
        elems.append(Spacer(1, 1 * cm))
        elems.append(_p(
            f"{cidade_ass}, {data_ass}",
            styles["corpo"]
        ))
        elems.append(Spacer(1, 1.5 * cm))

        todas_partes = list(vendedores) + list(compradores)
        if not todas_partes:
            todas_partes = [_BLANK, _BLANK]

        # Assinaturas em pares (2 por linha)
        sig_data = []
        for i in range(0, max(len(todas_partes), 2), 2):
            n1 = _safe_text(todas_partes[i]) if i < len(todas_partes) else _BLANK
            n2 = _safe_text(todas_partes[i + 1]) if i + 1 < len(todas_partes) else ""
            sig_data.append([
                Paragraph(f"_______________________________<br/>{n1}", styles["assinatura"]),
                Paragraph(f"_______________________________<br/>{n2}" if n2 else "", styles["assinatura"]),
            ])

        # Corretor signature
        if isinstance(cor, dict) and cor.get("incluir") and cor.get("nome"):
            sig_data.append([
                Paragraph(f"_______________________________<br/>{_safe_text(cor['nome'])}", styles["assinatura"]),
                Paragraph("", styles["assinatura"]),
            ])

        sig_tbl = Table(sig_data, colWidths=[8 * cm, 8 * cm])
        sig_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elems.append(sig_tbl)

        # Rodapé
        elems.append(Spacer(1, 1.5 * cm))
        elems.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        elems.append(_p(
            f"Gerado em {datetime.utcnow().strftime('%d/%m/%Y as %H:%M UTC')} "
            f"| AvalieImob / Romatec | Documento n. {contrato_id}",
            styles["rodape"]
        ))

        # ── Anexos do imóvel (fotos + documentos) — exclusividade ─────────────
        anexos = []
        try:
            from pdf.templates.anexos_imovel import anexos_imovel_flowables
            anexos = anexos_imovel_flowables(doc.get("objeto") or {})
        except Exception:
            logger.warning("Falha ao montar anexos do imóvel (tradicional).", exc_info=True)

        # Build resiliente: se os anexos quebrarem o build, gera o contrato sem eles.
        try:
            pdf.build(list(elems) + list(anexos))
        except Exception:
            logger.warning("Build com anexos falhou; gerando contrato sem anexos.", exc_info=True)
            buffer = io.BytesIO()
            pdf = SimpleDocTemplate(
                buffer, pagesize=A4,
                leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                topMargin=2 * cm, bottomMargin=2.5 * cm,
                title=f"Contrato {contrato_id}",
            )
            pdf.build(elems)

    except Exception as exc:
        logger.error("Erro ao gerar PDF do contrato %s: %s", contrato_id, exc, exc_info=True)
        if raise_on_error:
            raise
        return b""

    buffer.seek(0)
    return buffer.read()


async def _preload_anexos_imovel(db, doc: dict) -> None:
    """Pré-carrega os bytes (db.images → data_b64) das fotos e documentos do imóvel
    e injeta em objeto['_fotos_bytes'] / objeto['_documentos_bytes'] para o renderer
    síncrono montar os anexos. Defensivo: ids inválidos são ignorados."""
    import base64
    obj = doc.get("objeto")
    if not isinstance(obj, dict):
        return

    async def _carregar(ids) -> list:
        out = []
        for iid in (ids or []):
            if not iid:
                continue
            try:
                img = await db.images.find_one({"id": iid}, {"data_b64": 1})
                if img and img.get("data_b64"):
                    out.append(base64.b64decode(img["data_b64"]))
            except Exception:
                logger.warning("Anexo imóvel: falha ao carregar imagem %s", iid)
        return out

    obj["_fotos_bytes"] = await _carregar(obj.get("fotos_imovel"))
    obj["_documentos_bytes"] = await _carregar(obj.get("documentos_imovel"))
    doc["objeto"] = obj


_PODER_TEXTO_BASE = {
    "CERTIDOES_CRI": "solicitar e retirar, junto ao Cartorio de Registro de Imoveis competente, certidoes de inteiro teor, de onus reais e de acoes reipersecutorias relativas a matricula do imovel",
    "PREFEITURA_IPTU": "solicitar, junto a Prefeitura Municipal, carnes e demonstrativos de IPTU, certidoes negativas de debitos municipais, dados cadastrais (CIM) e certidao de valor venal do imovel",
    "BANCO_FINANCIAMENTO": "solicitar, junto ao credor fiduciario, extratos, saldo devedor, demonstrativos de evolucao da divida, boletos e demais informacoes necessarias a quitacao ou transferencia do financiamento que onera o imovel",
    "CONCESSIONARIAS": "solicitar, junto as concessionarias de servicos publicos, segundas vias, declaracoes e certidoes de debitos de energia eletrica e de agua/esgoto vinculadas ao imovel",
    "CONDOMINIO": "solicitar, junto ao condominio, declaracao de quitacao de debitos condominiais relativos ao imovel",
    "ANUNCIAR_DIVULGAR": "fotografar, anunciar, divulgar e promover o imovel em quaisquer meios, bem como acompanhar visitas de interessados",
    "RECEBER_PROPOSTAS": "receber e encaminhar aos OUTORGANTES propostas de compra, sem poderes para aceita-las, alienar o imovel, assinar contratos ou receber valores em nome dos OUTORGANTES",
    "RECEITA_CERTIDOES": "solicitar certidoes negativas federais relativas ao imovel e aos OUTORGANTES, estritamente para fins de instrucao da venda",
}
_MESES_PT = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
             "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _data_extenso(s) -> str:
    import re as _re
    if not s:
        from datetime import date as _date
        d = _date.today()
        return f"{d.day} de {_MESES_PT[d.month]} de {d.year}"
    m = _re.match(r"(\d{4})-(\d{2})-(\d{2})", str(s))
    if m:
        return f"{int(m.group(3))} de {_MESES_PT[int(m.group(2))]} de {m.group(1)}"
    return str(s)


def _generate_procuracao_pdf_bytes(doc: dict, uid: str, empresa: str) -> bytes:
    """PDF da PROCURAÇÃO PARTICULAR vinculada ao contrato de exclusividade.
    Outorgantes = vendedores (etapa 2); Outorgado = corretor (etapa 3);
    objeto limitado à matrícula (etapa 4). Texto em TA_JUSTIFY."""
    styles = _pdf_styles()
    buffer = io.BytesIO()
    proc = doc.get("procuracao") or {}
    obj = doc.get("objeto") or {}
    cor = doc.get("corretor") or {}
    outorgantes = doc.get("vendedores") or []

    try:
        pdf = SimpleDocTemplate(
            buffer, pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.5 * cm,
            topMargin=2 * cm, bottomMargin=2.5 * cm, title="Procuracao Particular",
        )
        elems: list = []
        verde = colors.HexColor("#1a4731")

        elems.append(_p(f"<b>{_safe_text(empresa or 'Romatec Consultoria Total')}</b>", styles["subtitulo"]))
        elems.append(_p("PROCURAÇÃO PARTICULAR", styles["titulo"]))
        numero = _s(doc.get("numero_contrato"), "")
        if numero:
            elems.append(_p(f"(vinculada ao Contrato de Exclusividade nº {numero})", styles["corpo"]))
        elems.append(HRFlowable(width="100%", thickness=1.2, color=verde, spaceAfter=8))

        # OUTORGANTES
        elems.append(_p("<b>OUTORGANTE(S):</b>", styles["secao"]))
        if not outorgantes:
            elems.append(_p(_BLANK, styles["corpo"]))
        for o in outorgantes:
            if isinstance(o, dict):
                q = _qualifica_pj(o) if o.get("tipo") == "pj" else _qualifica_pf(o)
            else:
                q = _safe_text(str(o))
            elems.append(_p(q + ".", styles["clausula_texto"]))

        # OUTORGADO
        elems.append(_p("<b>OUTORGADO:</b>", styles["secao"]))
        cor_nome = _s(cor.get("nome"), _BLANK)
        cor_creci = _s(cor.get("creci"), "")
        cor_doc = _s(cor.get("cpf_cnpj"), "")
        cor_end = _s(cor.get("endereco"), "")
        out_txt = f"{cor_nome}, corretor(a) de imóveis"
        if cor_creci:
            out_txt += f" inscrito(a) no CRECI sob nº {cor_creci}"
        if cor_doc:
            out_txt += f", inscrito(a) no CPF/CNPJ sob nº {cor_doc}"
        if cor_end:
            out_txt += f", com endereço profissional em {cor_end}"
        elems.append(_p(out_txt + ".", styles["clausula_texto"]))

        # OBJETO
        matricula = _s(obj.get("matricula"), _BLANK)
        reg_imoveis = _s(obj.get("registro_imovel") or obj.get("cartorio"), "Cartório de Registro de Imóveis competente")
        end_imovel = _s(obj.get("endereco"), _BLANK)
        area_total = _s(obj.get("area_total") or obj.get("area_terreno"), "")
        area_constr = _s(obj.get("area_construida") or obj.get("area_edificacao"), "")
        objeto_txt = (
            f"a presente procuração é outorgada em caráter EXCLUSIVO e LIMITADO ao imóvel objeto da "
            f"Matrícula nº {matricula} do {reg_imoveis}, situado em {end_imovel}"
        )
        if area_total:
            objeto_txt += f", com área total de {area_total} m²"
        if area_constr:
            objeto_txt += f" e área construída de {area_constr} m²"
        objeto_txt += (
            ", vinculada ao Contrato de Exclusividade de Intermediação Imobiliária celebrado entre as "
            "partes, não conferindo ao OUTORGADO quaisquer poderes sobre outros bens, direitos ou "
            "interesses dos OUTORGANTES."
        )
        elems.append(_p("<b>OBJETO:</b>", styles["secao"]))
        elems.append(_p(objeto_txt, styles["clausula_texto"]))

        # PODERES
        elems.append(_p("<b>PODERES:</b>", styles["secao"]))
        elems.append(_p(
            "Pelo presente instrumento particular de procuração, na forma dos arts. 653 a 666 e, "
            "especialmente, do art. 661 do Código Civil (Lei nº 10.406/2002), os OUTORGANTES nomeiam e "
            "constituem o OUTORGADO seu bastante procurador, com poderes específicos para, exclusivamente "
            "em relação ao imóvel acima descrito:",
            styles["clausula_texto"]))
        letras = "abcdefghijklmnopqrstuvwxyz"
        idx = 0
        for pd in (proc.get("poderes") or []):
            if not isinstance(pd, dict) or not pd.get("ativo"):
                continue
            txt = (pd.get("texto_customizado") or "").strip() or _PODER_TEXTO_BASE.get(pd.get("chave"), "")
            if not txt:
                continue
            elems.append(_p(f"{letras[idx]}) {_safe_text(txt)};", styles["clausula_texto"]))
            idx += 1
        if (proc.get("poderes_adicionais") or "").strip():
            elems.append(_p(f"{letras[idx]}) {_safe_text(proc['poderes_adicionais'].strip())};", styles["clausula_texto"]))
        elems.append(_p(
            "podendo, para tanto, assinar requerimentos, protocolos e recibos de entrega de documentos, "
            "prestar e receber informações, pagar taxas e emolumentos por conta dos OUTORGANTES e praticar "
            "os demais atos estritamente necessários ao fiel cumprimento deste mandato.",
            styles["clausula_texto"]))

        # VEDAÇÕES
        elems.append(_p("<b>VEDAÇÕES:</b>", styles["secao"]))
        ved = (
            "A presente procuração NÃO confere poderes para alienar, prometer alienar, onerar, hipotecar, "
            "dar em garantia, transigir, firmar compromisso de compra e venda, receber valores, dar quitação "
            "ou praticar qualquer ato de disposição sobre o imóvel, atos estes que dependem de manifestação "
            "pessoal e expressa dos OUTORGANTES."
        )
        if not proc.get("substabelecimento_permitido"):
            ved += " É vedado o substabelecimento, no todo ou em parte, dos poderes ora conferidos."
        elems.append(_p(ved, styles["clausula_texto"]))

        # VIGÊNCIA
        elems.append(_p("<b>VIGÊNCIA:</b>", styles["secao"]))
        if proc.get("vigencia_vinculada_contrato") is False and proc.get("vigencia_data_fim"):
            vig = f"esta procuração vigorará até {_data_extenso(proc.get('vigencia_data_fim'))}"
        else:
            vig = ("esta procuração vigorará enquanto vigente o Contrato de Exclusividade a que se vincula, "
                   "extinguindo-se de pleno direito com o seu término, resolução ou rescisão")
        elems.append(_p(
            f"{vig}, podendo ser revogada a qualquer tempo pelos OUTORGANTES, na forma da lei.",
            styles["clausula_texto"]))

        # Fecho + assinaturas
        local = _s(proc.get("local_assinatura"), "Açailândia/MA")
        elems.append(Spacer(1, 10))
        elems.append(_p("Por ser expressão da verdade, firmam o presente instrumento.", styles["corpo"]))
        elems.append(_p(f"{local}, {_data_extenso(proc.get('data_assinatura'))}.", styles["corpo"]))
        elems.append(Spacer(1, 1.2 * cm))

        for o in outorgantes:
            nome = _safe_text(o.get("nome") or o.get("razao_social") or _BLANK) if isinstance(o, dict) else _safe_text(str(o))
            cpf = _s(o.get("cpf") or o.get("cnpj"), "") if isinstance(o, dict) else ""
            elems.append(_p("_______________________________________", styles["corpo"]))
            elems.append(_p(f"OUTORGANTE — {nome}{', CPF ' + cpf if cpf else ''}", styles["corpo"]))
            elems.append(Spacer(1, 0.5 * cm))
            # cônjuge anuente
            if isinstance(o, dict) and o.get("conjuge_nome"):
                cjcpf = _s(o.get("conjuge_cpf"), "")
                elems.append(_p("_______________________________________", styles["corpo"]))
                elems.append(_p(f"OUTORGANTE (cônjuge) — {_safe_text(o['conjuge_nome'])}{', CPF ' + cjcpf if cjcpf else ''}", styles["corpo"]))
                elems.append(Spacer(1, 0.5 * cm))

        elems.append(Spacer(1, 0.3 * cm))
        elems.append(_p("_______________________________________", styles["corpo"]))
        elems.append(_p(f"OUTORGADO — {cor_nome}{', CRECI ' + cor_creci if cor_creci else ''}", styles["corpo"]))

        elems.append(Spacer(1, 0.8 * cm))
        elems.append(_p(
            "Recomenda-se o reconhecimento de firma das assinaturas dos OUTORGANTES, podendo ser exigido "
            "pelas instituições destinatárias (art. 654, § 2º, do Código Civil).",
            styles["rodape"]))

        pdf.build(elems)
    except Exception as exc:
        logger.error("Erro ao gerar PDF da procuração: %s", exc, exc_info=True)
        return b""

    buffer.seek(0)
    return buffer.read()


async def _next_contrato_numero(db, ano: int) -> str:
    seq = await db.counters.find_one_and_update(
        {"_id": f"contrato_numero_{ano}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    n = seq.get("seq", 1) if seq else 1
    return f"CV-{ano}-{n:04d}"


async def _next_lacre_versao(db, contrato_id: str, ano: int) -> str:
    seq = await db.counters.find_one_and_update(
        {"_id": f"lacre_{contrato_id}_{ano}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    n = seq.get("seq", 1) if seq else 1
    contrato_lookup = {"id": contrato_id}
    if ObjectId.is_valid(contrato_id):
        contrato_lookup = {"$or": [{"id": contrato_id}, {"_id": ObjectId(contrato_id)}]}
    doc = await db.contratos.find_one(contrato_lookup)
    numero_base = doc.get("numero_contrato", f"CV-{ano}") if doc else f"CV-{ano}"
    return f"{numero_base}-v{n}"


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/contratos/tipos")
async def listar_tipos():
    """Lista todos os tipos de contrato disponíveis (público)."""
    return TIPOS_CONTRATO


@router.post("/contratos", response_model=Contrato)
async def criar_contrato(
    body: ContratoCreate,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Cria um novo contrato com número automático."""
    ano = datetime.utcnow().year
    numero = await _next_contrato_numero(db, ano)
    
    # Monta o documento com todos os campos opcionais
    contrato_data = {
        "id": str(_uuid_module.uuid4()),
        "user_id": uid,
        "tipo_contrato": body.tipo_contrato,
        "numero_contrato": numero,
        "status": "minuta",
        "cidade_assinatura": body.cidade_assinatura or "",
        "data_assinatura": body.data_assinatura or "",
        "foro_eleito": body.foro_eleito or "",
        "vendedores": body.vendedores or [],
        "compradores": body.compradores or [],
        "corretor": body.corretor or {"incluir": False},
        "objeto": body.objeto or {},
        "pagamento": body.pagamento or {},
        "config": body.config or {"incluir_logo": True, "incluir_recibo_arras": True, "incluir_checklist": True},
        "clausulas": [],
        "alertas_juridicos": [],
        "versao_atual": 1,
        "lacrado": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await db.contratos.insert_one(contrato_data)
    return _normalize_contrato_doc(contrato_data)


@router.get("/contratos")
async def listar_contratos(
    status: Optional[str] = None,
    tipo_contrato: Optional[str] = None,
    busca: Optional[str] = None,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Lista contratos do usuário com filtros opcionais."""
    filtros = {"user_id": uid}
    if status:
        filtros["status"] = status
    else:
        # Por padrão, oculta os arquivados (soft delete) — assim o excluir "cola"
        filtros["status"] = {"$nin": ["arquivado"]}
    if tipo_contrato:
        filtros["tipo_contrato"] = tipo_contrato
    
    cursor = db.contratos.find(filtros).sort("updated_at", -1)
    docs = await cursor.to_list(length=1000)
    
    # Busca por nome das partes (simplificada)
    if busca:
        docs = [
            d for d in docs
            if busca.lower() in json.dumps(d.get("vendedores", []), ensure_ascii=False).lower()
            or busca.lower() in json.dumps(d.get("compradores", []), ensure_ascii=False).lower()
        ]
    
    return [_normalize_contrato_doc(d) for d in docs]


@router.get("/contratos/{cid}")
async def buscar_contrato(
    cid: str,
    uid: str = Depends(get_authenticated_user),
    db=Depends(get_db),
):
    """Busca um contrato completo pelo ID. Permite acesso mesmo com plano expirado."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    return _normalize_contrato_doc(doc)


@router.get("/contratos/{cid}/pdf")
async def baixar_contrato_pdf(
    cid: str,
    template: Optional[str] = None,   # prime1 | prime2 | tradicional (opcional)
    uid: str = Depends(get_authenticated_user),
    db=Depends(get_db),
):
    """Gera e retorna PDF binário válido do contrato do usuário autenticado.
    O template vem da query, senão do contrato (template_pdf), senão o padrão.
    Qualquer falha no template escolhido cai no gerador tradicional (download nunca quebra)."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    user = await db.users.find_one({"id": uid}, {"company": 1, "name": 1})
    empresa = (user or {}).get("company") or (user or {}).get("name") or "AvalieImob"

    await _preload_anexos_imovel(db, doc)

    from pdf.templates.registry import gerar_pdf_contrato
    pdf_bytes = gerar_pdf_contrato(doc=doc, uid=uid, empresa=empresa, template=template)
    if not pdf_bytes.startswith(b"%PDF-"):
        # Reexecuta o gerador tradicional propagando a exceção real p/ diagnóstico.
        try:
            _generate_contrato_pdf_bytes(doc, uid, empresa, raise_on_error=True)
        except Exception as exc:  # noqa: BLE001
            logger.error("Diagnóstico PDF contrato %s", cid, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Falha ao gerar PDF: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="Falha ao gerar PDF válido (sem exceção capturada)")

    filename_id = str(doc.get("id") or doc.get("_id") or cid)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="contrato_{filename_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/contratos/{cid}/procuracao/pdf")
async def baixar_procuracao_pdf(
    cid: str,
    uid: str = Depends(get_authenticated_user),
    db=Depends(get_db),
):
    """Gera o PDF da PROCURAÇÃO PARTICULAR vinculada ao contrato (exclusividade)."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    user = await db.users.find_one({"id": uid}, {"company": 1, "name": 1})
    empresa = (user or {}).get("company") or (user or {}).get("name") or "Romatec Consultoria Total"

    pdf_bytes = _generate_procuracao_pdf_bytes(doc, uid, empresa)
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=500, detail="Falha ao gerar a procuração")

    filename_id = str(doc.get("id") or doc.get("_id") or cid)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="procuracao_{filename_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/contratos/{cid}/docx")
async def baixar_contrato_docx(
    cid: str,
    uid: str = Depends(get_authenticated_user),
    db=Depends(get_db),
):
    """Gera DOCX juridico premium do contrato (Times New Roman, margens 3/2cm)."""
    from contrato_docx import generate_contrato_docx

    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato nao encontrado")

    user = await db.users.find_one({"id": uid}) or {}
    logo_id = user.get("company_logo")
    if logo_id:
        try:
            import gridfs
            from bson import ObjectId as BsonOID
            fs = gridfs.GridFS(db.delegate)
            logo_bytes = fs.get(BsonOID(logo_id)).read()
            user["_company_logo_bytes"] = logo_bytes
        except Exception:
            pass

    # Adapta o schema simplificado do wizard para o schema completo do docx generator
    contrato_adapted = _adapt_for_docx(doc)
    try:
        docx_bytes = generate_contrato_docx(contrato_adapted, user)
    except Exception as exc:
        logger.error("Erro ao gerar DOCX %s: %s", cid, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Falha ao gerar DOCX")

    filename_id = str(doc.get("id") or doc.get("_id") or cid)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="contrato_{filename_id}.docx"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/contratos/{cid}/recibo-arras/docx")
async def baixar_recibo_arras_docx(
    cid: str,
    uid: str = Depends(get_authenticated_user),
    db=Depends(get_db),
):
    """Gera DOCX do Recibo de Sinal/Arras do contrato."""
    from contrato_docx import generate_recibo_arras_docx

    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato nao encontrado")

    user = await db.users.find_one({"id": uid}) or {}
    contrato_adapted = _adapt_for_docx(doc)
    try:
        docx_bytes = generate_recibo_arras_docx(contrato_adapted, user)
    except Exception as exc:
        logger.error("Erro ao gerar recibo arras %s: %s", cid, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Falha ao gerar Recibo de Arras")

    filename_id = str(doc.get("id") or doc.get("_id") or cid)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="recibo_arras_{filename_id}.docx"',
            "Cache-Control": "no-store",
        },
    )


def _adapt_for_docx(doc: dict) -> dict:
    """Converte o schema simplificado do wizard para o schema do docx generator."""
    partes = []

    for v in doc.get("vendedores") or []:
        if not isinstance(v, dict):
            continue
        if v.get("tipo") == "pj":
            partes.append({"tipo": "pj", "qualificacao": "Vendedor", "pj": {
                "razao_social": v.get("razao_social") or v.get("nome"),
                "cnpj": v.get("cnpj"), "endereco": v.get("endereco"),
                "cidade": v.get("cidade"), "uf": v.get("uf"), "cep": v.get("cep"),
                "representante_nome": v.get("representante_nome"),
                "representante_cpf": v.get("representante_cpf"),
                "representante_cargo": v.get("representante_cargo"),
            }})
        else:
            partes.append({"tipo": "pf", "qualificacao": "Vendedor", "pf": {
                "nome": v.get("nome"), "cpf": v.get("cpf"), "rg": v.get("rg"),
                "rg_orgao": v.get("rg_orgao"), "data_nascimento": v.get("nascimento"),
                "estado_civil": v.get("estado_civil"), "profissao": v.get("profissao"),
                "nacionalidade": v.get("nacionalidade", "brasileiro(a)"),
                "cnh": v.get("cnh"), "cnh_categoria": v.get("cnh_categoria"),
                "cnh_orgao": v.get("cnh_orgao"), "cnh_validade": v.get("cnh_validade"),
                "filiacao_mae": v.get("filiacao_mae"), "filiacao_pai": v.get("filiacao_pai"),
                "endereco": v.get("endereco"), "cidade": v.get("cidade"),
                "uf": v.get("uf"), "cep": v.get("cep"),
                "conjuge_nome": v.get("conjuge_nome"), "conjuge_cpf": v.get("conjuge_cpf"),
                "regime_bens": v.get("conjuge_regime"),
                "procurador_nome": v.get("procurador_nome"),
                "procurador_cpf": v.get("procurador_cpf"),
                "procurador_instrumento": v.get("procurador_instrumento"),
            }})

    for c in doc.get("compradores") or []:
        if not isinstance(c, dict):
            continue
        if c.get("tipo") == "pj":
            partes.append({"tipo": "pj", "qualificacao": "Comprador", "pj": {
                "razao_social": c.get("razao_social") or c.get("nome"),
                "cnpj": c.get("cnpj"), "endereco": c.get("endereco"),
                "cidade": c.get("cidade"), "uf": c.get("uf"), "cep": c.get("cep"),
                "representante_nome": c.get("representante_nome"),
                "representante_cpf": c.get("representante_cpf"),
                "representante_cargo": c.get("representante_cargo"),
            }})
        else:
            partes.append({"tipo": "pf", "qualificacao": "Comprador", "pf": {
                "nome": c.get("nome"), "cpf": c.get("cpf"), "rg": c.get("rg"),
                "rg_orgao": c.get("rg_orgao"), "data_nascimento": c.get("nascimento"),
                "estado_civil": c.get("estado_civil"), "profissao": c.get("profissao"),
                "nacionalidade": c.get("nacionalidade", "brasileiro(a)"),
                "cnh": c.get("cnh"), "cnh_categoria": c.get("cnh_categoria"),
                "cnh_orgao": c.get("cnh_orgao"), "cnh_validade": c.get("cnh_validade"),
                "filiacao_mae": c.get("filiacao_mae"), "filiacao_pai": c.get("filiacao_pai"),
                "endereco": c.get("endereco"), "cidade": c.get("cidade"),
                "uf": c.get("uf"), "cep": c.get("cep"),
                "conjuge_nome": c.get("conjuge_nome"), "conjuge_cpf": c.get("conjuge_cpf"),
                "regime_bens": c.get("conjuge_regime"),
            }})

    pag_raw = doc.get("pagamento") or {}
    valor_total = pag_raw.get("valor_total") or 0
    try:
        valor_total = float(str(valor_total).replace(".", "").replace(",", "."))
    except Exception:
        valor_total = 0

    formas = pag_raw.get("formas") or []
    parcelas = []
    for i, f in enumerate(formas):
        if not isinstance(f, dict):
            continue
        parcelas.append({
            "numero": i + 1,
            "valor": f.get("valor", 0),
            "vencimento": f.get("data", ""),
            "forma_pagamento": f.get("tipo", ""),
            "banco": f.get("banco") or f.get("descricao", ""),
        })

    obj_raw = doc.get("objeto") or {}
    objeto = {
        "tipo": obj_raw.get("tipo_bem", "imovel_urbano"),
        "endereco": obj_raw.get("endereco"), "bairro": obj_raw.get("bairro"),
        "cidade": obj_raw.get("cidade"), "uf": obj_raw.get("uf"), "cep": obj_raw.get("cep"),
        "matricula": obj_raw.get("matricula"), "cartorio": obj_raw.get("registro_imovel"),
        "area_terreno": obj_raw.get("area_total"), "area_construida": obj_raw.get("area_construida"),
        "situacao": obj_raw.get("situacao_ocupacao"), "onus": obj_raw.get("onus"),
        "ccir": obj_raw.get("ccir"), "car": obj_raw.get("car"),
        "veiculo_marca": obj_raw.get("descricao_veiculo"),
        "veiculo_placa": obj_raw.get("placa"), "veiculo_renavam": obj_raw.get("renavam"),
        "veiculo_chassi": obj_raw.get("chassi"),
        "veiculo_ano_fabricacao": obj_raw.get("ano_fabricacao"),
        "veiculo_cor": obj_raw.get("cor"),
    }

    cor_raw = doc.get("corretor") or {}
    corretor = None
    if isinstance(cor_raw, dict) and cor_raw.get("incluir"):
        corretor = {
            "nome": cor_raw.get("nome"), "creci": cor_raw.get("creci"),
            "cpf_cnpj": cor_raw.get("cpf_cnpj"), "email": cor_raw.get("email"),
            "comissao_percentual": cor_raw.get("comissao_percentual"),
            "comissao_responsavel": cor_raw.get("comissao_responsavel", "Vendedor"),
            "exclusividade": cor_raw.get("exclusividade", False),
            "exclusividade_prazo_dias": cor_raw.get("prazo_exclusividade"),
        }

    testemunhas = []
    for key in ("testemunha_1", "testemunha_2"):
        t = doc.get(key)
        if isinstance(t, dict) and t.get("nome"):
            testemunhas.append({"nome": t.get("nome"), "cpf": t.get("cpf")})

    return {
        "tipo_contrato": doc.get("tipo_contrato", ""),
        "numero_contrato": doc.get("numero_contrato", ""),
        "status": doc.get("status", ""),
        "cidade_assinatura": doc.get("cidade_assinatura", ""),
        "uf_assinatura": doc.get("uf", ""),
        "data_assinatura": doc.get("data_assinatura", ""),
        "partes": partes,
        "objeto": objeto,
        "corretor": corretor,
        "clausulas": doc.get("clausulas") or [],
        "testemunhas": testemunhas,
        "condicoes_pagamento": {
            "valor_total": valor_total,
            "valor_total_extenso": _extenso(valor_total),
            "forma_principal": (formas[0].get("tipo") if formas else None),
            "sinal_valor": pag_raw.get("arras_valor"),
            "sinal_data": pag_raw.get("arras_data"),
            "sinal_arras_tipo": pag_raw.get("arras_tipo", "confirmatorias"),
            "parcelas": parcelas,
        },
    }


# ── Biblioteca de Cláusulas ──────────────────────────────────────────────────

@router.get("/contratos/clausulas/templates")
async def listar_templates_clausulas(
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Lista templates de clausulas disponíveis."""
    docs = await db.contrato_clause_templates.find({"ativo": True}).sort("nome", 1).to_list(50)
    return [serialize_doc(d) for d in docs]


@router.get("/contratos/clausulas/por-tipo/{tipo_contrato}")
async def clausulas_por_tipo(
    tipo_contrato: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Retorna cláusulas agrupadas por categoria para o tipo de contrato dado."""
    docs = await db.contrato_clausulas.find(
        {"$or": [{"tipo_contrato": tipo_contrato}, {"tipo_contrato": "todos"}]}
    ).sort([("categoria", 1), ("ordem", 1)]).to_list(100)

    agrupadas: dict = {}
    for d in docs:
        cat = d.get("categoria", "geral")
        agrupadas.setdefault(cat, []).append(serialize_doc(d))
    return agrupadas


@router.post("/contratos/seed-clausulas")
async def seed_clausulas(
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Popula a biblioteca de cláusulas PCV com as 15 cláusulas padrão Romatec."""
    from seed_contratos import CLAUSULAS_PCV, TEMPLATE_PCV
    existing = await db.contrato_clausulas.count_documents({"tipo_contrato": "compra_venda"})
    if existing > 0:
        return {"status": "ja_existem", "total": existing}
    await db.contrato_clause_templates.insert_one(TEMPLATE_PCV)
    if CLAUSULAS_PCV:
        await db.contrato_clausulas.insert_many(CLAUSULAS_PCV)
    return {"status": "ok", "inseridas": len(CLAUSULAS_PCV)}


@router.put("/contratos/{cid}")
async def atualizar_contrato(
    cid: str,
    body: ContratoUpdate,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Atualiza contrato e salva versão anterior."""
    query = _contrato_query_by_cid(cid, uid)
    doc = await db.contratos.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    contrato_id_ref = doc.get("id") or str(doc.get("_id"))
    
    # Salvar versão anterior
    versao_atual = doc.get("versao_atual", 1)
    snapshot_anterior = {k: v for k, v in doc.items() if not k.startswith("_")}
    hash_anterior = _calculate_hash(json.dumps(snapshot_anterior, sort_keys=True, default=str).encode())
    
    diffs = _deep_diff(snapshot_anterior, body.dict(exclude_unset=True))
    if diffs:
        version_doc = _create_version(
            contrato_id=contrato_id_ref,
            user_id=uid,
            numero_versao=versao_atual,
            tipo="auto",
            hash_sha256=hash_anterior,
            diffs=diffs,
            snapshot=snapshot_anterior,
        )
        await db.contrato_versions.insert_one(version_doc)
        versao_atual += 1
    
    # Atualizar
    update_data = body.dict(exclude_unset=True)
    if not doc.get("id"):
        update_data["id"] = contrato_id_ref
    update_data["versao_atual"] = versao_atual
    update_data["updated_at"] = datetime.utcnow()
    
    await db.contratos.update_one(
        query,
        {"$set": update_data}
    )
    
    doc_atualizado = await db.contratos.find_one(query)
    return _normalize_contrato_doc(doc_atualizado)


@router.delete("/contratos/{cid}")
async def deletar_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Soft delete do contrato (status = arquivado)."""
    query = _contrato_query_by_cid(cid, uid)
    doc = await db.contratos.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    
    await db.contratos.update_one(
        query,
        {"$set": {"status": "arquivado", "updated_at": datetime.utcnow()}}
    )
    return {"message": "Contrato arquivado com sucesso"}


@router.post("/contratos/{cid}/gerar-clausulas")
async def gerar_clausulas(
    cid: str,
    body: Optional[GerarClausulasRequest] = None,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Gera clausulas juridicas para o contrato usando Roma_IA.

    Retorna lista de clausulas sugeridas. As clausulas NAO sao salvas automaticamente
    — o front-end deve confirmar e chamar PUT /contratos/{cid} para persistir.
    """
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    tipo = (body.tipo if body and body.tipo else None) or doc.get("tipo_contrato") or ""
    if not tipo:
        raise HTTPException(status_code=400, detail="Tipo de contrato não definido")

    # Usa função específica para contrato de exclusividade
    if tipo == "exclusividade":
        dados_exclusividade = {
            "corretor_nome": doc.get("corretor", {}).get("nome", ""),
            "corretor_creci": doc.get("corretor", {}).get("creci", ""),
            "prazo_dias": doc.get("corretor", {}).get("prazo_exclusividade_dias", 90),
            "data_inicio": doc.get("data_assinatura", ""),
            "data_fim": doc.get("data_fim_exclusividade", ""),
            "comissao_percentual": doc.get("corretor", {}).get("percentual_comissao", 6),
            "imovel_endereco": doc.get("objeto", {}).get("endereco", ""),
            "proprietario_nome": doc.get("vendedores", [{}])[0].get("pf", {}).get("nome", "") if doc.get("vendedores") else "",
        }
        clausulas = await gerar_clausulas_exclusividade(dados=dados_exclusividade)
        clausulas_corretor = []  # Já incluído nas cláusulas de exclusividade
    else:
        clausulas = await gerar_clausulas_contrato(tipo=tipo, dados=doc)
        
        # Gera cláusulas de corretagem se houver corretor
        corretor = doc.get("corretor")
        clausulas_corretor = []
        if corretor and (corretor.get("nome") or corretor.get("creci")):
            clausulas_corretor = await gerar_clausulas_corretor(corretor=corretor, tipo_contrato=tipo)

    return {
        "clausulas": clausulas,
        "clausulas_corretagem": clausulas_corretor,
        "total": len(clausulas) + len(clausulas_corretor),
        "tipo_contrato": tipo,
    }


@router.post("/contratos/{cid}/validar-juridico")
async def validar_juridico(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Valida o contrato e retorna alertas juridicos via Roma_IA.

    Salva os alertas no banco e retorna a lista completa.
    """
    query = _contrato_query_by_cid(cid, uid)
    doc = await db.contratos.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    alertas = await validar_alertas_juridicos(contrato=doc)
    
    # Salvar alertas no contrato
    await db.contratos.update_one(
        query,
        {"$set": {"alertas_juridicos": alertas, "updated_at": datetime.utcnow()}}
    )
    
    return {"alertas": alertas, "total": len(alertas)}


@router.post("/contratos/{cid}/simulador-penalidades")
async def simulador_penalidades(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Calcula penalidades do contrato (multas, juros, correção)."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    resultado = calcular_penalidades(contrato=doc)
    return resultado


@router.get("/contratos/{cid}/clausulas-preview")
async def clausulas_preview(
    cid: str,
    uid: str = Depends(get_authenticated_user),
    db=Depends(get_db),
):
    """Texto montado das cláusulas (preview read-only da etapa 7). Para
    exclusividade retorna o texto canônico (preâmbulo + 12 cláusulas + fecho)."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    from pdf.templates.contrato_base import (
        montar_clausulas, preambulo_exclusividade, fecho_exclusividade,
    )
    is_excl = "exclusiv" in (doc.get("tipo_contrato") or "").lower()
    clausulas = [{"titulo": c.titulo, "itens": c.itens} for c in montar_clausulas(doc)]
    return {
        "canonico": is_excl,
        "preambulo": preambulo_exclusividade(doc) if is_excl else [],
        "clausulas": clausulas,
        "fecho": fecho_exclusividade(doc) if is_excl else "",
    }


@router.get("/contratos/{cid}/checklist")
async def checklist_documental(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Gera checklist de documentos necessários para o contrato."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    checklist = gerar_checklist(contrato=doc)
    return {"checklist": checklist, "total": len(checklist)}


@router.get("/contratos/{cid}/versoes")
async def listar_versoes(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Lista histórico de versões do contrato."""
    cursor = db.contrato_versions.find(
        {"contrato_id": cid, "user_id": uid}
    ).sort("numero_versao", -1)
    
    docs = await cursor.to_list(length=100)
    return [serialize_doc(d) for d in docs]


@router.post("/contratos/{cid}/lacrar")
async def lacrar_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Lacra a versão atual do contrato com hash SHA-256."""
    query = _contrato_query_by_cid(cid, uid)
    doc = await db.contratos.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    contrato_id_ref = doc.get("id") or str(doc.get("_id"))
    
    if doc.get("lacrado"):
        raise HTTPException(status_code=400, detail="Contrato já está lacrado")
    
    # Calcular hash
    snapshot = {k: v for k, v in doc.items() if not k.startswith("_")}
    hash_sha256 = _calculate_hash(json.dumps(snapshot, sort_keys=True, default=str).encode())
    
    # Gerar número de lacre
    ano = datetime.utcnow().year
    numero_lacre = await _next_lacre_versao(db, contrato_id_ref, ano)
    
    # Criar versão lacrada
    version_doc = _create_version(
        contrato_id=contrato_id_ref,
        user_id=uid,
        numero_versao=doc.get("versao_atual", 1),
        tipo="lacrado",
        hash_sha256=hash_sha256,
        diffs=[],
        snapshot=snapshot,
        numero_lacre=numero_lacre,
    )
    await db.contrato_versions.insert_one(version_doc)
    
    # Atualizar contrato
    await db.contratos.update_one(
        query,
        {
            "$set": {
                "id": contrato_id_ref,
                "lacrado": True,
                "versao_lacrada": numero_lacre,
                "hash_lacrado": hash_sha256,
                "updated_at": datetime.utcnow(),
            }
        }
    )
    
    return {
        "message": "Contrato lacrado com sucesso",
        "numero_lacre": numero_lacre,
        "hash_sha256": hash_sha256,
    }


@router.post("/contratos/{cid}/compartilhar")
async def compartilhar_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Gera link público para visualização do contrato."""
    query = _contrato_query_by_cid(cid, uid)
    doc = await db.contratos.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    
    # Gerar token único
    token = str(_uuid_module.uuid4())
    
    await db.contratos.update_one(
        query,
        {
            "$set": {
                "link_publico_token": token,
                "link_publico_ativo": True,
                "link_publico_criado_em": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        }
    )
    
    return {
        "token": token,
        "url": f"/contrato/public/{token}",
    }


@router.get("/contratos/public/{token}")
async def portal_publico(
    token: str,
    request: Request,
    db=Depends(get_db),
):
    """Portal público para visualização de contrato (sem autenticação)."""
    doc = await db.contratos.find_one({
        "link_publico_token": token,
        "link_publico_ativo": True,
    })
    
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado ou link inválido")
    
    # Conta a visualização (debounce por IP/24h) — alimenta o contador 👁 do card
    await _registrar_evento_contrato(
        db, doc, "visualizado", ip=_client_ip(request), user_agent=request.headers.get("user-agent")
    )

    # Retornar apenas dados não sensíveis
    return {
        "numero_contrato": doc.get("numero_contrato"),
        "numero_display": _format_numero_cont(doc),
        "tipo_contrato": doc.get("tipo_contrato"),
        "status": doc.get("status"),
        "status_card": _compute_status_card(doc),
        "data_assinatura": doc.get("data_assinatura"),
        "cidade_assinatura": doc.get("cidade_assinatura"),
        "assinado": doc.get("icp_status") == "assinado" or doc.get("d4sign_status") == "assinado",
        "icp_verificacao_url": doc.get("icp_verificacao_url"),
        "vendedores": [
            {"nome": v.get("pf", {}).get("nome") or v.get("pj", {}).get("razao_social", "")}
            for v in doc.get("vendedores", [])
        ],
        "compradores": [
            {"nome": c.get("pf", {}).get("nome") or c.get("pj", {}).get("razao_social", "")}
            for c in doc.get("compradores", [])
        ],
        "objeto": {
            "endereco": doc.get("objeto", {}).get("endereco", ""),
            "cidade": doc.get("objeto", {}).get("cidade", ""),
            "uf": doc.get("objeto", {}).get("uf", ""),
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# Auditoria do link público + contadores (espelha services.link_tracking do PTAM,
# porém escopado à coleção `contratos` / `contrato_link_eventos`).
# ──────────────────────────────────────────────────────────────────────────────

def _client_ip(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


async def _registrar_evento_contrato(
    db, doc: dict, tipo: str, *,
    canal: Optional[str] = None, destinatario: Optional[str] = None,
    ip: Optional[str] = None, user_agent: Optional[str] = None,
) -> None:
    """Registra evento (gerado|enviado|visualizado|desativado) e atualiza os
    contadores-resumo no contrato. Nunca propaga exceção."""
    try:
        cid = doc.get("id")
        if not cid:
            return
        agora = datetime.utcnow()

        if tipo == "visualizado":
            # Debounce: ignora visualizações do mesmo IP nas últimas 24h
            from datetime import timedelta
            ja = await db.contrato_link_eventos.find_one({
                "contrato_id": cid, "tipo": "visualizado", "ip": ip,
                "created_at": {"$gte": agora - timedelta(hours=24)},
            }) if ip else None
            if ja:
                return

        await db.contrato_link_eventos.insert_one({
            "id": str(_uuid_module.uuid4()),
            "user_id": doc.get("user_id"),
            "contrato_id": cid,
            "tipo": tipo,
            "canal": canal,
            "destinatario": destinatario,
            "ip": ip,
            "user_agent": (user_agent or "")[:300] or None,
            "created_at": agora,
        })

        set_fields, inc_fields = {}, {}
        if tipo == "visualizado":
            inc_fields["link_views"] = 1
            set_fields["link_views_last"] = agora
            await db.contratos.update_one(
                {"id": cid, "link_views_first": {"$exists": False}},
                {"$set": {"link_views_first": agora}},
            )
        elif tipo == "enviado":
            inc_fields["link_sends"] = 1
            set_fields["link_last_sent"] = agora
            set_fields["link_last_canal"] = canal
            if destinatario:
                set_fields["link_last_destinatario"] = destinatario
        elif tipo == "gerado":
            set_fields["link_gerado_em"] = agora

        if set_fields or inc_fields:
            update = {}
            if set_fields:
                update["$set"] = set_fields
            if inc_fields:
                update["$inc"] = inc_fields
            await db.contratos.update_one({"id": cid}, update)
    except Exception as e:  # noqa: BLE001
        logger.warning("Falha ao registrar evento de link do contrato (%s): %s", tipo, e)


@router.get("/contratos/{cid}/link-eventos")
async def listar_link_eventos(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Histórico de eventos do link público + resumo (modal Histórico do card)."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    real_id = doc.get("id") or cid
    eventos = await db.contrato_link_eventos.find(
        {"contrato_id": real_id, "user_id": uid}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return {
        "encontrado": True,
        "resumo": {
            "views": doc.get("link_views", 0),
            "views_first": doc.get("link_views_first"),
            "views_last": doc.get("link_views_last"),
            "sends": doc.get("link_sends", 0),
            "last_sent": doc.get("link_last_sent"),
            "last_canal": doc.get("link_last_canal"),
            "last_destinatario": doc.get("link_last_destinatario"),
            "gerado_em": doc.get("link_gerado_em"),
            "ativo": doc.get("link_publico_ativo", False),
        },
        "eventos": eventos,
    }


@router.post("/contratos/{cid}/clonar")
async def clonar_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Duplica o contrato: novo número, status minuta, zera assinaturas,
    contadores, link público, recibo e histórico."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    ano = datetime.utcnow().year
    numero = await _next_contrato_numero(db, ano)
    agora = datetime.utcnow()

    novo = {k: v for k, v in doc.items() if not k.startswith("_")}
    # Campos que NÃO devem ser clonados (assinatura, link, recibo, contadores, auditoria)
    for campo in (
        "icp_status", "icp_signed_at", "icp_cert_id", "icp_titular", "icp_documento",
        "icp_emissor", "icp_hash", "icp_pdf_url", "icp_verificacao_url", "icp_layouts",
        "pdf_assinatura_key", "d4sign_document_uuid", "d4sign_status", "d4sign_enviado_em",
        "d4sign_assinado_em", "d4sign_signatarios", "d4sign_pdf_assinado_url",
        "link_publico_token", "link_publico_ativo", "link_publico_criado_em",
        "link_views", "link_views_first", "link_views_last", "link_sends",
        "link_last_sent", "link_last_canal", "link_last_destinatario", "link_gerado_em",
        "contrato_link", "recibo_id", "recibo_emitido", "recibo_emitido_em",
        "recibo_pdf_url", "recibo_assinado", "recibo_assinado_em",
        "lacrado", "versao_lacrada", "hash_lacrado", "denunciado_em", "rescindido_em",
    ):
        novo.pop(campo, None)

    novo["id"] = str(_uuid_module.uuid4())
    novo["user_id"] = uid
    novo["numero_contrato"] = numero
    novo["status"] = "minuta"
    novo["versao_atual"] = 1
    novo["created_at"] = agora
    novo["updated_at"] = agora

    await db.contratos.insert_one(novo)
    return _normalize_contrato_doc(novo)


@router.post("/contratos/{cid}/zerar-assinatura")
async def zerar_assinatura_contrato(
    cid: str,
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """Remove a(s) assinatura(s) ICP do contrato e regride o status para minuta.
    Equivale ao /assinatura/icp/contrato/{id}/resetar, porém escopado ao contrato."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    real_id = doc.get("id") or cid

    removidos = 0
    cursor = db.assinaturas_pdf.find({"doc_tipo": "contrato", "doc_id": real_id})
    async for a in cursor:
        r2_key = a.get("r2_key")
        if r2_key:
            try:
                from services import r2_storage
                import asyncio as _aio
                await _aio.to_thread(r2_storage.delete_object, r2_key)
            except Exception as e:
                logger.warning("Falha ao apagar PDF assinado do R2 (%s): %s", r2_key, e)
        await db.assinaturas_pdf.delete_one({"id": a["id"]})
        removidos += 1

    await db.contratos.update_one(
        {"id": real_id},
        {
            "$unset": {
                "icp_status": "", "icp_signed_at": "", "icp_cert_id": "", "icp_titular": "",
                "icp_documento": "", "icp_emissor": "", "icp_hash": "", "icp_pdf_url": "",
                "icp_verificacao_url": "", "icp_layouts": "", "pdf_assinatura_key": "",
            },
            "$set": {"status": "minuta", "updated_at": datetime.utcnow()},
        },
    )
    return {"ok": True, "removidos": removidos, "status": "minuta"}
