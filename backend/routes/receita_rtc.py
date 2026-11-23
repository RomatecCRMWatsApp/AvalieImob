# @module routes.receita_rtc — administração da integração com as calculadoras da Receita (CBS/IBS).
#
# Só administrador. Nesta fase: diagnóstico das calculadoras e tabela interna de alíquotas
# (PENDENCIAS.md §3.3). A tela de simulação do assinante entra na Fase 4.
# Sem `from __future__ import annotations` (quebra o FastAPI com o rate limiter; ver avaliacao_publica.py).
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_db
from dependencies import get_admin_user
from services.receita_rtc import aliquotas as ALQ
from services.receita_rtc import service as SVC

router = APIRouter(prefix="/admin/receita-rtc", tags=["receita-rtc"], dependencies=[Depends(get_admin_user)])


class AliquotaNova(BaseModel):
    tributo: str
    uf: Optional[str] = None
    codigo_municipio: Optional[str] = None
    aliquota: str
    vigencia_inicio: str
    vigencia_fim: Optional[str] = None
    fonte: str


class Confirmacao(BaseModel):
    confirmado_por: str


class Revogacao(BaseModel):
    motivo: str


def _limpo(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


@router.get("/status")
async def status():
    return await SVC.diagnostico()


@router.get("/aliquotas")
async def listar_aliquotas(db=Depends(get_db)):
    docs = await db[ALQ.COLECAO].find({}).sort("vigencia_inicio", -1).to_list(2000)
    return {"aliquotas": [_limpo(d) for d in docs]}


@router.post("/aliquotas")
async def criar_aliquota(body: AliquotaNova, db=Depends(get_db), uid: str = Depends(get_admin_user)):
    try:
        return _limpo(await ALQ.criar(db, body.model_dump(), uid))
    except ALQ.AliquotaInvalida as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/aliquotas/{registro_id}/confirmar")
async def confirmar_aliquota(registro_id: str, body: Confirmacao, db=Depends(get_db),
                             uid: str = Depends(get_admin_user)):
    try:
        return _limpo(await ALQ.confirmar(db, registro_id, uid, body.confirmado_por))
    except ALQ.AliquotaInvalida as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/aliquotas/{registro_id}/revogar")
async def revogar_aliquota(registro_id: str, body: Revogacao, db=Depends(get_db),
                           uid: str = Depends(get_admin_user)):
    try:
        return _limpo(await ALQ.revogar(db, registro_id, uid, body.motivo))
    except ALQ.AliquotaInvalida as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/aliquotas/auditoria")
async def auditoria(db=Depends(get_db)):
    docs = await db[ALQ.COLECAO_AUDITORIA].find({}).sort("em", -1).to_list(500)
    return {"eventos": [_limpo(d) for d in docs]}


# ── assinante: configuração por conta e simulação de honorários (Fase 4) ─────────
from datetime import date as _date  # noqa: E402

from dependencies import get_active_subscriber  # noqa: E402
from services.receita_rtc import config as RCFG  # noqa: E402
from services.receita_rtc import conta as CONTA  # noqa: E402
from services.receita_rtc import mapper as MP  # noqa: E402
from services.receita_rtc.client import CalculadoraIndisponivel  # noqa: E402

router_assinante = APIRouter(prefix="/receita-rtc", tags=["receita-rtc"])


def _exigir_ativo():
    if not RCFG.carregar().enabled:
        raise HTTPException(status_code=404, detail="Simulador de CBS/IBS desativado.")


class ConfigConta(BaseModel):
    regime: Optional[str] = None
    uf: Optional[str] = None
    codigo_municipio: Optional[str] = None
    nome_municipio: Optional[str] = None
    nbs: Optional[str] = None
    cst: Optional[str] = None
    cClassTrib: Optional[str] = None
    descricao_classificacao: Optional[str] = None
    confirmado_com_contador: bool = False
    simples: Optional[dict] = None


class PedidoSimulacao(BaseModel):
    origem_tipo: str = "recibo"
    origem_id: str
    data_operacao: str


@router_assinante.get("/disponivel")
async def disponivel(db=Depends(get_db), uid: str = Depends(get_active_subscriber)):
    """O front só mostra o botão quando ativo. Com a flag desligada, nada aparece."""
    if not RCFG.carregar().enabled:
        return {"ativo": False}
    cfg = await CONTA.obter(db, uid)
    falta = CONTA.faltantes(cfg)
    return {"ativo": True, "configurado": not falta, "faltantes": falta, "config": cfg,
            "aviso": RCFG.AVISO_FIXO}


@router_assinante.put("/config")
async def salvar_config(body: ConfigConta, db=Depends(get_db), uid: str = Depends(get_active_subscriber)):
    _exigir_ativo()
    try:
        cfg = await CONTA.salvar(db, uid, body.model_dump())
    except MP.EntradaInvalida as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"config": cfg, "faltantes": CONTA.faltantes(cfg)}


@router_assinante.get("/municipios")
async def listar_municipios(uf: str, uid: str = Depends(get_active_subscriber)):
    _exigir_ativo()
    try:
        return {"municipios": await SVC.municipios(uf)}
    except CalculadoraIndisponivel as e:
        raise HTTPException(status_code=503, detail=str(e))


@router_assinante.get("/classificacoes")
async def classificacoes(nbs: str, data: Optional[str] = None, uid: str = Depends(get_active_subscriber)):
    _exigir_ativo()
    nbs = "".join(ch for ch in nbs if ch.isdigit())
    if len(nbs) != 9:
        raise HTTPException(status_code=422, detail="NBS: informe 9 dígitos.")
    try:
        return await SVC.classificacoes_do_nbs(nbs, data or _date.today().isoformat())
    except CalculadoraIndisponivel as e:
        raise HTTPException(status_code=503, detail=str(e))


async def _valor_da_origem(db, uid: str, origem_tipo: str, origem_id: str):
    if origem_tipo != "recibo":
        raise HTTPException(status_code=422, detail="Por enquanto a simulação é feita a partir do recibo de honorários.")
    rec = await db.recibos.find_one({"id": origem_id, "user_id": uid}, {"valor": 1})
    if not rec:
        raise HTTPException(status_code=404, detail="Recibo não encontrado.")
    return rec.get("valor")


@router_assinante.post("/simular")
async def simular(body: PedidoSimulacao, db=Depends(get_db), uid: str = Depends(get_active_subscriber)):
    _exigir_ativo()
    cfg = await CONTA.obter(db, uid)
    falta = CONTA.faltantes(cfg)
    if falta:
        raise HTTPException(status_code=409, detail={"mensagem": "Configure os dados tributários da conta antes de simular.",
                                                     "faltantes": falta})
    valor = await _valor_da_origem(db, uid, body.origem_tipo, body.origem_id)
    try:
        snap = await SVC.simular(db, uid, CONTA.montar_entrada(cfg, body.data_operacao, valor),
                                 body.origem_tipo, body.origem_id)
    except MP.EntradaInvalida as e:
        raise HTTPException(status_code=422, detail=str(e))
    except SVC.SemAliquota as e:
        raise HTTPException(status_code=409, detail={"mensagem": str(e), "faltantes": e.faltantes})
    except SVC.SimuladorDesativado as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CalculadoraIndisponivel as e:
        raise HTTPException(status_code=503, detail=str(e))
    return _publico(snap)


def _publico(snap: dict) -> dict:
    """O que a tela precisa. A resposta bruta e o pedido enviado ficam só no banco (auditoria)."""
    s = _limpo(snap)
    for k in ("resultado_bruto", "entrada_enviada", "user_id", "criado_por"):
        s.pop(k, None)
    return s


@router_assinante.get("/simulacoes")
async def listar_simulacoes(origem_tipo: str, origem_id: str, db=Depends(get_db),
                            uid: str = Depends(get_active_subscriber)):
    _exigir_ativo()
    docs = await db[SVC.COLECAO].find({"user_id": uid, "origem_tipo": origem_tipo, "origem_id": origem_id}) \
        .sort("criado_em", -1).to_list(50)
    return {"simulacoes": [_publico(d) for d in docs]}
