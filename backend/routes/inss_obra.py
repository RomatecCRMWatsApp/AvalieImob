# @module routes.inss_obra — INSS de obra: cadastro, simulação da aferição (SERO),
# prazos, checklist com comprovantes e PDF para o cliente.
#
# Escopo: AFERIÇÃO DIRETA (o cliente paga o INSS integral apurado no SERO). Sem folha,
# sem eSocial, sem fator de ajuste. Nada é transmitido à Receita: o usuário faz cada
# passo no e-CAC e sobe o comprovante aqui.
#
# Regras: isolamento por user_id em TODA query; simulações são IMUTÁVEIS (cada
# "Simular" acrescenta uma nova, nunca sobrescreve); o resultado oficial é o
# que o usuário informa a partir do SERO (campo `sero_oficial`), separado da simulação.
import asyncio
import hashlib
import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from services import r2_storage
from services.inss_obra import ErroSimulacao, simular
from services.inss_obra import params as P
from services.inss_obra import prazos as PRZ

logger = logging.getLogger("romatec")
router = APIRouter(prefix="/inss-obra", tags=["INSS de Obra"])

COL = "inss_obras"
_MAX_UPLOAD = 20 * 1024 * 1024
_TZ_BR = timezone(timedelta(hours=-3))

_ECAC = "https://cav.receita.fazenda.gov.br/autenticacao/login"
CHECKLIST = [
    {"chave": "alvara", "titulo": "Alvará de construção", "obrigatorio": False, "link": None,
     "dica": "Alvará da prefeitura. O CNO pode ser preenchido a partir dele."},
    {"chave": "art_rrt", "titulo": "ART/RRT/TRT da obra", "obrigatorio": False, "link": None,
     "dica": "Responsabilidade técnica do projeto/execução."},
    {"chave": "cno", "titulo": "Comprovante de inscrição no CNO", "obrigatorio": True, "link": _ECAC,
     "dica": "e-CAC → Cadastros → CNO. Prazo: 30 dias do início da obra."},
    {"chave": "habite_se", "titulo": "Habite-se", "obrigatorio": False, "link": None,
     "dica": "Se vinculado à aferição, a data de fim da obra é a do habite-se (Manual item 7.2)."},
    {"chave": "sero_memoria", "titulo": "Memória de cálculo do SERO", "obrigatorio": True, "link": _ECAC,
     "dica": "e-CAC → SERO → Aferir obra. Guarde a memória de cálculo em PDF."},
    {"chave": "dctfweb_recibo", "titulo": "Recibo da DCTFWeb Aferição de Obras", "obrigatorio": True,
     "link": _ECAC, "dica": "Concluir a aferição transmite a DCTFWeb Aferição."},
    {"chave": "darf_pago", "titulo": "DARF e comprovante de pagamento", "obrigatorio": True,
     "link": _ECAC, "dica": "Gerado no SERO após a DCTFWeb. Vence no dia 20 do mês seguinte."},
    {"chave": "certidao", "titulo": "Certidão da obra (CND ou CPEND)", "obrigatorio": True,
     "link": _ECAC, "dica": "Emitida após o pagamento. Leva-se ao cartório para averbar."},
]
_CHAVES = {c["chave"] for c in CHECKLIST}

_CAMPOS = ["cliente_id", "cliente_nome", "cpf_cnpj", "telefone", "responsavel", "endereco",
           "municipio", "uf", "cno", "alvara", "art_rrt", "data_inicio", "data_fim",
           "data_afericao", "areas", "vau", "vau_competencia", "vau_fonte", "usinado",
           "observacoes"]


class ObraBody(BaseModel):
    model_config = {"extra": "ignore"}
    cliente_id: str | None = None
    cliente_nome: str | None = None
    cpf_cnpj: str | None = None
    telefone: str | None = None
    responsavel: str | None = None
    endereco: str | None = None
    municipio: str | None = None
    uf: str | None = None
    cno: str | None = None
    alvara: str | None = None
    art_rrt: str | None = None
    data_inicio: str | None = None
    data_fim: str | None = None
    data_afericao: str | None = None
    areas: list[dict] | None = None
    vau: dict | None = None
    vau_competencia: str | None = None
    vau_fonte: str | None = None
    usinado: bool | None = None
    observacoes: str | None = None


class SeroOficialBody(BaseModel):
    total: str | None = None
    data: str | None = None
    observacao: str | None = None


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _hoje_br() -> date:
    return datetime.now(_TZ_BR).date()


async def _obter(db, oid: str, uid: str) -> dict:
    doc = await db[COL].find_one({"id": oid, "user_id": uid})
    if not doc:
        raise HTTPException(404, "Obra não encontrada")
    return doc


async def _proximo_numero(db) -> str:
    ano = _hoje_br().year
    r = await db.counters.find_one_and_update(
        {"_id": f"inss_obra_{ano}"}, {"$inc": {"seq": 1}}, upsert=True, return_document=True)
    return f"INSS-{ano}-{int((r or {}).get('seq') or 1):04d}"


def _view(doc: dict) -> dict:
    out = serialize_doc(dict(doc))
    sims = out.get("simulacoes") or []
    out["ultima_simulacao"] = sims[-1] if sims else None
    out["simulacoes_qtd"] = len(sims)
    out["simulacoes"] = [{"id": s.get("id"), "criada_em": s.get("criada_em"),
                          "total": (s.get("resultado") or {}).get("total")} for s in sims]
    out["prazos"] = PRZ.montar(doc, _hoje_br())
    ck = doc.get("checklist") or {}
    out["checklist_itens"] = [{**c, **{k: v for k, v in (ck.get(c["chave"]) or {}).items()
                                       if k not in ("key",)}} for c in CHECKLIST]
    feitos = sum(1 for c in CHECKLIST if (ck.get(c["chave"]) or {}).get("status") == "ok")
    out["checklist_progresso"] = {"feitos": feitos, "total": len(CHECKLIST)}
    return out


# ── Catálogo ─────────────────────────────────────────────────────────────────
@router.get("/opcoes")
async def opcoes(uid: str = Depends(get_active_subscriber)):
    return {**P.opcoes(), "checklist": CHECKLIST}


# ── CRUD ─────────────────────────────────────────────────────────────────────
@router.get("/obras")
async def listar(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    docs = await db[COL].find({"user_id": uid}).sort("criado_em", -1).to_list(500)
    out = []
    for d in docs:
        v = _view(d)
        v.pop("simulacoes", None)
        out.append(v)
    return out


@router.post("/obras", status_code=201)
async def criar(body: ObraBody, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    agora = _agora().isoformat()
    doc = {"id": str(uuid.uuid4()), "user_id": uid, "numero": await _proximo_numero(db),
           "status": "rascunho", "simulacoes": [], "checklist": {}, "sero_oficial": None,
           "criado_em": agora, "atualizado_em": agora,
           "responsavel": "PF", "areas": [], "vau": {}, "usinado": False}
    doc.update({k: v for k, v in body.model_dump().items() if v is not None})
    await db[COL].insert_one(doc)
    return _view(doc)


@router.get("/obras/{oid}")
async def obter(oid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return _view(await _obter(db, oid, uid))


@router.put("/obras/{oid}")
async def atualizar(oid: str, body: ObraBody, uid: str = Depends(get_active_subscriber),
                    db=Depends(get_db)):
    await _obter(db, oid, uid)
    campos = {k: v for k, v in body.model_dump(exclude_unset=True).items() if k in _CAMPOS}
    campos["atualizado_em"] = _agora().isoformat()
    await db[COL].update_one({"id": oid, "user_id": uid}, {"$set": campos})
    return _view(await _obter(db, oid, uid))


@router.delete("/obras/{oid}")
async def excluir(oid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await _obter(db, oid, uid)
    await db[COL].delete_one({"id": oid, "user_id": uid})
    return {"ok": True}


# ── Simulação ────────────────────────────────────────────────────────────────
def _entrada(doc: dict) -> dict:
    return {"responsavel": doc.get("responsavel"), "uf": doc.get("uf"), "vau": doc.get("vau"),
            "data_inicio": doc.get("data_inicio"), "data_fim": doc.get("data_fim"),
            "data_afericao": doc.get("data_afericao") or _hoje_br().isoformat(),
            "areas": doc.get("areas"), "usinado": doc.get("usinado")}


@router.post("/obras/{oid}/simular")
async def simular_obra(oid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _obter(db, oid, uid)
    entrada = _entrada(doc)
    try:
        res = simular(entrada)
    except ErroSimulacao as e:
        raise HTTPException(422, str(e))
    hash_in = hashlib.sha256(repr(sorted(entrada.items(), key=lambda kv: kv[0])).encode()).hexdigest()
    sim = {"id": str(uuid.uuid4()), "criada_em": _agora().isoformat(), "hash_entrada": hash_in,
           "vau_competencia": doc.get("vau_competencia"), "vau_fonte": doc.get("vau_fonte"),
           "resultado": res}
    set_ = {"atualizado_em": sim["criada_em"]}
    if not doc.get("data_afericao"):
        set_["data_afericao"] = entrada["data_afericao"]
    if doc.get("status") == "rascunho":
        set_["status"] = "simulada"
    await db[COL].update_one({"id": oid, "user_id": uid},
                             {"$push": {"simulacoes": sim}, "$set": set_})
    return sim


@router.post("/obras/{oid}/sero-oficial")
async def registrar_sero(oid: str, body: SeroOficialBody, uid: str = Depends(get_active_subscriber),
                         db=Depends(get_db)):
    """Valor oficial copiado da memória do SERO — separado da simulação, para comparar."""
    await _obter(db, oid, uid)
    valor = None
    if body.total:
        s = body.total.strip().replace("R$", "").strip()
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        try:
            valor = f"{float(s):.2f}"
        except ValueError:
            raise HTTPException(422, "Valor oficial inválido")
    reg = {"total": valor, "data": body.data, "observacao": body.observacao,
           "registrado_em": _agora().isoformat()}
    await db[COL].update_one({"id": oid, "user_id": uid},
                             {"$set": {"sero_oficial": reg if valor else None,
                                       "atualizado_em": reg["registrado_em"]}})
    return _view(await _obter(db, oid, uid))


# ── Checklist com comprovantes ───────────────────────────────────────────────
@router.post("/obras/{oid}/checklist/{chave}")
async def enviar_comprovante(oid: str, chave: str, file: UploadFile = File(...),
                             uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    if chave not in _CHAVES:
        raise HTTPException(422, "Item do checklist inválido")
    await _obter(db, oid, uid)
    data = await file.read()
    if not data:
        raise HTTPException(422, "Arquivo vazio")
    if len(data) > _MAX_UPLOAD:
        raise HTTPException(413, "Arquivo muito grande (máx. 20 MB)")
    nome = file.filename or "arquivo"
    ext = (nome.rsplit(".", 1)[-1].lower() if "." in nome else "pdf")[:5]
    mime = file.content_type or "application/octet-stream"
    key = f"inss-obra/{uid}/{oid}/{chave}/{uuid.uuid4()}.{ext}"
    await asyncio.to_thread(r2_storage.upload_bytes, data, key, mime)
    item = {"status": "ok", "key": key, "arquivo": nome, "mime": mime,
            "sha256": hashlib.sha256(data).hexdigest(), "enviado_em": _agora().isoformat()}
    set_ = {f"checklist.{chave}": item, "atualizado_em": item["enviado_em"]}
    if chave == "certidao":
        set_["status"] = "regularizada"
    await db[COL].update_one({"id": oid, "user_id": uid}, {"$set": set_})
    return _view(await _obter(db, oid, uid))


@router.delete("/obras/{oid}/checklist/{chave}")
async def remover_comprovante(oid: str, chave: str, uid: str = Depends(get_active_subscriber),
                              db=Depends(get_db)):
    if chave not in _CHAVES:
        raise HTTPException(422, "Item do checklist inválido")
    await _obter(db, oid, uid)
    await db[COL].update_one({"id": oid, "user_id": uid},
                             {"$unset": {f"checklist.{chave}": ""},
                              "$set": {"atualizado_em": _agora().isoformat()}})
    return _view(await _obter(db, oid, uid))


@router.get("/obras/{oid}/checklist/{chave}/arquivo")
async def baixar_comprovante(oid: str, chave: str, uid: str = Depends(get_active_subscriber),
                             db=Depends(get_db)):
    doc = await _obter(db, oid, uid)
    item = (doc.get("checklist") or {}).get(chave)
    if not item or not item.get("key"):
        raise HTTPException(404, "Comprovante não enviado")
    data = await asyncio.to_thread(r2_storage.download_bytes, item["key"])
    return Response(data, media_type=item.get("mime") or "application/octet-stream",
                    headers={"Content-Disposition": f'inline; filename="{item.get("arquivo") or chave}"',
                             "Cache-Control": "no-store"})


# ── PDF da simulação ─────────────────────────────────────────────────────────
async def _logo(db, uid: str):
    try:
        from services.branding_context import BrandContext
        brand = await BrandContext.for_user(db, uid)
        return await asyncio.to_thread(brand.custom_logo_bytes)
    except Exception:  # noqa: BLE001
        return None


async def _autor(db, uid: str) -> dict:
    try:
        from utils.avaliador import resolver_dados_avaliador
        perfil = await db.perfil_avaliador.find_one({"user_id": uid}) or {}
        user = await db.users.find_one({"id": uid}) or {}
        d = resolver_dados_avaliador(perfil=perfil, user=user)
        return {"nome": d.get("nome"), "registros": " · ".join(d.get("registros_linhas") or [])}
    except Exception:  # noqa: BLE001
        return {}


@router.get("/obras/{oid}/pdf")
async def pdf_simulacao(oid: str, sim_id: str | None = None,
                        uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _obter(db, oid, uid)
    sims = doc.get("simulacoes") or []
    if not sims:
        raise HTTPException(422, "Faça uma simulação antes de gerar o PDF")
    sim = next((s for s in sims if s.get("id") == sim_id), None) if sim_id else sims[-1]
    if not sim:
        raise HTTPException(404, "Simulação não encontrada")
    from services.inss_obra.pdf import gerar_pdf
    logo, autor = await _logo(db, uid), await _autor(db, uid)
    data = await asyncio.to_thread(gerar_pdf, doc, sim["resultado"], logo, autor)
    nome = f"Simulacao_INSS_{doc.get('numero') or oid}.pdf"
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{nome}"',
                             "Cache-Control": "no-store"})
