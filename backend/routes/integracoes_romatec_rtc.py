# @module routes.integracoes_romatec_rtc — ponte Romatec CRM -> calculadoras oficiais da Receita (CBS/IBS).
#
# O CRM roda em outro lugar e não alcança a rede privada das calculadoras. Ele chama o AvalieImob
# (servidor a servidor, HTTPS), assinando cada pedido com o MESMO segredo e o mesmo HMAC do
# provisionamento (ROMATEC_CRM_INTEGRACAO_SECRET; headers X-Romatec-Timestamp / X-Romatec-Signature
# sobre o corpo bruto, janela de ±300 s). O AvalieImob consulta as calculadoras e devolve o resultado.
# Mesmas regras do simulador do assinante: alíquotas híbridas, snapshot imutável, nada recalculado.
#
#   POST /api/integracoes/romatec/rtc/status        {}                         -> situação das calculadoras
#   POST /api/integracoes/romatec/rtc/municipios    {"uf": "MA"}               -> municípios da UF
#   POST /api/integracoes/romatec/rtc/classificacoes{"nbs": "...", "data": ...}-> CST/cClassTrib do NBS
#   POST /api/integracoes/romatec/rtc/simular       {...}                      -> simulação + snapshot
#
# Sem `from __future__ import annotations` (quebra o FastAPI com o rate limiter).
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db
from services import romatec_crm_integracao as RC
from services.receita_rtc import config as RCFG
from services.receita_rtc import mapper as MP
from services.receita_rtc import service as SVC
from services.receita_rtc.client import CalculadoraIndisponivel

logger = logging.getLogger("romatec")
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/integracoes/romatec/rtc", tags=["Integração Romatec CRM"])

CONTA_CRM = "romatec-crm"           # dono dos snapshots vindos do CRM (não é um usuário do AvalieImob)
ORIGENS_CRM = {"proposta": "crm_proposta", "contrato": "crm_contrato", "venda": "crm_venda"}


class OrigemCRM(BaseModel):
    tipo: str = Field(..., description="proposta | contrato | venda")
    id: str = Field(..., min_length=1, max_length=100)


class ItemCRM(BaseModel):
    valor: str
    nbs: str
    cst: Optional[str] = None
    cClassTrib: str


class SimularCRM(BaseModel):
    regime: str
    data_operacao: str
    uf: str
    codigo_municipio: str
    itens: List[ItemCRM] = Field(..., min_length=1, max_length=50)
    simples: Optional[dict] = None
    origem: OrigemCRM
    solicitado_por: Optional[str] = Field(None, max_length=120)


async def _corpo_assinado(request: Request) -> dict:
    """Valida a assinatura sobre o corpo BRUTO antes de interpretar o JSON."""
    try:
        segredo = RC.obter_segredo()
    except RC.IntegracaoNaoConfigurada:
        raise HTTPException(status_code=503, detail="Integração com o Romatec CRM não configurada")
    corpo = await request.body()
    if not RC.assinatura_valida(segredo, request.headers.get("X-Romatec-Timestamp"),
                                request.headers.get("X-Romatec-Signature"), corpo):
        logger.warning("Romatec CRM (rtc): assinatura inválida/expirada (ip=%s)",
                       request.client.host if request.client else None)
        raise HTTPException(status_code=401, detail="Requisição não autenticada")
    try:
        dados = json.loads(corpo.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=422, detail="Corpo JSON inválido")
    if not isinstance(dados, dict):
        raise HTTPException(status_code=422, detail="Corpo JSON inválido")
    return dados


def _exigir_ativo():
    if not RCFG.carregar().enabled:
        raise HTTPException(status_code=404, detail="Simulador de CBS/IBS desativado.")


def _publico(snap: dict) -> dict:
    s = dict(snap)
    for k in ("_id", "resultado_bruto", "entrada_enviada", "user_id", "criado_por"):
        s.pop(k, None)
    return s


@router.post("/status")
@limiter.limit("60/minute")
async def status(request: Request):
    await _corpo_assinado(request)
    return await SVC.diagnostico()


@router.post("/municipios")
@limiter.limit("60/minute")
async def municipios(request: Request):
    dados = await _corpo_assinado(request)
    _exigir_ativo()
    uf = str(dados.get("uf") or "").strip().upper()
    if len(uf) != 2:
        raise HTTPException(status_code=422, detail="uf: sigla de 2 letras.")
    try:
        return {"municipios": await SVC.municipios(uf)}
    except CalculadoraIndisponivel as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/classificacoes")
@limiter.limit("60/minute")
async def classificacoes(request: Request):
    dados = await _corpo_assinado(request)
    _exigir_ativo()
    nbs = "".join(ch for ch in str(dados.get("nbs") or "") if ch.isdigit())
    if len(nbs) != 9:
        raise HTTPException(status_code=422, detail="nbs: informe 9 dígitos.")
    data = str(dados.get("data") or "")[:10]
    if not data:
        raise HTTPException(status_code=422, detail="data: informe a data de referência (AAAA-MM-DD).")
    try:
        return await SVC.classificacoes_do_nbs(nbs, data)
    except CalculadoraIndisponivel as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/simular")
@limiter.limit("60/minute")
async def simular(request: Request, db=Depends(get_db)):
    dados = await _corpo_assinado(request)
    _exigir_ativo()
    try:
        p = SimularCRM.model_validate(dados)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=[{"campo": ".".join(str(x) for x in err.get("loc", ())),
                                                      "msg": err.get("msg")} for err in e.errors()])
    origem_tipo = ORIGENS_CRM.get(p.origem.tipo.lower())
    if not origem_tipo:
        raise HTTPException(status_code=422, detail="origem.tipo: use proposta, contrato ou venda.")
    entrada = p.model_dump(exclude={"origem", "solicitado_por"})
    try:
        snap = await SVC.simular(db, CONTA_CRM, entrada, origem_tipo, p.origem.id)
    except MP.EntradaInvalida as e:
        raise HTTPException(status_code=422, detail=str(e))
    except SVC.SemAliquota as e:
        raise HTTPException(status_code=409, detail={"mensagem": str(e), "faltantes": e.faltantes})
    except SVC.SimuladorDesativado as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CalculadoraIndisponivel as e:
        raise HTTPException(status_code=503, detail=str(e))
    if p.solicitado_por:
        await db[SVC.COLECAO].update_one({"id": snap["id"]}, {"$set": {"solicitado_por_crm": p.solicitado_por}})
    logger.info("Romatec CRM (rtc): simulação %s origem=%s situacao=%s", snap["id"], origem_tipo, snap["situacao"])
    return _publico(snap)
