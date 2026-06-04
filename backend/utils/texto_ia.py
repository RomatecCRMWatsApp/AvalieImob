# @module utils.texto_ia — Limpeza de artefatos de IA em textos do laudo (BUG-02).
# Remove marcadores e prefixos deixados pela geração assistida por IA antes de
# inserir o texto no PDF (ex.: **negrito**, "Campo: x", "Texto aperfeiçoado:").
from __future__ import annotations

import re

_RE_BOLD = re.compile(r"\*\*(.*?)\*\*", re.S)
_RE_CAMPO = re.compile(r"Campo:\s*\w+\s*", re.I)
_RE_APERF = re.compile(r"Texto aperfei[çc]oado:\s*", re.I)
_RE_REGIAO = re.compile(r"Regi[ãa]o de\s+\w+:\s*", re.I)
_RE_COMENTARIO = re.compile(r"---.*$", re.M | re.S)
_RE_QUEBRAS = re.compile(r"\n{3,}")


def limpar_texto_ia(texto) -> str:
    """
    Remove artefatos de IA de um campo de texto do laudo.

    - **negrito** → negrito (remove os asteriscos)
    - "Campo: x" → removido
    - "Texto aperfeiçoado:" → removido
    - "Região de X:" → removido
    - "--- comentário ..." até o fim → removido
    - normaliza 3+ quebras de linha para 2
    """
    if not texto:
        return ""
    t = str(texto)
    t = _RE_BOLD.sub(r"\1", t)
    t = _RE_CAMPO.sub("", t)
    t = _RE_APERF.sub("", t)
    t = _RE_REGIAO.sub("", t)
    t = _RE_COMENTARIO.sub("", t)
    t = _RE_QUEBRAS.sub("\n\n", t)
    return t.strip()
