# @module pdf.themes.prime2_theme — Design tokens do template PRIME II (Romatec)
# Fonte única de cores/fontes. NENHUMA cor literal deve viver fora deste módulo.
import os
import logging
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger("romatec")

# ── Paleta ────────────────────────────────────────────────────────────────────
VERDE_ESCURO = "#0C3320"   # capa, bandas, footer, títulos sobre claro
VERDE_MEDIO  = "#0E5A3C"   # itálico de destaque em títulos
DOURADO      = "#C9A84C"   # box de valor, bordas de cards, filete, valores
OFFWHITE     = "#F7F5F0"   # fundo de seções alternadas
BRANCO       = "#FFFFFF"
CINZA_GHOST  = "#E3E1DB"   # numerais gigantes de seção
CINZA_TEXTO  = "#555555"
TEXTO        = "#1A1A1A"

# Versões HexColor (uso direto no canvas / styles)
C_VERDE_ESCURO = HexColor(VERDE_ESCURO)
C_VERDE_MEDIO  = HexColor(VERDE_MEDIO)
C_DOURADO      = HexColor(DOURADO)
C_OFFWHITE     = HexColor(OFFWHITE)
C_BRANCO       = HexColor(BRANCO)
C_CINZA_GHOST  = HexColor(CINZA_GHOST)
C_CINZA_TEXTO  = HexColor(CINZA_TEXTO)
C_TEXTO        = HexColor(TEXTO)

# ── Fontes (Playfair com fallback automático para Times) ───────────────────────
# Nomes lógicos retornados por fonts(); o registro tenta TTF, senão usa built-ins.
_FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")

_PLAYFAIR_FILES = {
    "PlayfairDisplay":        "PlayfairDisplay-Regular.ttf",
    "PlayfairDisplay-Bold":   "PlayfairDisplay-Bold.ttf",
    "PlayfairDisplay-Italic": "PlayfairDisplay-Italic.ttf",
}

# Fallbacks built-in do ReportLab (sempre disponíveis)
_FALLBACK = {
    "serif":        "Times-Roman",
    "serif_bold":   "Times-Bold",
    "serif_italic": "Times-Italic",
    "sans":         "Helvetica",
    "sans_bold":    "Helvetica-Bold",
    "mono":         "Courier",
}

_registered = False
_resolved = dict(_FALLBACK)


def registrar_fontes() -> dict:
    """Registra Playfair Display se os TTFs existirem; caso contrário usa Times.
    Idempotente. Retorna o mapa de nomes lógicos -> nome de fonte registrado."""
    global _registered, _resolved
    if _registered:
        return _resolved
    try:
        disponiveis = set(pdfmetrics.getRegisteredFontNames())
        ok = True
        for face, arquivo in _PLAYFAIR_FILES.items():
            caminho = os.path.join(_FONTS_DIR, arquivo)
            if face in disponiveis:
                continue
            if os.path.exists(caminho):
                pdfmetrics.registerFont(TTFont(face, caminho))
            else:
                ok = False
        if ok:
            _resolved = {
                "serif":        "PlayfairDisplay",
                "serif_bold":   "PlayfairDisplay-Bold",
                "serif_italic": "PlayfairDisplay-Italic",
                "sans":         "Helvetica",
                "sans_bold":    "Helvetica-Bold",
                "mono":         "Courier",
            }
        else:
            logger.info("Prime II: Playfair Display ausente em %s — usando Times.", _FONTS_DIR)
            _resolved = dict(_FALLBACK)
    except Exception as e:  # noqa: BLE001
        logger.warning("Prime II: falha ao registrar fontes (%s) — fallback Times.", e)
        _resolved = dict(_FALLBACK)
    _registered = True
    return _resolved


def fonts() -> dict:
    """Mapa de nomes lógicos -> fonte registrada (registra na 1ª chamada)."""
    return registrar_fontes()


def tracking(texto: str, espacos: int = 1) -> str:
    """Microlabel com letter-spacing simulado (ex.: 'V A L O R')."""
    sep = " " * max(1, espacos)
    return sep.join(list((texto or "").upper()))
