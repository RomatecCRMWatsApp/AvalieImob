# @module server — Ponto de entrada: cria app FastAPI, registra routers e configura middlewares
"""RomaTec AvalieImob — FastAPI backend."""
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import logging
import os
import sys

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("romatec")


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if raw.strip():
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "https://www.romatecavalieimob.com.br",
        "https://romatecavalieimob.com.br",
        "https://avalieimob-production.up.railway.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

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

seen_prefixes = set()
for router in all_routers:
    api.include_router(router)
    prefix = router.prefix or "/"
    if prefix not in seen_prefixes:
        seen_prefixes.add(prefix)
        logger.info("Router registered: %s (%d routes)", prefix, len(router.routes))

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
            "package_name": "br.com.romatecavalieimob.www.twa",
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

# ── SEO: sitemap.xml e robots.txt ────────────────────────────────────
from fastapi.responses import Response as _Response
from datetime import datetime as _datetime

@app.get("/sitemap.xml")
async def sitemap():
    """Sitemap dinâmico para indexação pelo Google.
    Plano SEO v1.0 — Maio/2026: lista todas as páginas públicas com
    prioridade e changefreq ajustados conforme estratégia de conteúdo.
    """
    hoje = _datetime.utcnow().strftime("%Y-%m-%d")
    base = "https://www.romatecavalieimob.com.br"
    # (path, priority, changefreq)
    paginas = [
        ("/",                            "1.0", "weekly"),
        ("/sobre",                       "0.8", "monthly"),
        ("/planos",                      "0.9", "monthly"),
        ("/servicos/ptam",               "0.9", "monthly"),
        ("/servicos/laudo-tecnico",      "0.9", "monthly"),
        ("/servicos/avaliacao-rural",    "0.9", "monthly"),
        ("/servicos/avaliacao-garantia", "0.9", "monthly"),
        ("/servicos/avaliacao-urbana",   "0.9", "monthly"),
        ("/blog",                        "0.8", "daily"),
        ("/blog/como-fazer-ptam-passo-a-passo-nbr-14653",          "0.8", "monthly"),
        ("/blog/diferenca-ptam-laudo-avaliacao-imobiliaria",        "0.8", "monthly"),
        ("/blog/avaliacao-imovel-rural-nbr-14653-3-guia-completo",  "0.8", "monthly"),
        ("/blog/como-calcular-valor-liquidacao-forcada-vlf",        "0.8", "monthly"),
        ("/contato",                     "0.7", "monthly"),
        ("/cadastro",                    "0.8", "monthly"),
        ("/login",                       "0.6", "monthly"),
        ("/privacidade",                 "0.3", "yearly"),
    ]
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for path, prio, freq in paginas:
        loc = f"{base}{path}"
        parts.append(
            f'  <url><loc>{loc}</loc><lastmod>{hoje}</lastmod>'
            f'<changefreq>{freq}</changefreq><priority>{prio}</priority>'
            f'<xhtml:link rel="alternate" hreflang="pt-BR" href="{loc}"/>'
            f'<xhtml:link rel="alternate" hreflang="x-default" href="{loc}"/>'
            f'</url>'
        )
    parts.append('</urlset>')
    xml = "\n".join(parts)
    return _Response(content=xml, media_type="application/xml")

@app.get("/robots.txt")
async def robots():
    """robots.txt via backend. Bloqueia áreas de aplicação (dashboard, api,
    fluxos autenticados) e libera tudo o que é público pra indexação."""
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /dashboard/\n"
        "Disallow: /api/\n"
        "Disallow: /reset-senha\n"
        "Disallow: /*?token=\n"
        "Disallow: /*?reset=\n"
        "\n"
        "Sitemap: https://www.romatecavalieimob.com.br/sitemap.xml\n"
    )
    return _Response(content=content, media_type="text/plain")

# ── IndexNow (Bing/Yandex) ───────────────────────────────────────────
# Plano SEO v1.0 — Maio/2026. Chave gerada no Bing Webmaster Tools.
# Bing valida a chave acessando https://dominio/{KEY}.txt e o conteudo
# precisa ser exatamente a chave (texto puro). Tambem servimos no path
# raiz padrao do protocolo IndexNow.
INDEXNOW_KEY = "4d342968679b48f4817f345f7baa2881"

@app.get("/" + INDEXNOW_KEY + ".txt")
async def indexnow_key_file():
    return _Response(content=INDEXNOW_KEY, media_type="text/plain")

@app.post("/api/seo/indexnow-ping")
async def indexnow_ping(payload: dict):
    """Notifica Bing/Yandex via IndexNow sobre URLs novas ou atualizadas.
    Body: { "urls": ["https://www.romatecavalieimob.com.br/blog/xyz", ...] }
    Util pra disparar manualmente quando publicar artigo novo no blog.
    """
    import httpx
    urls = payload.get("urls") or []
    if not urls:
        return {"ok": False, "error": "passe ao menos 1 url"}
    body = {
        "host": "www.romatecavalieimob.com.br",
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://www.romatecavalieimob.com.br/{INDEXNOW_KEY}.txt",
        "urlList": urls,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post("https://api.indexnow.org/IndexNow", json=body)
            return {"ok": r.status_code in (200, 202), "status": r.status_code, "submitted": len(urls)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── React SPA static files ───────────────────────────────────────────
import pathlib as _pathlib
_frontend_build = _pathlib.Path(__file__).parent.parent / "frontend" / "build"
if _frontend_build.exists():
    from fastapi.staticfiles import StaticFiles
    from starlette.responses import FileResponse

    app.mount("/static", StaticFiles(directory=str(_frontend_build / "static")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Nunca servir arquivos internos do react-snap como rotas
        if full_path in ("200.html", "404.html") or full_path.startswith("_"):
            return FileResponse(str(_frontend_build / "index.html"))
        file_path = _frontend_build / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_build / "index.html"))

# ── Middlewares (ordem importa: após rotas, antes do startup) ────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Lifecycle ────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    init_db()
    logger.info("MongoDB conectado")
    # Auto-seed TVI é opcional e deve ser explicitamente habilitado.
    enable_tvi_autoseed = os.getenv("ENABLE_TVI_AUTOSEED", "").strip().lower() in {"1", "true", "yes", "on"}
    if not enable_tvi_autoseed:
        logger.info("TVI auto-seed desabilitado (ENABLE_TVI_AUTOSEED != true)")
        return

    # v2 campos profissionais 45 modelos — ao habilitar, dropa e reinsere.
    try:
        db = get_db()
        col = db.vistoria_models
        await col.drop()
        logger.info("vistoria_models: collection dropada para reinserção v2")
        from seed_tvi_models import ALL_MODELOS
        import uuid
        from datetime import datetime
        for modelo in ALL_MODELOS:
            doc = {**modelo, "ativo": True, "created_at": datetime.utcnow()}
            if not modelo.get("id"):
                doc["id"] = str(uuid.uuid4())
            await col.insert_one(doc)
        logger.info(f"TVI: {len(ALL_MODELOS)} modelos inseridos (v2)")
    except Exception as e:
        logger.error(f"Erro no auto-seed TVI: {e}")


@app.on_event("shutdown")
async def shutdown():
    await close_db()
