# @module services.nfse.exceptions — Erros do módulo de emissão de NFS-e.


class NFSeError(Exception):
    """Erro genérico do módulo NFS-e."""


class NFSeConfigError(NFSeError):
    """Configuração ausente/inválida (município, provider, credenciais)."""


class NFSeProviderError(NFSeError):
    """Falha de comunicação/transmissão com o provider (gateway/Sefin)."""


class NFSeRejeitada(NFSeError):
    """A NFS-e foi REJEITADA pelo fisco (schema/validação)."""

    def __init__(self, codigo: str, mensagem: str):
        self.codigo = codigo
        self.mensagem = mensagem
        super().__init__(f"[{codigo}] {mensagem}")
