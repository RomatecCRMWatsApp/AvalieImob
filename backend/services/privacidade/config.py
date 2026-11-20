# @module services.privacidade.config — Configuração dos recursos de privacidade (LGPD).
#
# Tudo aqui vem de VARIÁVEIS DE AMBIENTE. Nada de dado empresarial inventado: se a
# identificação do controlador não estiver configurada, o valor volta como None e o
# campo `pendente` lista o que falta (a tela e os documentos mostram "pendente").
#
# Flags (padrão DESLIGADO — produção não muda até aprovação):
#   PRIVACIDADE_RECURSOS_ATIVOS=1        → canal do titular, Central de Privacidade,
#                                           aceite versionado, consentimentos, exportação.
#   PRIVACIDADE_MINUTAS_ATIVAS=1         → serve os textos de Termos/Aviso (MINUTAS).
#   PRIVACIDADE_EXCLUSAO_EXECUCAO_ATIVA=1 → permite EXECUTAR anonimização de conta
#                                           (o plano/dry-run funciona sempre p/ admin).
import os
from typing import Dict, List, Optional


def _flag(nome: str) -> bool:
    return (os.getenv(nome, "") or "").strip().lower() in ("1", "true", "sim", "on", "yes")


def recursos_ativos() -> bool:
    return _flag("PRIVACIDADE_RECURSOS_ATIVOS")


def minutas_ativas() -> bool:
    return _flag("PRIVACIDADE_MINUTAS_ATIVAS")


def execucao_exclusao_ativa() -> bool:
    return _flag("PRIVACIDADE_EXCLUSAO_EXECUCAO_ATIVA")


def _int_env(nome: str, padrao: int, minimo: int, maximo: int) -> int:
    try:
        v = int(os.getenv(nome, "") or padrao)
    except ValueError:
        v = padrao
    return max(minimo, min(maximo, v))


def prazo_resposta_dias() -> int:
    """Prazo INTERNO de resposta a pedidos de titular (dias corridos).

    Valor a VALIDAR pelo jurídico (a LGPD prevê regimes distintos por tipo de pedido;
    ver docs/privacidade/retencao-e-direitos.md). Padrão técnico: 15.
    """
    return _int_env("PRIVACIDADE_PRAZO_DIAS", 15, 1, 90)


def validade_exportacao_minutos() -> int:
    return _int_env("PRIVACIDADE_EXPORTACAO_MINUTOS", 15, 1, 120)


_CAMPOS_CONTROLADOR = {
    "nome": "PRIVACIDADE_CONTROLADOR_NOME",
    "documento": "PRIVACIDADE_CONTROLADOR_DOCUMENTO",
    "endereco": "PRIVACIDADE_CONTROLADOR_ENDERECO",
    "email_privacidade": "PRIVACIDADE_EMAIL",
    "encarregado": "PRIVACIDADE_ENCARREGADO",
}


def controlador() -> Dict[str, Optional[str] | List[str]]:
    """Identificação do controlador lida do ambiente; `pendente` lista o que falta."""
    dados: Dict[str, Optional[str] | List[str]] = {}
    pendente: List[str] = []
    for campo, env in _CAMPOS_CONTROLADOR.items():
        v = (os.getenv(env, "") or "").strip() or None
        dados[campo] = v
        if not v:
            pendente.append(campo)
    dados["pendente"] = pendente
    return dados
