"""
Persistência do TenantBranding no MongoDB (Motor async).

Collection: tenant_branding  ·  índice único { user_id: 1 }.
Isolamento: todas as queries filtram por user_id (convenção do projeto).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from models.tenant_branding import TenantBranding

COLLECTION = "tenant_branding"


async def ensure_indexes(db) -> None:
    """Chamar no startup (db.setup_indexes ou lifespan)."""
    await db[COLLECTION].create_index("user_id", unique=True, name="uniq_user_id")


async def get_branding(db, user_id: str) -> TenantBranding:
    """Retorna o branding do usuário ou um default não persistido."""
    doc = await db[COLLECTION].find_one({"user_id": user_id})
    if not doc:
        return TenantBranding.default_for(user_id)
    doc.pop("_id", None)
    return TenantBranding(**doc)


async def _upsert(db, user_id: str, changes: dict[str, Any]) -> TenantBranding:
    now = datetime.now(timezone.utc)
    changes = {k: v for k, v in changes.items() if v is not None}
    changes["updated_at"] = now
    await db[COLLECTION].update_one(
        {"user_id": user_id},
        {"$set": changes, "$setOnInsert": {"user_id": user_id, "created_at": now}},
        upsert=True,
    )
    return await get_branding(db, user_id)


async def update_colors(db, user_id, colors: dict) -> TenantBranding:
    return await _upsert(db, user_id, colors)


async def update_footer(db, user_id, footer: dict) -> TenantBranding:
    return await _upsert(db, user_id, footer)


async def update_typography(db, user_id, typography: dict) -> TenantBranding:
    return await _upsert(db, user_id, typography)


async def set_use_default(db, user_id, value: bool) -> TenantBranding:
    return await _upsert(db, user_id, {"use_default": value})


async def set_logo(
    db, user_id: str, *, logo_url: str, original_name: str, mime: str,
    width_px: int, height_px: int,
) -> TenantBranding:
    return await _upsert(
        db,
        user_id,
        {
            "logo_url": logo_url,
            "logo_original_name": original_name,
            "logo_mime": mime,
            "logo_width_px": width_px,
            "logo_height_px": height_px,
            "logo_updated_at": datetime.now(timezone.utc),
            "use_default": False,  # subir logo implica querer marca própria
        },
    )


async def get_logo_url(db, user_id: str) -> Optional[str]:
    doc = await db[COLLECTION].find_one({"user_id": user_id}, {"logo_url": 1, "_id": 0})
    return doc.get("logo_url") if doc else None


async def clear_logo(db, user_id: str) -> TenantBranding:
    now = datetime.now(timezone.utc)
    await db[COLLECTION].update_one(
        {"user_id": user_id},
        {
            "$set": {"updated_at": now},
            "$unset": {
                "logo_url": "", "logo_original_name": "", "logo_mime": "",
                "logo_width_px": "", "logo_height_px": "", "logo_updated_at": "",
            },
        },
    )
    return await get_branding(db, user_id)


async def reset_branding(db, user_id: str) -> TenantBranding:
    """Restaura padrão AvalieImob: zera tudo e marca use_default=True."""
    now = datetime.now(timezone.utc)
    await db[COLLECTION].update_one(
        {"user_id": user_id},
        {
            "$set": {"use_default": True, "updated_at": now, "created_at": now},
            "$unset": {
                "logo_url": "", "logo_original_name": "", "logo_mime": "",
                "logo_width_px": "", "logo_height_px": "", "logo_updated_at": "",
                "color_primary": "", "color_secondary": "", "color_text": "",
                "color_background": "", "color_footer_bg": "", "color_footer_text": "",
                "font_title": "", "font_body": "",
                "footer_line1": "", "footer_line2": "", "footer_line3": "",
                "stamp_name": "", "stamp_credentials": "",
            },
        },
        upsert=True,
    )
    return await get_branding(db, user_id)
