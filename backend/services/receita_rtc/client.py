# @module services.receita_rtc.client — HTTP para as calculadoras (timeout, retry, circuit breaker, cache).
#
# - Retry: até 2 novas tentativas, com espera crescente, SÓ em falha de rede ou 5xx. Nunca em 4xx.
# - Circuit breaker: 3 falhas seguidas abrem o circuito por 30 s; nesse tempo responde "indisponível" na hora.
# - Cache de 24 h para consultas de referência (tabelas, descrições de erro, versão).
# - Logs: só caminho, status e duração. Nunca o corpo (pode ter valores do cliente).
import asyncio
import logging
import time
from typing import Any, Optional

import httpx

from . import config as cfg

logger = logging.getLogger("romatec")

CACHE_TTL_S = 24 * 3600
_BREAKER_LIMITE = 3
_BREAKER_PAUSA_S = 30.0
_RETRIES = 2


class CalculadoraIndisponivel(Exception):
    """Rede, timeout, 5xx ou circuito aberto. Mensagem amigável em cfg.MSG_INDISPONIVEL."""


class Resposta:
    def __init__(self, status: int, corpo: Any, headers: dict):
        self.status = status
        self.corpo = corpo
        self.headers = headers

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class _Breaker:
    def __init__(self):
        self.falhas = 0
        self.aberto_ate = 0.0

    def permitido(self) -> bool:
        return time.monotonic() >= self.aberto_ate

    def sucesso(self):
        self.falhas = 0
        self.aberto_ate = 0.0

    def falha(self):
        self.falhas += 1
        if self.falhas >= _BREAKER_LIMITE:
            self.aberto_ate = time.monotonic() + _BREAKER_PAUSA_S
            logger.warning("receita_rtc: circuito aberto por %.0f s após %d falhas", _BREAKER_PAUSA_S, self.falhas)


_breakers: dict = {}
_cache: dict = {}


def limpar_estado():
    """Usado em testes."""
    _breakers.clear()
    _cache.clear()


def _breaker(base: str) -> _Breaker:
    return _breakers.setdefault(base, _Breaker())


class CalculadoraClient:
    def __init__(self, base_url: str, conf: Optional[cfg.Config] = None, transport=None, espera_base_s: float = 0.3):
        self.base = base_url.rstrip("/")
        self.conf = conf or cfg.carregar()
        self._transport = transport
        self._espera = espera_base_s

    async def _uma(self, metodo: str, caminho: str, params=None, json=None) -> Resposta:
        timeout = httpx.Timeout(self.conf.timeout_leitura_s, connect=self.conf.timeout_conexao_s)
        async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as c:
            r = await c.request(metodo, f"{self.base}{caminho}", params=params, json=json)
        try:
            corpo = r.json()
        except ValueError:
            corpo = None
        return Resposta(r.status_code, corpo, {k.lower(): v for k, v in r.headers.items()})

    async def chamar(self, metodo: str, caminho: str, params=None, json=None) -> Resposta:
        br = _breaker(self.base)
        if not br.permitido():
            raise CalculadoraIndisponivel(cfg.MSG_INDISPONIVEL)
        ultima: Optional[Exception] = None
        for tentativa in range(_RETRIES + 1):
            t0 = time.perf_counter()
            try:
                resp = await self._uma(metodo, caminho, params, json)
            except (httpx.TransportError, httpx.TimeoutException) as e:
                ultima = e
                logger.warning("receita_rtc: %s %s falhou (%s) tentativa %d", metodo, caminho, type(e).__name__, tentativa + 1)
            else:
                ms = int((time.perf_counter() - t0) * 1000)
                logger.info("receita_rtc: %s %s -> %d (%d ms)", metodo, caminho, resp.status, ms)
                if resp.status < 500:
                    br.sucesso()
                    return resp
                ultima = RuntimeError(f"HTTP {resp.status}")
            if tentativa < _RETRIES:
                await asyncio.sleep(self._espera * (2 ** tentativa))
        br.falha()
        raise CalculadoraIndisponivel(cfg.MSG_INDISPONIVEL) from ultima

    async def get_cache(self, caminho: str, params: Optional[dict] = None) -> Resposta:
        """GET com cache de 24 h. Respostas 404 também entram no cache (ausência de alíquota é estável)."""
        chave = (self.base, caminho, tuple(sorted((params or {}).items())))
        hit = _cache.get(chave)
        if hit and hit[0] > time.monotonic():
            return hit[1]
        resp = await self.chamar("GET", caminho, params=params)
        if resp.ok or resp.status == 404:
            _cache[chave] = (time.monotonic() + CACHE_TTL_S, resp)
        return resp
