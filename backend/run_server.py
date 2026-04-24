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
    uvicorn.run("server:app", host=host, port=port, log_config=log_config)
