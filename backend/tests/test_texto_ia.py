# Testes do limpador de artefatos de IA (BUG-02).
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.texto_ia import limpar_texto_ia


def test_remove_bold_markdown():
    assert limpar_texto_ia("**ANÁLISE** texto") == "ANÁLISE texto"


def test_remove_prefixo_campo_e_aperfeicoado():
    assert limpar_texto_ia("Campo: regiao Texto aperfeiçoado: O mercado é estável.") == "O mercado é estável."


def test_remove_regiao_de():
    assert limpar_texto_ia("Região de Açailândia: forte demanda.") == "forte demanda."


def test_remove_comentario_final():
    assert limpar_texto_ia("Conteúdo bom.\n--- Este texto inicial foi elaborado por IA") == "Conteúdo bom."


def test_normaliza_quebras():
    assert limpar_texto_ia("A.\n\n\n\nB.") == "A.\n\nB."


def test_vazio_e_none():
    assert limpar_texto_ia("") == ""
    assert limpar_texto_ia(None) == ""


def test_texto_limpo_inalterado():
    txt = "O bairro possui boa infraestrutura urbana e tendência de valorização."
    assert limpar_texto_ia(txt) == txt


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    falhas = 0
    for fn in fns:
        try:
            fn(); print(f"OK   {fn.__name__}")
        except Exception:
            falhas += 1; print(f"FAIL {fn.__name__}"); traceback.print_exc()
    print(f"\n{len(fns) - falhas}/{len(fns)} testes passaram")
    sys.exit(1 if falhas else 0)
