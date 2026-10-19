# @module services.garantia_assets — Prepara o documento de Garantia para os geradores
# (PDF/DOCX/assinatura). Carrega bytes das fotos, perfil do avaliador, usuário e o
# logo white-label ANTES da geração (os geradores são síncronos e não acessam o banco).
# Fonte ÚNICA: PDF, DOCX, ICP, WhatsApp, Telegram, e-mail e link público usam isto,
# então o laudo é sempre o MESMO em qualquer canal.
from __future__ import annotations

import base64
import logging

from services import image_store

logger = logging.getLogger("romatec")

# Campos de lista que guardam ids de imagem/documento.
CAMPOS_DOCS = {
    "doc_mapa_sigef": "Mapa SIGEF",
    "doc_memorial_descritivo": "Memorial descritivo",
    "doc_ccir": "CCIR",
    "doc_itr": "ITR",
    "doc_car": "CAR",
}


def _img_id(item) -> str:
    if isinstance(item, dict):
        item = item.get("image_id") or item.get("id") or item.get("url") or ""
    s = str(item or "")
    return s.replace("/api/upload/image/", "").split("/")[-1].split("?")[0]


async def _bytes_de(db, item) -> bytes | None:
    iid = _img_id(item)
    if not iid:
        return None
    try:
        img = await image_store.find_one(db, {"id": iid})
    except Exception:  # noqa: BLE001
        img = None
    if img and img.get("data_b64"):
        try:
            return base64.b64decode(img["data_b64"])
        except Exception:  # noqa: BLE001
            return None
    return None


async def preparar(db, doc: dict, uid: str | None = None) -> dict:
    """Popula in-place os campos `_` que os geradores consomem. Nunca levanta."""
    uid = uid or doc.get("user_id")
    fotos = []
    for i, item in enumerate(doc.get("fotos") or [], 1):
        b = await _bytes_de(db, item)
        if b:
            leg = (item.get("legenda") or item.get("description")) if isinstance(item, dict) else None
            fotos.append((b, leg or f"Foto {i}"))
    doc["_fotos_bytes"] = fotos

    anexos = []
    for campo, rotulo in CAMPOS_DOCS.items():
        for j, item in enumerate(doc.get(campo) or [], 1):
            b = await _bytes_de(db, item)
            if b:
                anexos.append((b, f"{rotulo}" + (f" ({j})" if j > 1 else "")))
    doc["_anexos_bytes"] = anexos

    try:
        perfil = await db.perfil_avaliador.find_one({"user_id": uid}) or {}
        perfil.pop("_id", None)
    except Exception:  # noqa: BLE001
        perfil = {}
    try:
        user = await db.users.find_one({"id": uid}) or {}
        user.pop("_id", None)
        user.pop("password_hash", None)
    except Exception:  # noqa: BLE001
        user = {}
    doc["_perfil"] = perfil
    doc["_user"] = user

    try:
        from services import branding_repository as repo
        from services.branding_context import BrandContext
        branding = await repo.get_branding(db, uid)
        doc["_brand_logo_bytes"] = BrandContext.from_branding(branding).custom_logo_bytes()
    except Exception:  # noqa: BLE001
        doc["_brand_logo_bytes"] = None
    return doc


def nome_arquivo(doc: dict, sufixo: str = "", ext: str = "pdf") -> str:
    num = str(doc.get("numero") or doc.get("id") or "sem-numero").replace("/", "-")
    return f"Laudo_Garantia_{num}{sufixo}.{ext}"
