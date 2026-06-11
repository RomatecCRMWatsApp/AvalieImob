# @module tests.test_contrato_exclusividade — Trava regressões no texto jurídico canônico.
import re
import pytest

from pdf.templates.contrato_base import (
    clausulas_exclusividade, montar_clausulas, preambulo_exclusividade,
    clausulas_para_texto, _ORDINAIS,
)


def _doc(regime="determinado", **extra):
    base = {
        "tipo_contrato": "exclusividade",
        "vendedores": [{
            "pf": {
                "nome": "Weldon Gomes de Oliveira", "cpf": "000.000.000-00",
                "rg": "1234567", "orgao_emissor": "SSP/MA", "nacionalidade": "brasileiro",
                "estado_civil": "casado", "profissao": "empresário",
                "endereco": "Rua A", "numero": "10", "bairro": "Centro",
                "cidade": "Açailândia", "uf": "MA", "cep": "65930-000",
                "conjuge_nome": "Maria de Oliveira", "conjuge_cpf": "111.111.111-11",
            },
        }],
        "objeto": {"endereco": "Rua B, 200", "matricula": "12345", "cartorio": "1º Ofício",
                   "area_terreno": 360, "descricao": "casa residencial"},
        "pagamento": {"valor_total": 550000},
        "corretor": {"comissao_percentual": 6},
        "regime_prazo": regime,
        "cidade_assinatura": "Açailândia/MA",
    }
    base.update(extra)
    return base


def test_doze_clausulas_e_titulos():
    cls = clausulas_exclusividade(_doc())
    assert len(cls) == 12
    for i, cl in enumerate(cls, start=1):
        assert cl.titulo.startswith(f"CLÁUSULA {_ORDINAIS[i]} —")
        assert cl.itens, f"cláusula {i} sem itens"
        # numeração automática N.i
        assert cl.itens[0].startswith(f"{i}.1. ")


def test_sem_placeholder_literal():
    texto = clausulas_para_texto(_doc())
    assert "{" not in texto and "}" not in texto


def test_clausula_terceira_destaques():
    cls = clausulas_exclusividade(_doc())
    terceira = cls[2]
    corpo = " ".join(terceira.itens)
    assert "TODA E QUALQUER" in corpo
    assert "QUALQUER QUE SEJA A ORIGEM" in corpo
    assert "<b>" in corpo  # negrito preservado


def test_prazo_determinado_sem_renovacao_tem_um_item():
    cls = clausulas_exclusividade(_doc(regime="determinado", renovacao_automatica=False))
    quinta = cls[4]
    assert len(quinta.itens) == 1
    assert "6 (seis) meses" in quinta.itens[0] or "meses" in quinta.itens[0]


def test_prazo_determinado_com_renovacao_tem_dois_itens():
    cls = clausulas_exclusividade(_doc(regime="determinado", renovacao_automatica=True))
    assert len(cls[4].itens) == 2


def test_prazo_indeterminado():
    cls = clausulas_exclusividade(_doc(regime="indeterminado"))
    quinta = cls[4]
    assert "prazo indeterminado" in quinta.itens[0]
    decima = cls[9]
    assert "período mínimo" in decima.itens[0]


def test_conjuge_condicional():
    com = preambulo_exclusividade(_doc())
    assert any("Cônjuge anuente" in p for p in com)
    doc_sem = _doc()
    doc_sem["vendedores"][0]["pf"]["estado_civil"] = "solteiro"
    doc_sem["vendedores"][0]["pf"].pop("conjuge_nome", None)
    sem = preambulo_exclusividade(doc_sem)
    assert not any("Cônjuge anuente" in p for p in sem)


def test_dispatcher_tipo_generico():
    doc = {"tipo_contrato": "compra_venda", "clausulas": [{"numero": 1, "titulo": "DO OBJETO", "conteudo": "..."}]}
    cls = montar_clausulas(doc)
    assert len(cls) == 1
    assert "DO OBJETO" in cls[0].titulo
