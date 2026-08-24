# @module services.inferencia.blocos_ptam — seções do tratamento científico DENTRO do laudo PTAM.
#
# Quando o PTAM está vinculado a um modelo homologado, o laudo deixa de mostrar
# só a média das amostras e passa a trazer a regressão: coeficientes, pressupostos,
# gráficos e enquadramento — que é o que sustenta o Grau III em perícia.
#
# Recebe o SNAPSHOT congelado no vínculo (nunca o modelo vivo) e devolve
# flowables ReportLab, para o ptam_pdf_v2 apenas inserir onde manda a norma.
import io
import logging

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Image, KeepTogether, Paragraph, Spacer, Table, TableStyle

from services.inferencia import graficos as GRAF

logger = logging.getLogger("romatec")


def _n(v, casas=2) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return f"{float(v):,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def _pct(v, casas=2) -> str:
    return "—" if v is None else _n(float(v) * 100, casas) + "%"


def _sig(v) -> str:
    if v is None:
        return "—"
    v = float(v)
    return "< 0,0001%" if v * 100 < 1e-4 else _n(v * 100, 4) + "%"


def _brl(v) -> str:
    return "—" if v is None else "R$ " + _n(v, 2)


def tem_inferencia(ptam: dict) -> bool:
    snap = (ptam or {}).get("inferencia_snapshot") or {}
    return bool((snap.get("resultado") or {}).get("predicao"))


def resumo_metodologia(ptam: dict) -> list:
    """Linhas extras da Seção 6 (Metodologia) quando o valor vem da regressão."""
    snap = (ptam or {}).get("inferencia_snapshot") or {}
    r = snap.get("resultado") or {}
    enq = snap.get("enquadramento") or r.get("enquadramento") or {}
    return [
        ("Tratamento", "Científico — inferência estatística (regressão linear, OLS)"),
        ("Modelo", f"{snap.get('nome') or '—'} (v{snap.get('versao') or 1}, homologado)"),
        ("Norma de enquadramento", f"ABNT NBR {snap.get('norma') or '14653-2'}"),
        ("Amostra", f"{r.get('n', '—')} dados · {r.get('k', '—')} variáveis independentes"),
        ("Grau de Fundamentação", f"Grau {enq.get('grau_fundamentacao', '—')}"),
        ("Grau de Precisão",
         f"Grau {enq.get('grau_precisao', '—')} (amplitude do IP 80% = "
         f"{_pct(enq.get('amplitude_ip80'))})"),
    ]


def flowables(ptam: dict, largura: float, estilos: dict) -> list:
    """Bloco completo do tratamento científico, para entrar após os cálculos.

    `estilos` traz os ParagraphStyle do laudo (sBody, sCell, sub) — o bloco usa a
    tipografia do PTAM, não uma própria, para não destoar do resto do documento.
    """
    snap = (ptam or {}).get("inferencia_snapshot") or {}
    r = snap.get("resultado") or {}
    if not r:
        return []

    sBody = estilos["body"]
    sCell = estilos["cell"]
    sub = estilos["sub"]          # callable: (titulo, ancora) -> [flowables]
    tblh = estilos["tbl_header"]  # callable: (header, linhas, larguras) -> Table

    pred = r.get("predicao") or {}
    diag = r.get("diagnostico") or {}
    enq = snap.get("enquadramento") or r.get("enquadramento") or {}
    st = []

    # ── Especificação e equação ──
    st += sub("Modelo de Regressão Adotado", "sec7inf")
    esp = snap.get("especificacao") or {}
    dep = esp.get("dependente") or {}
    linhas = [["Variável", "Papel", "Transformação"]]
    linhas.append([dep.get("campo", "—"), "dependente", dep.get("transformacao", "identidade")])
    for reg in (esp.get("regressores") or []):
        linhas.append([reg.get("rotulo") or reg.get("campo"), "regressor",
                       reg.get("transformacao", "identidade")])
    st.append(tblh(["Variável", "Papel", "Transformação"], linhas[1:],
                   [largura * 0.40, largura * 0.28, largura * 0.32]))
    st.append(Spacer(1, 6))
    if r.get("equacao"):
        st.append(Paragraph(f"<b>Equação estimada:</b> {r['equacao']}", sBody))
        st.append(Spacer(1, 8))

    # ── Coeficientes ──
    linhas = [[g["nome"], _n(g["coeficiente"], 6), _n(g["erro_padrao"], 6),
               _n(g["t"], 4), _sig(g["significancia"])]
              for g in (r.get("regressores") or [])]
    st.append(tblh(["Regressor", "Coeficiente", "Erro-padrão", "t", "Significância"],
                   linhas, [largura * 0.28, largura * 0.19, largura * 0.19,
                            largura * 0.14, largura * 0.20]))
    st.append(Spacer(1, 6))
    st.append(tblh(["n", "k", "GL", "R²", "R² aj.", "F", "Signif. F"],
                   [[r.get("n"), r.get("k"), r.get("graus_liberdade"),
                     _n(r.get("r2"), 4), _n(r.get("r2_ajustado"), 4),
                     _n(r.get("f"), 3), _sig(r.get("signif_f"))]],
                   [largura / 7] * 7))
    st.append(Spacer(1, 10))

    # ── Pressupostos ──
    st += sub("Verificação dos Pressupostos do Modelo", "sec7press")
    linhas = []
    for chave, rotulo in (("normalidade_ks", "Normalidade — Kolmogorov-Smirnov"),
                          ("normalidade_jb", "Normalidade — Jarque-Bera"),
                          ("homocedasticidade_bp", "Homocedasticidade — Breusch-Pagan"),
                          ("homocedasticidade_white", "Homocedasticidade — White")):
        d = diag.get(chave) or {}
        atende = d.get("atende")
        linhas.append([rotulo, _n(d.get("estatistica"), 4), _n(d.get("p_valor"), 4),
                       "atende" if atende else ("—" if atende is None else "não atende")])
    dw = diag.get("durbin_watson") or {}
    linhas.append(["Não-autocorrelação — Durbin-Watson", _n(dw.get("estatistica"), 4), "—",
                   "atende" if dw.get("atende") else "não atende"])
    st.append(tblh(["Teste", "Estatística", "p-valor", "Situação"], linhas,
                   [largura * 0.46, largura * 0.18, largura * 0.16, largura * 0.20]))
    st.append(Spacer(1, 6))

    if diag.get("vif"):
        st.append(tblh(["Variável", "VIF"],
                       [[v["nome"], _n(v["vif"], 3)] for v in diag["vif"]],
                       [largura * 0.62, largura * 0.38]))
        st.append(Spacer(1, 6))

    outliers = diag.get("outliers") or []
    descartados = {a.get("dado_id"): a.get("motivo_descarte")
                   for a in (snap.get("amostra") or []) if not a.get("utilizado", True)}
    if outliers:
        st.append(tblh(["Dado discrepante", "Resíduo padronizado", "Decisão do avaliador"],
                       [[o["id"], _n(o["residuo_padronizado"], 3),
                         f"descartado — {descartados[o['id']]}" if o["id"] in descartados
                         else "mantido na amostra"] for o in outliers],
                       [largura * 0.22, largura * 0.28, largura * 0.50]))
    else:
        st.append(Paragraph("Não há pontos com resíduo padronizado fora de ±2σ.", sBody))
    st.append(Spacer(1, 10))

    # ── Gráficos 2×2 ──
    imagens = []
    for chave in ("residuos", "observado_estimado", "histograma", "qq"):
        registro = (snap.get("graficos") or {}).get(chave)
        raw = GRAF.carregar_bytes(registro) if registro else b""
        if not raw:
            continue
        try:
            img = Image(io.BytesIO(raw))
            escala = (largura / 2 - 6) / img.imageWidth
            img.drawWidth, img.drawHeight = largura / 2 - 6, img.imageHeight * escala
            imagens.append(img)
        except Exception as e:   # noqa: BLE001 — gráfico é acessório
            logger.warning("PTAM/inferência: gráfico %s ignorado (%s)", chave, e)
    if imagens:
        grade = [imagens[i:i + 2] for i in range(0, len(imagens), 2)]
        if len(grade[-1]) == 1:
            grade[-1].append("")
        t = Table(grade, colWidths=[largura / 2, largura / 2])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 2),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        st += sub("Gráficos de Diagnóstico", "sec7graf")
        st.append(t)
        st.append(Spacer(1, 8))

    # ── Enquadramento ──
    bloco = sub("Enquadramento — ABNT NBR " + str(snap.get("norma") or "14653-2"), "sec7enq")
    bloco.append(tblh(["Item", "Grau", "Apuração"],
                      [[i["item"], f"Grau {i['grau']}", i["detalhe"]]
                       for i in (enq.get("itens") or [])],
                      [largura * 0.34, largura * 0.13, largura * 0.53]))
    bloco.append(Spacer(1, 6))
    ip = pred.get("ip80") or {}
    bloco.append(Paragraph(
        f"<b>Valor central estimado:</b> {_brl(pred.get('valor_central'))}/unidade · "
        f"<b>IP 80%:</b> {_brl(ip.get('inferior'))} a {_brl(ip.get('superior'))} "
        f"(amplitude {_pct(pred.get('amplitude_ip80'))}).", sBody))
    if pred.get("observacao_destransformacao"):
        bloco.append(Paragraph(f"<i>{pred['observacao_destransformacao']}</i>", sCell))
    if enq.get("bloqueios_grau_iii"):
        bloco.append(Spacer(1, 4))
        bloco.append(Paragraph("<b>Restrições ao Grau III:</b> "
                               + "; ".join(enq["bloqueios_grau_iii"]) + ".", sBody))
    st.append(KeepTogether(bloco))
    return st
