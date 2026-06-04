# @module utils.texto_ia — Limpeza de artefatos de IA em textos do laudo (BUG-02).
# Remove APENAS marcadores/prefixos de IA — NUNCA remove o conteúdo real do texto.
from __future__ import annotations

import re

_RE_BOLD = re.compile(r"\*\*(.*?)\*\*", re.S)        # **negrito** → negrito
_RE_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.S)  # *itálico* → itálico
_RE_HEAD = re.compile(r"^#{1,6}\s+", re.M)            # # título markdown
_RE_CAMPO = re.compile(r"^Campo:\s*\S+\s*", re.I | re.M)
_RE_APERF = re.compile(r"^Texto aperfei[çc]oado:\s*", re.I | re.M)
_RE_REGIAO = re.compile(r"^Regi[ãa]o de\s+\w+:\s*", re.I | re.M)
# Só remove o comentário de IA específico — NÃO remove qualquer "---".
_RE_COMENTARIO = re.compile(r"-{3,}\s*[Ee]ste texto.*$", re.S)
_RE_QUEBRAS = re.compile(r"\n{4,}")


def limpar_texto_ia(texto) -> str:
    """
    Remove artefatos de IA preservando TODO o conteúdo real.
    - **negrito** / *itálico* → texto interno (sem asteriscos)
    - "# título", "Campo: x", "Texto aperfeiçoado:", "Região de X:" → removidos
    - "--- Este texto ..." (comentário de IA no fim) → removido
    - 4+ quebras de linha → 3
    Jamais retorna vazio para um texto que tinha conteúdo.
    """
    if texto is None:
        return ""
    t = str(texto)
    if not t.strip():
        return ""
    t = _RE_BOLD.sub(r"\1", t)
    t = _RE_ITALIC.sub(r"\1", t)
    t = _RE_HEAD.sub("", t)
    t = _RE_CAMPO.sub("", t)
    t = _RE_APERF.sub("", t)
    t = _RE_REGIAO.sub("", t)
    t = _RE_COMENTARIO.sub("", t)
    t = _RE_QUEBRAS.sub("\n\n\n", t)
    return t.strip()
