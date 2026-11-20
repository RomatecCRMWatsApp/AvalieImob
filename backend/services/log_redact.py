# @module services.log_redact — mascara dados pessoais e segredos nos logs.
"""Filtro de logging aplicado a TODOS os handlers no startup.

Por quê: vários pontos do código registram telefone, e-mail ou CPF de clientes
(ex.: falha de envio por WhatsApp). Log é cópia de dados pessoais com acesso amplo
(painel do Railway, suporte), então o conteúdo sai mascarado num lugar só, sem
depender de cada chamada lembrar disso.

O que é mascarado:
- e-mail          → j***@dominio.com
- telefone BR     → ***1246 (só os 4 últimos dígitos)
- CPF             → ***.***.***-00
- JWT/Bearer      → [jwt] / Bearer [redigido]
- token longo em URL (links de assinatura, aceite, laudo público) → [token]

Limites (documentados em docs/privacidade/auditoria-e-plano.md): o texto do
traceback de exceções é montado pelo formatter depois do filtro e não é mascarado.
"""
from __future__ import annotations

import logging
import re

_EMAIL = re.compile(r"\b([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-(\d{2})\b")
# +55 (99) 99181-1246 · 5599991811246 · 99 99181 1246 — sequências de 10 a 13 dígitos
_FONE = re.compile(r"(?<![\w.-])(?:\+?55[\s-]?)?\(?\d{2}\)?[\s-]?\d{4,5}[\s-]?(\d{4})(?![\w-])")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE)
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_SEGMENTO_LONGO = re.compile(r"(?<=/)[A-Za-z0-9_-]{32,}")


def _token_url(m: re.Match) -> str:
    s = m.group(0)
    # ids de documento (uuid) não são segredo e ajudam a investigar falhas
    return s if _UUID.match(s) else "[token]"


def redigir(texto: str) -> str:
    """Mascara dados pessoais e segredos num texto de log. Função pura."""
    if not texto or not isinstance(texto, str):
        return texto
    t = _JWT.sub("[jwt]", texto)
    t = _BEARER.sub(r"\1[redigido]", t)
    t = _SEGMENTO_LONGO.sub(_token_url, t)
    t = _EMAIL.sub(r"\1***@\2", t)
    t = _CPF.sub(r"***.***.***-\1", t)
    t = _FONE.sub(r"***\1", t)
    return t


class FiltroRedacao(logging.Filter):
    """Redige a mensagem e os argumentos de texto, sem mudar a formatação do record."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = redigir(record.msg)
            if isinstance(record.args, tuple):
                record.args = tuple(redigir(a) if isinstance(a, str) else a for a in record.args)
            elif isinstance(record.args, dict):
                record.args = {k: (redigir(v) if isinstance(v, str) else v) for k, v in record.args.items()}
        except Exception:  # nunca derruba um log
            pass
        return True


_FILTRO = FiltroRedacao()


def instalar() -> int:
    """Instala o filtro nos handlers do root e do uvicorn. Idempotente. Devolve quantos."""
    n = 0
    for nome in (None, "uvicorn", "uvicorn.access", "uvicorn.error"):
        for h in logging.getLogger(nome).handlers:
            if _FILTRO not in h.filters:
                h.addFilter(_FILTRO)
                n += 1
    return n
