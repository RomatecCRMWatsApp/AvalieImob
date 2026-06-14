# @module pdf.templates.procuracao_prime — PROCURAÇÃO PARTICULAR no layout PRIME
# (mesma capa verde/dourado + tipografia + section headers do contrato_prime2), para
# bater visualmente com o contrato. Reusa _styles/SecaoHeader/_draw_capa/_draw_footer
# do prime2 e os helpers de conteúdo (qualificação/poderes) de routes.contratos.
import io
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    Frame, KeepTogether, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

from pdf.themes import prime2_theme as T
from pdf.templates.contrato_prime2 import (
    _styles, SecaoHeader, _draw_capa, _draw_footer, MARGIN, PAGE_W, PAGE_H,
)
from pdf.templates.resilient import ResilientBaseDocTemplate

logger = logging.getLogger("romatec")


def render_procuracao(doc: dict, uid: str, empresa: str) -> bytes:
    """PDF da PROCURAÇÃO no layout Prime. Mesmo conteúdo jurídico do gerador sóbrio
    (_generate_procuracao_pdf_bytes), mas com capa/tipografia Prime."""
    from routes.contratos import (
        _qualifica_pf, _qualifica_pj, _data_extenso, _PODER_TEXTO_BASE, _s, _BLANK,
        _qualifica_outorgado,
    )
    from pdf.templates.contrato_base import codigo_contrato, _xml_escape, _norm_matricula
    from pdf.templates.contrato_prime2 import _endereco_full

    T.registrar_fontes()
    st = _styles()
    proc = doc.get("procuracao") or {}
    obj = doc.get("objeto") or {}
    cor = doc.get("corretor") or {}
    outorgantes = doc.get("vendedores") or []
    contratante = outorgantes[0] if (outorgantes and isinstance(outorgantes[0], dict)) else {}

    base_cod = codigo_contrato(doc)  # CONT_EXCLUSIV-AAAA-NNNN
    codigo = (base_cod.replace("CONT_EXCLUSIV-", "PROCURACAO-")
              .replace("CONT-", "PROCURACAO-")
              .replace("CV-", "PROCURACAO-"))

    meta = {
        "codigo": codigo,
        "titulo_linhas": ["Procuração", "Particular"],
        "subtitulo": "CC arts. 653-666 · art. 661 (mandato) · art. 654 §2º",
        "contratante_nome": (contratante.get("nome") or ""),
        "contratante_doc": (contratante.get("cpf") or contratante.get("cnpj") or ""),
        "contratante_end": (_endereco_full(contratante) or contratante.get("endereco") or ""),
        "emissao": f"Vinculada ao Contrato de Exclusividade {base_cod}".strip(),
        "validade": "",
    }

    buf = io.BytesIO()
    pdf = ResilientBaseDocTemplate(
        buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.4 * cm, bottomMargin=2.0 * cm, title=f"Procuracao {codigo}",
    )
    frame = Frame(MARGIN, 2.0 * cm, PAGE_W - 2 * MARGIN, PAGE_H - 4.4 * cm, id="corpo")
    pdf.addPageTemplates([
        PageTemplate(id="capa", frames=[frame], onPage=lambda c, d: _draw_capa(c, meta)),
        PageTemplate(id="interna", frames=[frame], onPage=lambda c, d: _draw_footer(c, meta)),
    ])
    cw = PAGE_W - 2 * MARGIN

    def P(txt, style="corpo"):
        return Paragraph(_xml_escape(txt) if isinstance(txt, str) else str(txt), st[style])

    story = [NextPageTemplate("interna"), PageBreak()]

    # 01 — OUTORGANTES
    story.append(SecaoHeader("01", "Outorgantes", None, width=cw))
    story.append(Spacer(1, 6))
    if not outorgantes:
        story.append(P(_BLANK))
    for o in outorgantes:
        q = (_qualifica_pj(o) if (isinstance(o, dict) and o.get("tipo") == "pj")
             else _qualifica_pf(o)) if isinstance(o, dict) else str(o)
        story.append(P(q + "."))
        story.append(Spacer(1, 3))

    # 02 — OUTORGADO
    story.append(Spacer(1, 8))
    story.append(SecaoHeader("02", "Outorgado", None, width=cw))
    story.append(Spacer(1, 6))
    cor_nome = _s(cor.get("nome"), _BLANK)
    cor_creci = _s(cor.get("creci"), "")
    # qualificação COMPLETA do outorgado (perfil do avaliador + corretor do contrato)
    out_txt = _qualifica_outorgado(cor, doc.get("_avaliador"))
    story.append(P(out_txt + "."))

    # 03 — OBJETO
    story.append(Spacer(1, 8))
    story.append(SecaoHeader("03", "Objeto", None, width=cw))
    story.append(Spacer(1, 6))
    matricula = _norm_matricula(obj.get("matricula")) or _BLANK
    reg = _s(obj.get("registro_imovel") or obj.get("cartorio"), "Cartório de Registro de Imóveis competente")
    end_im = _endereco_full(obj) or _s(obj.get("endereco"), _BLANK)
    area_t = _s(obj.get("area_total") or obj.get("area_terreno"), "")
    area_c = _s(obj.get("area_construida") or obj.get("area_edificacao"), "")
    objeto_txt = (f"A presente procuração é outorgada em caráter EXCLUSIVO e LIMITADO ao imóvel objeto da "
                  f"Matrícula nº {matricula} do {reg}, situado em {end_im}")
    if area_t:
        objeto_txt += f", com área total de {area_t} m²"
    if area_c:
        objeto_txt += f" e área construída de {area_c} m²"
    objeto_txt += (", vinculada ao Contrato de Exclusividade de Intermediação Imobiliária celebrado entre "
                   "as partes, não conferindo ao OUTORGADO quaisquer poderes sobre outros bens, direitos "
                   "ou interesses dos OUTORGANTES.")
    story.append(P(objeto_txt))

    # 04 — PODERES
    story.append(Spacer(1, 8))
    story.append(SecaoHeader("04", "Poderes", None, width=cw))
    story.append(Spacer(1, 6))
    story.append(P("Pelo presente instrumento particular de procuração, na forma dos arts. 653 a 666 e, "
                   "especialmente, do art. 661 do Código Civil (Lei nº 10.406/2002), os OUTORGANTES nomeiam "
                   "e constituem o OUTORGADO seu bastante procurador, com poderes específicos para, "
                   "exclusivamente em relação ao imóvel acima descrito:"))
    letras = "abcdefghijklmnopqrstuvwxyz"
    idx = 0
    for pdr in (proc.get("poderes") or []):
        if not isinstance(pdr, dict) or not pdr.get("ativo"):
            continue
        txt = (pdr.get("texto_customizado") or "").strip() or _PODER_TEXTO_BASE.get(pdr.get("chave"), "")
        if not txt:
            continue
        story.append(P(f"{letras[idx]}) {txt};"))
        idx += 1
    if (proc.get("poderes_adicionais") or "").strip():
        story.append(P(f"{letras[idx]}) {proc['poderes_adicionais'].strip()};"))
    story.append(P("Podendo, para tanto, assinar requerimentos, protocolos e recibos de entrega de "
                   "documentos, prestar e receber informações, pagar taxas e emolumentos por conta dos "
                   "OUTORGANTES e praticar os demais atos estritamente necessários ao fiel cumprimento "
                   "deste mandato."))

    # 05 — VEDAÇÕES
    story.append(Spacer(1, 8))
    story.append(SecaoHeader("05", "Vedações", None, width=cw))
    story.append(Spacer(1, 6))
    ved = ("A presente procuração NÃO confere poderes para alienar, prometer alienar, onerar, hipotecar, "
           "dar em garantia, transigir, firmar compromisso de compra e venda, receber valores, dar quitação "
           "ou praticar qualquer ato de disposição sobre o imóvel, atos estes que dependem de manifestação "
           "pessoal e expressa dos OUTORGANTES.")
    if not proc.get("substabelecimento_permitido"):
        ved += " É vedado o substabelecimento, no todo ou em parte, dos poderes ora conferidos."
    story.append(P(ved))

    # 06 — VIGÊNCIA
    story.append(Spacer(1, 8))
    story.append(SecaoHeader("06", "Vigência", None, width=cw))
    story.append(Spacer(1, 6))
    if proc.get("vigencia_vinculada_contrato") is False and proc.get("vigencia_data_fim"):
        vig = f"esta procuração vigorará até {_data_extenso(proc.get('vigencia_data_fim'))}"
    else:
        vig = ("esta procuração vigorará enquanto vigente o Contrato de Exclusividade a que se vincula, "
               "extinguindo-se de pleno direito com o seu término, resolução ou rescisão")
    story.append(P(f"{vig}, podendo ser revogada a qualquer tempo pelos OUTORGANTES, na forma da lei."))

    # 07 — ASSINATURAS (mantidas juntas)
    local = _s(proc.get("local_assinatura"), "Açailândia/MA")
    bloco = [
        Spacer(1, 12),
        P(f"Por ser expressão da verdade, firmam o presente instrumento. {local}, "
          f"{_data_extenso(proc.get('data_assinatura'))}."),
        Spacer(1, 10),
        SecaoHeader("07", "Assinaturas", None, width=cw),
        Spacer(1, 18),
    ]
    linha = "_" * 40
    for o in outorgantes:
        if not isinstance(o, dict):
            continue
        nome = _s(o.get("nome") or o.get("razao_social"), _BLANK)
        cpf = _s(o.get("cpf") or o.get("cnpj"), "")
        bloco += [Spacer(1, 30), Paragraph(linha, st["assina_nome"]),
                  Paragraph(_xml_escape(f"OUTORGANTE — {nome}" + (f", CPF {cpf}" if cpf else "")), st["assina_nome"]),
                  Spacer(1, 6)]
        if o.get("conjuge_nome"):
            cjcpf = _s(o.get("conjuge_cpf"), "")
            bloco += [Spacer(1, 30), Paragraph(linha, st["assina_nome"]),
                      Paragraph(_xml_escape(f"OUTORGANTE (cônjuge anuente) — {o['conjuge_nome']}" + (f", CPF {cjcpf}" if cjcpf else "")), st["assina_nome"]),
                      Spacer(1, 6)]
    bloco += [Spacer(1, 30), Paragraph(linha, st["assina_nome"]),
              Paragraph(_xml_escape(f"OUTORGADO — {cor_nome}" + (f", CRECI {cor_creci}" if cor_creci else "")), st["assina_nome"]),
              Spacer(1, 10),
              Paragraph("Recomenda-se o reconhecimento de firma das assinaturas dos OUTORGANTES, podendo ser "
                        "exigido pelas instituições destinatárias (art. 654, § 2º, do Código Civil).", st["assina_cred"])]
    # bloco de assinaturas inteiro numa única página (apresentação + facilita ao cliente assinar)
    story.append(KeepTogether(bloco))

    pdf.build(story)
    return buf.getvalue()
