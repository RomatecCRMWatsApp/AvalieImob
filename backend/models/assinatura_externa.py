# @module models.assinatura_externa — Modelos da assinatura externa BYOK.
from __future__ import annotations

from typing import List, Optional, Literal

from pydantic import BaseModel

Provider = Literal["d4sign", "clicksign", "autentique"]
OrigemTipo = Literal["ptam", "contrato_exclusividade", "documento_externo",
                     "recibo", "laudo_agrimensura", "outro"]


class CredencialInput(BaseModel):
    """Corpo do POST /credenciais. `credenciais` vem em CLARO e é cifrado no serviço."""
    provider: Provider
    ambiente: Literal["sandbox", "producao"] = "producao"
    credenciais: dict = {}
    padrao: bool = False


class EnvioInput(BaseModel):
    """Corpo do POST /envios. O PDF é carregado da origem no backend (não vem no body)."""
    provider: Optional[Provider] = None      # omitido → usa o provedor padrão do usuário
    origem_tipo: OrigemTipo
    origem_id: str
    signatarios: List[dict] = []             # {nome,email,whatsapp,cpf_cnpj,papel,autenticacao[],ordem}
    opcoes: dict = {}                        # {mensagem,prazo_dias,ordem_sequencial,...}
