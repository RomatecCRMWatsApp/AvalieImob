# @module routes.prospeccao — Prospecção B2B (imobiliárias/corretores) + campanhas de e-mail.
#
# CRM leve de prospects (por dono/admin) + disparo de PROPOSTA por e-mail em FILA THROTTLED
# (limite por rodada + intervalo entre e-mails, para proteger a reputação do domínio). O e-mail
# leva ao /cadastro (captação). Fonte dos e-mails: lista curada + importação (descoberta por
# API fica como extensão — ver /prospeccao/descobrir).
import asyncio
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from db import get_db
from dependencies import get_admin_user, serialize_doc

router = APIRouter(tags=["prospeccao"])
logger = logging.getLogger("romatec")

STATUS_LABELS = ["Não contatado", "Aguardando retorno", "Em conversa", "Parceria fechada", "Sem interesse"]


def _agora():
    return datetime.now(timezone.utc)


def _iso():
    return _agora().isoformat()


def _app_url() -> str:
    raw = (os.environ.get("APP_URL") or os.environ.get("PLATFORM_URL")
           or "https://www.romatecavalieimob.com.br").rstrip("/")
    return raw.replace("://romatecavalieimob.com.br", "://www.romatecavalieimob.com.br")


# Lista curada inicial (dados públicos — PJ com e-mail comercial publicado; região MA).
_SEED_REGIAO = [
    {"cidade": "Açailândia", "nome": "Stela Imóveis", "telefone": "+55 99 98844-2238", "endereco": "R. Rio Grande do Norte, 101 - Centro", "email": "stelaimoveis@gmail.com"},
    {"cidade": "Açailândia", "nome": "Adventu's Consultoria Imobiliária", "telefone": "+55 99 99150-0527", "endereco": "Rua Fortaleza, 502 - Centro", "email": "atendimento@adventusimobiliaria.com.br"},
    {"cidade": "Açailândia", "nome": "Value Consultoria Imobiliária", "telefone": "+55 99 99101-9997", "endereco": "R. São Raimundo, 240B", "email": ""},
    {"cidade": "Açailândia", "nome": "Morar Bem Imobiliária", "telefone": "+55 99 99188-0015", "endereco": "Av. Rafael de Almeida - Ouro Verde", "email": ""},
    {"cidade": "Açailândia", "nome": "CINAL Imóveis", "telefone": "+55 99 3538-1194", "endereco": "R. Dorgival Pinheiro de Souza, 1250", "email": ""},
    {"cidade": "Açailândia", "nome": "Vasconcelos Empreendimentos Imobiliários", "telefone": "+55 99 98121-3123", "endereco": "R. Pau Marfim", "email": ""},
    {"cidade": "Açailândia", "nome": "Porto Bello", "telefone": "+55 99 99171-2729", "endereco": "R. Tiradentes I, 1344 - Centro", "email": ""},
    {"cidade": "Imperatriz", "nome": "Imobiliária Borges", "telefone": "+55 99 98144-8000", "endereco": "Av. Babaçulândia, 335 - Entroncamento", "email": "borgesempreendimentos@outlook.com"},
    {"cidade": "Imperatriz", "nome": "Casal Corretor Negócios Imobiliários", "telefone": "+55 99 99105-6748", "endereco": "Av. Dorgival Pinheiro de Sousa - Vila Lobão", "email": ""},
    {"cidade": "Imperatriz", "nome": "Patrick Pereira - Corretor e Avaliador de Imóveis", "telefone": "+55 99 98483-3974", "endereco": "R. Ceará, 120 - Juçara", "email": ""},
    {"cidade": "Imperatriz", "nome": "Capto Imóveis", "telefone": "+55 99 99210-6290", "endereco": "R. Urbano Santos, 697 - Juçara", "email": "captoimoveis@gmail.com"},
    {"cidade": "Imperatriz", "nome": "Unyca Imobiliária", "telefone": "+55 99 99186-7008", "endereco": "Rua Projetada - Nova Imperatriz", "email": ""},
    {"cidade": "Imperatriz", "nome": "MC Imóveis Imperatriz", "telefone": "+55 99 98499-1112", "endereco": "R. José Bonifácio, 700", "email": ""},
    {"cidade": "Imperatriz", "nome": "Dias Imobiliária", "telefone": "+55 99 3524-4264", "endereco": "Av. Bernardo Sayão, 770", "email": ""},
    {"cidade": "Imperatriz", "nome": "Central Imobiliária", "telefone": "+55 99 3525-7683", "endereco": "R. Cel. Manoel Bandeira, 1897", "email": ""},
    {"cidade": "Imperatriz", "nome": "Rayza Machado Imobiliária", "telefone": "+55 99 99177-8809", "endereco": "Av. Pedro Neiva de Santana", "email": ""},
    {"cidade": "Imperatriz", "nome": "Ademar Mariano Empreendimentos", "telefone": "+55 99 3525-2000", "endereco": "R. Frei Manoel Procópio, 14", "email": "ademarmariano@hotmail.com"},
    {"cidade": "Grajaú", "nome": "Imobiliária Única", "telefone": "+55 99 98239-2579", "endereco": "BR-226", "email": ""},
    {"cidade": "Grajaú", "nome": "Maraca Imobiliária", "telefone": "+55 99 98121-4373", "endereco": "R. Frei Benjamin de Borno, 12A - Centro", "email": ""},
    {"cidade": "Grajaú", "nome": "Imobiliária Portular", "telefone": "+55 99 98538-6764", "endereco": "R. Rui Barbosa - Canoeiro", "email": ""},
    {"cidade": "Grajaú", "nome": "Grajaú Imóveis", "telefone": "+55 99 3532-9464", "endereco": "R. Rui Barbosa, 1 - Vila Tucum", "email": ""},
    {"cidade": "Grajaú", "nome": "Silvana Ramos Assessoria e Consultoria Imobiliária", "telefone": "+55 99 99184-1538", "endereco": "R. Melquisedeque - Vila Tucum", "email": ""},
    {"cidade": "Presidente Dutra", "nome": "Poliana Gomes - Imóveis", "telefone": "+55 98 99225-8753", "endereco": "Tv. Raimundo Matos, 55 - Centro", "email": ""},
    {"cidade": "Presidente Dutra", "nome": "Clerizam Corretora de Imóveis", "telefone": "+55 99 98183-1644", "endereco": "R. Magalhães de Almeida, 79", "email": ""},
    {"cidade": "Presidente Dutra", "nome": "Terra Casa Imobiliária", "telefone": "", "endereco": "Presidente Dutra - MA", "email": ""},
    {"cidade": "Gov. Edison Lobão", "nome": "Kit Imóveis", "telefone": "", "endereco": "R. Santa Rita, 127", "email": ""},
]
for _p in _SEED_REGIAO:
    _p.setdefault("uf", "MA")


# ──────────────────────────────────────────────────────────────────────────────
# Payloads
# ──────────────────────────────────────────────────────────────────────────────
class ProspectIn(BaseModel):
    cidade: str = ""
    nome: str = ""
    telefone: str = ""
    endereco: str = ""
    email: str = ""
    uf: str = "MA"


class ImportBody(BaseModel):
    prospects: List[ProspectIn] = []


class StatusBody(BaseModel):
    status: Optional[int] = None
    obs: Optional[str] = None
    email: Optional[str] = None


class CampanhaBody(BaseModel):
    limite: int = 40           # máx. e-mails nesta rodada
    intervalo: int = 20        # segundos entre e-mails
    teste_email: Optional[str] = None   # se setado, envia só 1 e-mail de teste


class AutoBody(BaseModel):
    ativo: bool = False
    hora: int = 9              # hora local (America/Fortaleza, UTC-3) do disparo diário
    limite_dia: int = 40       # máx. e-mails por dia
    intervalo: int = 30        # segundos entre e-mails


class WaConfigBody(BaseModel):
    ativo: bool = False
    hora: int = 10             # hora local do disparo diário de WhatsApp
    limite_dia: int = 1        # WhatsApp: 1 por dia (máx. 2) — proteção anti-bloqueio
    mensagem: Optional[str] = None


class WaEnviarBody(BaseModel):
    limite: int = 1                       # quantos enviar agora (cap 2/dia)
    teste_telefone: Optional[str] = None  # se setado, envia 1 mensagem de teste
    teste_texto: Optional[str] = None


_ELEGIVEL = {
    "email": {"$nin": [None, ""]},
    "email_enviado": {"$ne": True},
    "opt_out": {"$ne": True},
    "status": {"$ne": 4},
}


def _dedup_key(p: dict) -> str:
    e = re.sub(r"\s", "", (p.get("email") or "").lower())
    return e or f"{(p.get('nome') or '').strip().lower()}|{(p.get('cidade') or '').strip().lower()}"


def _novo_prospect(uid: str, p: dict) -> dict:
    return {
        "id": secrets.token_hex(8), "user_id": uid,
        "cidade": (p.get("cidade") or "").strip(), "nome": (p.get("nome") or "").strip(),
        "telefone": (p.get("telefone") or "").strip(), "endereco": (p.get("endereco") or "").strip(),
        "email": (p.get("email") or "").strip(), "uf": (p.get("uf") or "MA").strip().upper()[:2] or "MA",
        "status": 0, "obs": "", "email_enviado": False, "email_enviado_em": None, "email_erro": None,
        "whatsapp_enviado": False, "whatsapp_enviado_em": None, "whatsapp_erro": None,
        "opt_out": False, "opt_out_token": secrets.token_urlsafe(16), "origem": p.get("origem") or "manual",
        "created_at": _iso(), "updated_at": _iso(),
    }


async def _inserir_dedup(db, uid: str, itens: List[dict], origem: str) -> int:
    existentes = await db.prospeccao.find({"user_id": uid}, {"email": 1, "nome": 1, "cidade": 1}).to_list(20000)
    vistos = {_dedup_key(x) for x in existentes}
    novos = []
    for p in itens:
        if not (p.get("nome") or "").strip():
            continue
        k = _dedup_key(p)
        if k in vistos:
            continue
        vistos.add(k)
        d = _novo_prospect(uid, p)
        d["origem"] = origem
        novos.append(d)
    if novos:
        await db.prospeccao.insert_many(novos)
    return len(novos)


# ──────────────────────────────────────────────────────────────────────────────
# CRUD + import + seed
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/prospeccao")
async def listar(cidade: str = "", status: str = "", busca: str = "", com_email: str = "",
                 uid: str = Depends(get_admin_user), db=Depends(get_db)):
    q = {"user_id": uid}
    if cidade:
        q["cidade"] = cidade
    if status not in ("", None):
        q["status"] = int(status)
    if com_email == "1":
        q["email"] = {"$nin": [None, ""]}
    if busca:
        q["nome"] = {"$regex": re.escape(busca), "$options": "i"}
    docs = await db.prospeccao.find(q).sort([("cidade", 1), ("nome", 1)]).to_list(20000)
    cidades = await db.prospeccao.distinct("cidade", {"user_id": uid})
    return {"prospects": [serialize_doc(d) for d in docs], "cidades": sorted([c for c in cidades if c])}


@router.get("/prospeccao/stats")
async def stats(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    total = await db.prospeccao.count_documents({"user_id": uid})
    com_email = await db.prospeccao.count_documents({"user_id": uid, "email": {"$nin": [None, ""]}})
    enviados = await db.prospeccao.count_documents({"user_id": uid, "email_enviado": True})
    elegiveis = await db.prospeccao.count_documents({"user_id": uid, **_ELEGIVEL})
    por_status = []
    for i, lbl in enumerate(STATUS_LABELS):
        por_status.append({"status": i, "label": lbl,
                           "n": await db.prospeccao.count_documents({"user_id": uid, "status": i})})
    return {"total": total, "com_email": com_email, "enviados": enviados,
            "elegiveis": elegiveis, "por_status": por_status}


@router.post("/prospeccao/seed")
async def seed_regiao(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Importa a lista curada inicial das imobiliárias da região (dedup — não duplica)."""
    n = await _inserir_dedup(db, uid, _SEED_REGIAO, "seed_regiao")
    return {"ok": True, "importados": n, "total_lista": len(_SEED_REGIAO)}


@router.post("/prospeccao/importar")
async def importar(body: ImportBody, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    itens = [p.model_dump() for p in body.prospects]
    n = await _inserir_dedup(db, uid, itens, "import")
    return {"ok": True, "importados": n, "recebidos": len(itens)}


@router.post("/prospeccao", status_code=201)
async def criar(body: ProspectIn, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    d = _novo_prospect(uid, body.model_dump())
    await db.prospeccao.insert_one(d)
    return serialize_doc(d)


@router.patch("/prospeccao/{pid}")
async def atualizar(pid: str, body: StatusBody, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    sets = {"updated_at": _iso()}
    if body.status is not None:
        sets["status"] = int(body.status)
    if body.obs is not None:
        sets["obs"] = body.obs
    if body.email is not None:
        sets["email"] = body.email.strip()
    res = await db.prospeccao.update_one({"id": pid, "user_id": uid}, {"$set": sets})
    if not res.matched_count:
        raise HTTPException(404, "Prospect não encontrado")
    return {"ok": True}


@router.delete("/prospeccao/{pid}")
async def excluir(pid: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    res = await db.prospeccao.delete_one({"id": pid, "user_id": uid})
    return {"ok": True, "removido": bool(res.deleted_count)}


# ──────────────────────────────────────────────────────────────────────────────
# Proposta (preview) + campanha throttled
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/prospeccao/proposta/preview")
async def preview_proposta(uid: str = Depends(get_admin_user)):
    from email_service import build_prospeccao_email
    _, html = build_prospeccao_email("Imobiliária Exemplo", _app_url() + "/cadastro",
                                     _app_url() + "/api/prospeccao/descadastrar/exemplo")
    return Response(content=html, media_type="text/html")


async def _rodar_campanha(db, uid: str, limite: int, intervalo: int):
    from email_service import send_prospeccao_email_sync
    cta = _app_url() + "/cadastro"
    await db.prospeccao_campanha.update_one(
        {"_id": uid}, {"$set": {"enviando": True, "parar": False, "iniciado_em": _iso()}}, upsert=True)
    enviados = 0
    try:
        while enviados < limite:
            camp = await db.prospeccao_campanha.find_one({"_id": uid})
            if camp and camp.get("parar"):
                break
            p = await db.prospeccao.find_one({"user_id": uid, **_ELEGIVEL})
            if not p:
                break
            unsub = _app_url() + "/api/prospeccao/descadastrar/" + (p.get("opt_out_token") or "")
            try:
                await asyncio.to_thread(send_prospeccao_email_sync, p["email"], p.get("nome", ""), cta, unsub)
                await db.prospeccao.update_one({"id": p["id"], "user_id": uid}, {"$set": {
                    "email_enviado": True, "email_enviado_em": _iso(), "email_erro": None,
                    "status": max(int(p.get("status") or 0), 1), "updated_at": _iso()}})
            except Exception as e:  # noqa: BLE001 — marca enviado c/ erro p/ não repetir (loop)
                await db.prospeccao.update_one({"id": p["id"], "user_id": uid}, {"$set": {
                    "email_enviado": True, "email_erro": f"{type(e).__name__}: {e}", "updated_at": _iso()}})
                logger.warning("Prospecção: falha ao enviar p/ %s: %s", p.get("email"), e)
            enviados += 1
            await db.prospeccao_campanha.update_one(
                {"_id": uid}, {"$inc": {"enviados_total": 1}, "$set": {"ultimo_em": _iso()}})
            await asyncio.sleep(max(1, intervalo))
    finally:
        await db.prospeccao_campanha.update_one(
            {"_id": uid}, {"$set": {"enviando": False, "finalizado_em": _iso()}})


@router.post("/prospeccao/campanha/enviar")
async def enviar_campanha(body: CampanhaBody, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Inicia o disparo THROTTLED da proposta aos prospects elegíveis (fila em segundo plano)."""
    if body.teste_email:
        from email_service import send_prospeccao_email_sync
        try:
            await asyncio.to_thread(send_prospeccao_email_sync, body.teste_email.strip(), "Teste",
                                    _app_url() + "/cadastro", _app_url() + "/api/prospeccao/descadastrar/teste")
        except Exception as e:  # noqa: BLE001
            raise HTTPException(502, f"Falha no teste: {type(e).__name__}: {e}")
        return {"ok": True, "teste": True, "enviado_para": body.teste_email.strip()}

    camp = await db.prospeccao_campanha.find_one({"_id": uid})
    if camp and camp.get("enviando"):
        raise HTTPException(409, "Já há uma campanha em envio. Aguarde ou clique em Parar.")
    n = await db.prospeccao.count_documents({"user_id": uid, **_ELEGIVEL})
    if not n:
        raise HTTPException(422, "Nenhum prospect elegível (com e-mail, ainda não enviado e não descadastrado).")
    limite = max(1, min(int(body.limite or 40), 300))
    intervalo = max(1, min(int(body.intervalo or 20), 300))
    asyncio.create_task(_rodar_campanha(db, uid, limite, intervalo))
    return {"ok": True, "iniciada": True, "limite": limite, "intervalo": intervalo, "elegiveis": n}


@router.get("/prospeccao/campanha/status")
async def campanha_status(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    camp = await db.prospeccao_campanha.find_one({"_id": uid}) or {}
    return {
        "enviando": bool(camp.get("enviando")),
        "elegiveis": await db.prospeccao.count_documents({"user_id": uid, **_ELEGIVEL}),
        "enviados": await db.prospeccao.count_documents({"user_id": uid, "email_enviado": True}),
        "com_email": await db.prospeccao.count_documents({"user_id": uid, "email": {"$nin": [None, ""]}}),
        "com_erro": await db.prospeccao.count_documents({"user_id": uid, "email_erro": {"$nin": [None, ""]}}),
        "ultimo_em": camp.get("ultimo_em"),
    }


@router.post("/prospeccao/campanha/parar")
async def parar_campanha(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    await db.prospeccao_campanha.update_one({"_id": uid}, {"$set": {"parar": True}}, upsert=True)
    return {"ok": True}


@router.post("/prospeccao/campanha/reset-erros")
async def reset_erros(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Reabilita o reenvio dos prospects que falharam (limpa email_enviado/erro)."""
    res = await db.prospeccao.update_many(
        {"user_id": uid, "email_erro": {"$nin": [None, ""]}},
        {"$set": {"email_enviado": False, "email_erro": None, "email_enviado_em": None, "updated_at": _iso()}})
    return {"ok": True, "reabilitados": res.modified_count}


# ──────────────────────────────────────────────────────────────────────────────
# Agendamento diário automático (scheduler in-app com lease — roda em 1 worker só)
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/prospeccao/campanha/auto")
async def obter_auto(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    camp = await db.prospeccao_campanha.find_one({"_id": uid}) or {}
    return {
        "ativo": bool(camp.get("auto_ativo")),
        "hora": int(camp.get("auto_hora", 9)),
        "limite_dia": int(camp.get("auto_limite_dia", 40)),
        "intervalo": int(camp.get("auto_intervalo", 30)),
        "ultimo_dia": camp.get("auto_ultimo_dia"),
    }


@router.post("/prospeccao/campanha/auto")
async def salvar_auto(body: AutoBody, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    await db.prospeccao_campanha.update_one(
        {"_id": uid},
        {"$set": {
            "auto_ativo": bool(body.ativo),
            "auto_hora": max(0, min(int(body.hora), 23)),
            "auto_limite_dia": max(1, min(int(body.limite_dia), 500)),
            "auto_intervalo": max(1, min(int(body.intervalo), 300)),
        }},
        upsert=True)
    return {"ok": True}


_FORTALEZA_OFFSET = timedelta(hours=3)   # America/Fortaleza = UTC-3 (sem horário de verão)


# ──────────────────────────────────────────────────────────────────────────────
# Campanha por WHATSAPP (Z-API) — 1 a 2 por dia (anti-bloqueio), texto humano
# ──────────────────────────────────────────────────────────────────────────────
_WA_MSG_DEFAULT = (
    "Oi, {primeiro}! Tudo bem? 😊\n\n"
    "Aqui é o José, da Romatec, aqui de Açailândia. Vi que vocês trabalham com imóveis aí "
    "em {cidade} e queria te mostrar uma coisa que criei pra facilitar o dia a dia do corretor.\n\n"
    "É uma plataforma onde dá pra emitir avaliação de imóvel (PTAM/laudo NBR), fazer contrato "
    "de exclusividade com o cliente assinando pelo próprio WhatsApp, e até georreferenciamento — "
    "tudo do celular, rapidinho e com validade jurídica.\n\n"
    "É grátis pra testar, dá uma olhada quando puder: {link}\n\n"
    "Se fizer sentido pra vocês, é só se cadastrar por aí. Qualquer dúvida me chama, tô à disposição! 🤝"
)

_ELEGIVEL_WA = {
    "telefone": {"$nin": [None, ""]},
    "whatsapp_enviado": {"$ne": True},
    "opt_out": {"$ne": True},
    "status": {"$ne": 4},
}


def _wa_interpolar(tpl: str, p: dict) -> str:
    nome = (p.get("nome") or "").strip()
    primeiro = nome.split()[0] if nome else "tudo bem"
    return (str(tpl or _WA_MSG_DEFAULT)
            .replace("{primeiro}", primeiro)
            .replace("{nome}", nome or "tudo bem")
            .replace("{cidade}", (p.get("cidade") or "na sua região"))
            .replace("{link}", _app_url() + "/cadastro"))


async def _rodar_whatsapp(db, uid: str, limite_pedido: int) -> int:
    """Envia até `limite_pedido` mensagens de WhatsApp (Z-API), respeitando o teto DIÁRIO
    (wa_limite_dia, máx. 2). Estado do dia em prospeccao_campanha (wa_dia/wa_enviados_hoje)."""
    from services.integracoes_util import carregar_integracoes
    from services import zapi_service

    cfg = await carregar_integracoes(db, uid)
    if not (cfg.get("zapi_instance_id") and cfg.get("zapi_token")):
        logger.warning("Prospecção WA: Z-API não configurada p/ %s", uid)
        return 0
    camp = await db.prospeccao_campanha.find_one({"_id": uid}) or {}
    template = camp.get("wa_mensagem") or _WA_MSG_DEFAULT
    limite_dia = max(1, min(int(camp.get("wa_limite_dia", 1)), 2))
    hoje = (_agora() - _FORTALEZA_OFFSET).strftime("%Y-%m-%d")
    if camp.get("wa_dia") != hoje:
        await db.prospeccao_campanha.update_one(
            {"_id": uid}, {"$set": {"wa_dia": hoje, "wa_enviados_hoje": 0}}, upsert=True)
        enviados_hoje = 0
    else:
        enviados_hoje = int(camp.get("wa_enviados_hoje", 0))
    n_enviar = max(0, min(int(limite_pedido), limite_dia - enviados_hoje))
    enviados = 0
    for _ in range(n_enviar):
        p = await db.prospeccao.find_one({"user_id": uid, **_ELEGIVEL_WA})
        if not p:
            break
        msg = _wa_interpolar(template, p)
        try:
            await zapi_service.send_text(
                instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
                security_token=cfg.get("zapi_security_token"),
                phone=p["telefone"], message=msg)
            await db.prospeccao.update_one({"id": p["id"], "user_id": uid}, {"$set": {
                "whatsapp_enviado": True, "whatsapp_enviado_em": _iso(), "whatsapp_erro": None,
                "status": max(int(p.get("status") or 0), 1), "updated_at": _iso()}})
        except Exception as e:  # noqa: BLE001 — marca enviado c/ erro p/ não repetir
            await db.prospeccao.update_one({"id": p["id"], "user_id": uid}, {"$set": {
                "whatsapp_enviado": True, "whatsapp_erro": f"{type(e).__name__}: {e}", "updated_at": _iso()}})
            logger.warning("Prospecção WA: falha p/ %s: %s", p.get("telefone"), e)
        enviados += 1
        await db.prospeccao_campanha.update_one(
            {"_id": uid}, {"$inc": {"wa_enviados_hoje": 1, "wa_enviados_total": 1},
                           "$set": {"wa_ultimo_em": _iso()}})
        if enviados < n_enviar:
            await asyncio.sleep(25)   # pausa natural entre as (no máx. 2) mensagens do dia
    return enviados


@router.get("/prospeccao/whatsapp/config")
async def wa_config_get(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    camp = await db.prospeccao_campanha.find_one({"_id": uid}) or {}
    return {
        "ativo": bool(camp.get("wa_auto_ativo")),
        "hora": int(camp.get("wa_hora", 10)),
        "limite_dia": int(camp.get("wa_limite_dia", 1)),
        "mensagem": camp.get("wa_mensagem") or _WA_MSG_DEFAULT,
        "mensagem_padrao": _WA_MSG_DEFAULT,
    }


@router.post("/prospeccao/whatsapp/config")
async def wa_config_set(body: WaConfigBody, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    sets = {
        "wa_auto_ativo": bool(body.ativo),
        "wa_hora": max(0, min(int(body.hora), 23)),
        "wa_limite_dia": max(1, min(int(body.limite_dia), 2)),
    }
    if body.mensagem is not None:
        sets["wa_mensagem"] = body.mensagem.strip() or _WA_MSG_DEFAULT
    await db.prospeccao_campanha.update_one({"_id": uid}, {"$set": sets}, upsert=True)
    return {"ok": True}


@router.get("/prospeccao/whatsapp/status")
async def wa_status(uid: str = Depends(get_admin_user), db=Depends(get_db)):
    from services.integracoes_util import carregar_integracoes
    camp = await db.prospeccao_campanha.find_one({"_id": uid}) or {}
    cfg = await carregar_integracoes(db, uid)
    hoje = (_agora() - _FORTALEZA_OFFSET).strftime("%Y-%m-%d")
    return {
        "zapi_ok": bool(cfg.get("zapi_instance_id") and cfg.get("zapi_token")),
        "com_telefone": await db.prospeccao.count_documents({"user_id": uid, "telefone": {"$nin": [None, ""]}}),
        "elegiveis": await db.prospeccao.count_documents({"user_id": uid, **_ELEGIVEL_WA}),
        "enviados": await db.prospeccao.count_documents({"user_id": uid, "whatsapp_enviado": True}),
        "com_erro": await db.prospeccao.count_documents({"user_id": uid, "whatsapp_erro": {"$nin": [None, ""]}}),
        "enviados_hoje": (int(camp.get("wa_enviados_hoje", 0)) if camp.get("wa_dia") == hoje else 0),
        "limite_dia": int(camp.get("wa_limite_dia", 1)),
        "ultimo_em": camp.get("wa_ultimo_em"),
    }


@router.post("/prospeccao/whatsapp/enviar")
async def wa_enviar(body: WaEnviarBody, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    from services.integracoes_util import carregar_integracoes
    from services import zapi_service
    cfg = await carregar_integracoes(db, uid)
    if not (cfg.get("zapi_instance_id") and cfg.get("zapi_token")):
        raise HTTPException(status_code=400, detail="Z-API não configurada (Configurações ▸ Integrações).")

    if body.teste_telefone:
        camp = await db.prospeccao_campanha.find_one({"_id": uid}) or {}
        tpl = body.teste_texto or camp.get("wa_mensagem") or _WA_MSG_DEFAULT
        msg = _wa_interpolar(tpl, {"nome": "Amigo(a)", "cidade": "sua cidade"})
        try:
            await zapi_service.send_text(
                instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
                security_token=cfg.get("zapi_security_token"),
                phone=body.teste_telefone.strip(), message=msg)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Falha no teste: {type(e).__name__}: {e}")
        return {"ok": True, "teste": True}

    n = await db.prospeccao.count_documents({"user_id": uid, **_ELEGIVEL_WA})
    if not n:
        raise HTTPException(status_code=422,
                            detail="Nenhum contato elegível no WhatsApp (com telefone e ainda não enviado).")
    limite = max(1, min(int(body.limite or 1), 2))
    asyncio.create_task(_rodar_whatsapp(db, uid, limite))
    return {"ok": True, "iniciada": True, "elegiveis": n, "limite": limite}


async def _scheduler_tick(db, worker: str) -> None:
    now = _agora()
    # Lease em Mongo — só o worker detentor processa (evita disparo múltiplo entre workers).
    try:
        lease = await db.sys_leases.find_one_and_update(
            {"_id": "prospeccao_scheduler",
             "$or": [{"expires": {"$lt": now.isoformat()}}, {"holder": worker}]},
            {"$set": {"holder": worker, "expires": (now + timedelta(minutes=5)).isoformat()}},
            upsert=True, return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        return   # outro worker detém a lease
    if not lease or lease.get("holder") != worker:
        return

    local = now - _FORTALEZA_OFFSET
    hoje = local.strftime("%Y-%m-%d")
    async for camp in db.prospeccao_campanha.find({"auto_ativo": True}):
        uid = camp.get("_id")
        if not uid or camp.get("enviando"):
            continue
        if local.hour < int(camp.get("auto_hora", 9)):
            continue
        if camp.get("auto_ultimo_dia") == hoje:
            continue
        # marca o dia ANTES de disparar (idempotente entre ticks)
        await db.prospeccao_campanha.update_one({"_id": uid}, {"$set": {"auto_ultimo_dia": hoje}})
        n = await db.prospeccao.count_documents({"user_id": uid, **_ELEGIVEL})
        if not n:
            continue
        limite = int(camp.get("auto_limite_dia", 40))
        intervalo = int(camp.get("auto_intervalo", 30))
        logger.info("Prospecção: disparo AUTOMÁTICO diário p/ %s (até %s e-mails)", uid, limite)
        asyncio.create_task(_rodar_campanha(db, uid, limite, intervalo))

    # WhatsApp diário (1–2/dia) — o teto do dia é reforçado dentro de _rodar_whatsapp.
    async for camp in db.prospeccao_campanha.find({"wa_auto_ativo": True}):
        uid = camp.get("_id")
        if not uid:
            continue
        if local.hour < int(camp.get("wa_hora", 10)):
            continue
        limite_dia = max(1, min(int(camp.get("wa_limite_dia", 1)), 2))
        if camp.get("wa_dia") == hoje and int(camp.get("wa_enviados_hoje", 0)) >= limite_dia:
            continue
        logger.info("Prospecção WA: disparo AUTOMÁTICO diário p/ %s (até %s msgs)", uid, limite_dia)
        asyncio.create_task(_rodar_whatsapp(db, uid, limite_dia))


async def _scheduler_loop(db):
    worker = secrets.token_hex(4)
    logger.info("Prospecção: scheduler iniciado (worker %s)", worker)
    while True:
        try:
            await asyncio.sleep(120)
            await _scheduler_tick(db, worker)
        except asyncio.CancelledError:
            break
        except Exception as e:  # noqa: BLE001
            logger.warning("Prospecção scheduler: %s", e)
            await asyncio.sleep(30)


def start_scheduler(db) -> None:
    """Chamado no startup do server.py — 1 task por worker; a lease garante 1 ativo."""
    asyncio.create_task(_scheduler_loop(db))


# ──────────────────────────────────────────────────────────────────────────────
# Descadastro (PÚBLICO — LGPD/opt-out)
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/prospeccao/descadastrar/{token}")
async def descadastrar(token: str, db=Depends(get_db)):
    if token and token not in ("teste", "exemplo"):
        await db.prospeccao.update_one(
            {"opt_out_token": token},
            {"$set": {"opt_out": True, "status": 4, "updated_at": _iso()}})
    html = (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Descadastrado</title></head>"
        "<body style='font-family:Arial,sans-serif;background:#f4f2ec;margin:0;padding:40px;text-align:center;color:#1c1c1c'>"
        "<div style='max-width:460px;margin:0 auto;background:#fff;border-radius:12px;padding:32px 24px;"
        "box-shadow:0 1px 6px rgba(0,0,0,.08)'>"
        "<div style='width:56px;height:56px;background:#C9A84C;border-radius:12px;display:inline-block;"
        "line-height:56px;font-size:30px;font-weight:bold;color:#0C3320;font-family:Georgia,serif'>A</div>"
        "<h1 style='color:#0C3320;font-size:20px;margin:16px 0 8px'>Descadastro concluído</h1>"
        "<p style='color:#555;font-size:14px;line-height:1.6'>Pronto! Você não receberá mais e-mails de "
        "prospecção da <strong>Romatec / AvalieImob</strong>. Obrigado.</p></div></body></html>")
    return Response(content=html, media_type="text/html")


@router.post("/prospeccao/descobrir")
async def descobrir(uid: str = Depends(get_admin_user)):
    """Descoberta automática de imobiliárias por API (Google Places) — extensão futura.
    Requer GOOGLE_PLACES_API_KEY + billing; hoje a coleta é por lista curada + importação."""
    raise HTTPException(
        501, "Descoberta automática por API ainda não ativada. Configure GOOGLE_PLACES_API_KEY "
             "no Railway para habilitar. Por enquanto: use 'Importar lista da região' e a importação por colar/CSV.")
