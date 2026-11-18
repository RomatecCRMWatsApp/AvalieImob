"""HTML inicial das páginas públicas (services/seo_html) + coerência do sitemap."""
import re
from pathlib import Path

from services import seo_html as S

RAIZ = Path(__file__).resolve().parents[2]
INDEX = (RAIZ / "frontend/public/index.html").read_text(encoding="utf-8")


def _rotas_app_js():
    app = (RAIZ / "frontend/src/App.js").read_text(encoding="utf-8")
    return [p for p in re.findall(r'<Route\s+path="([^"]+)"', app) if p != "*"]


def test_toda_rota_do_app_responde_200():
    faltando = []
    for p in _rotas_app_js():
        exemplo = re.sub(r":[^/]+", "x", p).replace("/*", "/x")
        if S.status_para(exemplo) != 200:
            faltando.append(p)
    assert not faltando, f"Rotas do App.js que cairiam em 404 — inclua em seo_html: {faltando}"


def test_rota_inexistente_404_com_noindex():
    assert S.status_para("/nao-existe-xyz") == 404
    assert S.status_para("/sobre") == 404  # vira 301 no server.py antes de chegar aqui
    html = S.montar_html(INDEX, "/nao-existe-xyz")
    assert 'name="robots" content="noindex"' in html


def test_canonical_e_og_url_da_propria_rota():
    html = S.montar_html(INDEX, "/ptam")
    assert '<link rel="canonical" href="https://www.romatecavalieimob.com.br/ptam"' in html
    assert 'content="https://www.romatecavalieimob.com.br/ptam"' in html
    assert "<h1>PTAM — Parecer Técnico de Avaliação Mercadológica</h1>" in html
    assert "<title>PTAM — Parecer Técnico" in html


def test_alias_aponta_para_a_pagina_principal():
    html = S.montar_html(INDEX, "/avaliacao-imovel")
    assert 'href="https://www.romatecavalieimob.com.br/avaliacao-urbana"' in html


def test_home_mantem_titulo_e_ganha_links():
    html = S.montar_html(INDEX, "/")
    assert '<link rel="canonical" href="https://www.romatecavalieimob.com.br/"' in html
    root = html[html.index('<div id="root">'):]
    assert "<h1>" in root
    for href, _ in S.LINKS:
        assert f'<a href="{href}">' in root


def test_telas_de_conta_noindex_sem_bloco():
    for p in ("/login", "/esqueci-senha", "/redefinir-senha/abc", "/dashboard/ptam",
              "/laudo/tok", "/assinar-cliente/tok", "/aceite/tok", "/verificar/hash"):
        html = S.montar_html(INDEX, p)
        assert 'content="noindex"' in html, p
        assert 'rel="canonical"' not in html, p
        assert '<div id="root"></div>' in html, p


def test_html_valido_sem_quebrar_o_root():
    html = S.montar_html(INDEX, "/planos")
    assert html.count('<div id="root">') == 1
    assert "R$ 189,90" in html


def test_sitemap_so_com_paginas_canonicas_existentes():
    import ast
    src = (RAIZ / "backend/server.py").read_text(encoding="utf-8")
    bloco = src[src.index("SEO_PAGINAS = ["):]
    bloco = bloco[bloco.index("["): bloco.index("\n]") + 2]
    paths = [p for p, _a, _b in ast.literal_eval(bloco)]
    for p in paths:
        if p == "/privacidade":
            continue  # página servida pelo próprio backend
        assert S.status_para(p) == 200, f"sitemap aponta rota inexistente: {p}"
        assert p not in S.CANONICAL_DE, f"sitemap com alias não canônico: {p}"
        assert not S.eh_noindex(p), p
    assert "<lastmod>{" not in src[src.index("async def sitemap"):src.index("@app.get(\"/robots.txt\")")]


def test_planos_tem_json_ld_com_os_precos_da_fonte_unica():
    import json
    from services import planos as P
    html = S.montar_html(INDEX, "/planos")
    m = re.search(r'<script type="application/ld\+json" data-seo-planos>(.*?)</script>', html, re.S)
    assert m, "JSON-LD dos planos ausente em /planos"
    assert html.index("data-seo-planos") < html.index("</head>")
    dado = json.loads(m.group(1))
    assert dado["@type"] == "Product"
    precos = sorted(float(o["price"]) for o in dado["offers"]["offers"])
    assert precos == sorted(p["preco"] for p in P.PLANOS.values())
    assert dado["offers"]["lowPrice"] == "189.90" and dado["offers"]["highPrice"] == "1199.00"
    # só em /planos
    assert "data-seo-planos" not in S.montar_html(INDEX, "/ptam")
    assert "data-seo-planos" not in S.montar_html(INDEX, "/")
