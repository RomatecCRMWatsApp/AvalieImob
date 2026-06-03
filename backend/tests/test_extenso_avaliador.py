# Testes dos utilitários compartilhados de laudo (BUG-01, BUG-04, BUG-05).
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.extenso import valor_por_extenso
from utils.avaliador import formata_doc, resolver_dados_avaliador, cpf_solicitante


# ── BUG-01: valor por extenso ──────────────────────────────────────────────
def test_extenso_exemplo_pagrisa():
    assert valor_por_extenso(7188476.13) == (
        "sete milhões, cento e oitenta e oito mil, "
        "quatrocentos e setenta e seis reais e treze centavos"
    )


def test_extenso_basicos():
    assert valor_por_extenso(1) == "um real"
    assert valor_por_extenso(100) == "cem reais"
    assert valor_por_extenso(1000) == "mil reais"
    assert valor_por_extenso(1500.50) == "mil e quinhentos reais e cinquenta centavos"


def test_extenso_nunca_vazio_para_valor_valido():
    # BUG-01: jamais retornar vazio para valor > 0
    for v in [0.01, 50, 726108.70, 999_000_000_000]:
        assert valor_por_extenso(v) != ""


def test_extenso_zero_e_invalido():
    assert valor_por_extenso(0) == ""
    assert valor_por_extenso(None) == ""
    assert valor_por_extenso("abc") == ""


# ── BUG-05: CPF ────────────────────────────────────────────────────────────
def test_formata_cpf_cnpj():
    assert formata_doc("30971829349") == "309.718.293-49"
    assert formata_doc("11222333000181") == "11.222.333/0001-81"


def test_cpf_solicitante_fonte_unica():
    ptam = {"solicitante_cpf_cnpj": "30971829349", "proprietarios": [{"cpf_cnpj": "30971829649"}]}
    # Sempre a fonte única do solicitante, independentemente do proprietário
    assert cpf_solicitante(ptam) == "309.718.293-49"


# ── BUG-04: dados do avaliador (fonte única, sem hardcode) ─────────────────
def test_resolver_avaliador_do_perfil():
    perfil = {
        "nome_completo": "José Romário Pinto Bezerra",
        "registros": [
            {"tipo": "CNAI", "numero": "031161"},
            {"tipo": "CRECI", "numero": "4705", "uf": "MA"},
            {"tipo": "CFT", "numero": "01209185369", "uf": "MA"},
            {"tipo": "INCRA", "numero": "FQNS"},
        ],
        "telefone": "(99) 99181-1246",
        "email_profissional": "contato@consultoriaromatec.com.br",
    }
    ptam = {"art_rrt_numero": "BA-20260001"}
    d = resolver_dados_avaliador(perfil=perfil, user={}, ptam=ptam)
    assert d["nome"] == "José Romário Pinto Bezerra"
    assert d["cnai"] == "CNAI 031161"
    assert d["creci"] == "CRECI/MA 4.705"
    assert d["cft"] == "CFT/MA 01209185369"
    assert d["incra"] == "INCRA FQNS"
    assert d["art_trt"] == "BA-20260001"
    assert d["perfil_completo"] is True
    assert "CRECI/MA 4.705" in d["registros_linhas"]
    assert "CNAI 031161" in d["registros_linhas"]


def test_resolver_avaliador_perfil_vazio_cai_para_ptam():
    ptam = {"responsavel_nome": "Fulano", "responsavel_cnai": "031161", "responsavel_creci": "CRECI/MA 4.705"}
    d = resolver_dados_avaliador(perfil={}, user={}, ptam=ptam)
    assert d["nome"] == "Fulano"
    assert d["cnai"] == "CNAI 031161"
    assert d["perfil_completo"] is False  # perfil não cadastrado


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    falhas = 0
    for fn in fns:
        try:
            fn()
            print(f"OK   {fn.__name__}")
        except Exception:
            falhas += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - falhas}/{len(fns)} testes passaram")
    sys.exit(1 if falhas else 0)
