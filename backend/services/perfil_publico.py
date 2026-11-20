# @module services.perfil_publico — Projeção PÚBLICA do perfil do avaliador.
#
# O link público do laudo (`GET /ptam/public/{token}`) é aberto por qualquer pessoa
# que tenha o link (cliente, banco, cartório, quem recebeu o encaminhamento). Antes,
# a rota devolvia o documento INTEIRO de `perfil_avaliador`, incluindo CPF, RG, a
# IMAGEM DA ASSINATURA do avaliador (`assinatura_visual_b64`/`assinatura_tecnico_b64`)
# e as imagens do cartão/certidão CRECI e certificado CNAI. Nada disso é usado pela
# tela pública (PortalCliente.jsx usa foto_perfil, nome e registros).
#
# Regra: LISTA DE PERMISSÃO (allowlist). Campo novo no perfil NÃO vaza por padrão.
from typing import Any, Dict, Optional

# Dados profissionais que o próprio avaliador publica no laudo/portal.
CAMPOS_PUBLICOS = (
    "nome_completo",
    "foto_perfil",
    "bio_resumo",
    "registros",
    "formacoes",
    "especializacoes",
    "habilitacoes",
    "areas_atuacao",
    "membro_associacoes",
    "telefone",
    "email_profissional",
    "site",
    "cidade",
    "uf",
    "empresa_nome",
)


def perfil_publico(perfil: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Devolve só os campos profissionais públicos do perfil (ou None)."""
    if not perfil:
        return None
    return {k: perfil.get(k) for k in CAMPOS_PUBLICOS if perfil.get(k) not in (None, "", [])}
