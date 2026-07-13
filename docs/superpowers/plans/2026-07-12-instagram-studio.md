# Instagram Studio — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir um módulo admin no AvalieImob que gera posts de Instagram (texto via IA + arte com a marca) e organiza um calendário editorial, publicando por deep link (@avalieimob).

**Architecture:** Backend FastAPI (rota admin `/instagram`, serviço de IA que reusa a cascata Roma_IA existente, collection `instagram_posts` isolada por `user_id`). Frontend React (página `InstagramStudio` com Gerador + Calendário + componente de arte que exporta PNG). Sem API Meta, sem multi-tenant.

**Tech Stack:** Python/FastAPI/Motor/Pydantic v2 (backend), React 19/Tailwind (frontend), `html-to-image` (export PNG), pytest (testes backend).

**Spec:** `docs/superpowers/specs/2026-07-12-instagram-studio-design.md`

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `backend/models/instagram_post.py` | Modelos Pydantic do post |
| `backend/services/instagram_ia_service.py` | Prompts por pilar + chamada à cascata de IA |
| `backend/routes/instagram.py` | Rotas admin (gerar + CRUD + status) |
| `backend/routes/__init__.py` (modificar) | Registrar o router |
| `backend/server.py` (modificar) | Índices da collection |
| `backend/tests/test_instagram.py` | Testes de modelo, serviço e rotas |
| `frontend/src/lib/api.js` (modificar) | `instagramAPI` |
| `frontend/src/components/dashboard/instagram/InstagramStudio.jsx` | Página (Gerador + Calendário) |
| `frontend/src/components/dashboard/instagram/InstagramArt.jsx` | Templates da marca + export PNG |
| `frontend/src/components/Sidebar.jsx` (modificar) | Item de menu "Instagram" |
| `frontend/src/components/Dashboard.jsx` (modificar) | Rota `/dashboard/admin/instagram` |
| `frontend/build-number.txt` + `Dockerfile` (modificar) | Versionamento |

---

## Task 1: Modelo `instagram_post.py`

**Files:**
- Create: `backend/models/instagram_post.py`
- Test: `backend/tests/test_instagram.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_instagram.py
import asyncio
import pytest

from models.instagram_post import InstagramPost, InstagramPostCreate


def test_modelo_defaults():
    p = InstagramPost(user_id="u1")
    assert p.id and isinstance(p.id, str)
    assert p.user_id == "u1"
    assert p.status == "ideia"
    assert p.pilar == "recursos"
    assert p.formato == "post_unico"
    assert p.hashtags == []
    assert p.slides == []
    assert p.criado_em and p.atualizado_em


def test_create_para_dict():
    c = InstagramPostCreate(pilar="quanto_vale", formato="carrossel", titulo="X")
    d = c.dict()
    assert d["pilar"] == "quanto_vale"
    assert d["formato"] == "carrossel"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && py -m pytest tests/test_instagram.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'models.instagram_post'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/models/instagram_post.py
# @module models.instagram_post — Post do módulo Instagram Studio (marketing @avalieimob).
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Literal

from pydantic import BaseModel, Field

PILARES = ("recursos", "autoridade", "quanto_vale", "novidades")
FORMATOS = ("post_unico", "carrossel", "reel_roteiro")
STATUSES = ("ideia", "aprovado", "publicado")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Slide(BaseModel):
    titulo: str = ""
    texto: str = ""


class InstagramPostBase(BaseModel):
    pilar: Literal["recursos", "autoridade", "quanto_vale", "novidades"] = "recursos"
    formato: Literal["post_unico", "carrossel", "reel_roteiro"] = "post_unico"
    titulo: str = ""
    legenda: str = ""
    hashtags: List[str] = Field(default_factory=list)
    slides: List[Slide] = Field(default_factory=list)
    roteiro: str = ""
    cta: str = ""
    link: str = ""
    template_arte: str = "impacto"
    status: Literal["ideia", "aprovado", "publicado"] = "ideia"
    data_agendada: Optional[str] = None
    data_publicado: Optional[str] = None


class InstagramPostCreate(InstagramPostBase):
    pass


class InstagramPostUpdate(BaseModel):
    pilar: Optional[str] = None
    formato: Optional[str] = None
    titulo: Optional[str] = None
    legenda: Optional[str] = None
    hashtags: Optional[List[str]] = None
    slides: Optional[List[Any]] = None
    roteiro: Optional[str] = None
    cta: Optional[str] = None
    link: Optional[str] = None
    template_arte: Optional[str] = None
    status: Optional[str] = None
    data_agendada: Optional[str] = None
    data_publicado: Optional[str] = None


class InstagramPost(InstagramPostBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    criado_em: str = Field(default_factory=_iso)
    atualizado_em: str = Field(default_factory=_iso)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && py -m pytest tests/test_instagram.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/models/instagram_post.py backend/tests/test_instagram.py
git commit -m "feat(instagram): modelo InstagramPost + testes"
```

---

## Task 2: Serviço de IA `instagram_ia_service.py`

**Files:**
- Create: `backend/services/instagram_ia_service.py`
- Test: `backend/tests/test_instagram.py` (adicionar testes)

Reusa `_roma_ia_cascata` e `_parse_json_safe` de `contrato_ia_service.py` (DRY — não reimplementar a cascata).

- [ ] **Step 1: Write the failing test (adicionar ao arquivo de teste)**

```python
# adicionar em backend/tests/test_instagram.py
import services.instagram_ia_service as IA


def test_gerar_conteudo_monta_saida(monkeypatch):
    async def fake_cascata(messages, max_tokens=2000):
        return ('{"titulo":"Quanto vale seu imovel?","legenda":"Descubra agora. Siga @avalieimob",'
                '"hashtags":["#imovel","#avaliacao"],"slides":[],"roteiro":"","cta":"Acesse a calculadora"}')
    monkeypatch.setattr(IA, "_roma_ia_cascata", fake_cascata)
    out = asyncio.run(IA.gerar_conteudo("quanto_vale", "valor de mercado", "post_unico"))
    assert out["titulo"] == "Quanto vale seu imovel?"
    assert out["link"] == "/quanto-vale-meu-imovel"
    assert "@avalieimob" in out["legenda"]
    assert out["pilar"] == "quanto_vale"


def test_gerar_conteudo_pilar_invalido():
    with pytest.raises(Exception):
        asyncio.run(IA.gerar_conteudo("xxx", "a", "post_unico"))


def test_gerar_conteudo_json_ruim_erro(monkeypatch):
    async def fake_cascata(messages, max_tokens=2000):
        return "isso nao e json"
    monkeypatch.setattr(IA, "_roma_ia_cascata", fake_cascata)
    with pytest.raises(Exception):
        asyncio.run(IA.gerar_conteudo("recursos", "a", "post_unico"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && py -m pytest tests/test_instagram.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.instagram_ia_service'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/services/instagram_ia_service.py
# @module services.instagram_ia_service — Gera conteúdo de Instagram por pilar (reusa a cascata Roma_IA).
import logging
from typing import Any, Dict

from fastapi import HTTPException

from services.contrato_ia_service import _roma_ia_cascata, _parse_json_safe

logger = logging.getLogger("romatec")

CONTEXTO_SISTEMA = (
    "O AvalieImob é um sistema brasileiro de avaliação imobiliária (PTAM/laudos NBR 14.653), "
    "contratos, assinatura ICP-Brasil, georreferenciamento e prospecção. Público: corretores, "
    "imobiliárias e proprietários. Perfil no Instagram: @avalieimob."
)

_PILAR_INSTRUCAO = {
    "recursos": "Destaque UMA funcionalidade do sistema (PTAM, contratos, assinatura ICP, georreferenciamento) e o benefício prático para o corretor.",
    "autoridade": "Ensine algo útil sobre avaliação imobiliária (NBR 14.653, erros comuns, boas práticas). Tom de especialista.",
    "quanto_vale": "Chame o proprietário/corretor a descobrir o valor do imóvel na calculadora gratuita. Topo de funil.",
    "novidades": "Anuncie uma novidade/oferta do sistema com CTA de cadastro.",
}

_FORMATO_INSTRUCAO = {
    "post_unico": 'Gere "titulo" (frase de impacto curta) e "legenda". Deixe "slides" e "roteiro" vazios.',
    "carrossel": 'Gere "titulo" (capa) e "slides" (4 a 6 itens {titulo, texto}), o último com CTA. Deixe "roteiro" vazio.',
    "reel_roteiro": 'Gere "titulo" e "roteiro" (roteiro falado de 20-40s, com gancho nos 3 primeiros segundos). Deixe "slides" vazio.',
}

_LINK_MAP = {
    "recursos": "/cadastro",
    "autoridade": "/cadastro",
    "quanto_vale": "/quanto-vale-meu-imovel",
    "novidades": "/cadastro",
}


async def gerar_conteudo(pilar: str, assunto: str, formato: str) -> Dict[str, Any]:
    if pilar not in _PILAR_INSTRUCAO:
        raise HTTPException(status_code=400, detail="Pilar inválido")
    if formato not in _FORMATO_INSTRUCAO:
        raise HTTPException(status_code=400, detail="Formato inválido")

    prompt = (
        f"{CONTEXTO_SISTEMA}\n\n"
        "Crie um conteúdo para o Instagram @avalieimob.\n"
        f"PILAR: {_PILAR_INSTRUCAO[pilar]}\n"
        f"FORMATO: {_FORMATO_INSTRUCAO[formato]}\n"
        f"ASSUNTO: {assunto or 'livre, dentro do pilar'}\n\n"
        "REGRAS: português do Brasil; sem clickbait vazio; UM CTA claro; "
        "hashtags do nicho (avaliação imobiliária, corretor, imóveis, laudo); "
        'a legenda deve terminar com "Siga @avalieimob".\n\n'
        "Responda APENAS um JSON válido com as chaves exatas: "
        '{"titulo": str, "legenda": str, "hashtags": [str], '
        '"slides": [{"titulo": str, "texto": str}], "roteiro": str, "cta": str}.'
    )
    messages = [{"role": "user", "content": prompt}]
    texto = await _roma_ia_cascata(messages, max_tokens=2000)
    data = _parse_json_safe(texto)
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="A IA não retornou um JSON válido. Tente novamente.")

    return {
        "titulo": data.get("titulo", ""),
        "legenda": data.get("legenda", ""),
        "hashtags": data.get("hashtags", []) or [],
        "slides": data.get("slides", []) or [],
        "roteiro": data.get("roteiro", ""),
        "cta": data.get("cta", ""),
        "link": _LINK_MAP[pilar],
        "pilar": pilar,
        "formato": formato,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && py -m pytest tests/test_instagram.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/services/instagram_ia_service.py backend/tests/test_instagram.py
git commit -m "feat(instagram): serviço de IA por pilar (reusa cascata Roma_IA)"
```

---

## Task 3: Rotas `routes/instagram.py` + registro + índices

**Files:**
- Create: `backend/routes/instagram.py`
- Modify: `backend/routes/__init__.py` (import + `all_routers`)
- Modify: `backend/server.py` (índices no bloco de startup)
- Test: `backend/tests/test_instagram.py` (adicionar teste de rotas)

- [ ] **Step 1: Write the failing test**

```python
# adicionar em backend/tests/test_instagram.py
def test_router_registra_rotas():
    from routes.instagram import router
    paths = {r.path for r in router.routes}
    assert "/instagram/gerar" in paths
    assert "/instagram/posts" in paths
    assert "/instagram/posts/{pid}" in paths
    assert "/instagram/posts/{pid}/status" in paths
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && py -m pytest tests/test_instagram.py::test_router_registra_rotas -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'routes.instagram'`

- [ ] **Step 3: Write the router**

```python
# backend/routes/instagram.py
# @module routes.instagram — Instagram Studio (admin): gera conteúdo com IA + CRUD do calendário.
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_db
from dependencies import get_admin_user, serialize_doc
from models.instagram_post import (
    InstagramPost, InstagramPostCreate, InstagramPostUpdate, _iso,
)
from services import instagram_ia_service

router = APIRouter(tags=["instagram"])
logger = logging.getLogger("romatec")


class GerarBody(BaseModel):
    pilar: str
    assunto: str = ""
    formato: str = "post_unico"


class StatusBody(BaseModel):
    status: str


@router.post("/instagram/gerar")
async def gerar(body: GerarBody, uid: str = Depends(get_admin_user)):
    return await instagram_ia_service.gerar_conteudo(body.pilar, body.assunto, body.formato)


@router.post("/instagram/posts")
async def criar_post(body: InstagramPostCreate, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    doc = InstagramPost(user_id=uid, **body.dict()).dict()
    await db.instagram_posts.insert_one(doc)
    return serialize_doc(doc)


@router.get("/instagram/posts")
async def listar_posts(mes: Optional[str] = None, status: Optional[str] = None,
                       pilar: Optional[str] = None,
                       uid: str = Depends(get_admin_user), db=Depends(get_db)):
    q = {"user_id": uid}
    if status:
        q["status"] = status
    if pilar:
        q["pilar"] = pilar
    if mes:
        q["data_agendada"] = {"$regex": f"^{mes}"}  # mes = "YYYY-MM"
    docs = await db.instagram_posts.find(q).sort("criado_em", -1).to_list(500)
    return [serialize_doc(d) for d in docs]


@router.get("/instagram/posts/{pid}")
async def obter_post(pid: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    doc = await db.instagram_posts.find_one({"id": pid, "user_id": uid})
    if not doc:
        raise HTTPException(404, "Post não encontrado")
    return serialize_doc(doc)


@router.put("/instagram/posts/{pid}")
async def atualizar_post(pid: str, body: InstagramPostUpdate,
                         uid: str = Depends(get_admin_user), db=Depends(get_db)):
    upd = dict(body.dict(exclude_unset=True))
    upd["atualizado_em"] = _iso()
    r = await db.instagram_posts.update_one({"id": pid, "user_id": uid}, {"$set": upd})
    if r.matched_count == 0:
        raise HTTPException(404, "Post não encontrado")
    doc = await db.instagram_posts.find_one({"id": pid, "user_id": uid})
    return serialize_doc(doc)


@router.post("/instagram/posts/{pid}/status")
async def mudar_status(pid: str, body: StatusBody,
                       uid: str = Depends(get_admin_user), db=Depends(get_db)):
    if body.status not in ("ideia", "aprovado", "publicado"):
        raise HTTPException(400, "Status inválido")
    upd = {"status": body.status, "atualizado_em": _iso()}
    if body.status == "publicado":
        upd["data_publicado"] = _iso()
    r = await db.instagram_posts.update_one({"id": pid, "user_id": uid}, {"$set": upd})
    if r.matched_count == 0:
        raise HTTPException(404, "Post não encontrado")
    doc = await db.instagram_posts.find_one({"id": pid, "user_id": uid})
    return serialize_doc(doc)


@router.delete("/instagram/posts/{pid}")
async def excluir_post(pid: str, uid: str = Depends(get_admin_user), db=Depends(get_db)):
    r = await db.instagram_posts.delete_one({"id": pid, "user_id": uid})
    if r.deleted_count == 0:
        raise HTTPException(404, "Post não encontrado")
    return {"ok": True}
```

- [ ] **Step 4: Register the router in `routes/__init__.py`**

Add the import near the other imports (e.g. after the `prospeccao` import if present, else at the end of the import block):

```python
from routes.instagram import router as instagram_router
```

Then add `instagram_router` to the `all_routers` list (find the list literal that aggregates every `*_router` and append it). Example:

```python
all_routers = [
    # ... existing routers ...
    instagram_router,
]
```

- [ ] **Step 5: Add indexes in `server.py`**

In the startup indexes block (near the `leads_avaliacao` / `contratos_exclusividade` index calls), add:

```python
        await db.instagram_posts.create_index("id", unique=True)
        await db.instagram_posts.create_index([("user_id", 1), ("status", 1)])
        await db.instagram_posts.create_index([("user_id", 1), ("data_agendada", 1)])
```

- [ ] **Step 6: Run tests + import check**

Run: `cd backend && py -m pytest tests/test_instagram.py -v && py -c "import routes; print('routers ok')"`
Expected: PASS (6 passed) + `routers ok`

- [ ] **Step 7: Commit**

```bash
git add backend/routes/instagram.py backend/routes/__init__.py backend/server.py backend/tests/test_instagram.py
git commit -m "feat(instagram): rotas admin (gerar + CRUD calendário) + índices"
```

---

## Task 4: Frontend — `instagramAPI` + menu + rota + esqueleto

**Files:**
- Modify: `frontend/src/lib/api.js` (adicionar `instagramAPI`)
- Modify: `frontend/src/components/Sidebar.jsx` (item "Instagram", só admin)
- Modify: `frontend/src/components/Dashboard.jsx` (rota `/dashboard/admin/instagram`)
- Create: `frontend/src/components/dashboard/instagram/InstagramStudio.jsx` (esqueleto)

- [ ] **Step 1: Add `instagramAPI` in `lib/api.js`**

Add after the `aiAPI` block:

```javascript
// ---- Instagram Studio
export const instagramAPI = {
  gerar: (pilar, assunto, formato) =>
    api.post('/instagram/gerar', { pilar, assunto, formato }).then(r => r.data),
  listar: (params = {}) =>
    api.get('/instagram/posts', { params }).then(r => r.data),
  obter: (id) => api.get(`/instagram/posts/${id}`).then(r => r.data),
  criar: (data) => api.post('/instagram/posts', data).then(r => r.data),
  atualizar: (id, data) => api.put(`/instagram/posts/${id}`, data).then(r => r.data),
  status: (id, status) => api.post(`/instagram/posts/${id}/status`, { status }).then(r => r.data),
  excluir: (id) => api.delete(`/instagram/posts/${id}`).then(r => r.data),
};
```

- [ ] **Step 2: Create the page skeleton**

```jsx
// frontend/src/components/dashboard/instagram/InstagramStudio.jsx
import React from 'react';

export default function InstagramStudio() {
  return (
    <div className="p-4 md:p-8">
      <h1 className="text-2xl font-bold text-[#0C3320]">Instagram Studio</h1>
      <p className="text-gray-500 mt-1">Gere posts para @avalieimob e organize o calendário.</p>
      {/* Gerador (Task 5) + Calendário (Task 6) entram aqui */}
    </div>
  );
}
```

- [ ] **Step 3: Add sidebar item (admin only)**

In `Sidebar.jsx`, near the existing admin-only items (Prospecção / Divulgação), add — using a NAMED lucide import (never `import * as`):

```jsx
// no topo, garantir o import nomeado:
import { Instagram } from 'lucide-react';

// dentro do bloco isAdmin, junto de Prospecção/Divulgação:
{ to: '/dashboard/admin/instagram', label: 'Instagram', icon: Instagram },
```

(Se o Sidebar usa uma estrutura diferente para itens, seguir o mesmo formato dos itens admin já existentes — copie o padrão do item "Prospecção".)

- [ ] **Step 4: Add the route in `Dashboard.jsx`**

```jsx
// import (lazy, seguindo o padrão do arquivo):
const InstagramStudio = React.lazy(() => import('./dashboard/instagram/InstagramStudio'));

// dentro das <Routes> admin:
<Route path="admin/instagram" element={<InstagramStudio />} />
```

- [ ] **Step 5: Verify build**

Run: `cd frontend && yarn build`
Expected: Compiled successfully (no new warnings in the changed files)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/api.js frontend/src/components/Sidebar.jsx frontend/src/components/Dashboard.jsx frontend/src/components/dashboard/instagram/InstagramStudio.jsx
git commit -m "feat(instagram): instagramAPI + menu + rota + esqueleto da página"
```

---

## Task 5: Frontend — Gerador (form + gerar IA + edição)

**Files:**
- Modify: `frontend/src/components/dashboard/instagram/InstagramStudio.jsx`

- [ ] **Step 1: Implement the generator block**

Substituir o corpo do componente por um bloco Gerador completo. Estado + handlers:

```jsx
import React, { useState } from 'react';
import { instagramAPI } from '../../../lib/api';

const PILARES = [
  { v: 'recursos', label: 'Recursos do sistema' },
  { v: 'autoridade', label: 'Autoridade / educação' },
  { v: 'quanto_vale', label: 'Quanto vale meu imóvel' },
  { v: 'novidades', label: 'Novidades e ofertas' },
];
const FORMATOS = [
  { v: 'post_unico', label: 'Post único' },
  { v: 'carrossel', label: 'Carrossel' },
  { v: 'reel_roteiro', label: 'Roteiro de Reel' },
];

export default function InstagramStudio() {
  const [pilar, setPilar] = useState('recursos');
  const [formato, setFormato] = useState('post_unico');
  const [assunto, setAssunto] = useState('');
  const [gerando, setGerando] = useState(false);
  const [post, setPost] = useState(null); // conteúdo gerado/editado
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');

  const gerar = async () => {
    setErro(''); setGerando(true);
    try {
      const out = await instagramAPI.gerar(pilar, assunto, formato);
      setPost({ ...out, template_arte: 'impacto', status: 'ideia' });
    } catch (e) {
      setErro(e?.response?.data?.detail || 'Falha ao gerar. Tente novamente.');
    } finally { setGerando(false); }
  };

  const salvar = async () => {
    if (!post) return;
    setSalvando(true);
    try {
      // upsert: se já tem id (veio do calendário), atualiza; senão cria — evita duplicar
      const salvo = post.id
        ? await instagramAPI.atualizar(post.id, post)
        : await instagramAPI.criar(post);
      setPost({ ...salvo });
      // Task 6 adiciona `carregar()` aqui para atualizar a lista
    } finally { setSalvando(false); }
  };

  const upd = (campo, val) => setPost(p => ({ ...p, [campo]: val }));

  return (
    <div className="p-4 md:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#0C3320]">Instagram Studio</h1>
        <p className="text-gray-500 mt-1">Gere posts para @avalieimob e organize o calendário.</p>
      </div>

      {/* GERADOR */}
      <div className="bg-white rounded-xl border p-4 space-y-3">
        <div className="grid md:grid-cols-3 gap-3">
          <label className="text-sm">Pilar
            <select className="w-full border rounded p-2 mt-1" value={pilar} onChange={e => setPilar(e.target.value)}>
              {PILARES.map(p => <option key={p.v} value={p.v}>{p.label}</option>)}
            </select>
          </label>
          <label className="text-sm">Formato
            <select className="w-full border rounded p-2 mt-1" value={formato} onChange={e => setFormato(e.target.value)}>
              {FORMATOS.map(f => <option key={f.v} value={f.v}>{f.label}</option>)}
            </select>
          </label>
          <label className="text-sm">Assunto (opcional)
            <input className="w-full border rounded p-2 mt-1" value={assunto}
                   onChange={e => setAssunto(e.target.value)} placeholder="ex.: assinatura ICP" />
          </label>
        </div>
        <button onClick={gerar} disabled={gerando}
                className="bg-[#0C3320] text-white rounded px-4 py-2 disabled:opacity-50">
          {gerando ? 'Gerando…' : 'Gerar com IA'}
        </button>
        {erro && <p className="text-red-600 text-sm">{erro}</p>}
      </div>

      {/* EDIÇÃO DO CONTEÚDO GERADO */}
      {post && (
        <div className="bg-white rounded-xl border p-4 space-y-3">
          <input className="w-full border rounded p-2 font-semibold" value={post.titulo || ''}
                 onChange={e => upd('titulo', e.target.value)} placeholder="Título" />
          <textarea className="w-full border rounded p-2 h-40" value={post.legenda || ''}
                    onChange={e => upd('legenda', e.target.value)} placeholder="Legenda" />
          {post.formato === 'reel_roteiro' && (
            <textarea className="w-full border rounded p-2 h-32" value={post.roteiro || ''}
                      onChange={e => upd('roteiro', e.target.value)} placeholder="Roteiro do Reel" />
          )}
          {post.formato === 'carrossel' && (
            <div className="space-y-2">
              {(post.slides || []).map((s, i) => (
                <div key={i} className="border rounded p-2">
                  <input className="w-full border rounded p-1 mb-1 text-sm font-medium"
                         value={s.titulo || ''} placeholder={`Slide ${i + 1} — título`}
                         onChange={e => upd('slides', post.slides.map((x, j) => j === i ? { ...x, titulo: e.target.value } : x))} />
                  <textarea className="w-full border rounded p-1 text-sm"
                            value={s.texto || ''} placeholder="Texto do slide"
                            onChange={e => upd('slides', post.slides.map((x, j) => j === i ? { ...x, texto: e.target.value } : x))} />
                </div>
              ))}
            </div>
          )}
          <input className="w-full border rounded p-2 text-sm" value={(post.hashtags || []).join(' ')}
                 onChange={e => upd('hashtags', e.target.value.split(/\s+/).filter(Boolean))}
                 placeholder="#hashtags separadas por espaço" />
          <button onClick={salvar} disabled={salvando}
                  className="bg-[#C9A84C] text-[#0C3320] font-semibold rounded px-4 py-2 disabled:opacity-50">
            {salvando ? 'Salvando…' : 'Salvar no calendário'}
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && yarn build`
Expected: Compiled successfully

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/instagram/InstagramStudio.jsx
git commit -m "feat(instagram): gerador de conteúdo com IA + edição"
```

---

## Task 6: Frontend — Calendário editorial

**Files:**
- Modify: `frontend/src/components/dashboard/instagram/InstagramStudio.jsx`

- [ ] **Step 1: Add calendar state, loader and list UI**

Adicionar ao componente: carregar posts no mount, filtro por status/pilar, e a lista com badges e ações (mudar status / excluir). Trechos-chave:

```jsx
import React, { useState, useEffect, useCallback } from 'react';

const STATUS_META = {
  ideia:     { label: '💡 Ideia',     cls: 'bg-gray-100 text-gray-700' },
  aprovado:  { label: '✅ Aprovado',  cls: 'bg-blue-100 text-blue-700' },
  publicado: { label: '📤 Publicado', cls: 'bg-green-100 text-green-700' },
};

// dentro do componente:
const [posts, setPosts] = useState([]);
const [filtroStatus, setFiltroStatus] = useState('');

const carregar = useCallback(async () => {
  const params = {};
  if (filtroStatus) params.status = filtroStatus;
  setPosts(await instagramAPI.listar(params));
}, [filtroStatus]);

useEffect(() => { carregar(); }, [carregar]);

const mudarStatus = async (id, status) => {
  await instagramAPI.status(id, status);
  carregar();
};
const excluir = async (id) => {
  if (!window.confirm('Excluir este post?')) return;
  await instagramAPI.excluir(id);
  carregar();
};
```

Após salvar no gerador (Task 5), chamar `carregar()` no fim de `salvar()`.

Bloco JSX do calendário (abaixo do gerador):

```jsx
<div className="bg-white rounded-xl border p-4 space-y-3">
  <div className="flex items-center justify-between">
    <h2 className="font-semibold text-[#0C3320]">Calendário editorial</h2>
    <select className="border rounded p-1 text-sm" value={filtroStatus}
            onChange={e => setFiltroStatus(e.target.value)}>
      <option value="">Todos</option>
      <option value="ideia">Ideia</option>
      <option value="aprovado">Aprovado</option>
      <option value="publicado">Publicado</option>
    </select>
  </div>
  {posts.length === 0 && <p className="text-gray-400 text-sm">Nenhum post ainda.</p>}
  {posts.map(p => (
    <div key={p.id} className="border rounded-lg p-3 flex items-start justify-between gap-2">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded ${STATUS_META[p.status]?.cls}`}>
            {STATUS_META[p.status]?.label}
          </span>
          <span className="text-xs text-gray-400">{p.pilar}</span>
        </div>
        <p className="font-medium truncate mt-1">{p.titulo || '(sem título)'}</p>
        <p className="text-sm text-gray-500 line-clamp-2">{p.legenda}</p>
      </div>
      <div className="flex flex-col gap-1 shrink-0">
        {p.status === 'ideia' &&
          <button onClick={() => mudarStatus(p.id, 'aprovado')} className="text-xs text-blue-600">Aprovar</button>}
        {p.status === 'aprovado' &&
          <button onClick={() => mudarStatus(p.id, 'publicado')} className="text-xs text-green-600">Marcar publicado</button>}
        <button onClick={() => excluir(p.id)} className="text-xs text-red-500">Excluir</button>
      </div>
    </div>
  ))}
</div>
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && yarn build`
Expected: Compiled successfully

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/instagram/InstagramStudio.jsx
git commit -m "feat(instagram): calendário editorial (lista + status + excluir)"
```

---

## Task 7: Frontend — Arte com a marca + export PNG + publicar

**Files:**
- Create: `frontend/src/components/dashboard/instagram/InstagramArt.jsx`
- Modify: `frontend/src/components/dashboard/instagram/InstagramStudio.jsx` (abrir a arte + ações de publicação)
- Modify: `frontend/package.json` (dep `html-to-image`)

- [ ] **Step 1: Add the dependency**

Run: `cd frontend && yarn add html-to-image`
Expected: adiciona `html-to-image` em `dependencies`.

- [ ] **Step 2: Create the art component**

```jsx
// frontend/src/components/dashboard/instagram/InstagramArt.jsx
import React, { useRef } from 'react';
import { toPng } from 'html-to-image';

const VERDE = '#0C3320';
const DOURADO = '#C9A84C';

// 1 card = 1 "página" da arte (feed 1080 ou carrossel 1080x1350).
function Card({ innerRef, alt = false, children }) {
  return (
    <div
      ref={innerRef}
      style={{
        width: 540, height: 540, // preview a 50% (exporta em 2x = 1080)
        background: alt ? '#0f3a25' : VERDE,
        color: '#f3f1e6', padding: 40, boxSizing: 'border-box',
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        fontFamily: '"Playfair Display", serif', position: 'relative',
      }}
    >
      {children}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: DOURADO, fontFamily: 'Inter, sans-serif', fontSize: 16 }}>
        <span style={{
          width: 26, height: 26, borderRadius: 8, background: DOURADO, color: VERDE,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700,
        }}>A</span>
        @avalieimob
      </div>
    </div>
  );
}

export default function InstagramArt({ post }) {
  const refs = useRef([]);

  // define as "páginas": post/reel = 1 card; carrossel = capa + slides
  const paginas = post.formato === 'carrossel' && (post.slides || []).length
    ? [{ titulo: post.titulo, texto: post.cta }, ...post.slides]
    : [{ titulo: post.titulo, texto: post.cta }];

  const baixar = async () => {
    await document.fonts.ready;
    for (let i = 0; i < refs.current.length; i++) {
      const node = refs.current[i];
      if (!node) continue;
      const dataUrl = await toPng(node, { pixelRatio: 2, cacheBust: true });
      const a = document.createElement('a');
      a.download = `avalieimob-${post.id || 'post'}-${i + 1}.png`;
      a.href = dataUrl;
      a.click();
    }
  };

  const copiarLegenda = async () => {
    const tags = (post.hashtags || []).join(' ');
    await navigator.clipboard.writeText(`${post.legenda || ''}\n\n${tags}`.trim());
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-3 overflow-x-auto py-2">
        {paginas.map((pg, i) => (
          <Card key={i} innerRef={el => (refs.current[i] = el)} alt={i > 0}>
            <div style={{ fontSize: 34, fontWeight: 700, lineHeight: 1.15 }}>{pg.titulo}</div>
            {pg.texto && <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 18 }}>{pg.texto}</div>}
          </Card>
        ))}
      </div>
      <div className="flex gap-2 flex-wrap">
        <button onClick={baixar} className="bg-[#C9A84C] text-[#0C3320] font-semibold rounded px-4 py-2">
          Baixar arte (PNG)
        </button>
        <button onClick={copiarLegenda} className="border rounded px-4 py-2">Copiar legenda</button>
        <a href="https://www.instagram.com/avalieimob" target="_blank" rel="noreferrer"
           className="bg-[#0C3320] text-white rounded px-4 py-2">Abrir Instagram</a>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Wire the art into the page**

Em `InstagramStudio.jsx`, importar e renderizar a arte quando houver um post gerado/salvo:

```jsx
import InstagramArt from './InstagramArt';

// abaixo do bloco de edição (Task 5), dentro do `post &&`:
<InstagramArt post={post} />
```

E no calendário (Task 6), dentro do `posts.map(p => ...)`, adicionar um botão que carrega o post no editor + arte (a variável do item é `p`):

```jsx
<button onClick={() => setPost(p)} className="text-xs text-[#0C3320] font-medium">Abrir arte</button>
```

Ao clicar, `setPost(p)` traz o post do calendário para o editor + `<InstagramArt>`. Como esse `p` tem `id`, o botão "Salvar" fará `atualizar` (upsert da Task 5), sem duplicar.

- [ ] **Step 4: Verify build**

Run: `cd frontend && yarn build`
Expected: Compiled successfully

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/instagram/InstagramArt.jsx frontend/src/components/dashboard/instagram/InstagramStudio.jsx frontend/package.json frontend/yarn.lock
git commit -m "feat(instagram): arte com a marca + export PNG + ações de publicação (deep link)"
```

---

## Task 8: Versionamento + verificação final

**Files:**
- Modify: `frontend/build-number.txt`
- Modify: `Dockerfile` (CACHEBUST + CACHEBUST_BACKEND)

- [ ] **Step 1: Bump build number**

Increment `frontend/build-number.txt` by 1 over the current value.

- [ ] **Step 2: Bump CACHEBUST**

In `Dockerfile`, bump `CACHEBUST` and `CACHEBUST_BACKEND` to a new date-stamped value (e.g. `2026-07-12-01`), following the existing pattern in the file.

- [ ] **Step 3: Full verification**

Run: `cd backend && py -m pytest tests/test_instagram.py -v && py -c "import routes; print('routers ok')"`
Expected: all tests PASS + `routers ok`

Run: `cd frontend && yarn build`
Expected: Compiled successfully

- [ ] **Step 4: Manual smoke (browser preview)**

Start the app (dev server) and confirm: menu "Instagram" aparece para admin → gerar um post → editar → salvar → aparece no calendário → abrir arte → baixar PNG (1080px, marca correta) → copiar legenda.

- [ ] **Step 5: Commit**

```bash
git add frontend/build-number.txt Dockerfile
git commit -m "chore(instagram): bump versão v1.4.x — Instagram Studio"
```

---

## Simplificações conscientes (vs spec — incrementos futuros, não bloqueiam o v1)
- **Um template de arte adaptável** (post/carrossel/reel) em vez dos 3 templates distintos do
  spec. O campo `template_arte` já existe no modelo → dá para adicionar seletor de templates
  depois sem migração.
- **Cupom no pilar "novidades"**: a IA é instruída genericamente; a integração real com
  `cuponsAPI` (injetar um cupom ativo na legenda) fica como incremento. O link já vai para
  `/cadastro`.

## Notas de verificação
- Backend: `cd backend && py -m pytest tests/test_instagram.py -v` (6 testes).
- Import dos routers: `py -c "import routes"`.
- Frontend: `cd frontend && yarn build` (sem warnings novos nos arquivos alterados).
- Isolamento: toda query filtra `user_id` (admin logado). Sem multi-tenant.
- Marca: verde `#0C3320`, dourado `#C9A84C`, rodapé `@avalieimob` em toda arte.
