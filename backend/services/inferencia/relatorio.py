# @module services.inferencia.relatorio — payload e PDF do tratamento científico.
#
# Nove seções na ordem do MD §11. Cabeçalho verde com filete dourado, Times,
# tabelas com header verde e linhas alternadas — mesma identidade dos demais
# laudos (reusa pdf.themes.prime2_theme e pdf.brand_seal).
#
# `montar_payload` é a FONTE ÚNICA: a tela e o PDF leem os mesmos números, para
# o laudo reproduzir exatamente o que o avaliador viu (critério de aceite).
import io
import logging

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, Spacer,
                                Table, TableStyle)

from pdf.brand_seal import draw_header_monogram, draw_header_lockup
from pdf.templates.resilient import ResilientSimpleDocTemplate
from pdf.themes import prime2_theme as T
from services.inferencia import graficos as GRAF

logger = logging.getLogger("romatec")

GRAU_TEXTO = {"III": "Grau III", "II": "Grau II", "I": "Grau I",
              "fora": "não atendido"}


# ── Formatação pt-BR ─────────────────────────────────────────────────────────
def _n(v, casas=2) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return f"{float(v):,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _brl(v) -> str:
    return "R$ " + _n(v, 2) if v is not None else "—"


def _pct(v, casas=2) -> str:
    return "—" if v is None else _n(float(v) * 100, casas) + "%"


def _sig(v) -> str:
    """Significância como percentual — < 0,0001% quando ínfima."""
    if v is None:
        return "—"
    v = float(v)
    return "< 0,0001%" if v * 100 < 1e-4 else _n(v * 100, 4) + "%"


def _sim_nao(v) -> str:
    return "atende" if v else ("—" if v is None else "não atende")


# ── Payload (tela e PDF leem daqui) ──────────────────────────────────────────
def montar_payload(doc: dict) -> dict:
    r = doc.get("resultado") or {}
    esp = doc.get("especificacao") or {}
    pred = r.get("predicao") or {}
    enq = r.get("enquadramento") or doc.get("enquadramento") or {}
    amostra = doc.get("amostra") or []

    utilizados = [a for a in amostra if a.get("utilizado", True)]
    descartados = [a for a in amostra if not a.get("utilizado", True)]

    return {
        "modelo": {
            "id": doc.get("id"), "nome": doc.get("nome"),
            "status": doc.get("status"), "versao": doc.get("versao", 1),
            "tipo_imovel": doc.get("tipo_imovel"), "norma": doc.get("norma"),
            "homologado_em": doc.get("homologado_em"),
        },
        "avaliando": doc.get("avaliando") or {},
        "area_total_avaliando": doc.get("area_total_avaliando"),
        "amostra": {
            "total": len(amostra),
            "utilizados": len(utilizados),
            "descartados": [
                {"dado_id": a.get("dado_id"), "motivo": a.get("motivo_descarte")}
                for a in descartados
            ],
            "linhas": amostra,
        },
        "especificacao": esp,
        "equacao": r.get("equacao"),
        "estatisticas": {k: r.get(k) for k in
                         ("n", "k", "graus_liberdade", "r2", "r2_ajustado",
                          "erro_padrao_estimativa", "f", "signif_f")},
        "regressores": r.get("regressores") or [],
        "diagnostico": r.get("diagnostico") or {},
        "extrapolacoes": r.get("extrapolacoes") or [],
        "predicao": pred,
        "enquadramento": enq,
        "graficos": doc.get("graficos") or {},
        "checklist_manual": doc.get("checklist_manual") or {},
    }


# ── PDF ──────────────────────────────────────────────────────────────────────
def _estilos():
    f = T.fonts()
    return {
        "titulo": ParagraphStyle("tit", fontName=f["serif_bold"], fontSize=13,
                                 textColor=T.C_VERDE_ESCURO, spaceAfter=6, leading=16),
        "secao": ParagraphStyle("sec", fontName=f["serif_bold"], fontSize=10.5,
                                textColor=colors.white, leading=13),
        "corpo": ParagraphStyle("corpo", fontName=f["serif"], fontSize=9.4,
                                textColor=T.C_TEXTO, leading=13.4, alignment=TA_JUSTIFY),
        "nota": ParagraphStyle("nota", fontName=f["serif_italic"], fontSize=8.2,
                               textColor=T.C_CINZA_TEXTO, leading=11, alignment=TA_JUSTIFY),
        "cel": ParagraphStyle("cel", fontName=f["sans"], fontSize=7.6,
                              textColor=T.C_TEXTO, leading=9.6),
        "cel_b": ParagraphStyle("celb", fontName=f["sans_bold"], fontSize=7.6,
                                textColor=colors.white, leading=9.6),
        "centro": ParagraphStyle("centro", fontName=f["serif_bold"], fontSize=11,
                                 textColor=T.C_VERDE_ESCURO, alignment=TA_CENTER, leading=15),
    }


def _cabecalho_secao(numero: int, titulo: str, st, largura) -> Table:
    t = Table([[Paragraph(f"{numero:02d}", st["secao"]), Paragraph(titulo.upper(), st["secao"])]],
              colWidths=[1.1 * cm, largura - 1.1 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), T.C_VERDE_ESCURO),
        ("BACKGROUND", (0, 0), (0, 0), T.C_DOURADO),
        ("TEXTCOLOR", (0, 0), (0, 0), T.C_VERDE_ESCURO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
    ]))
    return t


def _tabela(dados, larguras, st, header=True, align_dir=()):
    linhas = [[Paragraph(str(c), st["cel_b"] if (header and i == 0) else st["cel"])
               for c in linha] for i, linha in enumerate(dados)]
    t = Table(linhas, colWidths=larguras, repeatRows=1 if header else 0)
    estilo = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        estilo += [("BACKGROUND", (0, 0), (-1, 0), T.C_VERDE_ESCURO)]
        for i in range(1, len(linhas)):
            if i % 2 == 0:
                estilo.append(("BACKGROUND", (0, i), (-1, i), T.C_OFFWHITE))
    for col in align_dir:
        estilo.append(("ALIGN", (col, 0), (col, -1), "RIGHT"))
    t.setStyle(TableStyle(estilo))
    return t


def _on_page(canvas, doc_):
    """Cabeçalho com o monograma + filete dourado; rodapé com o lockup."""
    canvas.saveState()
    w, h = A4
    draw_header_monogram(canvas, 2.0 * cm, h - 1.15 * cm)
    canvas.setStrokeColor(T.C_DOURADO)
    canvas.setLineWidth(0.9)
    canvas.line(2.0 * cm, h - 1.85 * cm, w - 2.0 * cm, h - 1.85 * cm)
    canvas.setFont(T.fonts()["sans"], 7)
    canvas.setFillColor(T.C_CINZA_TEXTO)
    canvas.drawRightString(w - 2.0 * cm, h - 1.45 * cm,
                           "TRATAMENTO CIENTÍFICO — INFERÊNCIA ESTATÍSTICA")
    draw_header_lockup(canvas, 2.0 * cm, 1.25 * cm, mark=7 * mm,
                       tagline="ABNT NBR 14.653")
    canvas.setFont(T.fonts()["sans"], 7)
    canvas.drawRightString(w - 2.0 * cm, 1.15 * cm, f"Pág. {doc_.page}")
    canvas.restoreState()


def gerar_pdf(doc: dict, tema: str = "prime2") -> bytes:
    p = montar_payload(doc)
    st = _estilos()
    buf = io.BytesIO()
    pdf = ResilientSimpleDocTemplate(
        buf, pagesize=A4, leftMargin=2.0 * cm, rightMargin=2.0 * cm,
        topMargin=2.35 * cm, bottomMargin=2.0 * cm,
        title=f"Inferência Estatística — {p['modelo'].get('nome')}")
    L = pdf.width
    S = []

    est, pred, enq, diag = (p["estatisticas"], p["predicao"], p["enquadramento"],
                            p["diagnostico"])

    S.append(Paragraph("LAUDO DE TRATAMENTO CIENTÍFICO — INFERÊNCIA ESTATÍSTICA", st["titulo"]))
    S.append(Paragraph(
        f"Modelo <b>{p['modelo'].get('nome')}</b> · versão {p['modelo'].get('versao')} · "
        f"norma ABNT NBR {p['modelo'].get('norma')} · "
        f"situação: {p['modelo'].get('status')}", st["nota"]))
    S.append(Spacer(1, 10))

    # 1. Identificação do imóvel avaliando
    S.append(_cabecalho_secao(1, "Identificação do imóvel avaliando", st, L))
    S.append(Spacer(1, 5))
    linhas = [["Característica", "Valor adotado"]]
    for k, v in (p["avaliando"] or {}).items():
        linhas.append([k, _n(v, 2) if isinstance(v, (int, float)) else str(v)])
    if p.get("area_total_avaliando"):
        linhas.append(["área total considerada", _n(p["area_total_avaliando"]) + " m²"])
    S.append(_tabela(linhas, [L * 0.55, L * 0.45], st, align_dir=(1,)))
    S.append(Spacer(1, 12))

    # 2. Amostra de mercado
    S.append(_cabecalho_secao(2, "Amostra de mercado e saneamento", st, L))
    S.append(Spacer(1, 5))
    campos = []
    for a in p["amostra"]["linhas"][:1]:
        campos = list((a.get("variaveis") or {}).keys())
    campos = campos[:7]
    cab = ["Dado"] + campos + ["Situação"]
    linhas = [cab]
    for a in p["amostra"]["linhas"]:
        v = a.get("variaveis") or {}
        linhas.append(
            [a.get("dado_id") or "—"]
            + [_n(v.get(c), 2) if isinstance(v.get(c), (int, float)) else str(v.get(c) or "—")
               for c in campos]
            + ["utilizado" if a.get("utilizado", True)
               else f"descartado — {a.get('motivo_descarte') or 'sem motivo'}"])
    col = [L * 0.10] + [(L * 0.62) / max(1, len(campos))] * len(campos) + [L * 0.28]
    S.append(_tabela(linhas, col, st))
    S.append(Spacer(1, 4))
    S.append(Paragraph(
        f"Total coletado: {p['amostra']['total']} dados; efetivamente utilizados: "
        f"{p['amostra']['utilizados']}; descartados: {len(p['amostra']['descartados'])}.",
        st["nota"]))
    S.append(Spacer(1, 12))

    # 3. Especificação do modelo
    S.append(_cabecalho_secao(3, "Especificação do modelo e transformações", st, L))
    S.append(Spacer(1, 5))
    dep = (p["especificacao"].get("dependente") or {})
    linhas = [["Variável", "Papel", "Transformação", "Tipo"]]
    linhas.append([dep.get("campo", "—"), "dependente",
                   dep.get("transformacao", "identidade"), "—"])
    for r in (p["especificacao"].get("regressores") or []):
        linhas.append([r.get("rotulo") or r.get("campo"), "regressor",
                       r.get("transformacao", "identidade"), r.get("tipo", "quantitativa")])
    S.append(_tabela(linhas, [L * 0.31, L * 0.19, L * 0.28, L * 0.22], st))
    S.append(Spacer(1, 12))

    # 4. Resultado da regressão
    S.append(_cabecalho_secao(4, "Resultado da regressão", st, L))
    S.append(Spacer(1, 5))
    linhas = [["Regressor", "Coeficiente", "Erro-padrão", "t", "Significância"]]
    for r in p["regressores"]:
        linhas.append([r["nome"], _n(r["coeficiente"], 6), _n(r["erro_padrao"], 6),
                       _n(r["t"], 4), _sig(r["significancia"])])
    S.append(_tabela(linhas, [L * 0.28, L * 0.19, L * 0.19, L * 0.14, L * 0.20], st,
                     align_dir=(1, 2, 3, 4)))
    S.append(Spacer(1, 6))
    linhas = [["n", "k", "GL", "R²", "R² ajustado", "Erro-padrão", "F", "Signif. F"],
              [est.get("n"), est.get("k"), est.get("graus_liberdade"),
               _n(est.get("r2"), 4), _n(est.get("r2_ajustado"), 4),
               _n(est.get("erro_padrao_estimativa"), 6), _n(est.get("f"), 3),
               _sig(est.get("signif_f"))]]
    S.append(_tabela(linhas, [L / 8] * 8, st))
    S.append(Spacer(1, 6))
    S.append(Paragraph(f"<b>Equação estimada:</b> {p.get('equacao') or '—'}", st["corpo"]))
    S.append(Spacer(1, 12))

    # 5. Verificação dos pressupostos
    S.append(_cabecalho_secao(5, "Verificação dos pressupostos", st, L))
    S.append(Spacer(1, 5))
    linhas = [["Teste", "Estatística", "p-valor", "Situação"]]
    for chave, rotulo in (("normalidade_ks", "Normalidade — Kolmogorov-Smirnov (Lilliefors)"),
                          ("normalidade_jb", "Normalidade — Jarque-Bera"),
                          ("homocedasticidade_bp", "Homocedasticidade — Breusch-Pagan"),
                          ("homocedasticidade_white", "Homocedasticidade — White")):
        d = diag.get(chave) or {}
        linhas.append([rotulo, _n(d.get("estatistica"), 4), _n(d.get("p_valor"), 4),
                       _sim_nao(d.get("atende"))])
    dw = diag.get("durbin_watson") or {}
    linhas.append(["Não-autocorrelação — Durbin-Watson", _n(dw.get("estatistica"), 4),
                   "—", _sim_nao(dw.get("atende"))])
    S.append(_tabela(linhas, [L * 0.48, L * 0.17, L * 0.15, L * 0.20], st, align_dir=(1, 2)))
    S.append(Spacer(1, 6))

    ader = diag.get("aderencia_residuos") or {}
    linhas = [["Faixa", "Observado", "Teórico"]]
    for faixa, rot in (("1.00", "±1,00σ"), ("1.64", "±1,64σ"), ("1.96", "±1,96σ")):
        d = ader.get(faixa) or {}
        linhas.append([rot, _pct(d.get("observado"), 1), _pct(d.get("teorico"), 0)])
    S.append(_tabela(linhas, [L * 0.34, L * 0.33, L * 0.33], st, align_dir=(1, 2)))
    S.append(Spacer(1, 6))

    if diag.get("vif"):
        linhas = [["Variável", "VIF", "Situação"]]
        for v in diag["vif"]:
            linhas.append([v["nome"], _n(v["vif"], 3),
                           _sim_nao(v.get("atende", v["vif"] < 10))])
        S.append(_tabela(linhas, [L * 0.48, L * 0.26, L * 0.26], st, align_dir=(1,)))
        S.append(Spacer(1, 6))

    if diag.get("outliers"):
        linhas = [["Dado", "Resíduo padronizado", "Decisão do avaliador"]]
        for o in diag["outliers"]:
            desc = next((d for d in p["amostra"]["descartados"] if d["dado_id"] == o["id"]), None)
            linhas.append([o["id"], _n(o["residuo_padronizado"], 3),
                           f"descartado — {desc['motivo']}" if desc else "mantido na amostra"])
        S.append(_tabela(linhas, [L * 0.20, L * 0.28, L * 0.52], st, align_dir=(1,)))
    else:
        S.append(Paragraph("Não há pontos com resíduo padronizado fora de ±2σ.", st["nota"]))
    S.append(Spacer(1, 12))

    # 6. Gráficos de diagnóstico (2×2)
    imagens = []
    for chave in ("residuos", "observado_estimado", "histograma", "qq"):
        registro = (p.get("graficos") or {}).get(chave)
        raw = GRAF.carregar_bytes(registro) if registro else b""
        if raw:
            img = Image(io.BytesIO(raw))
            escala = (L / 2 - 6) / img.imageWidth
            img.drawWidth = L / 2 - 6
            img.drawHeight = img.imageHeight * escala
            imagens.append(img)
    if imagens:
        S.append(PageBreak())
        S.append(_cabecalho_secao(6, "Gráficos de diagnóstico", st, L))
        S.append(Spacer(1, 6))
        grade = [imagens[i:i + 2] for i in range(0, len(imagens), 2)]
        if len(grade[-1]) == 1:
            grade[-1].append("")
        t = Table(grade, colWidths=[L / 2, L / 2])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 2),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        S.append(t)
        S.append(Spacer(1, 12))

    # 7. Estimativa de valor
    S.append(_cabecalho_secao(7, "Estimativa de valor", st, L))
    S.append(Spacer(1, 5))
    linhas = [["", "Valor unitário (R$/m²)", "Valor total (R$)"]]
    tot = pred.get("total") or {}

    def _par(rot, unit, total):
        linhas.append([rot, _brl(unit), _brl(total) if total else "—"])

    _par("Limite inferior do IP 80%", pred.get("ip80", {}).get("inferior"),
         tot.get("ip80", {}).get("inferior"))
    _par("Valor central estimado", pred.get("valor_central"), tot.get("valor_central"))
    _par("Limite superior do IP 80%", pred.get("ip80", {}).get("superior"),
         tot.get("ip80", {}).get("superior"))
    _par("Campo de arbítrio (−15%)", pred.get("campo_arbitrio", {}).get("inferior"),
         tot.get("campo_arbitrio", {}).get("inferior"))
    _par("Campo de arbítrio (+15%)", pred.get("campo_arbitrio", {}).get("superior"),
         tot.get("campo_arbitrio", {}).get("superior"))
    S.append(_tabela(linhas, [L * 0.42, L * 0.29, L * 0.29], st, align_dir=(1, 2)))
    S.append(Spacer(1, 5))
    S.append(Paragraph(
        f"Amplitude do intervalo de predição de 80%: <b>{_pct(pred.get('amplitude_ip80'))}</b> "
        f"do valor central. O intervalo de confiança de 80% da média situa-se entre "
        f"{_brl(pred.get('ic80', {}).get('inferior'))} e "
        f"{_brl(pred.get('ic80', {}).get('superior'))} por m².", st["corpo"]))
    if pred.get("observacao_destransformacao"):
        S.append(Spacer(1, 4))
        S.append(Paragraph(pred["observacao_destransformacao"], st["nota"]))
    S.append(Spacer(1, 12))

    # 8. Enquadramento na norma
    S.append(_cabecalho_secao(8, f"Enquadramento — ABNT NBR {p['modelo'].get('norma')}", st, L))
    S.append(Spacer(1, 5))
    linhas = [["Item", "Grau", "Apuração"]]
    for item in (enq.get("itens") or []):
        linhas.append([item["item"], GRAU_TEXTO.get(item["grau"], item["grau"]),
                       item["detalhe"]])
    S.append(_tabela(linhas, [L * 0.34, L * 0.13, L * 0.53], st))
    S.append(Spacer(1, 6))

    faixa = Table([[Paragraph(
        f"FUNDAMENTAÇÃO: {GRAU_TEXTO.get(enq.get('grau_fundamentacao'), '—')} &nbsp;·&nbsp; "
        f"PRECISÃO: {GRAU_TEXTO.get(enq.get('grau_precisao'), '—')}",
        ParagraphStyle("g", fontName=T.fonts()["serif_bold"], fontSize=11,
                       textColor=colors.white, alignment=TA_CENTER))]], colWidths=[L])
    faixa.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), T.C_VERDE_ESCURO),
                               ("TOPPADDING", (0, 0), (-1, -1), 7),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                               ("BOX", (0, 0), (-1, -1), 1.1, T.C_DOURADO)]))
    S.append(faixa)

    if enq.get("bloqueios_grau_iii"):
        S.append(Spacer(1, 6))
        S.append(Paragraph("<b>Restrições ao Grau III:</b>", st["corpo"]))
        for b in enq["bloqueios_grau_iii"]:
            S.append(Paragraph(f"• {b}", st["nota"]))
    if p.get("checklist_manual"):
        S.append(Spacer(1, 5))
        marcados = [k for k, v in p["checklist_manual"].items() if v]
        if marcados:
            S.append(Paragraph("<b>Conferência manual do responsável técnico:</b> "
                               + "; ".join(marcados) + ".", st["nota"]))
    S.append(Spacer(1, 14))

    # 9. Assinatura do RT
    av = doc.get("_avaliador") or {}
    S.append(_cabecalho_secao(9, "Responsável técnico", st, L))
    S.append(Spacer(1, 16))
    S.append(Paragraph("_" * 52, st["centro"]))
    S.append(Paragraph((av.get("nome") or "").upper() or "Responsável Técnico", st["centro"]))
    registros = av.get("registros") or av.get("registros_linha") or ""
    if registros:
        S.append(Paragraph(str(registros), st["nota"]))
    S.append(Spacer(1, 6))
    S.append(Paragraph(
        "Laudo elaborado por tratamento científico (inferência estatística), conforme "
        f"ABNT NBR {p['modelo'].get('norma')}. Os intervalos apresentados referem-se ao "
        "nível de confiança de 80%, na forma da norma.", st["nota"]))

    pdf.build(S, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()
