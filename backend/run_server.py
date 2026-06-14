"""Run Uvicorn with stdout-based log handlers for Railway-friendly log classification."""

import os
from copy import deepcopy

import uvicorn
from uvicorn.config import LOGGING_CONFIG


log_config = deepcopy(LOGGING_CONFIG)

# Route both uvicorn error and access logs to stdout so platforms don't label INFO as stderr.
for handler_name in ("default", "access"):
    if handler_name in log_config.get("handlers", {}):
        log_config["handlers"][handler_name]["stream"] = "ext://sys.stdout"


if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.getenv("PORT", "8000"))
    # MÚLTIPLOS WORKERS (processos): com 1 só, uma geração de PDF pesada (ReportLab é
    # CPU-bound e segura o GIL) travava o ÚNICO processo e ele parava de aceitar conexões
    # → ERR_CONNECTION_TIMED_OUT ao abrir o link de assinatura durante o envio. Com N
    # workers, enquanto um gera o PDF os outros atendem normalmente. Cada worker roda o
    # startup (índices são idempotentes). Configurável via WEB_CONCURRENCY (default 4).
    workers = max(1, int(os.getenv("WEB_CONCURRENCY", "4")))
    uvicorn.run("server:app", host=host, port=port, workers=workers, log_config=log_config)
