# @module services.seo_html — HTML inicial das páginas públicas (antes do JavaScript).
"""O site é um SPA React: sem isto, toda rota respondia o MESMO index.html — título
da home, `canonical` apontando para a home e corpo vazio ("habilite o JavaScript").

Aqui, função PURA sobre o index.html já renderizado:
  * `canonical` e `og:url` da PRÓPRIA rota (antes todas apontavam para a home);
  * título/descrição da rota quando a página tem texto próprio;
  * dentro de <div id="root">, um bloco com H1, resumo e links <a href> reais para as
    páginas de serviço. É o MESMO texto que a página mostra depois (copiado dos
    componentes), não texto escondido para robô; o React substitui o bloco ao montar
    (index.js usa createRoot, que limpa o conteúdo do container);
  * `noindex` nas telas de conta (login, recuperar senha, SSO);
  * `status_para` diz se a rota existe (200) ou não (404 — antes era 200 + redirect
    no navegador para a home, o "soft 404").

Ao criar rota pública nova no App.js: o teste `tests/test_seo_html.py` lê o App.js e
quebra se a rota cair em 404 aqui. O texto das páginas de serviço e dos artigos vem dos
JSON do frontend (data/servicos e data/blog) — edite lá, nunca aqui.
"""
import html as _html
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from services import planos as _planos

BASE = "https://www.romatecavalieimob.com.br"

# Igual ao SERVICOS_LINKS do ServicoTemplate.jsx (o teste confere).
_SERVICOS_LINKS = (
    ("ptam", "PTAM — Parecer Técnico de Avaliação Mercadológica"),
    ("laudo-tecnico", "Laudo Técnico de Avaliação"),
    ("avaliacao-rural", "Avaliação de Imóveis Rurais"),
    ("avaliacao-garantia", "Avaliação de Garantias Bancárias"),
    ("avaliacao-urbana", "Avaliação de Imóveis Urbanos"),
)

# Texto copiado das próprias páginas (ServicoTemplate titulo/meta, SEO.jsx, index.html).
PAGINAS = {
    "/": {
        "titulo": "AvalieImob — Software de PTAM e Avaliação Imobiliária Online | NBR 14.653",
        "h1": "AvalieImob — software de PTAM e avaliação imobiliária online",
        "descricao": ("Sistema online de avaliação imobiliária para emitir PTAM, Laudos Técnicos, "
                      "TVI e Avaliação de Garantias, com tratamento científico por inferência "
                      "estatística. Conforme NBR 14.653 e Resolução COFECI 1.066/2007."),
    },
    "/ptam": {
        "titulo": "PTAM — Parecer Técnico de Avaliação Mercadológica | AvalieImob - RomaTec",
        "h1": "PTAM — Parecer Técnico de Avaliação Mercadológica",
        "descricao": ("Emita PTAM (Parecer Técnico de Avaliação Mercadológica) online conforme "
                      "NBR 14.653 da ABNT. Wizard guiado, IA especializada e exportação DOCX/PDF."),
    },
    "/laudo-tecnico": {
        "titulo": "Laudo Técnico de Avaliação Imobiliária | AvalieImob - RomaTec",
        "h1": "Laudo Técnico de Avaliação Imobiliária",
        "descricao": "Emita laudos técnicos profissionais conforme NBR 14.653 com IA integrada.",
    },
    "/avaliacao-urbana": {
        "titulo": "Avaliação de Imóveis Urbanos | AvalieImob - RomaTec",
        "h1": "Avaliação de Imóveis Urbanos",
        "descricao": ("Avalie casas, apartamentos, terrenos, salas comerciais e galpões "
                      "conforme NBR 14.653-2."),
    },
    "/avaliacao-rural": {
        "titulo": "Avaliação de Imóveis Rurais — NBR 14.653-3 | AvalieImob - RomaTec",
        "h1": "Avaliação de Imóveis Rurais — NBR 14.653-3",
        "descricao": ("Avalie fazendas, sítios, terras nuas, benfeitorias, safras e semoventes "
                      "(penhor rural)."),
    },
    "/avaliacao-garantia": {
        "titulo": "Avaliação de Garantias Bancárias | AvalieImob - RomaTec",
        "h1": "Avaliação de Garantias Bancárias",
        "descricao": ("Laudos de avaliação para garantias hipotecárias, alienação fiduciária "
                      "e penhor."),
    },
    "/planos": {
        "titulo": "Planos e valores da assinatura | AvalieImob",
        "h1": "Planos e valores da assinatura",
        "descricao": ("Mensal R$ 189,90, trimestral R$ 449,90 ou anual R$ 1.199,00. "
                      "Cadastre-se e teste o AvalieImob grátis por 7 dias."),
    },
    "/quanto-vale-meu-imovel": {
        "titulo": "Quanto vale meu imóvel? Estimativa preliminar grátis | AvalieImob",
        "h1": "Quanto vale meu imóvel?",
        "descricao": ("Estimativa preliminar de valor de mercado, gratuita. Não substitui PTAM "
                      "nem laudo: o documento técnico é elaborado e assinado por profissional "
                      "habilitado."),
    },
    "/blog": {
        "titulo": "Blog AvalieImob — PTAM, NBR 14.653 e avaliação imobiliária",
        "h1": "Blog AvalieImob",
        "descricao": ("Guias sobre PTAM, NBR 14.653, avaliação urbana e rural, métodos "
                      "avaliatórios e documentos do avaliador."),
    },
    "/privacidade": {
        "titulo": "Privacidade e LGPD | AvalieImob",
        "h1": "Privacidade e LGPD",
        "descricao": ("Quem é o responsável pelos dados no AvalieImob e como pedir acesso, "
                      "correção ou eliminação dos seus dados pessoais."),
    },
    "/cadastro": {
        "titulo": "Cadastro grátis — Crie sua conta | AvalieImob",
        "h1": "Crie sua conta no AvalieImob",
        "descricao": ("Crie sua conta e teste o AvalieImob por 7 dias, sem cartão de crédito "
                      "e sem cobrança automática."),
    },
}

# Rotas que só repetem outra página: o canonical aponta para a principal.
CANONICAL_DE = {
    "/avaliacao-imovel": "/avaliacao-urbana",
    "/avaliacao-imobiliaria": "/avaliacao-urbana",
}

# Existem (200), mas não entram no índice de busca: telas de conta e links pessoais
# com token (laudo, assinatura, aceite, verificação) — dado de cliente não vai pro Google.
NOINDEX = ("/login", "/esqueci-senha", "/redefinir-senha", "/sso", "/dashboard",
           "/laudo", "/v", "/contrato", "/aceite", "/assinar-cliente", "/assinar-doc",
           "/assinar-geo", "/assinar", "/verificar", "/avaliacao", "/servicos")

# Links rastreáveis presentes em toda página pública (as páginas que existem de fato).
LINKS = [
    ("/ptam", "PTAM"),
    ("/laudo-tecnico", "Laudo técnico"),
    ("/avaliacao-urbana", "Imóveis urbanos"),
    ("/avaliacao-rural", "Imóveis rurais"),
    ("/avaliacao-garantia", "Garantias bancárias"),
    ("/quanto-vale-meu-imovel", "Quanto vale meu imóvel?"),
    ("/planos", "Planos"),
    ("/blog", "Blog"),
    ("/cadastro", "Criar conta"),
]

# Rotas do SPA (App.js). Exatas ou por prefixo "/x/". O resto é 404.
_EXATAS = {
    "/", "/ptam", "/laudo-tecnico", "/avaliacao-rural", "/avaliacao-garantia",
    "/avaliacao-urbana", "/avaliacao-imovel", "/avaliacao-imobiliaria", "/blog",
    "/login", "/cadastro", "/esqueci-senha", "/sso", "/como-assinar", "/planos", "/privacidade",
    "/quanto-vale-meu-imovel", "/dashboard",
}
_PREFIXOS = (
    "/servicos/", "/redefinir-senha/", "/laudo/", "/v/", "/contrato/",
    "/aceite/", "/assinar-cliente/", "/assinar-doc/", "/assinar-geo/", "/assinar/",
    "/verificar/", "/avaliacao/", "/dashboard/",
)


# Artigos do blog que existem (slugs de frontend/src/data/blogPosts.js e das rotas do
# App.js). Endereço inventado dentro de /blog/ responde 404 em vez de 200. Ao publicar
# artigo novo, acrescente o slug aqui — tests/test_seo_html.py acusa se faltar.
BLOG_SLUGS = frozenset({
    "checklist-vistoria-avaliacao-imobiliaria-ptam",
    "ficha-resumo-contrato-locacao-comercial",
    "inferencia-estatistica-avaliacao-imoveis-tratamento-cientifico",
    "contrato-exclusividade-procuracao-corretor-imoveis",
    "assinatura-icp-brasil-laudos-contratos-validade-juridica",
    "precificar-georreferenciamento-demarcacao-averbacao-proposta",
    "como-emitir-art-rrt-trt-avaliacao-imobiliaria",
    "avaliacao-imovel-inventario-partilha",
    "metodo-comparativo-direto-passo-a-passo",
    "grau-fundamentacao-precisao-nbr-14653",
    "como-fazer-ptam-passo-a-passo-nbr-14653",
    "diferenca-ptam-laudo-avaliacao-imobiliaria",
    "avaliacao-imovel-rural-nbr-14653-3-guia-completo",
    "como-calcular-valor-liquidacao-forcada-vlf",
})


def _norm(path: str) -> str:
    p = "/" + (path or "").split("?", 1)[0].split("#", 1)[0].strip("/")
    return p if p != "/" else "/"


def rota_existe(path: str) -> bool:
    p = _norm(path)
    if p.startswith("/blog/"):
        return p[len("/blog/"):] in BLOG_SLUGS
    return p in _EXATAS or any((p + "/").startswith(pref) for pref in _PREFIXOS)


def status_para(path: str) -> int:
    return 200 if rota_existe(path) else 404


def _esc(s: str) -> str:
    return _html.escape(s or "", quote=True)


def _sub_attr(html: str, pattern: str, valor: str) -> str:
    return re.sub(pattern, lambda m: m.group(1) + valor + m.group(3), html,
                  count=1, flags=re.I | re.S)


def _bloco(info: dict) -> str:
    links = "".join(f'<li><a href="{href}">{_esc(txt)}</a></li>' for href, txt in LINKS)
    h1 = f"<h1>{_esc(info['h1'])}</h1><p>{_esc(info['descricao'])}</p>" if info else ""
    return (
        '<div data-seo-inicial style="font-family:system-ui,sans-serif;max-width:860px;'
        'margin:0 auto;padding:32px 20px;color:#0C3320">'
        f'{h1}<nav aria-label="Páginas do AvalieImob"><ul>{links}</ul></nav>'
        '<p><small>RomaTec Consultoria Total — AvalieImob · Açailândia/MA</small></p></div>'
    )


# ── Artigos do blog com texto completo no HTML inicial ─────────────────────────
# Fonte ÚNICA: frontend/src/data/blog/<slug>.json. O React renderiza esse arquivo; o
# prebuild (scripts/genblogseo.js) junta todos em build/blog-seo.json, que é o que existe
# no container (o src não vai para a imagem). Em dev/teste, lê direto do src.
_FRONT = Path(__file__).resolve().parents[2] / "frontend"


def _carregar(pasta: str, empacotado: str) -> dict:
    """Lê o pacote do build (produção) ou os JSON de src/ (dev e testes). Nunca levanta."""
    try:
        arq = _FRONT / "build" / empacotado
        if arq.exists():
            return json.loads(arq.read_text(encoding="utf-8"))
        d = _FRONT / "src" / "data" / pasta
        return {f.stem: json.loads(f.read_text(encoding="utf-8"))
                for f in sorted(d.glob("*.json"))} if d.exists() else {}
    except Exception:  # arquivo ruim nunca derruba o site: cai no HTML genérico
        return {}


@lru_cache(maxsize=1)
def carregar_artigos() -> dict:
    return _carregar("blog", "blog-seo.json")


@lru_cache(maxsize=1)
def carregar_servicos() -> dict:
    return _carregar("servicos", "servicos-seo.json")


def _bloco_conteudo(b: dict) -> str:
    """Um bloco do artigo, com a MESMA estrutura do BlogPostTemplate.renderBloco."""
    e = _esc
    if b.get("h2"):
        return f"<h2>{e(b['h2'])}</h2>"
    if b.get("h3"):
        return f"<h3>{e(b['h3'])}</h3>"
    if b.get("tabela"):
        t = b["tabela"]
        cab = "".join(f"<th>{e(c)}</th>" for c in t.get("cabecalho", []))
        lin = "".join("<tr>" + "".join(f"<td>{e(c)}</td>" for c in l) + "</tr>"
                      for l in t.get("linhas", []))
        nota = f"<p>{e(b['tabelaNota'])}</p>" if b.get("tabelaNota") else ""
        return f"<table><thead><tr>{cab}</tr></thead><tbody>{lin}</tbody></table>{nota}"
    if b.get("link"):
        p = f"<p>{e(b['p'])}</p>" if b.get("p") else ""
        return f'{p}<p><a href="{e(b["link"])}">{e(b.get("linkTexto") or "Saiba mais →")}</a></p>'
    if b.get("p"):
        return f"<p>{e(b['p'])}</p>"
    if b.get("lista"):
        return "<ul>" + "".join(f"<li>{e(i)}</li>" for i in b["lista"]) + "</ul>"
    if b.get("listaOrd"):
        return "<ol>" + "".join(f"<li>{e(i)}</li>" for i in b["listaOrd"]) + "</ol>"
    if b.get("callout"):
        tit = f"<strong>{e(b['calloutTitulo'])}</strong> " if b.get("calloutTitulo") else ""
        return f"<aside><p>{tit}{e(b['callout'])}</p></aside>"
    if b.get("cta"):
        return (f"<p>{e(b['cta'])}</p>"
                f'<p><a href="{e(b.get("ctaLink") or "/cadastro")}">{e(b.get("ctaTexto") or "Começar grátis →")}</a></p>')
    return ""


def _bloco_artigo(a: dict) -> str:
    e = _esc
    corpo = "".join(_bloco_conteudo(b) for b in a.get("conteudo") or [] if isinstance(b, dict))
    servicos = "".join(f'<li><a href="/{e(s.get("slug", ""))}">{e(s.get("titulo", ""))}</a></li>'
                       for s in a.get("servicosRelacionados") or [])
    servicos = f"<h3>Serviços relacionados</h3><ul>{servicos}</ul>" if servicos else ""
    resumo = f"<p><strong>Resumo executivo:</strong> {e(a['resumo'])}</p>" if a.get("resumo") else ""
    sub = f"<p>{e(a['subtitulo'])}</p>" if a.get("subtitulo") else ""
    return (
        '<div data-seo-inicial style="font-family:system-ui,sans-serif;max-width:760px;'
        'margin:0 auto;padding:32px 20px;color:#1f2937;line-height:1.7">'
        '<nav aria-label="breadcrumb"><a href="/">Início</a> › <a href="/blog">Blog</a></nav>'
        f'<article><h1>{e(a.get("titulo"))}</h1>{sub}'
        f'<p><small>Por {e(a.get("autor") or "José Romário Pinto Bezerra")} · '
        f'{e(a.get("tempoLeitura") or "")} de leitura</small></p>'
        f'{resumo}{corpo}{servicos}</article>'
        '<p><a href="/cadastro">Teste grátis</a> · <a href="/planos">Planos</a> · '
        '<a href="/blog">Mais artigos</a></p></div>'
    )


def _bloco_servico(sv: dict) -> str:
    """Página de serviço com a MESMA estrutura do ServicoTemplate (hero, intro, benefícios,
    como funciona, público, perguntas frequentes, chamada final e links internos)."""
    e = _esc
    def cards(itens):
        return "".join(f"<h3>{e(i.get('titulo'))}</h3><p>{e(i.get('descricao'))}</p>" for i in itens or [])
    intro = "".join(f"<p>{e(p)}</p>" for p in sv.get("intro") or [])
    ben = (f"<h2>Por que escolher o AvalieImob para {e((sv.get('titulo') or '').lower())}?</h2>"
           + cards(sv.get("beneficios"))) if sv.get("beneficios") else ""
    passos = ("<h2>Como funciona</h2><ol>" + "".join(
        f"<li><h3>{e(i.get('titulo'))}</h3><p>{e(i.get('descricao'))}</p></li>"
        for i in sv["comoFunciona"]) + "</ol>") if sv.get("comoFunciona") else ""
    publico = ("<h2>Para quem é este serviço</h2><ul>" + "".join(
        f"<li>{e(p)}</li>" for p in sv["publicoAlvo"]) + "</ul>") if sv.get("publicoAlvo") else ""
    faq = ("<h2>Perguntas frequentes</h2>" + "".join(
        f"<details><summary>{e(f.get('q'))}</summary><p>{e(f.get('a'))}</p></details>"
        for f in sv["faq"]) + "") if sv.get("faq") else ""
    outros = "".join(f'<li><a href="/{e(s2)}">{e(t)}</a></li>'
                     for s2, t in _SERVICOS_LINKS if s2 != sv.get("slug"))
    return (
        '<div data-seo-inicial style="font-family:system-ui,sans-serif;max-width:860px;'
        'margin:0 auto;padding:32px 20px;color:#1f2937;line-height:1.7">'
        '<nav><a href="/">Início</a> · <a href="/planos">Planos</a> · <a href="/blog">Blog</a> · '
        '<a href="/cadastro">Teste Grátis</a></nav>'
        f'<main><h1>{e(sv.get("titulo"))}</h1><p>{e(sv.get("subtitulo"))}</p><p>{e(sv.get("hero"))}</p>'
        '<p><a href="/cadastro">Começar grátis →</a> · <a href="/planos">Ver planos</a></p>'
        f'{intro}{ben}{passos}{publico}{faq}'
        f'<h2>{e(sv.get("ctaTitulo"))}</h2><p>{e(sv.get("ctaTexto"))}</p>'
        '<p><a href="/cadastro">Comece agora grátis →</a></p>'
        f'<h3>Outros serviços do AvalieImob</h3><ul>{outros}</ul></main></div>'
    )


def servico_do_path(p: str) -> Optional[dict]:
    return carregar_servicos().get(CANONICAL_DE.get(p, p).lstrip("/")) if p != "/" else None


def artigo_do_path(p: str):
    if not p.startswith("/blog/"):
        return None
    return carregar_artigos().get(p[len("/blog/"):])


def _noindex(html: str) -> str:
    # Sem canonical: "noindex" + canonical para a home seriam sinais contraditórios.
    html = re.sub(r'\s*<link\s+rel=["\']canonical["\'][^>]*>', "", html, count=1, flags=re.I)
    return html.replace("<head>", '<head><meta name="robots" content="noindex" />', 1)


def eh_noindex(path: str) -> bool:
    p = _norm(path)
    return any(p == n or p.startswith(n + "/") for n in NOINDEX)


def schema_planos() -> dict:
    """JSON-LD dos 3 planos (Product + AggregateOffer) — preços de services/planos.py.

    É o mesmo preço que a página /planos mostra; o Google pode exibir a faixa
    "R$ 189,90 – R$ 1.199,00" no resultado da busca.
    """
    url = BASE + "/planos"
    ofertas = [
        {
            "@type": "Offer",
            "name": f"Plano {p['nome']}",
            "price": f"{p['preco']:.2f}",
            "priceCurrency": "BRL",
            "availability": "https://schema.org/InStock",
            "url": url,
            "priceSpecification": {
                "@type": "UnitPriceSpecification",
                "price": f"{p['preco']:.2f}",
                "priceCurrency": "BRL",
                "billingDuration": f"P{p['meses']}M",
            },
        }
        for p in _planos.PLANOS.values()
    ]
    precos = [p["preco"] for p in _planos.PLANOS.values()]
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "AvalieImob — assinatura do software de avaliação imobiliária",
        "description": ("Software online para emitir PTAM, laudos técnicos e avaliações "
                        "conforme NBR 14.653. Assinatura mensal, trimestral ou anual."),
        "brand": {"@type": "Brand", "name": "AvalieImob"},
        "image": BASE + "/brand/og-banner.png",
        "url": url,
        "offers": {
            "@type": "AggregateOffer",
            "priceCurrency": "BRL",
            "lowPrice": f"{min(precos):.2f}",
            "highPrice": f"{max(precos):.2f}",
            "offerCount": len(ofertas),
            "offers": ofertas,
        },
    }


def _json_ld(dado: dict) -> str:
    # "</" escapado: o JSON nunca fecha a tag <script> antes da hora.
    txt = json.dumps(dado, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json" data-seo-planos>{txt}</script>'


def montar_html(html: str, path: str) -> str:
    """Ajusta o index.html para a rota pedida (ver docstring do módulo)."""
    p = _norm(path)
    if not rota_existe(p):
        return _noindex(html).replace('<div id="root"></div>', f'<div id="root">{_bloco(None)}</div>', 1)
    if eh_noindex(p):
        return _noindex(html)
    url = BASE + (CANONICAL_DE.get(p, p) if p != "/" else "/")
    html = _sub_attr(html, r'(<link\s+rel=["\']canonical["\']\s+href=["\'])(.*?)(["\'])', _esc(url))
    html = _sub_attr(html, r'(<meta\s+property=["\']og:url["\']\s+content=["\'])(.*?)(["\'])', _esc(url))
    info = PAGINAS.get(CANONICAL_DE.get(p, p))
    artigo = artigo_do_path(p)
    servico = None if artigo else servico_do_path(p)
    if servico:
        # Mesmo título que o Helmet do ServicoTemplate põe depois do JavaScript.
        info = {"titulo": f"{servico.get('titulo', '')} | AvalieImob - RomaTec",
                "descricao": servico.get("meta") or ""}
    if artigo:
        # Mesmo título que o Helmet do BlogPostTemplate põe depois do JavaScript.
        info = {"titulo": f"{artigo.get('titulo', '')} | Blog AvalieImob",
                "descricao": artigo.get("meta") or artigo.get("resumo") or ""}
    if info and p != "/":
        t, d = _esc(info["titulo"]), _esc(info["descricao"])
        for pat, val in (
            (r'(<title[^>]*>)(.*?)(</title>)', t),
            (r'(<meta\s+name=["\']description["\']\s+content=["\'])(.*?)(["\'])', d),
            (r'(<meta\s+property=["\']og:title["\']\s+content=["\'])(.*?)(["\'])', t),
            (r'(<meta\s+property=["\']og:description["\']\s+content=["\'])(.*?)(["\'])', d),
            (r'(<meta\s+name=["\']twitter:title["\']\s+content=["\'])(.*?)(["\'])', t),
            (r'(<meta\s+name=["\']twitter:description["\']\s+content=["\'])(.*?)(["\'])', d),
        ):
            html = _sub_attr(html, pat, val)
    if p == "/planos":
        html = html.replace("</head>", _json_ld(schema_planos()) + "</head>", 1)
    bloco = _bloco_artigo(artigo) if artigo else (_bloco_servico(servico) if servico else _bloco(info))
    return html.replace('<div id="root"></div>', f'<div id="root">{bloco}</div>', 1)
