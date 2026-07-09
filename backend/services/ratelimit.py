# @module services.ratelimit — Limiter compartilhado por IP REAL do cliente.
#
# Atrás do proxy da Railway, `request.client.host` é o IP do load balancer (bucket
# compartilhado por TODOS os clientes → um limite baixo bloquearia usuários legítimos).
# Aqui a chave usa o X-Forwarded-For (1º salto = cliente real), como o resto do código
# já faz. Use `pub_limiter.limit("N/minute")` nos endpoints públicos/sensíveis; o
# handler global de RateLimitExceeded (registrado no server.py) devolve 429.
from slowapi import Limiter
from starlette.requests import Request


def real_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "0.0.0.0"


pub_limiter = Limiter(key_func=real_ip)
