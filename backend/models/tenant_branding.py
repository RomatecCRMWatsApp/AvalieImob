"""
TenantBranding — modelo de white-label por tenant (AvalieImob).

Pydantic v2. Define o contrato de marca personalizada injetada em todos os
documentos gerados (PTAM, Laudo, Recibo, Contrato, TVI). Quando um campo não é
preenchido — ou use_default=True — o sistema cai no padrão Romatec/AvalieImob.

Stack: FastAPI + MongoDB (Motor async). Persistência fica no
backend/services/branding_repository.py.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# ─────────────────────────────────────────────────────────────────────────────
# Padrões AvalieImob (fallback). Ajuste o caminho do logo conforme o deploy.
# ─────────────────────────────────────────────────────────────────────────────
AVALIEIMOB_DEFAULTS = {
    "color_primary": "#0d4f3c",
    "color_secondary": "#c9a84c",
    "color_text": "#1a1a1a",
    "color_background": "#ffffff",
    "color_footer_bg": "#0d4f3c",
    "color_footer_text": "#ffffff",
    "font_title": "Montserrat",
    "font_body": "Inter",
    "footer_line1": "AvalieImob — Romatec Consultoria Total · Açailândia/MA",
    "footer_line2": "CNAI 031161 · CRECI/MA 4.705 · CFT/MA 01209185369",
    "footer_line3": "romatecavalieimob.com.br",
    "stamp_name": "José Romário Pinto Bezerra",
    "stamp_credentials": "Avaliador CNAI 031161 · CRECI/MA 4.705 · CFT/MA 01209185369",
}

# Logo padrão embarcado na aplicação (PNG com transparência, 300 DPI).
AVALIEIMOB_DEFAULT_LOGO_PATH = "backend/assets/avalieimob_logo.png"

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

ACCEPTED_LOGO_MIMES = {
    "image/png": "png",
    "image/svg+xml": "svg",
    "image/jpeg": "jpg",
}

LOGO_MAX_BYTES = 2 * 1024 * 1024          # 2 MB
LOGO_MIN_DIMENSIONS = (200, 60)           # (w, h)
LOGO_MAX_DIMENSIONS = (2000, 600)
LOGO_TARGET_DPI = 300


def _normalize_hex(value: Optional[str]) -> Optional[str]:
    """Valida e normaliza cor hex para minúsculas com '#'. None passa direto."""
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    if not v.startswith("#"):
        v = "#" + v
    if not _HEX_RE.match(v):
        raise ValueError(f"cor inválida: '{value}' — use formato hex #RRGGBB")
    return v.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Sub-payloads para os endpoints PUT (atualização parcial)
# ─────────────────────────────────────────────────────────────────────────────
class BrandingColors(BaseModel):
    color_primary: Optional[str] = None
    color_secondary: Optional[str] = None
    color_text: Optional[str] = None
    color_background: Optional[str] = None
    color_footer_bg: Optional[str] = None
    color_footer_text: Optional[str] = None

    @field_validator("*", mode="before")
    @classmethod
    def _validate_hex(cls, v):
        return _normalize_hex(v)


class BrandingFooter(BaseModel):
    footer_line1: Optional[str] = Field(default=None, max_length=160)
    footer_line2: Optional[str] = Field(default=None, max_length=160)
    footer_line3: Optional[str] = Field(default=None, max_length=160)
    stamp_name: Optional[str] = Field(default=None, max_length=120)
    stamp_credentials: Optional[str] = Field(default=None, max_length=200)


class BrandingTypography(BaseModel):
    font_title: Optional[str] = Field(default=None, max_length=60)
    font_body: Optional[str] = Field(default=None, max_length=60)


# ─────────────────────────────────────────────────────────────────────────────
# Modelo completo persistido (collection: tenant_branding)
# ─────────────────────────────────────────────────────────────────────────────
class TenantBranding(BaseModel):
    user_id: str  # chave de isolamento do projeto (== conta/tenant)

    # Logo
    logo_url: Optional[str] = None
    logo_original_name: Optional[str] = None
    logo_mime: Optional[str] = None
    logo_width_px: Optional[int] = None
    logo_height_px: Optional[int] = None
    logo_updated_at: Optional[datetime] = None

    # Paleta de cores
    color_primary: Optional[str] = None
    color_secondary: Optional[str] = None
    color_text: Optional[str] = None
    color_background: Optional[str] = None
    color_footer_bg: Optional[str] = None
    color_footer_text: Optional[str] = None

    # Tipografia
    font_title: Optional[str] = None
    font_body: Optional[str] = None

    # Rodapé personalizado
    footer_line1: Optional[str] = None
    footer_line2: Optional[str] = None
    footer_line3: Optional[str] = None

    # Carimbo / assinatura técnica
    stamp_name: Optional[str] = None
    stamp_credentials: Optional[str] = None

    # Fallback
    use_default: bool = True

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator(
        "color_primary", "color_secondary", "color_text",
        "color_background", "color_footer_bg", "color_footer_text",
        mode="before",
    )
    @classmethod
    def _validate_colors(cls, v):
        return _normalize_hex(v)

    # ── Resolução de marca efetiva (com fallback AvalieImob) ──────────────────
    def resolved(self) -> "ResolvedBranding":
        """
        Devolve a marca pronta para renderização, já aplicando os fallbacks.
        Se use_default=True, ignora cores/textos custom e usa o padrão AvalieImob,
        mas preserva o logo do tenant caso exista (a menos que não haja logo).
        """
        use_custom = not self.use_default

        def pick(field: str) -> str:
            if use_custom:
                val = getattr(self, field, None)
                if val:
                    return val
            return AVALIEIMOB_DEFAULTS[field]

        logo = self.logo_url if (use_custom and self.logo_url) else None

        return ResolvedBranding(
            logo_url=logo or AVALIEIMOB_DEFAULT_LOGO_PATH,
            logo_is_default=logo is None,
            color_primary=pick("color_primary"),
            color_secondary=pick("color_secondary"),
            color_text=pick("color_text"),
            color_background=pick("color_background"),
            color_footer_bg=pick("color_footer_bg"),
            color_footer_text=pick("color_footer_text"),
            font_title=pick("font_title"),
            font_body=pick("font_body"),
            footer_line1=pick("footer_line1"),
            footer_line2=pick("footer_line2"),
            footer_line3=pick("footer_line3"),
            stamp_name=pick("stamp_name"),
            stamp_credentials=pick("stamp_credentials"),
        )

    @classmethod
    def default_for(cls, user_id: str) -> "TenantBranding":
        """Instância padrão (sem custom) para um usuário ainda sem branding salvo."""
        return cls(user_id=user_id, use_default=True)


class ResolvedBranding(BaseModel):
    """Marca efetiva (já com fallbacks) consumida pelo gerador de PDF e pelo preview."""
    logo_url: str
    logo_is_default: bool
    color_primary: str
    color_secondary: str
    color_text: str
    color_background: str
    color_footer_bg: str
    color_footer_text: str
    font_title: str
    font_body: str
    footer_line1: str
    footer_line2: str
    footer_line3: str
    stamp_name: str
    stamp_credentials: str
