# @module server — Ponto de entrada: cria app FastAPI, registra routers e configura middlewares
"""RomaTec AvalieImob — FastAPI backend."""
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from db import init_db, close_db, get_db
from routes import all_routers

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("romatec")

# ── Rate limiter ────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["100/10minutes"])

# ── App ─────────────────────────────────────────────────────────────
app = FastAPI(title="RomaTec AvalieImob API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Security headers middleware ──────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


# ── Register all routers under /api prefix ──────────────────────────
from fastapi import APIRouter
api = APIRouter(prefix="/api")

for router in all_routers:
    api.include_router(router)

# Root health check
@api.get("/")
async def root():
    return {"app": "RomaTec AvalieImob API", "version": "1.0.0"}

app.include_router(api)

# ── React SPA static files ───────────────────────────────────────────
import pathlib as _pathlib
_frontend_build = _pathlib.Path(__file__).parent.parent / "frontend" / "build"
if _frontend_build.exists():
    from fastapi.staticfiles import StaticFiles
    from starlette.responses import FileResponse

    app.mount("/static", StaticFiles(directory=str(_frontend_build / "static")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = _frontend_build / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_build / "index.html"))

# ── Middlewares (ordem importa: após rotas, antes do startup) ────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Lifecycle ────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    init_db()
    logger.info("MongoDB conectado")


@app.on_event("shutdown")
async def shutdown():
    await close_db()
