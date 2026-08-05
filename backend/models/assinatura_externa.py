# @module models.assinatura_externa — Modelos da assinatura externa BYOK.
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Provider = Literal["d4sign", "clicksign", "autentique"]


class CredencialInput(BaseModel):
    """Corpo do POST /credenciais. `credenciais` vem em CLARO e é cifrado no serviço."""
    provider: Provider
    ambiente: Literal["sandbox", "producao"] = "producao"
    credenciais: dict = {}
    padrao: bool = False
