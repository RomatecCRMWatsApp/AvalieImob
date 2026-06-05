# Testes do conversor HTML (RichTextEditor) -> blocos reportlab.
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.html_render import html_para_blocks, is_html


def test_inline_negrito_italico():
    b = html_para_blocks("<div>Texto <b>negrito</b> e <em>itálico</em></div>")
    assert b == [{"markup": "Texto <b>negrito</b> e <i>itálico</i>", "align": "left", "bullet": False}]


def test_lista_marcadores():
    b = html_para_blocks("<ul><li>um</li><li>dois</li></ul>")
    assert [x["markup"] for x in b] == ["• um", "• dois"]
    assert all(x["bullet"] for x in b)


def test_lista_numerada():
    b = html_para_blocks("<ol><li>um</li><li>dois</li></ol>")
    assert [x["markup"] for x in b] == ["1. um", "2. dois"]


def test_alinhamento():
    assert html_para_blocks('<div style="text-align:center">x</div>')[0]["align"] == "center"
    assert html_para_blocks('<div style="text-align:justify">x</div>')[0]["align"] == "justify"


def test_escape_entidades():
    b = html_para_blocks('<div>R&amp;D &lt; 100</div>')
    assert b[0]["markup"] == "R&amp;D &lt; 100"


def test_texto_puro_vira_linhas():
    b = html_para_blocks("linha 1\nlinha 2")
    assert [x["markup"] for x in b] == ["linha 1", "linha 2"]
    assert is_html("linha 1") is False


def test_strong_e_br():
    b = html_para_blocks("<strong>Conclusão</strong><br>Próximo")
    assert b[0]["markup"] == "<b>Conclusão</b><br/>Próximo"


def test_vazio():
    assert html_para_blocks("") == []
    assert html_para_blocks(None) == []


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    falhas = 0
    for fn in fns:
        try:
            fn(); print(f"OK   {fn.__name__}")
        except Exception:
            falhas += 1; print(f"FAIL {fn.__name__}"); traceback.print_exc()
    print(f"\n{len(fns)-falhas}/{len(fns)} testes passaram")
    sys.exit(1 if falhas else 0)
