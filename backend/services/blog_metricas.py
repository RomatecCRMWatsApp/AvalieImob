# @module services.blog_metricas — leitura e cliques nos artigos do blog, por artigo.
"""Contagem ANÔNIMA: só artigo, tipo de evento, posição do botão e dia.
Nada de IP, e-mail, telefone ou identificador de pessoa. Agregado por dia num único
documento (`_id = dia:slug:tipo:posicao`, com `$inc n`), então a coleção não cresce
por visita.

O funil por artigo cruza esses números com os cadastros: o cadastro guarda a página de
entrada da visita (`page_origin`, v1.4.1545), então dá para saber quantas contas
começaram num artigo e quantas viraram teste ou assinatura.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional

from services import origem_trafego as OT
from services.seo_html import BLOG_SLUGS

COL = "blog_eventos"

TIPOS = {"leitura", "clique"}
# Onde fica o botão no artigo. Lista fechada: valor fora dela é recusado.
POSICOES = {
    "topo": "Botão do topo",
    "meio": "Chamada no texto",
    "fim": "Faixa do fim",
    "link": "Link contextual",
    "servico": "Serviço relacionado",
    "relacionado": "Artigo relacionado",
    "pagina": "Abertura do artigo",
}


def valida(slug: str, tipo: str, posicao: str) -> Optional[str]:
    """Devolve a mensagem de erro, ou None se o evento é aceitável."""
    if slug not in BLOG_SLUGS:
        return "Artigo desconhecido."
    if tipo not in TIPOS:
        return "Tipo de evento desconhecido."
    if posicao not in POSICOES:
        return "Posição desconhecida."
    if tipo == "leitura" and posicao != "pagina":
        return "Leitura só é contada na abertura do artigo."
    if tipo == "clique" and posicao == "pagina":
        return "Clique precisa de uma posição de botão."
    return None


def chave(dia: str, slug: str, tipo: str, posicao: str) -> str:
    return f"{dia}:{slug}:{tipo}:{posicao}"


def dia_hoje(agora: Optional[datetime] = None) -> str:
    return (agora or datetime.utcnow()).strftime("%Y-%m-%d")


def dia_corte(dias: int, agora: Optional[datetime] = None) -> str:
    return ((agora or datetime.utcnow()) - timedelta(days=dias - 1)).strftime("%Y-%m-%d")


def _slug_da_entrada(page_origin: str) -> Optional[str]:
    p = (page_origin or "").split("?", 1)[0].split("#", 1)[0].rstrip("/")
    if not p.startswith("/blog/"):
        return None
    s = p[len("/blog/"):]
    return s if s in BLOG_SLUGS else None


def resumo(eventos: Iterable[dict], usuarios: Iterable[dict], dias: int,
           agora: Optional[datetime] = None, titulos: Optional[dict] = None) -> dict:
    """Funil por artigo: leituras → cliques → cadastros → teste/assinatura.

    `eventos`: docs da coleção (já filtrados pelo período ou não — filtra de novo aqui).
    `usuarios`: docs de `users` (só `page_origin`, `created_at` e dados de plano são lidos).
    """
    agora = agora or datetime.utcnow()
    corte_dia = dia_corte(dias, agora)
    corte_dt = agora - timedelta(days=dias)
    titulos = titulos or {}

    por: dict = {}

    def item(slug):
        return por.setdefault(slug, {
            "slug": slug, "titulo": titulos.get(slug) or slug,
            "leituras": 0, "cliques": 0, "cliques_por_posicao": {},
            "cadastros": 0, "em_teste": 0, "assinantes": 0, "nunca_acessaram": 0,
        })

    for e in eventos or []:
        if (e.get("dia") or "") < corte_dia or e.get("slug") not in BLOG_SLUGS:
            continue
        it = item(e["slug"])
        n = int(e.get("n") or 0)
        if e.get("tipo") == "leitura":
            it["leituras"] += n
        elif e.get("tipo") == "clique":
            it["cliques"] += n
            pos = e.get("posicao") or "?"
            it["cliques_por_posicao"][pos] = it["cliques_por_posicao"].get(pos, 0) + n

    for u in usuarios or []:
        slug = _slug_da_entrada(u.get("page_origin") or "")
        if not slug:
            continue
        criado = OT._naive(u.get("created_at"))
        if criado and criado < corte_dt:
            continue
        it = item(slug)
        it["cadastros"] += 1
        sit = OT.situacao_do_cadastro(u)
        if sit == "assinante":
            it["assinantes"] += 1
        elif sit == "em_teste":
            it["em_teste"] += 1
        if not u.get("last_login_at") and not u.get("login_count"):
            it["nunca_acessaram"] += 1

    artigos = sorted(por.values(), key=lambda x: (-x["cadastros"], -x["cliques"], -x["leituras"], x["slug"]))
    for a in artigos:
        a["taxa_clique"] = round(100.0 * a["cliques"] / a["leituras"], 1) if a["leituras"] else 0.0
    totais = {k: sum(a[k] for a in artigos)
              for k in ("leituras", "cliques", "cadastros", "em_teste", "assinantes", "nunca_acessaram")}
    totais["taxa_clique"] = round(100.0 * totais["cliques"] / totais["leituras"], 1) if totais["leituras"] else 0.0
    return {"dias": dias, "totais": totais, "artigos": artigos, "posicoes": POSICOES}
