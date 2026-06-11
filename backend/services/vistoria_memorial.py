# @module services.vistoria_memorial — Memorial de Vistoria (caracterização) p/ importar no PTAM
"""
Gera o `memorial_vistoria` — texto técnico de CARACTERIZAÇÃO do imóvel a partir da
vistoria, SEM as seções de metodologia avaliatória (que pertencem ao PTAM).

Saída em HTML simples (<p>...</p>) para colar no RichTextEditor do PTAM.
Cobre vistorias de Averbação (reusa o gerador de seções) e vistorias genéricas do TVI.
"""
from __future__ import annotations

import html as _html


def _p(txt: str) -> str:
    t = (txt or "").strip()
    return f"<p>{_html.escape(t)}</p>" if t else ""


def gerar_memorial_vistoria(vistoria: dict) -> str:
    vistoria = vistoria or {}
    blocos: list[str] = []

    av = vistoria.get("averbacao")
    if av:
        # Reusa as seções da averbação, mantendo só a CARACTERIZAÇÃO
        # (objeto, confronto de áreas e sistemas construtivos).
        try:
            from services.vistoria_averbacao_relatorio import gerar_secoes_averbacao
            secoes = {t: c for t, c in gerar_secoes_averbacao(vistoria)}
        except Exception:
            secoes = {}
        for chave in ("OBJETO E FINALIDADE", "CONFRONTO DE ÁREAS", "SISTEMAS CONSTRUTIVOS"):
            corpo = secoes.get(chave)
            if corpo:
                for par in str(corpo).split("\n"):
                    blocos.append(_p(par))
    else:
        # Vistoria genérica do TVI — caracterização a partir dos campos.
        end = vistoria.get("imovel_endereco")
        if end:
            blocos.append(_p(f"Imóvel objeto da vistoria localizado em {end}"
                             + (f", matrícula nº {vistoria.get('imovel_matricula')}" if vistoria.get("imovel_matricula") else "") + "."))
        if vistoria.get("imovel_tipo"):
            blocos.append(_p(f"Tipologia: {vistoria['imovel_tipo']}."))
        # Ambientes vistoriados
        ambientes = vistoria.get("ambientes") or []
        for amb in ambientes:
            if not isinstance(amb, dict) or not amb.get("nome"):
                continue
            partes = [f"<b>{_html.escape(amb['nome'])}</b>"]
            if amb.get("descricao"):
                partes.append(_html.escape(amb["descricao"]))
            if amb.get("estado_conservacao"):
                partes.append(f"Estado de conservação: {_html.escape(amb['estado_conservacao'])}.")
            if amb.get("observacoes"):
                partes.append(_html.escape(amb["observacoes"]))
            blocos.append("<p>" + " — ".join(partes) + "</p>")
        if vistoria.get("conclusao_tecnica"):
            blocos.append(_p(vistoria["conclusao_tecnica"]))

    blocos = [b for b in blocos if b]
    if not blocos:
        blocos = [_p("Caracterização do imóvel conforme vistoria técnica realizada.")]
    return "".join(blocos)
