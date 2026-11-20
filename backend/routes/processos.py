# @module routes.processos — processos de trabalho e agenda de vistorias.
# Sem `from __future__ import annotations` (padrão do repositório para rotas).
#
# O processo referencia documentos que já existem (PTAM, vistoria, contrato…) e nunca
# os altera. Toda consulta é escopada por user_id; referência a documento de outra
# conta é recusada com 404.
import re
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from services import processos as P

router = APIRouter(tags=["processos"], prefix="/processos")


# ── corpos ──────────────────────────────────────────────────────────────────
class ProcessoNovo(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)
    tipo_servico: str = "avaliacao"
    cliente_nome: Optional[str] = ""
    cliente_id: Optional[str] = None
    responsavel: Optional[str] = ""
    prazo: Optional[str] = None  # AAAA-MM-DD
    observacoes: Optional[str] = ""


class ProcessoEdicao(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[str] = None
    cliente_nome: Optional[str] = None
    responsavel: Optional[str] = None
    prazo: Optional[str] = None
    observacoes: Optional[str] = None


class EtapaNova(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)


class EtapaEdicao(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=200)
    concluida: Optional[bool] = None


class ReferenciaNova(BaseModel):
    tipo: str
    id: str


class CompromissoNovo(BaseModel):
    tipo: str = "vistoria"
    inicio: str
    duracao_min: int = 60
    local: Optional[str] = ""
    contato: Optional[str] = ""
    observacao: Optional[str] = ""


class AcaoAgenda(BaseModel):
    acao: str  # confirmar | realizado | cancelar | reagendar
    novo_inicio: Optional[str] = None
    motivo: Optional[str] = ""


# ── utilidades ──────────────────────────────────────────────────────────────
async def _carregar(db, uid: str, pid: str) -> dict:
    doc = await db.processos.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return doc


async def _salvar(db, uid: str, pid: str, mudancas: dict, evento: Optional[dict] = None) -> dict:
    upd = {"$set": {**mudancas, "updated_at": P.agora()}}
    if evento:
        upd["$push"] = {"historico": evento}
    doc = await db.processos.find_one_and_update(
        {"id": pid, "user_id": uid}, upd, return_document=ReturnDocument.AFTER)
    if not doc:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return _view(doc)


def _view(doc: dict) -> dict:
    d = serialize_doc(doc)
    d["progresso"] = P.progresso(doc)
    d["status_rotulo"] = P.STATUS_ROTULO.get(doc.get("status"), doc.get("status"))
    return d


def _prazo(v: Optional[str]) -> Optional[str]:
    if v in (None, ""):
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
        raise HTTPException(status_code=422, detail="Prazo deve ser AAAA-MM-DD.")
    return str(v)


async def _numero(db, uid: str) -> str:
    ano = datetime.utcnow().year
    r = await db.counters.find_one_and_update(
        {"_id": f"processo_{uid}_{ano}"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=ReturnDocument.AFTER)
    return f"PROC-{ano}-{int(r['seq']):04d}"


async def _todos_compromissos(db, uid: str) -> list:
    out = []
    async for p in db.processos.find({"user_id": uid}, {"_id": 0, "id": 1, "agenda": 1}):
        for c in p.get("agenda") or []:
            out.append({**c, "_processo_id": p["id"]})
    return out


def _conflitos_view(lista: list) -> list:
    return [{"id": c.get("id"), "processo_id": c.get("_processo_id"), "tipo": c.get("tipo"),
             "inicio": c.get("inicio"), "duracao_min": c.get("duracao_min"),
             "local": c.get("local")} for c in lista]


# ── catálogo ────────────────────────────────────────────────────────────────
@router.get("/opcoes")
async def opcoes(uid: str = Depends(get_active_subscriber)):
    return {
        "status": [{"id": s, "rotulo": P.STATUS_ROTULO[s]} for s in P.STATUS],
        "tipos_servico": [{"id": k, "rotulo": v, "etapas": P.ETAPAS_PADRAO[k]}
                          for k, v in P.TIPOS_SERVICO.items()],
        "referencias": [{"id": k, "rotulo": v} for k, v in P.REF_ROTULO_TIPO.items()],
        "agenda_tipos": [{"id": k, "rotulo": v} for k, v in P.AGENDA_TIPOS.items()],
    }


@router.get("/documentos-disponiveis")
async def documentos_disponiveis(tipo: str, q: str = "", uid: str = Depends(get_active_subscriber),
                                 db=Depends(get_db)):
    """Documentos da PRÓPRIA conta que podem ser vinculados (para o seletor)."""
    if tipo not in P.REFERENCIAS:
        raise HTTPException(status_code=422, detail="Tipo de documento inválido.")
    colecao = P.REFERENCIAS[tipo][0]
    docs = await db[colecao].find({"user_id": uid}).sort("updated_at", -1).to_list(200)
    termo = (q or "").strip().lower()
    out = []
    for d in docs:
        rot = P.rotulo_documento(tipo, d)
        if termo and termo not in rot.lower():
            continue
        out.append({"tipo": tipo, "id": d.get("id"), "rotulo": rot})
        if len(out) >= 30:
            break
    return out


@router.get("/agenda")
async def agenda(de: Optional[str] = None, ate: Optional[str] = None,
                 uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Compromissos de todos os processos da conta no período (padrão: hoje a +30 dias)."""
    try:
        ini = P.parse_inicio(de) if de else datetime.utcnow() - timedelta(days=1)
        fim = P.parse_inicio(ate) if ate else ini + timedelta(days=31)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    out = []
    async for p in db.processos.find({"user_id": uid}):
        for c in p.get("agenda") or []:
            ci = c.get("inicio")
            if isinstance(ci, datetime) and ini <= ci < fim:
                out.append({**c, "processo_id": p["id"], "processo_numero": p.get("numero"),
                            "processo_titulo": p.get("titulo"),
                            "cliente_nome": p.get("cliente_nome")})
    out.sort(key=lambda c: c["inicio"])
    return out


# ── processos ───────────────────────────────────────────────────────────────
@router.get("")
async def listar(status: Optional[str] = None, q: str = "",
                 uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    filtro = {"user_id": uid}
    if status:
        filtro["status"] = status
    docs = await db.processos.find(filtro, {"_id": 0, "historico": 0}).sort(
        "updated_at", -1).to_list(500)
    termo = (q or "").strip().lower()
    if termo:
        docs = [d for d in docs if termo in " ".join(
            str(d.get(k) or "") for k in ("numero", "titulo", "cliente_nome", "responsavel")).lower()]
    return [_view(d) for d in docs]


@router.post("", status_code=201)
async def criar(body: ProcessoNovo, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    if body.tipo_servico not in P.TIPOS_SERVICO:
        raise HTTPException(status_code=422, detail="Tipo de serviço inválido.")
    agora = P.agora()
    doc = {
        "id": P._id(), "user_id": uid, "numero": await _numero(db, uid),
        "titulo": body.titulo.strip(), "tipo_servico": body.tipo_servico,
        "cliente_nome": (body.cliente_nome or "").strip(), "cliente_id": body.cliente_id,
        "responsavel": (body.responsavel or "").strip(), "prazo": _prazo(body.prazo),
        "observacoes": (body.observacoes or "").strip(), "status": "aberto",
        "etapas": P.etapas_iniciais(body.tipo_servico), "referencias": [], "agenda": [],
        "historico": [P.evento("Processo aberto")], "created_at": agora, "updated_at": agora,
    }
    await db.processos.insert_one(doc)
    return _view(doc)


@router.get("/{pid}")
async def obter(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, uid, pid)
    view = _view(doc)
    # rótulo e link atuais de cada documento vinculado; some quem foi apagado na origem
    refs = []
    for r in doc.get("referencias") or []:
        tipo = r.get("tipo")
        if tipo not in P.REFERENCIAS:
            continue
        origem = await db[P.REFERENCIAS[tipo][0]].find_one({"id": r.get("id"), "user_id": uid})
        refs.append({**r, "rotulo": P.rotulo_documento(tipo, origem) if origem else r.get("rotulo"),
                     "tipo_rotulo": P.REF_ROTULO_TIPO[tipo],
                     "link": P.link_documento(tipo, r.get("id")), "existe": bool(origem)})
    view["referencias"] = refs
    return view


@router.put("/{pid}")
async def editar(pid: str, body: ProcessoEdicao, uid: str = Depends(get_active_subscriber),
                 db=Depends(get_db)):
    doc = await _carregar(db, uid, pid)
    mud = {}
    for campo in ("titulo", "cliente_nome", "responsavel", "observacoes"):
        v = getattr(body, campo)
        if v is not None:
            mud[campo] = v.strip()
    if body.prazo is not None:
        mud["prazo"] = _prazo(body.prazo)
    evento = None
    if body.status is not None and body.status != doc.get("status"):
        try:
            mud["status"] = P.validar_status(body.status)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        evento = P.evento(f"Situação: {P.STATUS_ROTULO[body.status]}")
    return await _salvar(db, uid, pid, mud, evento)


@router.delete("/{pid}")
async def excluir(pid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    r = await db.processos.delete_one({"id": pid, "user_id": uid})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return {"ok": True}  # os documentos vinculados continuam onde estão


# ── etapas ──────────────────────────────────────────────────────────────────
@router.post("/{pid}/etapas", status_code=201)
async def nova_etapa(pid: str, body: EtapaNova, uid: str = Depends(get_active_subscriber),
                     db=Depends(get_db)):
    doc = await _carregar(db, uid, pid)
    etapas = list(doc.get("etapas") or []) + [
        {"id": P._id(), "titulo": body.titulo.strip(), "concluida": False, "concluida_em": None}]
    return await _salvar(db, uid, pid, {"etapas": etapas})


@router.patch("/{pid}/etapas/{eid}")
async def editar_etapa(pid: str, eid: str, body: EtapaEdicao,
                       uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, uid, pid)
    etapas, evento = [], None
    achou = False
    for e in doc.get("etapas") or []:
        if e.get("id") == eid:
            achou = True
            e = dict(e)
            if body.titulo is not None:
                e["titulo"] = body.titulo.strip()
            if body.concluida is not None and body.concluida != e.get("concluida"):
                e["concluida"] = body.concluida
                e["concluida_em"] = P.agora() if body.concluida else None
                evento = P.evento(("Etapa concluída: " if body.concluida else "Etapa reaberta: ")
                                  + e["titulo"])
        etapas.append(e)
    if not achou:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")
    return await _salvar(db, uid, pid, {"etapas": etapas}, evento)


@router.delete("/{pid}/etapas/{eid}")
async def excluir_etapa(pid: str, eid: str, uid: str = Depends(get_active_subscriber),
                        db=Depends(get_db)):
    doc = await _carregar(db, uid, pid)
    etapas = [e for e in doc.get("etapas") or [] if e.get("id") != eid]
    if len(etapas) == len(doc.get("etapas") or []):
        raise HTTPException(status_code=404, detail="Etapa não encontrada")
    return await _salvar(db, uid, pid, {"etapas": etapas})


# ── documentos vinculados ───────────────────────────────────────────────────
@router.post("/{pid}/referencias", status_code=201)
async def vincular(pid: str, body: ReferenciaNova, uid: str = Depends(get_active_subscriber),
                   db=Depends(get_db)):
    doc = await _carregar(db, uid, pid)
    if body.tipo not in P.REFERENCIAS:
        raise HTTPException(status_code=422, detail="Tipo de documento inválido.")
    origem = await db[P.REFERENCIAS[body.tipo][0]].find_one({"id": body.id, "user_id": uid})
    if not origem:  # inexistente OU de outra conta: mesma resposta
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    refs = list(doc.get("referencias") or [])
    if any(r.get("tipo") == body.tipo and r.get("id") == body.id for r in refs):
        return _view(doc)
    rotulo = P.rotulo_documento(body.tipo, origem)
    refs.append({"tipo": body.tipo, "id": body.id, "rotulo": rotulo, "vinculado_em": P.agora()})
    return await _salvar(db, uid, pid, {"referencias": refs},
                         P.evento(f"{P.REF_ROTULO_TIPO[body.tipo]} vinculado: {rotulo}"))


@router.delete("/{pid}/referencias/{tipo}/{rid}")
async def desvincular(pid: str, tipo: str, rid: str, uid: str = Depends(get_active_subscriber),
                      db=Depends(get_db)):
    doc = await _carregar(db, uid, pid)
    refs = [r for r in doc.get("referencias") or [] if not (r.get("tipo") == tipo and r.get("id") == rid)]
    if len(refs) == len(doc.get("referencias") or []):
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")
    return await _salvar(db, uid, pid, {"referencias": refs},
                         P.evento(f"{P.REF_ROTULO_TIPO.get(tipo, tipo)} desvinculado"))


# ── agenda ──────────────────────────────────────────────────────────────────
@router.post("/{pid}/agenda", status_code=201)
async def agendar(pid: str, body: CompromissoNovo, uid: str = Depends(get_active_subscriber),
                  db=Depends(get_db)):
    doc = await _carregar(db, uid, pid)
    try:
        c = P.novo_compromisso(body.tipo, body.inicio, body.duracao_min, body.local,
                               body.contato, body.observacao)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    choques = P.conflitos(c, await _todos_compromissos(db, uid))
    agenda = list(doc.get("agenda") or []) + [c]
    view = await _salvar(db, uid, pid, {"agenda": agenda},
                         P.evento(f"{P.AGENDA_TIPOS[c['tipo']]} agendada", para=c["inicio"]))
    return {"processo": view, "compromisso": c, "conflitos": _conflitos_view(choques)}


@router.post("/{pid}/agenda/{aid}/acao")
async def acao_agenda(pid: str, aid: str, body: AcaoAgenda,
                      uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, uid, pid)
    agenda, alvo = [], None
    for c in doc.get("agenda") or []:
        if c.get("id") == aid:
            try:
                c = P.aplicar_acao_agenda(c, body.acao, body.novo_inicio, body.motivo or "")
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))
            alvo = c
        agenda.append(c)
    if alvo is None:
        raise HTTPException(status_code=404, detail="Compromisso não encontrado")
    choques = []
    if body.acao == "reagendar":
        choques = P.conflitos(alvo, await _todos_compromissos(db, uid), ignorar_id=aid)
    rotulo = {"confirmar": "confirmada", "realizado": "realizada", "cancelar": "cancelada",
              "reagendar": "reagendada"}.get(body.acao, body.acao)
    view = await _salvar(db, uid, pid, {"agenda": agenda},
                         P.evento(f"{P.AGENDA_TIPOS.get(alvo['tipo'], 'Compromisso')} {rotulo}",
                                  para=alvo["inicio"] if body.acao == "reagendar" else None))
    return {"processo": view, "compromisso": alvo, "conflitos": _conflitos_view(choques)}
