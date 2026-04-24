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
    clausulas: Optional[List[Any]] = None
    alertas_juridicos: Optional[List[Any]] = None
    testemunha_1: Optional[Any] = None
    testemunha_2: Optional[Any] = None
    incluir_logo: Optional[bool] = None
    incluir_recibo_arras: Optional[bool] = None
    incluir_checklist: Optional[bool] = None


class GerarClausulasRequest(BaseModel):
    tipo: Optional[str] = None  # sobreescreve o tipo do contrato se fornecido


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

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


def _normalize_contrato_doc(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return doc
    raw_id = doc.get("_id")
    payload = serialize_doc(doc)
    if not payload.get("id") and raw_id is not None:
        payload["id"] = str(raw_id)
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
    cep_part = f", CEP {cep}" if cep else ""
    loc = f"{endereco}, {cidade}-{uf}{cep_part}"

    qualif = (
        f"{nome}, {nacionalidade}, {estado_civil}, {profissao}, "
        f"portador(a) do CPF n. {cpf}{rg_part}, "
        f"nascido(a) em {nascimento}, "
        f"residente em {loc}"
    )

    conjuge = p.get("conjuge_nome") or ""
    if conjuge:
        cjcpf = _s(p.get("conjuge_cpf"), _BLANK)
        qualif += f"; conjuge: {_safe_text(conjuge)}, CPF {cjcpf}"

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


def _p(text: str, style) -> Paragraph:
    return Paragraph(_safe_text(text), style)


def _generate_contrato_pdf_bytes(doc: dict, uid: str, empresa: str) -> bytes:
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

                onus = _s(obj.get("onus"), "")
                if onus and onus != _BLANK:
                    elems.append(_p(f"Onus/Gravames: {onus}", styles["corpo"]))

                benf = _s(obj.get("benfeitorias"), "")
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
        clausulas = doc.get("clausulas") or []
        if clausulas:
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

        pdf.build(elems)

    except Exception as exc:
        logger.error("Erro ao gerar PDF do contrato %s: %s", contrato_id, exc, exc_info=True)
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
    uid: str = Depends(get_authenticated_user),
    db=Depends(get_db),
):
    """Gera e retorna PDF binário válido do contrato do usuário autenticado."""
    doc = await db.contratos.find_one(_contrato_query_by_cid(cid, uid))
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    user = await db.users.find_one({"id": uid}, {"company": 1, "name": 1})
    empresa = (user or {}).get("company") or (user or {}).get("name") or "AvalieImob"

    pdf_bytes = _generate_contrato_pdf_bytes(doc=doc, uid=uid, empresa=empresa)
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=500, detail="Falha ao gerar PDF válido")

    filename_id = str(doc.get("id") or doc.get("_id") or cid)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="contrato_{filename_id}.pdf"',
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
    db=Depends(get_db),
):
    """Portal público para visualização de contrato (sem autenticação)."""
    doc = await db.contratos.find_one({
        "link_publico_token": token,
        "link_publico_ativo": True,
    })
    
    if not doc:
        raise HTTPException(status_code=404, detail="Contrato não encontrado ou link inválido")
    
    # Retornar apenas dados não sensíveis
    return {
        "numero_contrato": doc.get("numero_contrato"),
        "tipo_contrato": doc.get("tipo_contrato"),
        "status": doc.get("status"),
        "data_assinatura": doc.get("data_assinatura"),
        "cidade_assinatura": doc.get("cidade_assinatura"),
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
