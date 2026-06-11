# @module pdf.themes.prime1 — Tokens do template PRIME I (editorial preto × verde).
# Reaproveita fontes e parte da paleta do Prime II; só adiciona o que é específico.
from reportlab.lib.colors import HexColor
from pdf.themes.prime2_theme import (  # reuso (sem duplicar)
    VERDE_ESCURO, DOURADO, CINZA_TEXTO, CINZA_GHOST, BRANCO,
    C_VERDE_ESCURO, C_DOURADO, C_CINZA_TEXTO, C_CINZA_GHOST, C_BRANCO,
    fonts, registrar_fontes, tracking,
)

PRETO          = "#0E0E0E"   # painel esquerdo da capa e footer
VERDE_GRAD_TOP = "#15724A"   # topo do gradiente do painel direito

C_PRETO          = HexColor(PRETO)
C_VERDE_GRAD_TOP = HexColor(VERDE_GRAD_TOP)
