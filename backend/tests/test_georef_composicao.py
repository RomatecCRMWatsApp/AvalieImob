"""Composição do dossiê do Georref-rural (services/georef/composicao.py)."""
from services.georef import composicao as C


def _doc(**kw):
    base = {
        "tipo_servico": "desmembramento",
        "uploads": {"art_trt": {"key": "a"}, "mapa": {"key": "m"}, "certidao": {"key": "c"}},
        "confrontantes": [{"nome": "Fulano"}],
    }
    base.update(kw)
    return base


def test_opcoes_lista_pecas_e_presets():
    op = C.opcoes()
    assert op["presets"] == ["COMPLETO", "PROTOCOLO", "SIMPLIFICADO", "PERSONALIZADO"]
    chaves = {p["chave"] for p in op["pecas"]}
    assert {"requerimento", "laudo_tecnico", "memorial", "mapa", "art_trt"} <= chaves
    assert "doc_cliente" in chaves
    assert "dossie" not in chaves          # capa/sumário/dossiê não são peças alternáveis


def test_default_tudo_ligado_retrocompativel():
    # sem composição salva → todas ligadas (dossiê inalterado)
    lig = C.pecas_ligadas(_doc())
    assert all(lig.values())
    assert lig["itr"] is True


def test_preset_simplificado_desliga_pecas():
    comp = {"preset": "SIMPLIFICADO", "pecas": C.preset_pecas("SIMPLIFICADO")}
    lig = C.pecas_ligadas(_doc(composicao=comp))
    assert [k for k, v in lig.items() if v] == ["requerimento", "memorial", "mapa", "art_trt"]


def test_resolver_marca_habilitada_por_insumo():
    res = C.resolver_composicao(_doc())
    by = {i["chave"]: i for i in res["pecas"]}
    # com upload/confrontantes → habilitadas e no PDF
    assert by["art_trt"]["habilitada"] and by["art_trt"]["no_pdf"]
    assert by["mapa"]["habilitada"] and by["certidao_matricula"]["habilitada"]
    assert by["drl"]["habilitada"]  # há confrontantes
    assert by["drl_unificada"]["habilitada"]  # desmembramento
    # sem upload → desabilitada, com motivo, fora do PDF
    assert not by["ccir"]["habilitada"] and by["ccir"]["motivo"] and not by["ccir"]["no_pdf"]


def test_drl_unificada_so_desmembramento_remembramento():
    res = C.resolver_composicao(_doc(tipo_servico="georreferenciamento"))
    by = {i["chave"]: i for i in res["pecas"]}
    assert not by["drl_unificada"]["habilitada"]


def test_toggle_manual_vira_personalizado_via_preset_pecas():
    # peças manuais sem preset → PERSONALIZADO é decidido na rota; aqui só o filtro
    comp = {"preset": "PERSONALIZADO", "pecas": {**C.preset_pecas("COMPLETO"), "ccir": False}}
    lig = C.pecas_ligadas(_doc(composicao=comp))
    assert lig["ccir"] is False
    assert lig["requerimento"] is True
