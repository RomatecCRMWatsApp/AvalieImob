# @module routes.zayra — Feature 04: importação de fotos da Galeria ZAYRA para o PTAM
"""
Importa fotos de campo já capturadas no ZAYRA (câmera + GPS + sync) direto para
um PTAM do AvalieImob, sem re-tirar nem reupar manualmente.

Base efetiva: /api/zayra  (montado sob o APIRouter global prefix="/api").

Pipeline (alinhado ao AvalieImob real):
  ZAYRA export → baixa bytes → grava em db.images (base64, igual a um upload) →
  referencia por image_id em ptam_documents.fotos_imovel, com GPS e data já
  preenchidos (meta_gps/meta_data_hora). Assim a foto RENDERIZA no PDF com GPS,
  idêntica às fotos tiradas pelo próprio AvalieImob.
"""
import base64
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from dependencies import get_active_subscriber, get_authenticated_user
from services.zayra_galeria import baixar_foto_bytes, buscar_fotos_zayra

router = APIRouter(prefix="/zayra", tags=["zayra"])
logger = logging.getLogger("romatec")


def _fmt_gps(lat, lon) -> str:
    try:
        if lat in (None, "") or lon in (None, ""):
            return ""
        return f"{float(lat):.6f}, {float(lon):.6f}"
    except (TypeError, ValueError):
        return ""


@router.get("/galeria")
async def listar_galeria(
    desde: str = None,
    limit: int = 100,
    uid: str = Depends(get_authenticated_user),
    db=Depends(get_db),
):
    """Fotos do avaliador disponíveis no ZAYRA para importação (grid de seleção).

    O ZAYRA casa a foto pelo NOME do colaborador (não há e-mail no schema de fotos),
    então enviamos o nome do avaliador (perfil_avaliador.nome > users.name).
    """
    perfil = await db.perfil_avaliador.find_one({"user_id": uid})
    user = await db.users.find_one({"id": uid})
    identificador = (
        (perfil or {}).get("nome")
        or (perfil or {}).get("nome_completo")
        or (user or {}).get("name")
        or ""
    ).strip()
    fotos = await buscar_fotos_zayra(identificador, desde=desde, limit=limit)
    return {"fotos": fotos, "total": len(fotos), "filtro_colaborador": identificador}


@router.post("/importar/{ptam_id}")
async def importar_para_ptam(
    ptam_id: str,
    payload: dict,  # { "fotos": [ {id, numero, url, latitude, longitude, endereco, data_hora, legenda} ] }
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    """
    Vincula as fotos selecionadas do ZAYRA a um PTAM. Baixa cada foto, grava em
    db.images e adiciona a referência em fotos_imovel (origem='zayra').
    """
    ptam = await db.ptam_documents.find_one({"id": ptam_id, "user_id": uid})
    if not ptam:
        raise HTTPException(404, "PTAM não encontrado")

    selecionadas = payload.get("fotos") or []
    if not selecionadas:
        raise HTTPException(422, "Nenhuma foto selecionada.")

    novas = []
    falhas = 0
    for f in selecionadas:
        url = f.get("url")
        if not url:
            falhas += 1
            continue
        try:
            content, ctype = await baixar_foto_bytes(url)
        except HTTPException:
            falhas += 1
            logger.warning("Falha ao baixar foto ZAYRA (ptam=%s, foto=%s)", ptam_id, f.get("id"))
            continue

        image_id = str(uuid.uuid4())
        gps = _fmt_gps(f.get("latitude"), f.get("longitude"))
        data_hora = f.get("data_hora") or ""
        legenda = f.get("legenda") or f.get("endereco") or ""
        numero = f.get("numero") or f.get("id") or image_id

        await db.images.insert_one({
            "id": image_id,
            "user_id": uid,
            "filename": f"zayra_{numero}.jpg",
            "content_type": ctype,
            "data_b64": base64.b64encode(content).decode("utf-8"),
            "size_bytes": len(content),
            "created_at": datetime.utcnow(),
            # GPS/data já vêm do ZAYRA → não precisa EXIF/OCR no gerador.
            "meta_gps": gps,
            "meta_data_hora": data_hora,
            "meta_ocr_done": True,
            "origem": "zayra",
            "zayra_foto_id": str(f.get("id") or ""),
        })

        novas.append({
            "image_id": image_id,
            "url": f"/api/upload/image/{image_id}",
            "gps": gps,
            "data_hora": data_hora,
            "legenda": legenda,
            "description": legenda,
            "origem": "zayra",
        })

    # Também faz o push no doc (consistência imediata p/ contextos sem autosave),
    # mas o frontend do wizard DEVE anexar `fotos` ao estado do formulário — senão
    # o autosave (que substitui fotos_imovel) sobrescreve estas referências.
    if novas:
        await db.ptam_documents.update_one(
            {"id": ptam_id, "user_id": uid},
            {"$push": {"fotos_imovel": {"$each": novas}},
             "$set": {"updated_at": datetime.utcnow()}},
        )

    return {"importadas": len(novas), "falhas": falhas, "fotos": novas}
