# White-label — Integração em TODOS os documentos

> Objetivo: a marca configurada em `/api/branding` (logo, cores, rodapé) entra em
> **PTAM, Contrato, Recibo, TVI e Locação** — PDF e DOCX. Fallback transparente:
> sem marca salva ou `use_default=true`, o documento sai idêntico ao de hoje
> (verde `#1B4D1B` / dourado `#D4A830` / logo AvalieImob).

## Princípio único

Todos os geradores recebem `user: dict`. O resolvedor universal injeta a marca em
chaves reservadas `_brand_*` nesse dict. Cada gerador lê essas chaves **com
fallback** às constantes atuais. Zero quebra nos documentos existentes.

```python
# Em QUALQUER rota que gera documento, antes de chamar o gerador:
from services.branding_context import inject_brand

user = await db.users.find_one({"id": uid})
user = await inject_brand(db, uid, user)   # injeta _brand_* + _company_logo_bytes
pdf_bytes = generate_ptam_pdf(ptam, user)  # idem para os demais geradores
```

Chaves injetadas: `_company_logo_bytes`, `_brand_primary`, `_brand_secondary`,
`_brand_text`, `_brand_footer_bg`, `_brand_footer_text`, `_brand_footer_lines`,
`_brand_stamp_name`, `_brand_stamp_credentials`, `_brand_font_title`,
`_brand_font_body`.

---

## 1. PTAM — `ptam_pdf.py` (ReportLab)

**Nível 1 (logo + nome) — já funciona sem alterar o gerador.** `generate_ptam_pdf`
já lê `user["_company_logo_bytes"]` e `user["company"]`. Basta injetar a marca na
rota `routes/ptam.py`:

```python
# routes/ptam.py — onde hoje há generate_ptam_pdf(ptam, user)
from services.branding_context import inject_brand
user = await inject_brand(db, uid, user)
pdf = generate_ptam_pdf(ptam, user)
```

**Nível 2 (faixa do cabeçalho/rodapé na cor do cliente) — diff no `_on_page`.**
Substituir as constantes fixas por valores vindos de `doc`, com fallback:

```python
# ptam_pdf.py  → _RomaTecDoc.__init__  (após super().__init__)
self._brand_primary = colors.HexColor((company_brand or {}).get("primary")) if company_brand else GREEN
# ...ou simplesmente leia de generate_ptam_pdf abaixo.

# ptam_pdf.py  → _on_page  (trocar os usos diretos de GREEN/GOLD)
band   = getattr(doc, "_brand_primary", None) or GREEN
accent = getattr(doc, "_brand_accent", None)  or GOLD
canvas.setFillColor(band)                 # faixa do cabeçalho (linha 236)
# ...
canvas.setStrokeColor(accent)             # underline dourado (linha 283)
# ...
canvas.setFillColor(band)                 # faixa do rodapé (linha 288)
```

```python
# ptam_pdf.py  → generate_ptam_pdf  (após criar `doc`)
from reportlab.lib.colors import HexColor
doc._brand_primary = HexColor(user["_brand_primary"]) if user.get("_brand_primary") else GREEN
doc._brand_accent  = HexColor(user["_brand_secondary"]) if user.get("_brand_secondary") else GOLD
# rodapé textual: se o usuário definiu linhas próprias, usa-as
_fl = user.get("_brand_footer_lines")
if _fl:
    doc._footer_text = "  |  ".join(_fl)
```

E no rodapé (linha ~296), trocar a string fixa por:
`getattr(doc, "_footer_text", "RomaTec Consultoria Total  —  ABNT NBR 14653-1/-2/-3 | ...")`.

---

## 2. Contrato — `contrato_docx.py` (python-docx)

`generate_contrato_docx(contrato, user, perfil=None)`. A capa usa `GREEN`/`GOLD`
e o logo. Patch (com fallback):

```python
# contrato_docx.py — topo da função, após `doc = Document()`
from docx.shared import RGBColor
def _rgb(hex_str, default):
    if not hex_str:
        return default
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

brand_green = _rgb(user.get("_brand_primary"), GREEN)
brand_gold  = _rgb(user.get("_brand_secondary"), GOLD)
logo_bytes  = user.get("_company_logo_bytes")
```

Depois, onde hoje aparece `GREEN`/`GOLD` no cabeçalho/títulos da capa, use
`brand_green`/`brand_gold`. Para o logo no cabeçalho:

```python
if logo_bytes:
    import io as _io
    doc.sections[0].header.paragraphs[0].add_run().add_picture(_io.BytesIO(logo_bytes), width=Cm(3))
```

Rota `routes/contratos.py`: `user = await inject_brand(db, uid, user)` antes de
`generate_contrato_docx(...)`.

---

## 3. Recibo — `services/recibo_inline.py` (ReportLab) e arras DOCX

`gerar_recibo_pdf(*, ptam, user, perfil, valor, ...)`. O cabeçalho usa
`#1B4D1B` fixo (linha 53). Patch:

```python
# recibo_inline.py — início da função
from reportlab.lib import colors
brand_primary = colors.HexColor(user.get("_brand_primary") or "#1B4D1B")
logo_bytes = user.get("_company_logo_bytes")
# ...
c.setFillColor(brand_primary)            # troca o HexColor("#1B4D1B") da linha 53
c.rect(0, page_h - 35*mm, page_w, 35*mm, fill=1, stroke=0)
if logo_bytes:
    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(io.BytesIO(logo_bytes)), 12*mm, page_h-30*mm,
                width=22*mm, height=22*mm, preserveAspectRatio=True, mask="auto")
```

Arras DOCX (`generate_recibo_arras_docx(contrato, user)`): mesmo padrão do contrato.

Rota `routes/recibos.py`: `user = await inject_brand(db, uid, user)` antes de gerar.

---

## 4. TVI e Locação

- `pdf/tvi_pdf.py` e `pdf/locacao_pdf.py` (ReportLab): mesmo padrão da seção 1
  (faixa/linha pela cor `_brand_primary`/`_brand_secondary`, logo por
  `_company_logo_bytes`).
- `docx_gen/tvi_docx.py` e `locacao_docx.py` (python-docx): mesmo padrão da seção 2.
- Nas rotas `routes/tvi.py` e `routes/locacao.py`: `user = await inject_brand(db, uid, user)`
  antes de chamar o gerador.

---

## Checklist de rollout (uma rota por vez, sem risco)

1. `routes/ptam.py` → injeta marca → **logo do cliente já aparece** (Nível 1).
2. Aplica Nível 2 no `ptam_pdf.py` (cores da faixa) e valida um PTAM real.
3. Repete para contratos, recibos, TVI, locação.
4. Índice MongoDB: criado por `branding_repository.ensure_indexes(db)` —
   adicione a chamada em `db.setup_indexes()`:

```python
# db.py → setup_indexes(), ao final
from services.branding_repository import ensure_indexes as _branding_indexes
await _branding_indexes(_db)
```

## Dependências novas (requirements)

```
boto3>=1.34        # Cloudflare R2 (S3-compatible)
python-magic>=0.4  # detecção de MIME por magic bytes  (Debian: libmagic1)
cairosvg>=2.7      # rasterização de SVG               (Debian: libcairo2)
# Pillow e reportlab já estão no projeto.
# pdf2image (opcional, p/ preview PNG)                 (Debian: poppler-utils)
```

## Variáveis de ambiente (Railway)

```
R2_ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
R2_ACCESS_KEY=...
R2_SECRET_KEY=...
R2_BUCKET=avalieimob-assets
R2_PUBLIC_BASE=https://assets.romatecavalieimob.com.br   # opcional (CDN)
AVALIEIMOB_DEFAULT_LOGO_URL=https://.../logo_avalieimob.png  # opcional
```
