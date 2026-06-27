# Documentos Externos (`doc-ext`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir upload de um PDF externo, cadastro de N signatários, posicionamento das assinaturas, coleta por desenho no WhatsApp, carimbo auditável e selo ICP-Brasil opcional do RT — reusando o motor existente sem tocar o fluxo de contratos.

**Architecture:** Módulo novo `documentos_externos` (coleção própria, uuid `id`, `user_id` isolation) que delega o trabalho pesado às funções já existentes (`assinatura_cliente_carimbo`, `pdf_preview`, `marca_dagua`, `zapi_service`, `r2_storage`) e ao pipeline ICP de `routes/assinatura.py`. As únicas edições em arquivos de produção são **aditivas**: um branch `doc-ext` no ICP e duas funções novas no módulo de carimbo. Nenhuma linha do fluxo de contratos é alterada.

**Tech Stack:** FastAPI · MongoDB (Motor async) · Pydantic v2 · pypdf · PyMuPDF · ReportLab · Z-API · React CRA/JSX · Tailwind · pytest (testes de função pura; rotas verificadas por import + `yarn build`).

**Convenções do repo (obrigatórias):** rotas sob `/api` em `backend/routes/`; auth `Depends(get_active_subscriber)` → `uid: str`; `db=Depends(get_db)`; `serialize_doc` para resposta; toda query inclui `{"user_id": uid}`; numeração via `db.counters.find_one_and_update($inc)`; **NUNCA** `import * as Icons from 'lucide-react'` (quebra no iOS — usar import nomeado). Testes existentes são funções puras (sem mongo) — seguir o mesmo padrão (`backend/tests/`).

**Comandos base:**
- Testes backend: a partir de `backend/`: `python -m pytest tests/test_documentos_externos.py -v`
- Import-check de rota: a partir de `backend/`: `python -c "import routes.documentos_externos, routes.documentos_externos_publico; print('ok')"`
- Build frontend: a partir de `frontend/`: `yarn build`

---

## File Structure

**Novos (backend):**
- `backend/models/documento_externo.py` — modelos Pydantic + helpers puros (`gerar_codigo` placeholder, `recalcular_status`).
- `backend/services/documento_externo_service.py` — orquestração fina (preparar/posicionar/processar-carimbo/distribuir), Z-API e R2.
- `backend/routes/documentos_externos.py` — rotas autenticadas (CRUD + signatários + preparar/posicionar/reenviar/status/distribuir).
- `backend/routes/documentos_externos_publico.py` — rotas públicas (obter por token / assinar / recusar), rate-limited.
- `backend/tests/test_documentos_externos.py` — testes de função pura (modelo, status, carimbo multi/texto, numeração).

**Novos (frontend):**
- `frontend/src/components/dashboard/documentos-externos/DocumentosExternosList.jsx`
- `frontend/src/components/dashboard/documentos-externos/ModalUpload.jsx`
- `frontend/src/components/dashboard/documentos-externos/ModalSignatarios.jsx`
- `frontend/src/components/dashboard/documentos-externos/PositionerDocExt.jsx`

**Edições aditivas:**
- `backend/services/assinatura_cliente_carimbo.py` — `carimbar_texto_em_pagina`, `carimbar_multi` (novas funções; `carimbar_documento` intocada).
- `backend/routes/assinatura.py` — `_TIPO_COLECAO["doc-ext"]` + branch `doc-ext` em `_gerar_pdf`.
- `backend/routes/__init__.py` — registra 2 routers.
- `backend/server.py` — índices idempotentes.
- `frontend/src/lib/api.js` — `documentosExternosAPI`.
- `frontend/src/components/Sidebar.jsx` — item no bloco CONTRATOS (após "Assinar Documentos").
- `frontend/src/components/Dashboard.jsx` — rota `/dashboard/documentos-externos`.
- `frontend/src/App.js` — rota pública `/assinar-doc/:token`.
- `frontend/build-number.txt` + `CLAUDE.md` — versionamento.

---

## Task 1: Modelos Pydantic + helpers puros

**Files:**
- Create: `backend/models/documento_externo.py`
- Test: `backend/tests/test_documentos_externos.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_documentos_externos.py`:

```python
# Testes do módulo Documentos Externos — funções puras (sem mongo).
import io

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas

from models.documento_externo import (
    PosicaoAssinatura, Signatario, recalcular_status, novo_signatario,
)


def test_posicao_defaults_tipo_assinatura():
    p = PosicaoAssinatura(pagina=0, x_pt=10, y_pt=20, larg_pt=200, alt_pt=60)
    assert p.tipo == "assinatura"


def test_posicao_rejeita_tipo_invalido():
    with pytest.raises(Exception):
        PosicaoAssinatura(pagina=0, x_pt=0, y_pt=0, larg_pt=1, alt_pt=1, tipo="carimbo")


def test_novo_signatario_gera_id_e_token():
    s = novo_signatario({"nome": "Antônio", "cpf_cnpj": "12345678901",
                         "papel": "Vendedor", "whatsapp": "5599991204706"})
    assert s["id"] and s["token"] and s["status"] == "pendente"
    assert s["whatsapp"] == "5599991204706"


def test_recalcular_status_progressao():
    base = {"requer_icp_rt": True}
    assert recalcular_status({**base, "signatarios": []}) == "rascunho"
    s_pend = [{"status": "enviado"}, {"status": "enviado"}]
    assert recalcular_status({**base, "signatarios": s_pend}) == "aguardando"
    s_parc = [{"status": "assinado"}, {"status": "enviado"}]
    assert recalcular_status({**base, "signatarios": s_parc}) == "parcial"
    s_all = [{"status": "assinado"}, {"status": "assinado"}]
    assert recalcular_status({**base, "signatarios": s_all}) == "clientes_ok"


def test_recalcular_status_sem_icp_finaliza_direto():
    s_all = [{"status": "assinado"}]
    assert recalcular_status({"requer_icp_rt": False, "signatarios": s_all}) == "finalizado"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_documentos_externos.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'models.documento_externo'`

- [ ] **Step 3: Write the model**

Create `backend/models/documento_externo.py`:

```python
# @module models.documento_externo — Documentos Externos (doc-ext): assinatura de PDF
# enviado por upload, via WhatsApp + ICP. Pydantic v2 + helpers puros (sem mongo).
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field

from services.contrato_exclusividade_assinatura import gerar_token

TipoPosicao = Literal["assinatura", "rubrica", "data", "nome_extenso"]
StatusSignatario = Literal["pendente", "enviado", "assinado", "recusado"]
StatusDoc = Literal["rascunho", "aguardando", "parcial", "clientes_ok", "finalizado", "cancelado"]


class PosicaoAssinatura(BaseModel):
    pagina: int                       # 0-indexed (igual ao "Posicionar")
    x_pt: float
    y_pt: float
    larg_pt: float
    alt_pt: float
    tipo: TipoPosicao = "assinatura"
    label: Optional[str] = None


class Signatario(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    nome: str
    cpf_cnpj: str = ""
    papel: str = "Signatário"          # texto livre c/ sugestões no front
    whatsapp: str = ""
    email: Optional[str] = None
    posicoes: List[PosicaoAssinatura] = Field(default_factory=list)
    token: str = Field(default_factory=gerar_token)
    status: StatusSignatario = "pendente"
    assinado_em: Optional[datetime] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    geo_lat: Optional[float] = None
    geo_lng: Optional[float] = None
    traco_b64: Optional[str] = None


class DocumentoExternoCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    valor_referencia: Optional[float] = None
    requer_icp_rt: bool = True


def _so_dig(v: Any) -> str:
    return "".join(filter(str.isdigit, str(v or "")))


def novo_signatario(data: dict) -> dict:
    """Cria o dict de um signatário a partir do input do front (id/token/status preenchidos)."""
    return Signatario(
        nome=str(data.get("nome") or "").strip() or "Signatário",
        cpf_cnpj=_so_dig(data.get("cpf_cnpj")),
        papel=str(data.get("papel") or "Signatário").strip(),
        whatsapp=_so_dig(data.get("whatsapp") or data.get("telefone")),
        email=(data.get("email") or None),
    ).model_dump(mode="json")


def recalcular_status(doc: dict) -> StatusDoc:
    """Status global derivado dos signatários. requer_icp_rt define se 'todos assinaram'
    vira clientes_ok (falta ICP) ou finalizado direto."""
    sigs = doc.get("signatarios") or []
    if not sigs:
        return "rascunho"
    total = len(sigs)
    assinados = sum(1 for s in sigs if s.get("status") == "assinado")
    if assinados == 0:
        return "aguardando"
    if assinados < total:
        return "parcial"
    return "clientes_ok" if doc.get("requer_icp_rt") else "finalizado"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_documentos_externos.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/models/documento_externo.py backend/tests/test_documentos_externos.py
git commit -m "feat(doc-ext): modelo Pydantic + helpers de status/signatário"
```

---

## Task 2: Carimbo multi-signatário com tipos de posição (aditivo)

**Files:**
- Modify: `backend/services/assinatura_cliente_carimbo.py` (acrescenta 2 funções; nada existente é alterado)
- Test: `backend/tests/test_documentos_externos.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_documentos_externos.py`:

```python
def _pdf_uma_pagina() -> bytes:
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.drawString(72, 720, "Documento de teste")
    c.showPage()
    c.save()
    return buf.getvalue()


def _png_1x1() -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGBA", (4, 4), (0, 0, 0, 255)).save(b, format="PNG")
    return b.getvalue()


def test_carimbar_multi_estampa_e_anexa_folha():
    from services.assinatura_cliente_carimbo import carimbar_multi
    from pypdf import PdfReader
    pdf = _pdf_uma_pagina()
    sigs = [{
        "nome": "Antônio", "cpf": "12345678901", "role": "Vendedor",
        "assinado_em": None, "ip": "1.2.3.4", "user_agent": "UA",
        "traco_png": _png_1x1(),
        "posicoes": [
            {"pagina": 0, "x_pt": 60, "y_pt": 80, "larg_pt": 180, "alt_pt": 50, "tipo": "assinatura"},
            {"pagina": 0, "x_pt": 60, "y_pt": 140, "larg_pt": 180, "alt_pt": 20, "tipo": "nome_extenso"},
            {"pagina": 0, "x_pt": 300, "y_pt": 80, "larg_pt": 120, "alt_pt": 20, "tipo": "data"},
        ],
    }]
    out, h = carimbar_multi(pdf, sigs)
    assert out.startswith(b"%PDF-") and len(h) == 64
    # original 1 pág + folha de autoria = 2 páginas
    assert len(PdfReader(io.BytesIO(out)).pages) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_documentos_externos.py::test_carimbar_multi_estampa_e_anexa_folha -v`
Expected: FAIL — `ImportError: cannot import name 'carimbar_multi'`

- [ ] **Step 3: Add the new functions**

Append to `backend/services/assinatura_cliente_carimbo.py` (NÃO altere `carimbar_documento`):

```python
def _overlay_texto(page_w: float, page_h: float, rect: Tuple[float, float, float, float],
                   texto: str) -> bytes:
    """Página transparente (tamanho da página alvo) com `texto` centralizado verticalmente
    no rect, fonte auto-ajustada p/ caber na largura. Usado p/ tipos data/nome_extenso."""
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as _canvas
    from reportlab.pdfbase.pdfmetrics import stringWidth

    x0, y0, x1, y1 = rect
    box_w = max(1.0, (x1 - x0) - 8)
    texto = (texto or "").strip()
    size = 10.0
    while size > 5.0 and stringWidth(texto, "Helvetica", size) > box_w:
        size -= 0.5
    buf = io.BytesIO()
    c = _canvas.Canvas(buf, pagesize=(page_w, page_h))
    c.setFont("Helvetica", size)
    c.setFillColor(colors.HexColor("#1A1A1A"))
    c.drawString(x0 + 4, y0 + ((y1 - y0) - size) / 2 + 1, texto[:200])
    c.showPage()
    c.save()
    return buf.getvalue()


def carimbar_texto_em_pagina(pdf_bytes: bytes, pagina_idx: int,
                             rect: Tuple[float, float, float, float], texto: str) -> bytes:
    """Carimba TEXTO no rect (pontos, origem inf-esq) da página 0-based. Para data/nome."""
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(io.BytesIO(pdf_bytes))
    total = len(reader.pages)
    if pagina_idx < 0 or pagina_idx >= total:
        raise ValueError(f"Página de âncora inválida: {pagina_idx} (0..{total - 1})")
    mb = reader.pages[pagina_idx].mediabox
    overlay = _overlay_texto(float(mb.width), float(mb.height), rect, texto)
    overlay_page = PdfReader(io.BytesIO(overlay)).pages[0]
    writer = PdfWriter()
    for i, p in enumerate(reader.pages):
        if i == pagina_idx:
            try:
                p.merge_page(overlay_page)
            except Exception as e:
                logger.warning("Overlay de texto falhou na página %s (%s)", i, e)
        writer.add_page(p)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def carimbar_multi(pdf_bytes: bytes, signatarios: List[dict]) -> Tuple[bytes, str]:
    """Carimba N signatários, cada um com VÁRIAS posições de tipos distintos, e anexa a
    folha de autoria. `signatarios`: [{nome, cpf, role, traco_png, ip, geo_lat, geo_lng,
    user_agent, assinado_em, posicoes:[{pagina,x_pt,y_pt,larg_pt,alt_pt,tipo}]}].
    Retorna (pdf_carimbado, sha256)."""
    out = pdf_bytes
    for sig in signatarios:
        nome = sig.get("nome") or ""
        traco = sig.get("traco_png")
        ass_em = sig.get("assinado_em")
        ass_txt = ass_em.strftime("%d/%m/%Y %H:%M:%S") if isinstance(ass_em, datetime) else ""
        for pos in (sig.get("posicoes") or []):
            try:
                x = float(pos.get("x_pt", 0)); y = float(pos.get("y_pt", 0))
                w = float(pos.get("larg_pt", 0)); h = float(pos.get("alt_pt", 0))
                rect = (x, y, x + w, y + h)
                pg = int(pos.get("pagina", 0))
                tipo = pos.get("tipo") or "assinatura"
                if tipo in ("assinatura", "rubrica") and traco:
                    legenda = f"Assinado eletronicamente · {nome}" if tipo == "assinatura" else ""
                    out = carimbar_traco_em_pagina(out, pg, rect, traco, legenda)
                elif tipo == "data":
                    out = carimbar_texto_em_pagina(out, pg, rect, ass_txt)
                elif tipo == "nome_extenso":
                    out = carimbar_texto_em_pagina(out, pg, rect, nome.upper())
            except Exception:
                logger.warning("Falha ao carimbar posição de %s", nome, exc_info=True)
    out = _append_pagina(out, _folha_autoria(signatarios))
    return out, hashlib.sha256(out).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_documentos_externos.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/services/assinatura_cliente_carimbo.py backend/tests/test_documentos_externos.py
git commit -m "feat(doc-ext): carimbar_multi + carimbar_texto_em_pagina (tipos de posição), aditivo"
```

---

## Task 3: Service de orquestração (numeração, Z-API, carimbo, distribuição)

**Files:**
- Create: `backend/services/documento_externo_service.py`
- Test: `backend/tests/test_documentos_externos.py`

O service concentra a lógica reutilizável e testável; as rotas (Task 4-6) só fazem I/O HTTP.

- [ ] **Step 1: Write the failing test (numeração pura)**

Append to `backend/tests/test_documentos_externos.py`:

```python
def test_formatar_codigo():
    from services.documento_externo_service import formatar_codigo
    assert formatar_codigo(2026, 1) == "DOCEXT-2026-0001"
    assert formatar_codigo(2026, 42) == "DOCEXT-2026-0042"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_documentos_externos.py::test_formatar_codigo -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.documento_externo_service'`

- [ ] **Step 3: Write the service**

Create `backend/services/documento_externo_service.py`:

```python
# @module services.documento_externo_service — orquestração do módulo Documentos Externos.
# Reusa o motor existente: carimbo (carimbar_multi), preview, Z-API, R2. NÃO toca contratos.
import asyncio
import base64
import logging
from datetime import datetime

from pymongo import ReturnDocument

from models.documento_externo import recalcular_status

logger = logging.getLogger("romatec")

COL = "documentos_externos"


def formatar_codigo(ano: int, seq: int) -> str:
    return f"DOCEXT-{ano}-{seq:04d}"


async def proximo_codigo(db) -> str:
    ano = datetime.utcnow().year
    res = await db.counters.find_one_and_update(
        {"_id": f"docext_{ano}"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=ReturnDocument.AFTER)
    return formatar_codigo(ano, res["seq"])


# ── Z-API (reusa a config do owner via assinatura_cliente helpers) ───────────────
async def zapi_cfg(db, uid: str) -> dict:
    from services.integracoes_util import carregar_integracoes
    cfg = await carregar_integracoes(db, uid)
    if not cfg or not cfg.get("zapi_instance_id") or not cfg.get("zapi_token"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Z-API não configurada em Integrações.")
    return cfg


async def enviar_texto(cfg: dict, phone: str, message: str):
    from services import zapi_service
    return await zapi_service.send_text(
        instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
        security_token=cfg.get("zapi_security_token"), phone=phone, message=message)


async def enviar_pdf(cfg: dict, phone: str, pdf_bytes: bytes, filename: str, caption: str = ""):
    from services import zapi_service
    return await zapi_service.send_document_pdf(
        instance_id=cfg["zapi_instance_id"], token=cfg["zapi_token"],
        security_token=cfg.get("zapi_security_token"), phone=phone,
        pdf_bytes=pdf_bytes, filename=filename, caption=caption)


async def atualizar_status(db, doc_id: str):
    doc = await db[COL].find_one({"id": doc_id})
    if not doc:
        return None
    novo = recalcular_status(doc)
    await db[COL].update_one({"id": doc_id},
                             {"$set": {"status": novo, "updated_at": datetime.utcnow()}})
    return novo


async def processar_carimbo(db, doc: dict):
    """Quando TODOS os signatários assinaram: baixa o PDF-base do R2, carimba os traços +
    folha de autoria via carimbar_multi, sobe o intermediário, e distribui se NÃO exigir ICP."""
    from services import r2_storage
    from services.assinatura_cliente_carimbo import carimbar_multi
    base = await asyncio.to_thread(r2_storage.download_bytes, doc["pdf_key"])
    sigs = []
    for s in doc.get("signatarios", []):
        if not s.get("traco_b64"):
            continue
        try:
            png = base64.b64decode(s["traco_b64"])
        except Exception:
            continue
        sigs.append({
            "nome": s.get("nome"), "cpf": s.get("cpf_cnpj"), "role": s.get("papel"),
            "traco_png": png, "ip": s.get("ip"), "geo_lat": s.get("geo_lat"),
            "geo_lng": s.get("geo_lng"), "user_agent": s.get("user_agent"),
            "assinado_em": s.get("assinado_em"), "posicoes": s.get("posicoes") or [],
        })
    final, _h = await asyncio.to_thread(carimbar_multi, base, sigs)
    key_inter = f"documentos-externos/{doc['user_id']}/{doc['id']}_intermediario.pdf"
    await asyncio.to_thread(r2_storage.upload_bytes, final, key_inter, "application/pdf")
    await db[COL].update_one({"id": doc["id"]}, {"$set": {"pdf_key_intermediario": key_inter}})
    doc["pdf_key_intermediario"] = key_inter
    await atualizar_status(db, doc["id"])
    if not doc.get("requer_icp_rt"):
        await distribuir(db, doc, final, "clientes")
    return key_inter


async def distribuir(db, doc: dict, pdf_bytes: bytes, etapa: str):
    """Envia o PDF (intermediário ou final) a todos os signatários por WhatsApp."""
    try:
        cfg = await zapi_cfg(db, doc["user_id"])
    except Exception:
        logger.warning("Z-API indisponível p/ distribuir doc-ext %s", doc.get("id"))
        return
    rotulo = "documento FINAL assinado (todas as assinaturas + ICP)" if etapa == "final" \
        else "documento assinado por todas as partes"
    for s in doc.get("signatarios", []):
        fone = "".join(filter(str.isdigit, str(s.get("whatsapp") or "")))
        if not fone:
            continue
        try:
            await enviar_pdf(cfg, fone, pdf_bytes, f"{doc.get('codigo', 'documento')}_assinado",
                             f"Segue o {rotulo}. Obrigado! — Romatec Consultoria Total")
        except Exception:
            logger.warning("Falha ao distribuir doc-ext p/ %s", fone, exc_info=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_documentos_externos.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/services/documento_externo_service.py backend/tests/test_documentos_externos.py
git commit -m "feat(doc-ext): service de orquestração (numeração, Z-API, carimbo, distribuição)"
```

---

## Task 4: Rotas autenticadas — CRUD + upload + signatários

**Files:**
- Create: `backend/routes/documentos_externos.py`

- [ ] **Step 1: Write the route file**

Create `backend/routes/documentos_externos.py`:

```python
# @module routes.documentos_externos — Documentos Externos (doc-ext): upload de PDF arbitrário,
# N signatários, posicionar, enviar por WhatsApp, ICP opcional do RT. Isolado por user_id.
import asyncio
import hashlib
import io
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from db import get_db
from dependencies import get_active_subscriber, serialize_doc
from models.documento_externo import novo_signatario, recalcular_status
from services import r2_storage
from services.documento_externo_service import COL, proximo_codigo
from services.upload_security import detect_content_type, normalize_filename

router = APIRouter(prefix="/documentos-externos", tags=["documentos-externos"])
logger = logging.getLogger("romatec")
_MAX_BYTES = 25 * 1024 * 1024


def _contar_paginas(pdf_bytes: bytes) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    except Exception:
        return 0


async def _carregar(db, doc_id: str, uid: str) -> dict:
    doc = await db[COL].find_one({"id": doc_id, "user_id": uid})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return doc


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    titulo: str = Form(...),
    descricao: str = Form(""),
    requer_icp_rt: bool = Form(True),
    uid: str = Depends(get_active_subscriber),
    db=Depends(get_db),
):
    conteudo = await file.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(conteudo) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"Arquivo excede 25 MB ({len(conteudo)/1024/1024:.1f} MB).")
    if detect_content_type(conteudo) != "application/pdf" or not conteudo.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF válido.")

    doc_id = uuid.uuid4().hex
    nome = normalize_filename(file.filename, fallback="documento")
    if not nome.lower().endswith(".pdf"):
        nome = f"{nome}.pdf"
    pdf_key = f"documentos-externos/{uid}/{doc_id}.pdf"
    try:
        await asyncio.to_thread(r2_storage.upload_bytes, conteudo, pdf_key, "application/pdf", "private, max-age=0")
    except Exception as e:  # noqa: BLE001
        logger.error("Falha ao subir doc-ext ao R2: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao armazenar o documento.")

    reg = {
        "id": doc_id, "user_id": uid, "codigo": await proximo_codigo(db),
        "titulo": titulo.strip() or nome, "descricao": (descricao or "").strip() or None,
        "requer_icp_rt": bool(requer_icp_rt),
        "pdf_key": pdf_key, "pdf_hash_sha256": hashlib.sha256(conteudo).hexdigest(),
        "nome_arquivo": nome, "paginas": _contar_paginas(conteudo), "tamanho": len(conteudo),
        "signatarios": [], "pdf_key_intermediario": None, "pdf_key_final": None,
        "status": "rascunho", "historico": [{"em": datetime.utcnow(), "tipo": "criado"}],
        "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
    }
    await db[COL].insert_one(reg)
    return serialize_doc(reg)


@router.get("")
async def listar(uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    docs = await db[COL].find({"user_id": uid}).sort("created_at", -1).to_list(length=500)
    return [serialize_doc(d) for d in docs]


@router.get("/{doc_id}")
async def obter(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return serialize_doc(await _carregar(db, doc_id, uid))


@router.patch("/{doc_id}")
async def editar(doc_id: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await _carregar(db, doc_id, uid)
    campos = {k: payload[k] for k in ("titulo", "descricao", "requer_icp_rt", "valor_referencia") if k in payload}
    campos["updated_at"] = datetime.utcnow()
    await db[COL].update_one({"id": doc_id, "user_id": uid}, {"$set": campos})
    return serialize_doc(await _carregar(db, doc_id, uid))


@router.delete("/{doc_id}")
async def excluir(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, doc_id, uid)
    for key in (doc.get("pdf_key"), doc.get("pdf_key_intermediario"), doc.get("pdf_key_final")):
        if key:
            try:
                await asyncio.to_thread(r2_storage.delete_object, key)
            except Exception:
                pass
    await db[COL].delete_one({"id": doc_id, "user_id": uid})
    try:
        await db["assinaturas_pdf"].delete_many({"doc_tipo": "doc-ext", "doc_id": doc_id})
    except Exception:
        pass
    return {"ok": True}


# ── PDFs ──────────────────────────────────────────────────────────────────────
async def _servir_pdf(db, doc_id: str, uid: str, campo: str, nome: str):
    doc = await _carregar(db, doc_id, uid)
    key = doc.get(campo) or doc.get("pdf_key")
    try:
        pdf = await asyncio.to_thread(r2_storage.download_bytes, key)
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo indisponível.")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{nome}"', "Cache-Control": "no-store"})


@router.get("/{doc_id}/pdf-original")
async def pdf_original(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await _servir_pdf(db, doc_id, uid, "pdf_key", "documento.pdf")


@router.get("/{doc_id}/pdf-intermediario")
async def pdf_intermediario(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    return await _servir_pdf(db, doc_id, uid, "pdf_key_intermediario", "documento_clientes.pdf")


@router.get("/{doc_id}/pdf-final")
async def pdf_final(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Serve o PDF ASSINADO ICP se houver; senão o intermediário; senão o original."""
    from routes.assinatura import _load_assinatura_bytes
    assinado, _ = await _load_assinatura_bytes(db, "doc-ext", doc_id)
    if assinado:
        return Response(content=assinado, media_type="application/pdf",
                        headers={"Content-Disposition": 'inline; filename="documento_final.pdf"', "Cache-Control": "no-store"})
    return await _servir_pdf(db, doc_id, uid, "pdf_key_intermediario", "documento_final.pdf")


# ── Signatários ─────────────────────────────────────────────────────────────────
@router.post("/{doc_id}/signatarios")
async def add_signatario(doc_id: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    await _carregar(db, doc_id, uid)
    sig = novo_signatario(payload)
    await db[COL].update_one({"id": doc_id, "user_id": uid},
                             {"$push": {"signatarios": sig}, "$set": {"updated_at": datetime.utcnow()}})
    return sig


@router.patch("/{doc_id}/signatarios/{sid}")
async def edit_signatario(doc_id: str, sid: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, doc_id, uid)
    sig = next((s for s in doc.get("signatarios", []) if s.get("id") == sid), None)
    if not sig:
        raise HTTPException(status_code=404, detail="Signatário não encontrado.")
    if sig.get("status") == "assinado":
        raise HTTPException(status_code=409, detail="Signatário já assinou — não pode editar.")
    upd = {}
    for k in ("nome", "papel"):
        if k in payload:
            upd[f"signatarios.$.{k}"] = str(payload[k] or "")
    for k in ("cpf_cnpj", "whatsapp"):
        if k in payload:
            upd[f"signatarios.$.{k}"] = "".join(filter(str.isdigit, str(payload[k] or "")))
    if "email" in payload:
        upd["signatarios.$.email"] = payload["email"] or None
    upd["updated_at"] = datetime.utcnow()
    await db[COL].update_one({"id": doc_id, "user_id": uid, "signatarios.id": sid}, {"$set": upd})
    return {"ok": True}


@router.delete("/{doc_id}/signatarios/{sid}")
async def del_signatario(doc_id: str, sid: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, doc_id, uid)
    sig = next((s for s in doc.get("signatarios", []) if s.get("id") == sid), None)
    if sig and sig.get("status") == "assinado":
        raise HTTPException(status_code=409, detail="Signatário já assinou — não pode remover.")
    await db[COL].update_one({"id": doc_id, "user_id": uid},
                             {"$pull": {"signatarios": {"id": sid}}, "$set": {"updated_at": datetime.utcnow()}})
    return {"ok": True}
```

- [ ] **Step 2: Import-check**

Run (from `backend/`): `python -c "import routes.documentos_externos; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Run the test suite (no regressions)**

Run: `python -m pytest tests/test_documentos_externos.py -v`
Expected: PASS (7 passed)

- [ ] **Step 4: Commit**

```bash
git add backend/routes/documentos_externos.py
git commit -m "feat(doc-ext): rotas CRUD + upload + signatários"
```

---

## Task 5: Rotas preparar / posicionar / reenviar / status

**Files:**
- Modify: `backend/routes/documentos_externos.py` (acrescenta rotas ao mesmo router)

- [ ] **Step 1: Append the orchestration routes**

Append to `backend/routes/documentos_externos.py`:

```python
# ── Preparar / Posicionar / Enviar ───────────────────────────────────────────────
@router.post("/{doc_id}/preparar")
async def preparar(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Renderiza as páginas do PDF original p/ o RT posicionar as caixas, e pré-carrega a
    assinatura visual salva do RT (ou gera uma cursiva do nome)."""
    doc = await _carregar(db, doc_id, uid)
    pdf = await asyncio.to_thread(r2_storage.download_bytes, doc["pdf_key"])
    from services.pdf_preview import renderizar_paginas
    paginas = await asyncio.to_thread(renderizar_paginas, pdf)
    perfil = await db.perfil_avaliador.find_one({"user_id": uid}) or {}
    rt_nome = perfil.get("nome") or "Responsável Técnico"
    rt_b64 = perfil.get("assinatura_visual_b64")
    rt_padrao = False
    if not rt_b64:
        from services.assinatura_default import gerar_assinatura_nome_b64
        rt_b64 = await asyncio.to_thread(gerar_assinatura_nome_b64, rt_nome)
        rt_padrao = bool(rt_b64)
    return {"ok": True, "paginas": paginas, "signatarios": doc.get("signatarios", []),
            "rt": {"nome": rt_nome, "assinatura_b64": rt_b64, "assinatura_padrao": rt_padrao}}


@router.post("/{doc_id}/posicionar")
async def posicionar(doc_id: str, payload: dict, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Salva as posições por signatário, carimba o traço do RT na base (opção A), gera/dispara
    os links por WhatsApp. payload: {posicoes: {sid: [{pagina,x_pt,y_pt,larg_pt,alt_pt,tipo}]},
    rt_traco: 'data:image/png;base64,...', rt_ancora: {pagina,x_pt,...}}."""
    import base64
    from services.documento_externo_service import zapi_cfg, enviar_texto, enviar_pdf
    doc = await _carregar(db, doc_id, uid)
    sigs = doc.get("signatarios", [])
    if not sigs:
        raise HTTPException(status_code=422, detail="Cadastre ao menos um signatário.")
    pos_map = payload.get("posicoes") or {}
    faltam_pos = [s["nome"] for s in sigs if not (pos_map.get(s["id"]) or [])]
    if faltam_pos:
        raise HTTPException(status_code=422, detail=f"Posicione a assinatura de: {', '.join(faltam_pos)}")
    faltam_fone = [s["nome"] for s in sigs if not "".join(filter(str.isdigit, str(s.get("whatsapp") or "")))]
    if faltam_fone:
        raise HTTPException(status_code=422, detail=f"Informe o WhatsApp de: {', '.join(faltam_fone)}")

    # grava posições em cada signatário
    for s in sigs:
        s["posicoes"] = pos_map.get(s["id"], [])
        s["status"] = "enviado"

    # RT desenha + posiciona: carimba o traço do RT na base ANTES de enviar (opção A)
    rt_traco = payload.get("rt_traco") or ""
    rt_anc = payload.get("rt_ancora") or {}
    if rt_traco.startswith("data:image/png;base64,") and rt_anc:
        try:
            png = base64.b64decode(rt_traco.split(",", 1)[1])
            await db.perfil_avaliador.update_one(
                {"user_id": uid}, {"$set": {"assinatura_visual_b64": rt_traco.split(",", 1)[1]}}, upsert=True)
            base = await asyncio.to_thread(r2_storage.download_bytes, doc["pdf_key"])
            from services.assinatura_cliente_carimbo import carimbar_traco_em_pagina
            x = float(rt_anc.get("x_pt", 0)); y = float(rt_anc.get("y_pt", 0))
            w = float(rt_anc.get("larg_pt", 0)); h = float(rt_anc.get("alt_pt", 0))
            base = await asyncio.to_thread(carimbar_traco_em_pagina, base, int(rt_anc.get("pagina", 0)),
                                           (x, y, x + w, y + h), png, "Responsável Técnico")
            await asyncio.to_thread(r2_storage.upload_bytes, base, doc["pdf_key"], "application/pdf")
        except Exception:
            logger.warning("Falha ao carimbar assinatura do RT (doc-ext).", exc_info=True)

    await db[COL].update_one({"id": doc_id, "user_id": uid},
                             {"$set": {"signatarios": sigs, "updated_at": datetime.utcnow()}})
    await db[COL].update_one({"id": doc_id}, {"$set": {"status": recalcular_status({**doc, "signatarios": sigs})}})

    # minuta (marca d'água) p/ leitura + link por signatário
    from services.marca_dagua import aplicar_marca_dagua
    base_atual = await asyncio.to_thread(r2_storage.download_bytes, doc["pdf_key"])
    minuta = await asyncio.to_thread(aplicar_marca_dagua, base_atual, "MINUTA")
    cfg = await zapi_cfg(db, uid)
    from routes.assinatura_cliente import APP_URL
    links = []
    for s in sigs:
        url = f"{APP_URL}/assinar-doc/{s['token']}"
        primeiro = str(s.get("nome") or "").split(" ")[0]
        msg = (f"Olá, {primeiro}! A *Romatec Consultoria Total* enviou um documento para sua "
               f"assinatura eletrônica.\n\nLeia a *MINUTA* abaixo e assine com segurança neste link:\n{url}\n\n"
               f"Link pessoal, validade limitada (Lei 14.063/2020).")
        try:
            await enviar_texto(cfg, s["whatsapp"], msg)
            if minuta and minuta.startswith(b"%PDF-"):
                await enviar_pdf(cfg, s["whatsapp"], minuta, "minuta", "MINUTA (rascunho) — para leitura.")
        except Exception:
            logger.warning("Falha ao enviar link doc-ext p/ %s", s.get("whatsapp"), exc_info=True)
        links.append({"sid": s["id"], "nome": s["nome"], "url": url})
    return {"ok": True, "links": links}


@router.post("/{doc_id}/reenviar")
async def reenviar(doc_id: str, payload: dict = None, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Reenvia o link aos pendentes (telefones editáveis em payload.signatarios=[{id,whatsapp}])."""
    from services.documento_externo_service import zapi_cfg, enviar_texto
    doc = await _carregar(db, doc_id, uid)
    novos = {s.get("id"): "".join(filter(str.isdigit, str(s.get("whatsapp") or "")))
             for s in (payload or {}).get("signatarios", []) if s.get("id")}
    pendentes = [s for s in doc.get("signatarios", []) if s.get("status") != "assinado"]
    if not pendentes:
        raise HTTPException(status_code=400, detail="Nenhum signatário pendente.")
    cfg = await zapi_cfg(db, uid)
    from routes.assinatura_cliente import APP_URL
    enviados = 0
    for s in pendentes:
        fone = novos.get(s["id"]) or "".join(filter(str.isdigit, str(s.get("whatsapp") or "")))
        if not fone:
            continue
        if novos.get(s["id"]):
            await db[COL].update_one({"id": doc_id, "signatarios.id": s["id"]},
                                     {"$set": {"signatarios.$.whatsapp": fone}})
        url = f"{APP_URL}/assinar-doc/{s['token']}"
        try:
            await enviar_texto(cfg, fone, f"Olá! Reenvio do link para assinar:\n{url}")
            enviados += 1
        except Exception:
            logger.warning("Falha ao reenviar doc-ext p/ %s", fone, exc_info=True)
    return {"ok": True, "reenviados": enviados}


@router.get("/{doc_id}/sessao-status")
async def sessao_status(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    doc = await _carregar(db, doc_id, uid)
    sigs = [{"id": s["id"], "nome": s.get("nome"), "papel": s.get("papel"),
             "whatsapp": s.get("whatsapp"), "status": s.get("status"),
             "assinado_em": s.get("assinado_em")} for s in doc.get("signatarios", [])]
    assinados = sum(1 for s in sigs if s["status"] == "assinado")
    return {"ok": True, "status": doc.get("status"), "signatarios": sigs,
            "assinados": assinados, "total": len(sigs), "requer_icp_rt": doc.get("requer_icp_rt")}


@router.post("/{doc_id}/distribuir-final")
async def distribuir_final(doc_id: str, uid: str = Depends(get_active_subscriber), db=Depends(get_db)):
    """Após o ICP do RT, envia o PDF FINAL assinado a todos os signatários e marca finalizado.
    Chamado pelo frontend ao concluir a assinatura ICP."""
    from routes.assinatura import _load_assinatura_bytes
    from services.documento_externo_service import distribuir
    doc = await _carregar(db, doc_id, uid)
    assinado, _ = await _load_assinatura_bytes(db, "doc-ext", doc_id)
    if not assinado:
        raise HTTPException(status_code=400, detail="Nenhum PDF assinado (ICP) encontrado.")
    await db[COL].update_one({"id": doc_id, "user_id": uid},
                             {"$set": {"status": "finalizado", "pdf_final_assinado_em": datetime.utcnow()}})
    await distribuir(db, doc, assinado, "final")
    return {"ok": True}
```

- [ ] **Step 2: Import-check**

Run (from `backend/`): `python -c "import routes.documentos_externos; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/routes/documentos_externos.py
git commit -m "feat(doc-ext): preparar/posicionar/reenviar/status/distribuir-final"
```

---

## Task 6: Rotas públicas (assinar / recusar)

**Files:**
- Create: `backend/routes/documentos_externos_publico.py`

- [ ] **Step 1: Write the public router**

Create `backend/routes/documentos_externos_publico.py`:

```python
# @module routes.documentos_externos_publico — página pública de assinatura do doc-ext.
# SEM auth + rate-limit. O signatário desenha a assinatura (PNG) e consente; quando todos
# assinam, dispara o carimbo (service.processar_carimbo).
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db
from services.documento_externo_service import COL, atualizar_status, processar_carimbo

logger = logging.getLogger("romatec")
limiter = Limiter(key_func=get_remote_address)
router_publico = APIRouter(prefix="/publico/documentos-externos", tags=["Documentos Externos Público"])


def _sig(sessao: dict, token: str):
    return next((s for s in sessao.get("signatarios", []) if s.get("token") == token), None)


@router_publico.get("/{token}")
@limiter.limit("30/minute")
async def obter_por_token(token: str, request: Request, db=Depends(get_db)):
    doc = await db[COL].find_one({"signatarios.token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Link inválido")
    sig = _sig(doc, token)
    if not sig:
        raise HTTPException(status_code=404, detail="Link inválido")
    return {"ok": True, "nome": sig.get("nome"), "papel": sig.get("papel"),
            "titulo": doc.get("titulo"), "cpf_cnpj": sig.get("cpf_cnpj"),
            "ja_assinado": sig.get("status") == "assinado"}


@router_publico.post("/{token}")
@limiter.limit("10/minute")
async def assinar(token: str, payload: dict, request: Request, db=Depends(get_db)):
    doc = await db[COL].find_one({"signatarios.token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Link inválido")
    sig = _sig(doc, token)
    if not sig:
        raise HTTPException(status_code=404, detail="Link inválido")
    if sig.get("status") == "assinado":
        return {"ok": True, "ja_assinado": True}
    traco = payload.get("traco_base64") or ""
    if not traco.startswith("data:image/png;base64,"):
        raise HTTPException(status_code=400, detail="Assinatura (traço) inválida")
    if not payload.get("concordo"):
        raise HTTPException(status_code=400, detail="É necessário concordar para assinar")

    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "0.0.0.0")
    ua = (request.headers.get("user-agent") or "")[:255]
    await db[COL].update_one(
        {"id": doc["id"], "signatarios.token": token},
        {"$set": {
            "signatarios.$.status": "assinado", "signatarios.$.assinado_em": datetime.utcnow(),
            "signatarios.$.ip": ip, "signatarios.$.user_agent": ua,
            "signatarios.$.geo_lat": payload.get("geo_lat"), "signatarios.$.geo_lng": payload.get("geo_lng"),
            "signatarios.$.traco_b64": traco.split(",", 1)[1], "updated_at": datetime.utcnow(),
        }})
    doc = await db[COL].find_one({"id": doc["id"]})
    await atualizar_status(db, doc["id"])
    todos = all(s.get("status") == "assinado" for s in doc["signatarios"])
    if todos:
        try:
            await processar_carimbo(db, doc)
        except Exception:
            logger.error("Falha ao carimbar doc-ext %s", doc["id"], exc_info=True)
    return {"ok": True, "concluido": todos}


@router_publico.post("/{token}/recusar")
@limiter.limit("10/minute")
async def recusar(token: str, payload: dict = None, request: Request = None, db=Depends(get_db)):
    doc = await db[COL].find_one({"signatarios.token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Link inválido")
    motivo = (payload or {}).get("motivo", "")[:300]
    await db[COL].update_one({"id": doc["id"], "signatarios.token": token},
                             {"$set": {"signatarios.$.status": "recusado", "updated_at": datetime.utcnow()}})
    await atualizar_status(db, doc["id"])
    return {"ok": True}
```

- [ ] **Step 2: Import-check**

Run (from `backend/`): `python -c "import routes.documentos_externos_publico; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/routes/documentos_externos_publico.py
git commit -m "feat(doc-ext): rotas públicas de assinatura (assinar/recusar)"
```

---

## Task 7: ICP branch + registro de routers + índices

**Files:**
- Modify: `backend/routes/assinatura.py:23-36` (dict `_TIPO_COLECAO`) e `backend/routes/assinatura.py:437` (branch `_gerar_pdf`)
- Modify: `backend/routes/__init__.py`
- Modify: `backend/server.py` (índices no startup)

- [ ] **Step 1: Add `doc-ext` to `_TIPO_COLECAO`**

In `backend/routes/assinatura.py`, edit the `_TIPO_COLECAO` dict (after the `"georef"` entry, before the closing `}`):

```python
    "georef": "georef_assinaturas",
    # PDF externo (módulo Documentos Externos): base do ICP = intermediário carimbado.
    "doc-ext": "documentos_externos",
}
```

- [ ] **Step 2: Add the `doc-ext` branch in `_gerar_pdf`**

In `backend/routes/assinatura.py`, change the existing branch header at line ~437 from:

```python
    elif tipo in ("documento", "georef"):
```

to add a dedicated branch immediately BEFORE it:

```python
    elif tipo == "doc-ext":
        # PDF externo: a base do ICP é o intermediário JÁ carimbado com as assinaturas dos
        # clientes (se houver); senão, o original. Só BAIXA do R2 + normaliza rotação.
        from services import r2_storage
        key = doc.get("pdf_key_intermediario") or doc.get("pdf_key")
        if not key:
            raise HTTPException(status_code=400, detail="Documento sem arquivo (pdf_key vazio).")
        pdf = await asyncio.to_thread(r2_storage.download_bytes, key)
        if not pdf or not pdf.startswith(b"%PDF-"):
            raise HTTPException(status_code=500, detail="Arquivo do documento inválido.")
        pdf = await asyncio.to_thread(_normalizar_rotacao_pdf, pdf)
        return pdf
    elif tipo in ("documento", "georef"):
```

- [ ] **Step 3: Register the routers**

In `backend/routes/__init__.py`, add the import after the `documentos_assinatura` import (line ~52):

```python
from routes.documentos_assinatura import router as documentos_assinatura_router
from routes.documentos_externos import router as documentos_externos_router
from routes.documentos_externos_publico import router_publico as documentos_externos_publico_router
```

And add to `all_routers` (after `documentos_assinatura_router,`):

```python
    documentos_assinatura_router,
    documentos_externos_router,
    documentos_externos_publico_router,
```

- [ ] **Step 4: Add indices in `server.py`**

Find the startup index-creation block in `backend/server.py` (search for an existing `create_index` near `georef_verificacoes` or `documentos_assinatura`) and add, mirroring the existing idempotent pattern:

```python
    try:
        await db.documentos_externos.create_index("codigo", unique=True)
        await db.documentos_externos.create_index("signatarios.token", unique=True, sparse=True)
        await db.documentos_externos.create_index([("user_id", 1), ("created_at", -1)])
        await db.documentos_externos.create_index([("status", 1), ("created_at", -1)])
    except Exception as e:
        logger.warning("Índices documentos_externos: %s", e)
```

- [ ] **Step 5: Import-check the whole route package**

Run (from `backend/`): `python -c "import routes; print(len(routes.all_routers), 'routers')"`
Expected: prints a number 2 higher than before (no ImportError).

- [ ] **Step 6: Run the full backend test suite (no regressions)**

Run: `python -m pytest tests/test_documentos_externos.py -v`
Expected: PASS (7 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/routes/assinatura.py backend/routes/__init__.py backend/server.py
git commit -m "feat(doc-ext): branch ICP doc-ext + registro de routers + índices"
```

---

## Task 8: Frontend — API client

**Files:**
- Modify: `frontend/src/lib/api.js`

- [ ] **Step 1: Add `documentosExternosAPI`**

In `frontend/src/lib/api.js`, near `documentosAPI` (the "Assinar Documentos" client), add:

```javascript
export const documentosExternosAPI = {
  listar: () => api.get('/documentos-externos').then(r => r.data),
  obter: (id) => api.get(`/documentos-externos/${id}`).then(r => r.data),
  upload: (formData) => api.post('/documentos-externos/upload', formData).then(r => r.data),
  editar: (id, body) => api.patch(`/documentos-externos/${id}`, body).then(r => r.data),
  excluir: (id) => api.delete(`/documentos-externos/${id}`).then(r => r.data),
  addSignatario: (id, body) => api.post(`/documentos-externos/${id}/signatarios`, body).then(r => r.data),
  editSignatario: (id, sid, body) => api.patch(`/documentos-externos/${id}/signatarios/${sid}`, body).then(r => r.data),
  delSignatario: (id, sid) => api.delete(`/documentos-externos/${id}/signatarios/${sid}`).then(r => r.data),
  preparar: (id) => api.post(`/documentos-externos/${id}/preparar`).then(r => r.data),
  posicionar: (id, body) => api.post(`/documentos-externos/${id}/posicionar`, body).then(r => r.data),
  reenviar: (id, body) => api.post(`/documentos-externos/${id}/reenviar`, body).then(r => r.data),
  status: (id) => api.get(`/documentos-externos/${id}/sessao-status`).then(r => r.data),
  distribuirFinal: (id) => api.post(`/documentos-externos/${id}/distribuir-final`).then(r => r.data),
  pdfOriginal: (id) => api.get(`/documentos-externos/${id}/pdf-original`, { responseType: 'blob' }).then(r => r.data),
  pdfFinal: (id) => api.get(`/documentos-externos/${id}/pdf-final`, { responseType: 'blob' }).then(r => r.data),
};

// Público (sem token JWT) — usa o mesmo axios base; o backend não exige auth nessas rotas.
export const documentosExternosPublicoAPI = {
  obter: (token) => api.get(`/publico/documentos-externos/${token}`).then(r => r.data),
  assinar: (token, body) => api.post(`/publico/documentos-externos/${token}`, body).then(r => r.data),
  recusar: (token, body) => api.post(`/publico/documentos-externos/${token}/recusar`, body).then(r => r.data),
};
```

> Nota: confira o nome real do axios instance em `api.js` (provavelmente `api`). Se o upload exigir header multipart, **NÃO** setar `Content-Type` manualmente — o browser adiciona o boundary sozinho (lição da v1.4.933).

- [ ] **Step 2: Build check**

Run (from `frontend/`): `yarn build`
Expected: build green (0 erros).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.js
git commit -m "feat(doc-ext): cliente de API frontend"
```

---

## Task 9: Frontend — lista, card, upload e signatários

**Files:**
- Create: `frontend/src/components/dashboard/documentos-externos/DocumentosExternosList.jsx`
- Create: `frontend/src/components/dashboard/documentos-externos/ModalUpload.jsx`
- Create: `frontend/src/components/dashboard/documentos-externos/ModalSignatarios.jsx`

Estes três componentes clonam o padrão de UX do módulo **Assinar Documentos**
(`frontend/src/components/dashboard/documentos/DocumentosList.jsx`) e da lista de Contratos.
Reusam `BrandSpinner`, `useToast`, e `clientsAPI` (quick-add de signatário).

- [ ] **Step 1: ModalUpload — upload do PDF + metadados**

Create `frontend/src/components/dashboard/documentos-externos/ModalUpload.jsx`:

```jsx
import React, { useState } from 'react';
import { X, UploadCloud } from 'lucide-react';
import { documentosExternosAPI } from '../../../lib/api';

export default function ModalUpload({ onClose, onCreated }) {
  const [titulo, setTitulo] = useState('');
  const [descricao, setDescricao] = useState('');
  const [requerIcp, setRequerIcp] = useState(true);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [erro, setErro] = useState('');

  const enviar = async () => {
    if (!file) { setErro('Selecione um PDF.'); return; }
    if (!titulo.trim()) { setErro('Informe um título.'); return; }
    setBusy(true); setErro('');
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('titulo', titulo.trim());
      fd.append('descricao', descricao.trim());
      fd.append('requer_icp_rt', requerIcp ? 'true' : 'false');
      const doc = await documentosExternosAPI.upload(fd);
      onCreated && onCreated(doc);
    } catch (e) {
      setErro(e?.response?.data?.detail || 'Falha ao enviar.');
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold text-emerald-950">Novo documento externo</h3>
          <button onClick={onClose}><X /></button>
        </div>
        <label className="block border-2 border-dashed border-emerald-300 rounded-xl p-6 text-center cursor-pointer mb-4">
          <UploadCloud className="mx-auto mb-2 text-emerald-700" />
          <span className="text-sm">{file ? file.name : 'Selecionar PDF (máx 25 MB)'}</span>
          <input type="file" accept="application/pdf" className="hidden"
                 onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </label>
        <input className="w-full border rounded-lg p-2 mb-3" placeholder="Título"
               value={titulo} onChange={(e) => setTitulo(e.target.value)} />
        <textarea className="w-full border rounded-lg p-2 mb-3" placeholder="Descrição (opcional)"
                  value={descricao} onChange={(e) => setDescricao(e.target.value)} />
        <label className="flex items-center gap-2 mb-4 text-sm">
          <input type="checkbox" checked={requerIcp} onChange={(e) => setRequerIcp(e.target.checked)} />
          Exigir assinatura ICP-Brasil do RT no final
        </label>
        {erro && <div className="text-red-600 text-sm mb-3">{erro}</div>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border rounded-lg">Cancelar</button>
          <button onClick={enviar} disabled={busy}
                  className="px-4 py-2 bg-emerald-700 text-white rounded-lg disabled:opacity-50">
            {busy ? 'Enviando…' : 'Criar'}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: ModalSignatarios — N signatários com quick-add de clientes**

Create `frontend/src/components/dashboard/documentos-externos/ModalSignatarios.jsx`. Carrega
`clientsAPI.list()` no mount; cada linha tem nome / CPF-CNPJ / papel (`<input>` livre com
`<datalist>` de sugestões: Vendedor, Compradora, Comprador, Cônjuge anuente, Representante legal,
Procurador, Testemunha 1, Testemunha 2, Avalista, Fiador, Anuente) / WhatsApp / email; botão
"Adicionar do cliente" preenche nome+CPF+WhatsApp a partir do cadastro
(`clientsAPI.list()` → mapeia `name`/`doc`/`phone`). Persiste via
`documentosExternosAPI.addSignatario(id, {...})` e remove via `delSignatario`. Use o mesmo
shell de modal do ModalUpload (header verde + footer). Datalist:

```jsx
const PAPEIS = ['Vendedor','Compradora','Comprador','Cônjuge anuente do vendedor',
  'Cônjuge anuente do comprador','Representante legal','Procurador','Testemunha 1',
  'Testemunha 2','Avalista','Fiador','Anuente'];
// <input list="papeis-doc-ext" .../> <datalist id="papeis-doc-ext">{PAPEIS.map(p=><option key={p} value={p}/>)}</datalist>
```

- [ ] **Step 3: DocumentosExternosList — lista + card**

Create `frontend/src/components/dashboard/documentos-externos/DocumentosExternosList.jsx`.
Clona o layout de card do módulo `documentos/DocumentosList.jsx` e da lista de contratos:
- Carrega `documentosExternosAPI.listar()` no mount (com `BrandSpinner` no loading).
- Botão CTA "Novo documento externo" → abre `ModalUpload`; `onCreated` recarrega e abre `ModalSignatarios`.
- Card por documento: `codigo` (DOCEXT-AAAA-NNNN), `titulo`, badge de status
  (`rascunho`/`aguardando`/`parcial`/`clientes_ok`/`finalizado`/`cancelado` — cores como nos contratos),
  linha "Assinaturas · X/N" (de `status()`), e botões:
  - **Signatários** (abre `ModalSignatarios`)
  - **Posicionar** (abre `PositionerDocExt` — Task 10)
  - **Ver PDF** (`pdfOriginal` → `window.open` síncrono no clique, depois seta `location` com o blob — padrão v1.4.922 p/ não bloquear popup)
  - **Ver final** (`pdfFinal`)
  - **Assinar ICP** (abre o `AssinaturaPosicionadaModal` existente com `tipo="doc-ext"` e o id do documento; ao concluir, chama `documentosExternosAPI.distribuirFinal(id)`) — só aparece se `requer_icp_rt` e `status === 'clientes_ok'`
  - **Reenviar** (`reenviar`) — quando `aguardando`/`parcial`
  - **Excluir** (`excluir`)
- Use `useToast` para feedback e mostre o `detail` real do erro do backend.

- [ ] **Step 4: Build check**

Run (from `frontend/`): `yarn build`
Expected: build green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/documentos-externos/
git commit -m "feat(doc-ext): lista, card, modal de upload e de signatários"
```

---

## Task 10: Frontend — posicionador multi-signatário

**Files:**
- Create: `frontend/src/components/dashboard/documentos-externos/PositionerDocExt.jsx`

Clona `AssinaturaClienteModal.jsx` (full-screen, header esmeralda, visualizador de páginas,
caixas arrastáveis em frações 0..1, canvas da assinatura do RT), generalizando p/ **N signatários**.

- [ ] **Step 1: Implement PositionerDocExt**

Estrutura (reusa o shell do `AssinaturaClienteModal`):
- `documentosExternosAPI.preparar(id)` → `{paginas, signatarios, rt}`.
- Lista de "alvos posicionáveis" = `[...signatarios, {id:'__rt__', nome: rt.nome, papel:'Responsável Técnico'}]`,
  cada um com uma **cor distinta** (mapa por índice).
- Para o signatário selecionado: botão "+ Adicionar caixa" cria um retângulo na página atual;
  cada caixa tem um seletor de **tipo** (`assinatura | rubrica | data | nome_extenso`); o usuário
  arrasta/redimensiona (frações da largura/altura da página renderizada — resolução-independente,
  igual ao modal existente). Várias caixas por signatário são permitidas.
- Canvas "Sua assinatura (RT)": pré-carrega `rt.assinatura_b64`; o RT também posiciona UMA caixa
  do próprio traço (alvo `__rt__`, sempre `tipo='assinatura'`).
- Converte frações → pontos PDF usando `largura_pt`/`altura_pt` da página (origem inferior-esquerda;
  `y_pt = altura_pt * (1 - fracao_y_topo) - alt_pt`), exatamente como o modal de cliente já faz.
- Ao enviar, monta:
  ```js
  const posicoes = {};            // { [sid]: [{pagina,x_pt,y_pt,larg_pt,alt_pt,tipo}] }
  signatarios.forEach(s => { posicoes[s.id] = caixasDe(s.id); });
  const rtCaixa = caixasDe('__rt__')[0];
  await documentosExternosAPI.posicionar(id, {
    posicoes,
    rt_traco: rtTracoDataUrl,           // 'data:image/png;base64,...'
    rt_ancora: rtCaixa && { pagina: rtCaixa.pagina, x_pt: rtCaixa.x_pt, y_pt: rtCaixa.y_pt,
                            larg_pt: rtCaixa.larg_pt, alt_pt: rtCaixa.alt_pt },
  });
  ```
- Validação no front: cada signatário precisa de ≥1 caixa; RT precisa de traço + caixa (se quiser
  assinatura visual). Mostra erro do backend (`detail`) se 422.

- [ ] **Step 2: Build check**

Run (from `frontend/`): `yarn build`
Expected: build green.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/documentos-externos/PositionerDocExt.jsx
git commit -m "feat(doc-ext): posicionador multi-signatário com tipos de caixa"
```

---

## Task 11: Frontend — página pública + rotas + menu

**Files:**
- Modify: `frontend/src/App.js` (rota pública `/assinar-doc/:token`)
- Modify: `frontend/src/components/Sidebar.jsx` (item no bloco CONTRATOS)
- Modify: `frontend/src/components/Dashboard.jsx` (rota `/dashboard/documentos-externos`)
- Possibly modify: `frontend/src/pages/AssinarCliente.jsx` (parametrizar o endpoint público)

- [ ] **Step 1: Página pública de assinatura**

A página `AssinarCliente.jsx` já é mobile-first (token, canvas responsivo, geo, consentimento).
Generalize-a para aceitar os endpoints `doc-ext`. Abordagem de menor risco: criar
`frontend/src/pages/AssinarDocExt.jsx` que **reusa o mesmo JSX/UX** mas chama
`documentosExternosPublicoAPI.obter/assinar/recusar` (em vez de `assinaturaClienteAPI`). Se o
`AssinarCliente.jsx` for facilmente parametrizável por props, prefira extrair um componente
compartilhado; senão, duplicar é aceitável (o componente é pequeno). O payload de `assinar`:
`{ traco_base64, concordo: true, geo_lat, geo_lng }`.

In `frontend/src/App.js`, add the public route (fora do guard de auth, junto das outras rotas públicas como `/assinar-cliente/:token`):

```jsx
<Route path="/assinar-doc/:token" element={<AssinarDocExt />} />
```

(e o `import AssinarDocExt from './pages/AssinarDocExt';` — lazy, seguindo o padrão das outras páginas.)

- [ ] **Step 2: Item no menu (bloco CONTRATOS, após "Assinar Documentos")**

In `frontend/src/components/Sidebar.jsx`:
- Add `Send` to the lucide named import (line ~11).
- In the `Contratos` section items array (line ~52-58), insert AFTER the `documentos` item and BEFORE `recibos`:

```jsx
    { id: 'documentos-externos', label: 'Documentos Externos', icon: Send, route: '/dashboard/documentos-externos', tag: 'NOVO' },
```

- [ ] **Step 3: Rota no Dashboard**

In `frontend/src/components/Dashboard.jsx`, add the route mapping (mirroring how `documentos` → `DocumentosList` is wired):

```jsx
<Route path="documentos-externos" element={<DocumentosExternosList />} />
```

(import `DocumentosExternosList` from `./dashboard/documentos-externos/DocumentosExternosList`; use lazy import if the file uses that pattern.)

- [ ] **Step 4: Build check**

Run (from `frontend/`): `yarn build`
Expected: build green (0 warnings novos).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.js frontend/src/components/Sidebar.jsx frontend/src/components/Dashboard.jsx frontend/src/pages/AssinarDocExt.jsx
git commit -m "feat(doc-ext): página pública /assinar-doc + item de menu + rota"
```

---

## Task 12: Versionamento + verificação final

**Files:**
- Modify: `frontend/build-number.txt`
- Modify: `CLAUDE.md` (entrada de release)

- [ ] **Step 1: Incrementar build-number**

Read `frontend/build-number.txt`, increment by 1 (ex.: 1062 → 1063), write back.

- [ ] **Step 2: Adicionar entrada de release no topo do CLAUDE.md**

Atualize o "Estado atual" e a entrada de release descrevendo: novo módulo Documentos Externos
(`doc-ext`), reuso do motor (carimbo/preview/ICP/Z-API), edições aditivas
(`_TIPO_COLECAO["doc-ext"]`, `carimbar_multi`/`carimbar_texto_em_pagina`), endpoints, frontend,
e "X testes verdes; build CRA verde". Bumpar o Dockerfile CACHEBUST conforme a regra do projeto.

- [ ] **Step 3: Verificação final (backend + frontend)**

Run (from `backend/`): `python -m pytest tests/test_documentos_externos.py -v` → PASS (7+)
Run (from `backend/`): `python -c "import routes; print(len(routes.all_routers))"` → sem erro
Run (from `frontend/`): `yarn build` → green

- [ ] **Step 4: Commit**

```bash
git add frontend/build-number.txt CLAUDE.md backend/Dockerfile
git commit -m "chore(doc-ext): bump build-number + release notes (v1.4.10XX)"
```

---

## Self-Review

**Cobertura do spec:**
- §2 Path B (módulo novo fino, sem tocar contratos) → Tasks 1-7 (backend isolado), edições só aditivas ✓
- §3 escopo v1 (tipos de posição múltiplos, ICP opcional, RT desenha+ICP, sem webhook/ordem) → Task 2 (tipos), Task 1 (`requer_icp_rt`), Task 5 (RT carimba + ICP via Task 7), webhook/ordem ausentes ✓
- §4 modelo de dados → Task 1 (modelo) + Task 4 (registro completo no upload) ✓
- §5 endpoints (CRUD, signatários, preparar/posicionar/reenviar/status/distribuir, públicas) → Tasks 4, 5, 6 ✓
- §6 carimbo por tipo → Task 2 ✓
- §7 frontend (api, lista/card, modais, posicionador, página pública, menu) → Tasks 8-11 ✓
- §8 fluxo ponta-a-ponta → coberto pelas tasks na ordem do fluxo ✓
- ICP branch + índices → Task 7 ✓
- versionamento → Task 12 ✓

**Placeholder scan:** Tasks 9-11 do frontend descrevem adaptação de componentes existentes
(card/modal/posicionador) com o código novo essencial inline (ModalUpload completo, datalist de
papéis, payload do posicionar, rota/menu exatos). Isso é deliberado: clonar componentes de
500-650 linhas por inteiro seria pior que referenciar a fonte exata + entregar os deltas. As
partes onde a correção importa (payload `posicionar`, conversão fração→pt, `tipo` por caixa,
endpoint multipart sem Content-Type manual) têm código/instrução explícita.

**Consistência de tipos:** `posicoes` é `[{pagina,x_pt,y_pt,larg_pt,alt_pt,tipo}]` no modelo
(Task 1), no carimbo (`carimbar_multi`, Task 2), no service (`processar_carimbo`, Task 3), na
rota `posicionar` (Task 5) e no posicionador front (Task 10) — mesma forma em todos. `doc-ext`
é a chave de tipo consistente em `_TIPO_COLECAO`, `_gerar_pdf`, `_load_assinatura_bytes`,
`pdf-final`, `distribuir-final` e no `AssinaturaPosicionadaModal` do front. `COL =
"documentos_externos"` é importado do service em todas as rotas.

**Riscos conhecidos a validar na execução:**
- Confirmar o nome do axios instance e o padrão de rota/lazy em `App.js`/`Dashboard.jsx` antes de editar (Tasks 8, 11).
- Confirmar a assinatura de `_load_assinatura_bytes(db, tipo, doc_id)` (retorna `(bytes, meta)`).
- Z-API real só testável com instância configurada — o fluxo ponta-a-ponta (link no celular) é
  verificação manual pós-deploy, como nos módulos irmãos.
