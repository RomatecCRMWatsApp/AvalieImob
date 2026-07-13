# @module routes.instagram — Instagram Studio (admin): gera conteúdo com IA + CRUD do calendário.
import base64
import logging
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_db
from dependencies import get_admin_user, serialize_doc
from models.instagram_post import (
    InstagramPost, InstagramPostCreate, InstagramPostUpdate, _iso,
)
from services import instagram_ia_service

router = APIRouter(tags=["instagram"])
logger = logging.getLogger("romatec")


class GerarBody(BaseModel):
    pilar: str
    assunto: str = ""
    formato: str = "post_unico"


class StatusBody(BaseModel):
    status: str


@router.post("/instagram/gerar")
async def gerar(body: GerarBody, uid: str = Depends(get_admin_user)):
    return await instagram_ia_service.gerar_conteudo(body.pilar, body.assunto, body.formato)


@router.post("/instagram/posts")
async def criar_post(body: InstagramPostCreate, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    doc = InstagramPost(user_id=uid, **body.dict()).dict()
    await db.instagram_posts.insert_one(doc)
    return serialize_doc(doc)


@router.get("/instagram/posts")
async def listar_posts(mes: Optional[str] = None, status: Optional[str] = None,
                       pilar: Optional[str] = None,
                       uid: str = Depends(get_admin_user), db=Depends(get_db)):
    q = {"user_id": uid}
    if status:
        q["status"] = status
    if pilar:
        q["pilar"] = pilar
    if mes:
        q["data_agendada"] = {"$regex": f"^{mes}"}
    docs = await db.instagram_posts.find(q).sort("criado_em", -1).to_list(500)
    return [serialize_doc(d) for d in docs]


@router.get("/instagram/posts/{pid}")
async def obter_post(pid: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    doc = await db.instagram_posts.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(404, "Post não encontrado")
    return serialize_doc(doc)


@router.put("/instagram/posts/{pid}")
async def atualizar_post(pid: str, body: InstagramPostUpdate,
                         uid: str = Depends(get_admin_user), db=Depends(get_db)):
    upd = dict(body.dict(exclude_unset=True))
    upd["atualizado_em"] = _iso()
    r = await db.instagram_posts.update_one({"id": pid, "user_id": uid}, {"$set": upd})
    if r.matched_count == 0:
        raise HTTPException(404, "Post não encontrado")
    doc = await db.instagram_posts.find_one({"id": pid, "user_id": uid})
    return serialize_doc(doc)


@router.post("/instagram/posts/{pid}/status")
async def mudar_status(pid: str, body: StatusBody,
                       uid: str = Depends(get_admin_user), db=Depends(get_db)):
    if body.status not in ("ideia", "aprovado", "publicado"):
        raise HTTPException(400, "Status inválido")
    upd = {"status": body.status, "atualizado_em": _iso()}
    if body.status == "publicado":
        upd["data_publicado"] = _iso()
    r = await db.instagram_posts.update_one({"id": pid, "user_id": uid}, {"$set": upd})
    if r.matched_count == 0:
        raise HTTPException(404, "Post não encontrado")
    doc = await db.instagram_posts.find_one({"id": pid, "user_id": uid})
    return serialize_doc(doc)


@router.delete("/instagram/posts/{pid}")
async def excluir_post(pid: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    r = await db.instagram_posts.delete_one({"id": pid, "user_id": uid})
    if r.deleted_count == 0:
        raise HTTPException(404, "Post não encontrado")
    return {"ok": True}


class EnviarWhatsAppBody(BaseModel):
    phone: Optional[str] = None          # destino; se vazio usa o telefone do usuário
    imagens: List[str] = []              # PNGs da arte (dataURL ou base64 puro)
    legenda: Optional[str] = None        # se None, monta de legenda + hashtags do post


def _b64_para_bytes(s: str) -> bytes:
    s = s or ""
    m = re.match(r"^data:[^;]+;base64,(.*)$", s, re.S)
    if m:
        s = m.group(1)
    return base64.b64decode(s)


@router.post("/instagram/posts/{pid}/enviar-whatsapp")
async def enviar_whatsapp(pid: str, body: EnviarWhatsAppBody,
                          uid: str = Depends(get_admin_user), db=Depends(get_db)):
    """Envia a arte (PNG) + legenda do post para o WhatsApp do dono (Z-API ou Meta).

    Usado na automação pós-aprovação: aprovou → cai pronto no seu WhatsApp para postar.
    """
    from services import zapi_service
    from services import meta_whatsapp_service as meta
    from services.integracoes_util import carregar_integracoes

    doc = await db.instagram_posts.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(404, "Post não encontrado")

    cfg = await carregar_integracoes(db, uid)
    if not cfg:
        raise HTTPException(400, "Nenhum provedor WhatsApp configurado em Configurações → Integrações.")

    user = await db.users.find_one({"id": uid}) or {}
    phone = (body.phone or user.get("whatsapp") or user.get("telefone")
             or user.get("phone") or "").strip()
    if not phone:
        raise HTTPException(400, "Informe o número de WhatsApp de destino.")

    legenda = body.legenda
    if legenda is None:
        tags = " ".join(doc.get("hashtags") or [])
        legenda = f"{doc.get('legenda', '')}\n\n{tags}".strip()

    imgs: List[bytes] = []
    for s in (body.imagens or []):
        try:
            b = _b64_para_bytes(s)
            if b:
                imgs.append(b)
        except Exception:  # noqa: BLE001
            logger.warning("Imagem base64 inválida ignorada no envio do post %s", pid)

    provider = (cfg.get("whatsapp_provider") or "zapi").lower()
    enviadas = 0
    try:
        if provider == "meta":
            if not cfg.get("meta_phone_number_id") or not cfg.get("meta_access_token"):
                raise HTTPException(400, "Meta WhatsApp não configurada")
            for i, b in enumerate(imgs):
                media_id = await meta.upload_media(
                    phone_number_id=cfg["meta_phone_number_id"],
                    access_token=cfg["meta_access_token"],
                    file_bytes=b, filename=f"avalieimob-{pid}-{i + 1}.png",
                    mime_type="image/png",
                )
                await meta.send_document(
                    phone_number_id=cfg["meta_phone_number_id"],
                    access_token=cfg["meta_access_token"],
                    phone=phone, media_id=media_id,
                    filename=f"avalieimob-{pid}-{i + 1}.png",
                    caption=(legenda if i == 0 else ""),
                )
                enviadas += 1
        else:
            if not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
                raise HTTPException(400, "Z-API não configurada")
            iz = dict(instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
                      security_token=cfg.get("zapi_security_token"))
            for i, b in enumerate(imgs):
                await zapi_service.send_document(
                    **iz, phone=phone, file_bytes=b,
                    filename=f"avalieimob-{pid}-{i + 1}.png", content_type="image/png",
                    caption=(legenda if i == 0 else ""),
                )
                enviadas += 1
            # Manda a legenda como texto separado — fica fácil de copiar e colar no Instagram.
            if legenda:
                await zapi_service.send_text(**iz, phone=phone, message=legenda)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Falha ao enviar pelo WhatsApp: {e}")

    await db.instagram_posts.update_one(
        {"id": pid, "user_id": uid},
        {"$set": {"wpp_enviado_em": _iso(), "atualizado_em": _iso()}},
    )
    return {"ok": True, "enviadas": enviadas}
