# @module routes.privacidade — Canal do titular, Central de Privacidade e ferramentas
# administrativas de privacidade (LGPD). Ver docs/privacidade/.
#
# ⚠️ NÃO adicionar `from __future__ import annotations` (slowapi + FastAPI: o body
# Pydantic vira query param — ver nota em routes/avaliacao_publica.py).
#
# Tudo atrás de flags (services/privacidade/config.py), padrão DESLIGADO:
#   PRIVACIDADE_RECURSOS_ATIVOS  → endpoints de titular/usuário respondem 404 quando off
#   PRIVACIDADE_MINUTAS_ATIVAS   → textos de Termos/Aviso
#   PRIVACIDADE_EXCLUSAO_EXECUCAO_ATIVA → execução da anonimização de conta
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from db import get_db
from dependencies import get_admin_user, get_authenticated_user
from services.privacidade import aceites as AC
from services.privacidade import config as CFG
from services.privacidade import documentos as DOCS
from services.privacidade import exclusao as EXC
from services.privacidade import exportacao as EXP
from services.privacidade import pedidos as PED
from services.ratelimit import pub_limiter

router = APIRouter(prefix="/privacidade", tags=["privacidade"])

_MSG_PEDIDO = ("Se os dados estiverem corretos, você receberá no e-mail informado um código "
               "para confirmar o pedido. Guarde o número do protocolo.")


def _exigir_recursos() -> None:
    if not CFG.recursos_ativos():
        raise HTTPException(status_code=404, detail="Recurso indisponível.")


# ── Público ─────────────────────────────────────────────────────────────────
@router.get("/config")
async def config_publica():
    """Estado das flags e identificação do controlador (o que faltar vem em `pendente`)."""
    return {
        "recursos_ativos": CFG.recursos_ativos(),
        "minutas_ativas": CFG.minutas_ativas(),
        "controlador": CFG.controlador(),
        "prazo_resposta_dias": CFG.prazo_resposta_dias(),
        "tipos_direito": {k: v for k, v in PED.TIPOS_DIREITO.items() if k in PED.TIPOS_PUBLICOS},
    }


@router.get("/documentos/{tipo}")
async def documento(tipo: Literal["termos", "privacidade"]):
    if not CFG.minutas_ativas():
        raise HTTPException(status_code=404, detail="Documento em revisão.")
    d = DOCS.carregar(tipo)
    if not d:
        raise HTTPException(status_code=404, detail="Documento indisponível.")
    return d


class PedidoTitularIn(BaseModel):
    nome: str = Field(max_length=120)
    email: str = Field(max_length=320)
    relacao: str = Field(max_length=40)
    tipo_direito: str = Field(max_length=60)
    descricao: str = Field(default="", max_length=4000)
    declaracao_veracidade: bool = False
    website: str = ""  # honeypot (campo oculto no formulário)


@router.post("/titular/pedidos", status_code=202)
@pub_limiter.limit("5/hour")
async def abrir_pedido(request: Request, body: PedidoTitularIn, db=Depends(get_db)):
    _exigir_recursos()
    if body.website:  # robô: resposta idêntica, nada gravado
        return {"ok": True, "protocolo": PED.gerar_protocolo(), "mensagem": _MSG_PEDIDO}
    try:
        doc = await PED.criar_pedido(db, body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True, "protocolo": doc["protocolo"], "mensagem": _MSG_PEDIDO}


class VerificarIn(BaseModel):
    email: str = Field(max_length=320)
    codigo: str = Field(max_length=12)


@router.post("/titular/pedidos/{protocolo}/verificar")
@pub_limiter.limit("10/hour")
async def verificar_pedido(request: Request, protocolo: str, body: VerificarIn, db=Depends(get_db)):
    _exigir_recursos()
    try:
        doc = await PED.verificar(db, protocolo, body.email, body.codigo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PED.visao_titular(doc)


class ConsultarIn(BaseModel):
    email: str = Field(max_length=320)


@router.post("/titular/pedidos/{protocolo}/status")
@pub_limiter.limit("20/hour")
async def status_pedido(request: Request, protocolo: str, body: ConsultarIn, db=Depends(get_db)):
    """POST (e não GET) para o e-mail não ir parar em URL/log de acesso."""
    _exigir_recursos()
    doc = await db.privacidade_pedidos.find_one(
        {"protocolo": protocolo.strip().upper(), "email": PED.normalizar_email(body.email)})
    if not doc:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado para este e-mail.")
    return PED.visao_titular(doc)


# ── Central de Privacidade (usuário logado) ─────────────────────────────────
@router.get("/me")
async def minha_privacidade(uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    _exigir_recursos()
    pedidos = await db.privacidade_pedidos.find({"user_id": uid}).to_list(200)
    return {
        "aceites": await AC.estado_aceites(db, uid),
        "consentimentos": await AC.estado_consentimentos(db, uid),
        "pedidos": [PED.visao_titular(p) for p in pedidos],
    }


class AceiteIn(BaseModel):
    tipo: Literal["termos", "privacidade"]
    versao: str = Field(max_length=60)
    hash: str = Field(max_length=64)


@router.post("/me/aceites")
async def aceitar(body: AceiteIn, uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    _exigir_recursos()
    if not CFG.minutas_ativas():
        raise HTTPException(status_code=409, detail="Documento ainda em revisão; aceite indisponível.")
    try:
        reg = await AC.registrar_aceite(db, uid, body.tipo, body.versao, body.hash)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"ok": True, "tipo": reg["tipo"], "versao": reg["versao"], "aceito_em": reg["aceito_em"]}


class ConsentimentoIn(BaseModel):
    finalidade: str = Field(max_length=40)
    concedido: bool


@router.post("/me/consentimentos")
async def consentir(body: ConsentimentoIn, uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    _exigir_recursos()
    try:
        await AC.registrar_consentimento(db, uid, body.finalidade, body.concedido)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return await AC.estado_consentimentos(db, uid)


class PedidoContaIn(BaseModel):
    tipo_direito: str = Field(max_length=60)
    descricao: str = Field(default="", max_length=4000)


@router.post("/me/pedidos", status_code=201)
async def pedido_da_conta(body: PedidoContaIn, uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    _exigir_recursos()
    if body.tipo_direito not in PED.TIPOS_PUBLICOS:
        raise HTTPException(status_code=422, detail="Tipo de pedido inválido.")
    u = await db.users.find_one({"id": uid}) or {}
    doc = await PED.criar_pedido(db, {"nome": u.get("name"), "email": u.get("email"),
                                      "tipo_direito": body.tipo_direito, "descricao": body.descricao,
                                      "relacao": "usuario"}, origem="central", user_id=uid)
    return PED.visao_titular(doc)


class ExportacaoIn(BaseModel):
    formato: Literal["json", "csv"] = "json"


@router.post("/me/exportacao", status_code=201)
@pub_limiter.limit("5/hour")
async def criar_exportacao(request: Request, body: ExportacaoIn,
                           uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    _exigir_recursos()
    r = await EXP.criar(db, uid, body.formato)
    return {"url": f"/api/privacidade/me/exportacao/{r['token']}", "expira_em": r["expira_em"],
            "formato": r["formato"], "uso_unico": True}


@router.get("/me/exportacao/{token}")
async def baixar_exportacao(token: str, uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    """Exige o token E a sessão do mesmo usuário; expira e vale para um download só."""
    _exigir_recursos()
    try:
        conteudo, formato = await EXP.baixar(db, uid, token)
    except EXP.ExportacaoIndisponivel:
        raise HTTPException(status_code=404, detail="Exportação não encontrada.")
    except EXP.ExportacaoExpirada:
        raise HTTPException(status_code=410, detail="Link expirado ou já utilizado. Gere uma nova exportação.")
    mime = "application/json" if formato == "json" else "text/csv; charset=utf-8"
    return Response(content=conteudo, media_type=mime, headers={
        "Content-Disposition": f'attachment; filename="meus-dados-avalieimob.{formato}"',
        "Cache-Control": "no-store",
    })


# ── Assinatura: informação clara + pedido de arrependimento (sem estorno automático) ──
PRAZO_ARREPENDIMENTO_DIAS = 7


@router.get("/me/assinatura")
async def minha_assinatura(uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    _exigir_recursos()
    u = await db.users.find_one({"id": uid}) or {}
    pagos = await db.transactions.find({"user_id": uid, "status": "approved"}).to_list(500)
    ultimo = max(pagos, key=lambda t: t.get("created_at") or datetime.min) if pagos else None
    agora = datetime.utcnow()
    dentro = bool(ultimo and ultimo.get("created_at")
                  and agora - ultimo["created_at"] <= timedelta(days=PRAZO_ARREPENDIMENTO_DIAS))
    return {
        "plano": u.get("plan"),
        "status": u.get("plan_status"),
        "acesso_ate": u.get("plan_expires"),
        # O checkout atual (Mercado Pago, preferência avulsa) NÃO renova sozinho.
        "renovacao_automatica": False,
        "como_cancelar": ("Não há cobrança recorrente: o acesso termina na data indicada e "
                          "nenhuma nova cobrança é feita sem um novo pagamento seu."),
        "ultimo_pagamento_em": ultimo and ultimo.get("created_at"),
        "dentro_prazo_arrependimento_7_dias": dentro,
        "observacao": ("O pedido de arrependimento é analisado pelo atendimento; a devolução, quando "
                       "cabível, é feita por decisão humana — o sistema não estorna automaticamente."),
    }


@router.post("/me/assinatura/arrependimento", status_code=201)
async def pedir_arrependimento(uid: str = Depends(get_authenticated_user), db=Depends(get_db)):
    _exigir_recursos()
    aberto = await db.privacidade_pedidos.find_one({"user_id": uid, "tipo_direito": "arrependimento_cdc",
                                                    "status": {"$in": ["recebido", "em_analise",
                                                                       "aguardando_informacao"]}})
    if aberto:
        return PED.visao_titular(aberto)  # idempotente: não duplica pedido aberto
    u = await db.users.find_one({"id": uid}) or {}
    doc = await PED.criar_pedido(db, {"nome": u.get("name"), "email": u.get("email"),
                                      "tipo_direito": "arrependimento_cdc", "relacao": "usuario",
                                      "descricao": "Pedido de arrependimento registrado pela Central."},
                                 origem="central", user_id=uid)
    return PED.visao_titular(doc)


# ── Administração ───────────────────────────────────────────────────────────
@router.get("/admin/pedidos")
async def admin_listar(status: Optional[str] = None, _admin: str = Depends(get_admin_user), db=Depends(get_db)):
    filtro = {"status": status} if status else {}
    docs = await db.privacidade_pedidos.find(filtro).sort("criado_em", -1).to_list(500)
    return [PED.visao_admin(d) for d in docs]


class AdminPedidoIn(BaseModel):
    status: Optional[str] = None
    responsavel: Optional[str] = Field(default=None, max_length=120)
    nota: Optional[str] = Field(default=None, max_length=500)


@router.patch("/admin/pedidos/{pedido_id}")
async def admin_atualizar(pedido_id: str, body: AdminPedidoIn,
                          admin: str = Depends(get_admin_user), db=Depends(get_db)):
    try:
        doc = await PED.atualizar_admin(db, pedido_id, admin, status=body.status,
                                        responsavel=body.responsavel, nota=body.nota)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return PED.visao_admin(doc)


@router.get("/admin/titular/localizar")
async def admin_localizar(email: str = "", documento: str = "", telefone: str = "",
                          _admin: str = Depends(get_admin_user), db=Depends(get_db)):
    try:
        return await EXC.localizar_titular(db, email=email, documento=documento, telefone=telefone)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/admin/exclusao/conta/{user_id}/plano")
async def admin_plano_exclusao(user_id: str, _admin: str = Depends(get_admin_user), db=Depends(get_db)):
    try:
        return await EXC.planejar_conta(db, user_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


class ExecutarExclusaoIn(BaseModel):
    confirmacao: str = Field(max_length=80)


@router.post("/admin/exclusao/conta/{user_id}/executar")
async def admin_executar_exclusao(user_id: str, body: ExecutarExclusaoIn,
                                  admin: str = Depends(get_admin_user), db=Depends(get_db)):
    if not CFG.execucao_exclusao_ativa():
        raise HTTPException(status_code=403, detail="Execução desativada (PRIVACIDADE_EXCLUSAO_EXECUCAO_ATIVA).")
    if body.confirmacao != f"ANONIMIZAR {user_id}":
        raise HTTPException(status_code=422, detail=f'Digite exatamente: ANONIMIZAR {user_id}')
    if user_id == admin:
        raise HTTPException(status_code=409, detail="Não é possível anonimizar a própria conta por aqui.")
    try:
        return await EXC.anonimizar_conta(db, user_id, admin)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))
