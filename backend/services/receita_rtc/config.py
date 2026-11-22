# @module services.receita_rtc.config — URLs, tempos e flags (variáveis de ambiente).
import os
from dataclasses import dataclass

AVISO_FIXO = ("Estimativa baseada nas calculadoras oficiais da Receita Federal. "
              "Não substitui o sistema emissor nem a validação do contador.")
AVISO_TABELA_INTERNA = "Estimativa com alíquota informada manualmente, aguardando confirmação."
MSG_INDISPONIVEL = "Calculadora da Receita indisponível no momento. Tente novamente."


def _flag(nome: str, padrao: bool = False) -> bool:
    v = os.environ.get(nome)
    if v is None:
        return padrao
    return v.strip().lower() in ("1", "true", "sim", "yes", "on")


def _ms(nome: str, padrao: int) -> float:
    try:
        return max(1, int(os.environ.get(nome, padrao))) / 1000.0
    except (TypeError, ValueError):
        return padrao / 1000.0


@dataclass(frozen=True)
class Config:
    enabled: bool
    regime_regular_url: str
    simples_url: str
    timeout_conexao_s: float
    timeout_leitura_s: float

    @property
    def configurada(self) -> bool:
        return bool(self.regime_regular_url and self.simples_url)


def carregar() -> Config:
    """Lido a cada uso: desligar a flag no Railway vale na próxima requisição."""
    return Config(
        enabled=_flag("RECEITA_RTC_ENABLED", False),
        regime_regular_url=os.environ.get("RECEITA_RTC_REGIME_REGULAR_URL", "").rstrip("/"),
        simples_url=os.environ.get("RECEITA_RTC_SIMPLES_URL", "").rstrip("/"),
        timeout_conexao_s=_ms("RECEITA_RTC_CONNECT_TIMEOUT_MS", 3000),
        timeout_leitura_s=_ms("RECEITA_RTC_TIMEOUT_MS", 15000),
    )
