# Testes da integração do croqui no PDF da proposta de demarcação (SPEC-Demarcacao §9 4.6/4.7).
from reportlab.graphics.shapes import Drawing

from services.pricing import demarcacao_geo as G
from pdf import proposta_pdf as PP


def _rect_pontos():
    return [
        {"vertice": "P1", "utm_e": 0.0, "utm_n": 0.0},
        {"vertice": "P2", "utm_e": 9.0, "utm_n": 0.0},
        {"vertice": "P3", "utm_e": 9.0, "utm_n": 22.0},
        {"vertice": "P4", "utm_e": 0.0, "utm_n": 22.0},
    ]


def test_projeto_croqui_anexa_distancia_por_vertice():
    proj = G.projeto_croqui(_rect_pontos())
    vs = proj["vertices"]
    assert [round(v["distancia_m"], 2) for v in vs] == [9.0, 22.0, 9.0, 22.0]
    assert all("coord_e" in v and "de" in v for v in vs)


def test_projeto_croqui_confrontantes():
    proj = G.projeto_croqui(_rect_pontos(), confrontantes={1: "Estrada", 3: "Fazenda Vizinha"})
    vs = proj["vertices"]
    assert vs[0]["confrontante_lado"] == "Estrada"
    assert vs[2]["confrontante_lado"] == "Fazenda Vizinha"


def test_croqui_flowables_vazio_sem_pontos_suficientes():
    st = PP._styles()
    assert PP._croqui_flowables({"dados_imovel": {}}, st) == []
    assert PP._croqui_flowables({"dados_imovel": {"pontos": [{"utm_e": 0, "utm_n": 0}]}}, st) == []


def test_croqui_flowables_geral():
    fl = PP._croqui_flowables({"dados_imovel": {"pontos": _rect_pontos()}}, PP._styles())
    draws = [x for x in fl if isinstance(x, Drawing)]
    assert len(draws) == 1


def test_croqui_flowables_com_alinhamento():
    fl = PP._croqui_flowables(
        {"dados_imovel": {"pontos": _rect_pontos(), "alinhamento_lados": [2]}}, PP._styles())
    draws = [x for x in fl if isinstance(x, Drawing)]
    assert len(draws) == 2  # 4.6 croqui geral + 4.7 croqui de alinhamento


def test_rotas_demarcacao_registradas():
    from routes.propostas import router
    paths = {getattr(r, "path", None) for r in router.routes}
    assert "/propostas/coletora/parse" in paths
    assert "/propostas/geometria" in paths
    assert "/propostas/croqui-svg" in paths


def test_gerar_proposta_pdf_com_croqui_nao_quebra():
    prop = {
        "numero": "PROP-2026-0001", "subtipo": "demarcacao_rural",
        "subtipo_label": "Demarcação Rural",
        "custos_calculados": {
            "secao_1_projetos": ["Levantamento GNSS"],
            "secao_3_honorarios": [{"ordem": 1, "descricao": "Honorários", "valor": 5000}],
            "secao_5_total": 5000, "condicoes_pagamento": [], "avisos": [],
        },
        "dados_imovel": {"pontos": _rect_pontos(), "alinhamento_lados": [2]},
    }
    b = PP.gerar_proposta_pdf(prop)
    assert b[:4] == b"%PDF"
    assert len(b) > 2000
