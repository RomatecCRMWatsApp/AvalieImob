# @module services.receita_rtc.aliquotas — alíquotas (modelo híbrido) e tabela interna.
#
# Ordem (PENDENCIAS.md §3.2), por tributo (CBS, IBS_UF, IBS_MUN):
#   1. tabelas da calculadora na data da operação;
#   2. sem valor lá: registro CONFIRMADO e vigente da tabela interna (global, mantida pelo administrador);
#   3. sem valor nos dois: NÃO calcula e diz qual tributo falta. Nunca assume valor.
#
# Contrato observado na calculadora 1.7.2 (21/11/2026):
#   - fato gerador ANTES de 2027: a calculadora resolve as alíquotas sozinha e RECUSA alíquotas informadas
#     (REG-036). O sistema só consulta para mostrar, nunca envia.
#   - A PARTIR de 2027: alíquotas obrigatórias na entrada (REG-037); as tabelas de referência devolvem 404.
#
# Nenhuma alíquota de 2027 em diante fica no código (decisão do dono; entra só pela administração).
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from pymongo import ReturnDocument

from .client import CalculadoraClient

TRIBUTOS = ("CBS", "IBS_UF", "IBS_MUN")
SITUACOES = ("RASCUNHO", "CONFIRMADA", "REVOGADA")
INICIO_ALIQUOTA_OBRIGATORIA = date(2027, 1, 1)
NOME_TRIBUTO = {"CBS": "CBS", "IBS_UF": "IBS estadual", "IBS_MUN": "IBS municipal"}
COLECAO = "rtc_aliquotas"
COLECAO_AUDITORIA = "rtc_aliquotas_auditoria"
_MAX_CASAS = 6


class AliquotaInvalida(ValueError):
    pass


def _data(v, campo: str) -> date:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        raise AliquotaInvalida(f"{campo}: data inválida (use AAAA-MM-DD).")


def normalizar_aliquota(v) -> Decimal:
    """Percentual em Decimal, 0 a 100, até 6 casas. Nunca float."""
    try:
        d = Decimal(str(v).strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        raise AliquotaInvalida("aliquota: informe um número (percentual).")
    if not d.is_finite() or d < 0 or d > 100:
        raise AliquotaInvalida("aliquota: deve estar entre 0 e 100 (percentual).")
    if -d.as_tuple().exponent > _MAX_CASAS:
        raise AliquotaInvalida(f"aliquota: no máximo {_MAX_CASAS} casas decimais.")
    return d


def validar_registro(dados: dict) -> dict:
    """Valida e normaliza um registro novo (sempre nasce RASCUNHO)."""
    tributo = str(dados.get("tributo", "")).upper()
    if tributo not in TRIBUTOS:
        raise AliquotaInvalida("tributo: use CBS, IBS_UF ou IBS_MUN.")
    uf = str(dados.get("uf") or "").strip().upper()
    mun = "".join(ch for ch in str(dados.get("codigo_municipio") or "") if ch.isdigit())
    if tributo == "CBS":
        uf, mun = "", ""
    else:
        if len(uf) != 2 or not uf.isalpha():
            raise AliquotaInvalida("uf: obrigatória para IBS (sigla de 2 letras).")
        if tributo == "IBS_MUN" and len(mun) != 7:
            raise AliquotaInvalida("codigo_municipio: obrigatório para IBS municipal (código IBGE de 7 dígitos).")
        if tributo == "IBS_UF":
            mun = ""
    inicio = _data(dados.get("vigencia_inicio"), "vigencia_inicio")
    fim_raw = dados.get("vigencia_fim")
    fim = _data(fim_raw, "vigencia_fim") if fim_raw else None
    if fim and fim < inicio:
        raise AliquotaInvalida("vigencia_fim: não pode ser anterior ao início.")
    fonte = str(dados.get("fonte") or "").strip()
    if len(fonte) < 5:
        raise AliquotaInvalida("fonte: obrigatória (norma, resolução, portaria ou documento do contador).")
    return {
        "tributo": tributo, "uf": uf, "codigo_municipio": mun,
        "aliquota": str(normalizar_aliquota(dados.get("aliquota"))),
        "vigencia_inicio": inicio.isoformat(),
        "vigencia_fim": fim.isoformat() if fim else None,
        "fonte": fonte[:500],
    }


def sobrepoe(a_ini: str, a_fim: Optional[str], b_ini: str, b_fim: Optional[str]) -> bool:
    """Intervalos fechados; fim vazio = sem fim."""
    a_f = a_fim or "9999-12-31"
    b_f = b_fim or "9999-12-31"
    return a_ini <= b_f and b_ini <= a_f


def _chave(r: dict) -> dict:
    return {"tributo": r["tributo"], "uf": r["uf"], "codigo_municipio": r["codigo_municipio"]}


async def _auditar(db, acao: str, registro_id: str, uid: str, detalhe: dict):
    await db[COLECAO_AUDITORIA].insert_one({
        "id": str(uuid.uuid4()), "acao": acao, "registro_id": registro_id,
        "por": uid, "em": datetime.utcnow(), "detalhe": detalhe,
    })


async def criar(db, dados: dict, uid: str) -> dict:
    reg = validar_registro(dados)
    existentes = await db[COLECAO].find({**_chave(reg), "situacao": {"$in": ["RASCUNHO", "CONFIRMADA"]}}).to_list(1000)
    for e in existentes:
        if sobrepoe(reg["vigencia_inicio"], reg["vigencia_fim"], e["vigencia_inicio"], e.get("vigencia_fim")):
            raise AliquotaInvalida(
                f"Vigência sobreposta com o registro {e['id']} ({e['vigencia_inicio']} a "
                f"{e.get('vigencia_fim') or 'sem fim'}). Revogue o anterior ou ajuste as datas.")
    agora = datetime.utcnow()
    doc = {**reg, "id": str(uuid.uuid4()), "situacao": "RASCUNHO",
           "confirmado_por": None, "confirmado_em": None,
           "criado_por": uid, "criado_em": agora}
    await db[COLECAO].insert_one(dict(doc))
    await _auditar(db, "criar", doc["id"], uid, reg)
    return doc


async def confirmar(db, registro_id: str, uid: str, confirmado_por: str) -> dict:
    nome = str(confirmado_por or "").strip()
    if len(nome) < 3:
        raise AliquotaInvalida("confirmado_por: informe quem validou (ex.: nome do contador).")
    doc = await db[COLECAO].find_one_and_update(
        {"id": registro_id, "situacao": "RASCUNHO"},
        {"$set": {"situacao": "CONFIRMADA", "confirmado_por": nome[:200], "confirmado_em": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER)
    if not doc:
        raise AliquotaInvalida("Só um registro em RASCUNHO pode ser confirmado (confirmado é imutável).")
    await _auditar(db, "confirmar", registro_id, uid, {"confirmado_por": nome[:200]})
    return doc


async def revogar(db, registro_id: str, uid: str, motivo: str) -> dict:
    motivo = str(motivo or "").strip()
    if len(motivo) < 5:
        raise AliquotaInvalida("motivo: informe por que o registro está sendo revogado.")
    doc = await db[COLECAO].find_one_and_update(
        {"id": registro_id, "situacao": {"$in": ["RASCUNHO", "CONFIRMADA"]}},
        {"$set": {"situacao": "REVOGADA", "revogado_por": uid, "revogado_em": datetime.utcnow(),
                  "motivo_revogacao": motivo[:500]}},
        return_document=ReturnDocument.AFTER)
    if not doc:
        raise AliquotaInvalida("Registro não encontrado ou já revogado.")
    await _auditar(db, "revogar", registro_id, uid, {"motivo": motivo[:500]})
    return doc


async def vigente(db, tributo: str, uf: str, municipio: str, data_op: date) -> Optional[dict]:
    """Registro CONFIRMADO cuja vigência cobre a data. RASCUNHO e REVOGADA nunca entram."""
    filtro = {"tributo": tributo, "situacao": "CONFIRMADA",
              "uf": "" if tributo == "CBS" else uf,
              "codigo_municipio": municipio if tributo == "IBS_MUN" else ""}
    d = data_op.isoformat()
    for r in await db[COLECAO].find(filtro).to_list(1000):
        if r["vigencia_inicio"] <= d and (not r.get("vigencia_fim") or d <= r["vigencia_fim"]):
            return r
    return None


async def resolver(db, client: CalculadoraClient, data_op: date, uf: str, codigo_uf: int, municipio: str) -> dict:
    """Devolve {"aliquotas": {tributo: {...}}, "faltantes": [...], "enviar": bool}.

    "enviar" diz se as alíquotas vão na requisição (só a partir de 2027, por contrato da calculadora).
    """
    d = data_op.isoformat()
    consultas = {
        "CBS": ("/calculadora/dados-abertos/aliquota-uniao", {"data": d}),
        "IBS_UF": ("/calculadora/dados-abertos/aliquota-uf", {"codigoUf": codigo_uf, "data": d}),
        "IBS_MUN": ("/calculadora/dados-abertos/aliquota-municipio", {"codigoMunicipio": int(municipio), "data": d}),
    }
    enviar = data_op >= INICIO_ALIQUOTA_OBRIGATORIA
    out, faltantes = {}, []
    for trib, (caminho, params) in consultas.items():
        resp = await client.get_cache(caminho, params)
        if resp.ok and isinstance(resp.corpo, dict) and resp.corpo.get("aliquotaReferencia") is not None:
            out[trib] = {"aliquota": str(Decimal(str(resp.corpo["aliquotaReferencia"]))),
                         "origem": "CALCULADORA", "registro_id": None}
            continue
        if not enviar:
            # Antes de 2027 a calculadora resolve sozinha e não aceita alíquota informada.
            out[trib] = {"aliquota": None, "origem": "CALCULADORA", "registro_id": None}
            continue
        reg = await vigente(db, trib, uf, municipio, data_op)
        if reg:
            out[trib] = {"aliquota": reg["aliquota"], "origem": "TABELA_INTERNA", "registro_id": reg["id"],
                         "fonte": reg.get("fonte"), "confirmado_por": reg.get("confirmado_por")}
        else:
            faltantes.append(trib)
    return {"aliquotas": out, "faltantes": faltantes, "enviar": enviar}


def mensagem_faltantes(faltantes: list, data_op: date) -> str:
    data_br = data_op.strftime("%d/%m/%Y")
    nomes = ", ".join(NOME_TRIBUTO[t] for t in faltantes)
    return (f"Não há alíquota cadastrada para {nomes} na data {data_br}. "
            "Solicite ao administrador o cadastro.")
