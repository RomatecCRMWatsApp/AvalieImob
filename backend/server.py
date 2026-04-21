# @module server — Ponto de entrada: cria app FastAPI, registra routers e configura middlewares
"""RomaTec AvalieImob — FastAPI backend."""
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import logging
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
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

# ── Play Store TWA: assetlinks.json ──────────────────────────────────
from fastapi.responses import JSONResponse
import json

@app.get("/.well-known/assetlinks.json")
async def assetlinks():
    """Digital Asset Links para Trusted Web Activity (TWA)."""
    return JSONResponse(content=[{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": "br.com.romatec.avalieimob",
            "sha256_cert_fingerprints": ["0A:A2:42:55:DD:80:C5:11:3C:65:36:76:73:96:7F:05:D3:D5:94:A5:32:42:E9:2B:7B:5C:67:FE:6A:A6:49:01"]
        }
    }])

# ── Página de Privacidade (LGPD) ─────────────────────────────────────
@app.get("/privacidade", response_class=HTMLResponse)
async def privacidade():
    """Política de Privacidade exigida pela Play Store."""
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Política de Privacidade — Romatec AvaliImob</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #333; }
        h1 { color: #1B4D1B; }
        h2 { color: #2d6a2d; margin-top: 2rem; }
        .date { color: #666; font-size: 0.9rem; }
        .contact { background: #f5f5f5; padding: 1rem; border-radius: 8px; margin-top: 2rem; }
    </style>
</head>
<body>
    <h1>Política de Privacidade</h1>
    <p class="date">Última atualização: 21 de abril de 2026</p>
    
    <p>O <strong>Romatec AvaliImob</strong> é operado por <strong>J R P Bezerra Ltda</strong> (Romatec Consultoria Imobiliária), CNPJ 12.091.853/0001-69, com sede em Açailândia, MA.</p>
    
    <h2>1. Dados Coletados</h2>
    <ul>
        <li><strong>Dados de cadastro:</strong> nome, e-mail, telefone, CREA/CAU/CFTMA</li>
        <li><strong>Dados de clientes:</strong> CPF/CNPJ das partes envolvidas em laudos</li>
        <li><strong>Dados de imóveis:</strong> endereço, coordenadas GPS, fotos</li>
        <li><strong>Dados técnicos:</strong> informações para elaboração de PTAM e TVI</li>
    </ul>
    
    <h2>2. Finalidade do Uso</h2>
    <p>Os dados são utilizados exclusivamente para:</p>
    <ul>
        <li>Elaboração de laudos técnicos de avaliação imobiliária</li>
        <li>Emissão de certidões negativas de débito (CND)</li>
        <li>Geração de documentos PDF/DOCX para partes interessadas</li>
        <li>Comunicação com clientes sobre serviços contratados</li>
    </ul>
    
    <h2>3. Armazenamento e Segurança</h2>
    <p>Seus dados são armazenados em servidores seguros na Railway (cloud computing), com criptografia em trânsito (HTTPS/TLS) e acesso restrito apenas aos profissionais credenciados da Romatec.</p>
    
    <h2>4. Compartilhamento</h2>
    <p>Não vendemos nem compartilhamos dados pessoais com terceiros, exceto:</p>
    <ul>
        <li>Quando exigido por lei ou ordem judicial</li>
        <li>Para cumprimento de obrigações regulatórias (INCRA, CFTMA)</li>
        <li>Com consentimento expresso do titular</li>
    </ul>
    
    <h2>5. Direitos do Titular (LGPD)</h2>
    <p>Você tem direito a:</p>
    <ul>
        <li>Acessar seus dados pessoais</li>
        <li>Corrigir dados incompletos ou desatualizados</li>
        <li>Solicitar exclusão (direito ao esquecimento)</li>
        <li>Revogar consentimento</li>
        <li>Portabilidade dos dados</li>
    </ul>
    
    <h2>6. Exclusão de Dados</h2>
    <p>Para solicitar exclusão de dados pessoais, entre em contato pelo e-mail abaixo. A exclusão será processada em até 30 dias, conforme prazo legal.</p>
    
    <div class="contact">
        <h2>Contato</h2>
        <p><strong>Responsável:</strong> José Romário P. Bezerra</p>
        <p><strong>E-mail:</strong> contato@consultoriaromatec.com.br</p>
        <p><strong>Telefone:</strong> (99) 9 9181-1246</p>
        <p><strong>Endereço:</strong> Açailândia, MA — CEP 65940-000</p>
    </div>
</body>
</html>"""

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
    # Auto-seed TVI models if collection is empty
    try:
        from db import get_db
        db = get_db()
        col = db.vistoria_models
        count = await col.count_documents({})
        if count == 0:
            logger.info("Seeding TVI models...")
            from seed_tvi_models import ALL_MODELOS
            import uuid
            from datetime import datetime
            for modelo in ALL_MODELOS:
                doc = {**modelo, "id": str(uuid.uuid4()), "ativo": True, "created_at": datetime.utcnow()}
                await col.insert_one(doc)
            logger.info(f"TVI: {len(ALL_MODELOS)} modelos inseridos")
        else:
            logger.info(f"TVI: {count} modelos já existem, skip seed")
    except Exception as e:
        logger.error(f"Erro no auto-seed TVI: {e}")


@app.on_event("shutdown")
async def shutdown():
    await close_db()
