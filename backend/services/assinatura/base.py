# @module services.assinatura.base — Interface comum dos provedores BYOK + tipos de resultado.
# O restante do sistema fala só com SignatureProvider; nunca sabe qual provedor está em uso.
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


# ── Tipos de entrada/saída ────────────────────────────────────────────────────
@dataclass
class SignatarioEnvio:
    nome: str
    email: Optional[str] = None
    whatsapp: Optional[str] = None          # E.164
    cpf_cnpj: Optional[str] = None
    papel: str = "signatario"
    autenticacao: List[str] = field(default_factory=lambda: ["email"])
    ordem: Optional[int] = None


@dataclass
class OpcoesEnvio:
    mensagem: Optional[str] = None
    prazo_dias: Optional[int] = None
    lembrete_automatico: bool = True
    ordem_sequencial: bool = False
    pasta_destino: Optional[str] = None
    webhook_url: Optional[str] = None       # setada pelo caller (rota de envio)


@dataclass
class TesteConexaoResult:
    ok: bool
    mensagem: str
    dados: Optional[dict] = None            # ex.: {"cofres": [...]} p/ D4Sign


@dataclass
class EnvioResult:
    provider_doc_id: str
    url_assinatura_embed: Optional[str] = None
    raw: Optional[dict] = None


@dataclass
class StatusResult:
    status: str                             # rascunho|enviado|parcialmente_assinado|assinado|recusado|cancelado|expirado|erro
    signatarios: List[dict] = field(default_factory=list)
    raw: Optional[dict] = None


@dataclass
class WebhookEvent:
    tipo: str
    provider_doc_id: Optional[str] = None
    signatario: Optional[str] = None
    novo_status: Optional[str] = None       # status derivado p/ o envio (opcional)
    raw: Optional[dict] = None


# ── Erros ─────────────────────────────────────────────────────────────────────
class ProviderError(Exception):
    def __init__(self, mensagem: str, status_code: Optional[int] = None, raw=None):
        super().__init__(mensagem)
        self.status_code = status_code
        self.raw = raw


class CredencialNaoConfigurada(Exception):
    """Usuário não configurou o provedor (HTTP 409, código PROVIDER_NAO_CONFIGURADO)."""
    codigo = "PROVIDER_NAO_CONFIGURADO"


def safe_json(resp) -> dict:
    """r.json() tolerante — nunca levanta; devolve {'_text': ...} em corpo não-JSON."""
    try:
        return resp.json()
    except Exception:  # noqa: BLE001
        try:
            return {"_text": (resp.text or "")[:500]}
        except Exception:  # noqa: BLE001
            return {}


# ── Interface ─────────────────────────────────────────────────────────────────
class SignatureProvider(ABC):
    slug: str = ""
    nome_exibicao: str = ""
    suporta_whatsapp: bool = False
    suporta_ordem_assinatura: bool = False
    suporta_icp_brasil: bool = False

    def __init__(self, credenciais: dict, ambiente: str = "producao"):
        self.credenciais = credenciais or {}
        self.ambiente = "sandbox" if ambiente == "sandbox" else "producao"

    @abstractmethod
    async def testar_conexao(self) -> TesteConexaoResult: ...

    @abstractmethod
    async def enviar_documento(self, pdf_bytes: bytes, nome: str,
                               signatarios: List[SignatarioEnvio],
                               opcoes: OpcoesEnvio) -> EnvioResult: ...

    @abstractmethod
    async def consultar_status(self, provider_doc_id: str) -> StatusResult: ...

    @abstractmethod
    async def baixar_assinado(self, provider_doc_id: str) -> bytes: ...

    @abstractmethod
    async def cancelar(self, provider_doc_id: str, motivo: str = "") -> bool: ...

    @abstractmethod
    def parse_webhook(self, headers: dict, body: dict) -> WebhookEvent: ...
