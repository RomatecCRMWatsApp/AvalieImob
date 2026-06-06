# @module utils.html_render — Converte o HTML do RichTextEditor em blocos prontos
# para o reportlab (que só entende <b>/<i>/<u>/<strike> inline + alinhamento por Paragraph).
#
# Saída: lista de blocos {markup, align, bullet}, onde:
#   - markup: string com markup inline aceito pelo reportlab Paragraph (& < > escapados)
#   - align: 'left' | 'center' | 'right' | 'justify'
#   - bullet: True quando é item de lista (já vem com prefixo "• " ou "N. ")
from __future__ import annotations

import re
from html import unescape  # resolve entidades HTML nomeadas (&eacute;, &ccedil;, ...)
from html.parser import HTMLParser
from xml.sax.saxutils import escape

_TAG_RE = re.compile(r"<[^>]+>")

# Tags inline → tag equivalente no reportlab
_INLINE = {"b": "b", "strong": "b", "i": "i", "em": "i", "u": "u",
           "s": "strike", "strike": "strike"}
_ALIGN_RE = re.compile(r"text-align\s*:\s*(left|center|right|justify)", re.I)


def _align_from_style(attrs):
    for k, v in attrs:
        if k == "style" and v:
            m = _ALIGN_RE.search(v)
            if m:
                return m.group(1).lower()
    return None


class _Conv(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self._buf = []
        self._align = "left"
        self._lists = []  # pilha: ('ul', 0) ou ('ol', n)

    def _flush(self, bullet=False, prefix=""):
        markup = "".join(self._buf).strip()
        self._buf = []
        if markup:
            self.blocks.append({"markup": prefix + markup, "align": self._align, "bullet": bullet})

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _INLINE:
            self._buf.append(f"<{_INLINE[tag]}>")
        elif tag == "br":
            self._buf.append("<br/>")
        elif tag in ("p", "div"):
            self._flush()
            self._align = _align_from_style(attrs) or "left"
        elif tag in ("ul", "ol"):
            self._flush()
            self._lists.append([tag, 0])
        elif tag == "li":
            self._flush()

    def handle_startendtag(self, tag, attrs):
        if tag.lower() == "br":
            self._buf.append("<br/>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _INLINE:
            self._buf.append(f"</{_INLINE[tag]}>")
        elif tag == "li":
            prefix = "• "
            if self._lists and self._lists[-1][0] == "ol":
                self._lists[-1][1] += 1
                prefix = f"{self._lists[-1][1]}. "
            self._flush(bullet=True, prefix=prefix)
        elif tag in ("p", "div"):
            self._flush()
            self._align = "left"
        elif tag in ("ul", "ol"):
            self._flush()
            if self._lists:
                self._lists.pop()

    def handle_data(self, data):
        if data:
            self._buf.append(escape(data))

    def close(self):
        super().close()
        self._flush()


def is_html(texto) -> bool:
    """Heurística: o conteúdo parece HTML do editor (tem tag)."""
    return bool(texto) and bool(re.search(r"<(b|strong|i|em|u|s|strike|ul|ol|li|p|div|br|span)\b", str(texto), re.I))


def html_para_blocks(texto):
    """
    Converte HTML em lista de blocos {markup, align, bullet}.
    Se o texto não for HTML, devolve um único bloco por linha (texto puro).
    """
    if texto is None:
        return []
    s = str(texto)
    if not s.strip():
        return []
    if not is_html(s):
        return [{"markup": escape(l.strip()), "align": "left", "bullet": False}
                for l in s.split("\n") if l.strip()]
    conv = _Conv()
    conv.feed(s)
    conv.close()
    return conv.blocks


def html_to_inline(texto):
    """Converte HTML (ou texto puro) em UMA string com markup inline do reportlab
    (blocos separados por <br/>). Útil para células de tabela / campos curtos."""
    return "<br/>".join(b["markup"] for b in html_para_blocks(texto) if b["markup"])


def html_to_plain(texto) -> str:
    """Converte HTML (ou texto puro) em TEXTO PURO: sem tags, entidades resolvidas,
    parágrafos/itens separados por quebra de linha. Use com canvas.drawString e
    qualquer lugar que NÃO entenda markup (a capa do laudo, por exemplo)."""
    if texto is None:
        return ""
    s = str(texto)
    if not s.strip():
        return ""
    if not is_html(s):
        return s.strip()
    # quebras de bloco viram newline; <br> também
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|li|ul|ol|h[1-6]|tr)>", "\n", s)
    s = _TAG_RE.sub("", s)        # remove todas as tags restantes
    s = unescape(s)              # &amp; -> & ; &lt; -> < ; etc.
    linhas = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in s.split("\n")]
    return "\n".join(ln for ln in linhas if ln)
