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


def test_blog_slugs_batem_com_o_frontend():
    import re
    posts = (RAIZ / "frontend/src/data/blogPosts.js").read_text(encoding="utf-8")
    app = (RAIZ / "frontend/src/App.js").read_text(encoding="utf-8")
    import json as _json
    slugs_posts = set(re.findall(r"slug: '([^']+)'", posts)) | {
        _json.loads(f.read_text(encoding="utf-8"))["slug"]
        for f in (RAIZ / "frontend/src/data/blog").glob("*.json")}
    slugs_rotas = set(re.findall(r'path="/blog/([^"/:]+)"', app))
    assert slugs_posts == S.BLOG_SLUGS, f"Atualize BLOG_SLUGS em seo_html: {slugs_posts ^ S.BLOG_SLUGS}"
    assert slugs_rotas == S.BLOG_SLUGS, f"Rota de blog sem slug (ou vice-versa): {slugs_rotas ^ S.BLOG_SLUGS}"


def test_artigo_inexistente_404_e_artigo_real_200():
    assert S.status_para("/blog/nao-existe-esse-artigo") == 404
    assert S.status_para("/blog/como-fazer-ptam-passo-a-passo-nbr-14653") == 200
    assert S.status_para("/blog/como-fazer-ptam-passo-a-passo-nbr-14653/") == 200
    assert S.status_para("/blog") == 200
    assert S.eh_noindex("/blog/nao-existe-esse-artigo") or "noindex" in S.montar_html(
        "<html><head><title>x</title></head><body><div id=\"root\"></div></body></html>", "/blog/nao-existe-esse-artigo")


def _html_artigo(slug):
    html = "<html><head><title>x</title><link rel=\"canonical\" href=\"https://x/\" />" \
           "<meta name=\"description\" content=\"x\" /></head><body><div id=\"root\"></div></body></html>"
    return S.montar_html(html, "/blog/" + slug)


def test_artigos_migrados_entregam_o_texto_completo_no_html_inicial():
    """Fonte única: todo texto do JSON do artigo aparece no HTML inicial (antes do JS)."""
    import html as _h
    import json as _json
    arquivos = sorted((RAIZ / "frontend/src/data/blog").glob("*.json"))
    assert {f.stem for f in arquivos} == set(S.BLOG_SLUGS), "todo artigo do blog precisa do JSON"
    for f in arquivos:
        a = _json.loads(f.read_text(encoding="utf-8"))
        assert a["slug"] + ".json" == f.name and a["slug"] in S.BLOG_SLUGS
        out = _html_artigo(a["slug"])
        assert f"<title>{_h.escape(a['titulo'])} | Blog AvalieImob</title>" in out
        assert out.count("<h1>") == 1 and _h.escape(a["titulo"]) in out
        assert f'href="https://www.romatecavalieimob.com.br/blog/{a["slug"]}"' in out
        textos = []
        for b in a["conteudo"]:
            for k in ("h2", "h3", "p", "callout", "cta", "linkTexto", "tabelaNota"):
                if b.get(k):
                    textos.append(b[k])
            textos += b.get("lista") or []
            textos += b.get("listaOrd") or []
            for linha in (b.get("tabela") or {}).get("linhas", []):
                textos += linha
            if b.get("link"):
                assert f'href="{_h.escape(b["link"])}"' in out
        faltando = [t for t in textos if _h.escape(t, quote=True) not in out]
        assert not faltando, f"{a['slug']}: texto da tela ausente do HTML inicial: {faltando[:3]}"


def test_componente_do_artigo_migrado_le_o_json():
    """Garante que a tela renderiza o MESMO arquivo que o servidor (sem cópia do texto no JSX)."""
    import json as _json
    for f in (RAIZ / "frontend/src/data/blog").glob("*.json"):
        a = _json.loads(f.read_text(encoding="utf-8"))
        comps = [c for c in (RAIZ / "frontend/src/pages/blog").glob("*.jsx")
                 if f"data/blog/{a['slug']}.json" in c.read_text(encoding="utf-8")]
        assert len(comps) == 1, f"{a['slug']}: nenhum componente importa o JSON"
        assert "conteudo={[" not in comps[0].read_text(encoding="utf-8")
    for c in (RAIZ / "frontend/src/pages/blog").glob("*.jsx"):
        assert "conteudo={[" not in c.read_text(encoding="utf-8"), f"{c.name}: texto ainda no JSX"


SERVICOS_ROTAS = ("ptam", "laudo-tecnico", "avaliacao-rural", "avaliacao-garantia", "avaliacao-urbana")


def test_paginas_de_servico_entregam_o_texto_completo_no_html_inicial():
    """Mesma fonte da tela (data/servicos/<slug>.json): todo texto aparece antes do JavaScript."""
    import html as _h
    import json as _json
    arquivos = {f.stem: f for f in (RAIZ / "frontend/src/data/servicos").glob("*.json")}
    assert set(arquivos) == set(SERVICOS_ROTAS)
    for slug, f in arquivos.items():
        sv = _json.loads(f.read_text(encoding="utf-8"))
        assert sv["slug"] == slug
        out = S.montar_html(INDEX, "/" + slug)
        assert f"<title>{_h.escape(sv['titulo'])} | AvalieImob - RomaTec</title>" in out
        assert out.count("<h1>") == 1
        textos = [sv["titulo"], sv["subtitulo"], sv["hero"], sv["ctaTitulo"], sv["ctaTexto"]]
        textos += sv["intro"] + sv["publicoAlvo"]
        for i in sv["beneficios"] + sv["comoFunciona"]:
            textos += [i["titulo"], i["descricao"]]
        for q in sv["faq"]:
            textos += [q["q"], q["a"]]
        faltando = [t for t in textos if _h.escape(t, quote=True) not in out]
        assert not faltando, f"{slug}: texto da tela ausente do HTML inicial: {faltando[:3]}"
        # links internos apontam para a URL canônica, não para /servicos/ (noindex)
        assert 'href="/servicos/' not in out


def test_componentes_de_servico_leem_o_json_e_links_batem():
    tpl = (RAIZ / "frontend/src/pages/ServicoTemplate.jsx").read_text(encoding="utf-8")
    for slug, titulo in S._SERVICOS_LINKS:
        assert f"{{ slug: '{slug}', titulo: '{titulo}' }}" in tpl
    assert "`/servicos/${s.slug}`" not in tpl
    for c in (RAIZ / "frontend/src/pages").glob("Servico*.jsx"):
        if c.name == "ServicoTemplate.jsx":
            continue
        txt = c.read_text(encoding="utf-8")
        assert "../data/servicos/" in txt and "intro={[" not in txt, c.name


def test_index_html_sem_faq_invisivel_e_sem_promessa_de_conformidade_total():
    """Perguntas frequentes só vão em dados estruturados quando aparecem na página."""
    assert '"FAQPage"' not in INDEX
    assert "partes 1 a 7" not in INDEX
