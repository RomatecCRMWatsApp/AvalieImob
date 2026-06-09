"""
Resolvedor de marca UNIVERSAL do AvalieImob.

Ponto único que TODOS os geradores de documento consultam para aplicar o
white-label do usuário — PTAM, TVI, Locação (ReportLab) e Contrato, Recibo,
TVI/Locação DOCX (python-docx). Quando o usuário usa o padrão (use_default=True)
ou não tem branding salvo, devolve as cores/logo padrão Romatec/AvalieImob,
mantendo os documentos existentes idênticos ao que já são hoje.

Uso típico dentro de um gerador:

    from services.branding_context import BrandContext

    brand = await BrandContext.for_user(db, user_id)
    # ReportLab:
    green = brand.rl_color("primary")        # reportlab HexColor
    logo_reader = brand.logo_image_reader()  # reportlab ImageReader | None
    # python-docx:
    green_docx = brand.docx_color("primary") # docx.shared.RGBColor
    logo_stream = brand.logo_bytesio()        # io.BytesIO | None
"""
from __future__ import annotations

import io
import os
import urllib.request
from functools import lru_cache
from typing import Optional

from models.tenant_branding import (
    AVALIEIMOB_DEFAULT_LOGO_PATH,
    ResolvedBranding,
    TenantBranding,
)

# Logo padrão atual do projeto (mantém compatibilidade com ptam_pdf.LOGO_URL).
DEFAULT_LOGO_URL = os.getenv(
    "AVALIEIMOB_DEFAULT_LOGO_URL",
    "https://customer-assets.emergentagent.com"
    "/job_review-simples/artifacts/0n08eo2p_02_icone_512.png",
)


@lru_cache(maxsize=128)
def _load_logo_bytes(ref: str) -> Optional[bytes]:
    """Baixa/lê o logo uma vez por referência (URL http(s) ou caminho local)."""
    try:
        if ref.startswith("http://") or ref.startswith("https://"):
            with urllib.request.urlopen(ref, timeout=8) as resp:
                return resp.read()
        if os.path.exists(ref):
            with open(ref, "rb") as fh:
                return fh.read()
    except Exception:
        return None
    return None


class BrandContext:
    """Marca resolvida + conversores para os dois motores de documento."""

    def __init__(self, resolved: ResolvedBranding):
        self.r = resolved

    # ── Construtores ──────────────────────────────────────────────────────────
    @classmethod
    async def for_user(cls, db, user_id: str) -> "BrandContext":
        from services import branding_repository as repo  # import tardio evita ciclo
        branding = await repo.get_branding(db, user_id)
        return cls.from_branding(branding)

    @classmethod
    def from_branding(cls, branding: TenantBranding) -> "BrandContext":
        return cls(branding.resolved())

    @classmethod
    def default(cls) -> "BrandContext":
        return cls(TenantBranding.default_for("__default__").resolved())

    # ── Cores ────────────────────────────────────────────────────────────────
    def hex(self, role: str) -> str:
        """role ∈ primary|secondary|text|background|footer_bg|footer_text"""
        return {
            "primary": self.r.color_primary,
            "secondary": self.r.color_secondary,
            "text": self.r.color_text,
            "background": self.r.color_background,
            "footer_bg": self.r.color_footer_bg,
            "footer_text": self.r.color_footer_text,
        }[role]

    def rl_color(self, role: str):
        """reportlab.lib.colors.HexColor da cor pedida."""
        from reportlab.lib.colors import HexColor
        return HexColor(self.hex(role))

    def docx_color(self, role: str):
        """docx.shared.RGBColor da cor pedida."""
        from docx.shared import RGBColor
        h = self.hex(role).lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    def docx_hex(self, role: str) -> str:
        """Hex sem '#', para shading de célula em python-docx (w:fill)."""
        h = self.hex(role).lstrip("#")
        return "".join(c * 2 for c in h) if len(h) == 3 else h

    # ── Fontes ───────────────────────────────────────────────────────────────
    @property
    def font_title(self) -> str:
        return self.r.font_title

    @property
    def font_body(self) -> str:
        return self.r.font_body

    # ── Textos de rodapé / assinatura ────────────────────────────────────────
    @property
    def footer_lines(self) -> list[str]:
        return [l for l in (self.r.footer_line1, self.r.footer_line2, self.r.footer_line3) if l]

    @property
    def stamp_name(self) -> str:
        return self.r.stamp_name

    @property
    def stamp_credentials(self) -> str:
        return self.r.stamp_credentials

    # ── Logo ─────────────────────────────────────────────────────────────────
    def _logo_ref(self) -> str:
        ref = self.r.logo_url
        # Quando é o padrão local placeholder, prefere a URL pública conhecida.
        if not ref or ref == AVALIEIMOB_DEFAULT_LOGO_PATH:
            return DEFAULT_LOGO_URL
        return ref

    def logo_bytes(self) -> Optional[bytes]:
        return _load_logo_bytes(self._logo_ref())

    def logo_bytesio(self) -> Optional[io.BytesIO]:
        data = self.logo_bytes()
        return io.BytesIO(data) if data else None

    def logo_image_reader(self):
        """reportlab.lib.utils.ImageReader pronto p/ canvas.drawImage. None se falhar."""
        data = self.logo_bytes()
        if not data:
            return None
        from reportlab.lib.utils import ImageReader
        try:
            return ImageReader(io.BytesIO(data))
        except Exception:
            return None

    # ── Injeção no dict `user` (padrão universal dos geradores) ───────────────
    def inject_into_user(self, user: Optional[dict]) -> dict:
        """
        Injeta a marca em chaves reservadas do dict `user` consumido por TODOS
        os geradores (generate_ptam_pdf, generate_contrato_docx, gerar_recibo_pdf,
        TVI/Locação). Não sobrescreve dados de perfil do usuário; só adiciona as
        chaves `_brand_*`. Generators leem essas chaves com fallback aos padrões.
        """
        user = dict(user or {})
        user["_company_logo_bytes"] = self.logo_bytes()
        user["_brand_primary"] = self.hex("primary")        # ex.: "#1b4d1b"
        user["_brand_secondary"] = self.hex("secondary")    # ex.: "#d4a830"
        user["_brand_text"] = self.hex("text")
        user["_brand_footer_bg"] = self.hex("footer_bg")
        user["_brand_footer_text"] = self.hex("footer_text")
        user["_brand_footer_lines"] = self.footer_lines
        user["_brand_stamp_name"] = self.stamp_name
        user["_brand_stamp_credentials"] = self.stamp_credentials
        user["_brand_font_title"] = self.font_title
        user["_brand_font_body"] = self.font_body
        return user


async def inject_brand(db, user_id: str, user: Optional[dict]) -> dict:
    """Atalho: resolve a marca do usuário e injeta no dict `user`. Use nas rotas."""
    brand = await BrandContext.for_user(db, user_id)
    return brand.inject_into_user(user)
