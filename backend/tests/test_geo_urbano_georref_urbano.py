# Testes da Fase 6 — Georreferenciamento de lote urbano (localização e situação).
# Núcleo PURO (composição/presets/validação/import de coordenadas) + wiring do
# modelo (enum, campos novos, payload de atualização).
import pytest

from models.geo_urbano import GeoUrbanoProjeto, AtualizarProjetoBody, ComposicaoPreset
from services.geo_urbano import georref_urbano as GU


# ── Modelo ─────────────────────────────────────────────────────────────────────
def test_modelo_aceita_georref_urbano_e_campos_novos():
    p = GeoUrbanoProjeto(
        user_id="u1", denominacao_imovel="Lote 08 Qd 41",
        tipo_servico="georref_urbano", finalidade="financiamento_bancario",
        instituicao_financeira="CAIXA ECONÔMICA FEDERAL",
        proprietario_natureza="pf", possui_benfeitoria=True, area_declarada=360.0,
        memoriais_selecionados=["MD-PER", "MD-SIT"],
    )
    d = p.model_dump(mode="json")
    assert d["tipo_servico"] == "georref_urbano"
    assert d["finalidade"] == "financiamento_bancario"
    assert d["memoriais_selecionados"] == ["MD-PER", "MD-SIT"]
    # dicts têm default vazio (não None) p/ o merge parcial da rota
    for k in ("representante_legal", "levantamento", "composicao", "quadra_dados", "art_trt"):
        assert d[k] == {}


def test_payload_atualizacao_aceita_campos_fase6():
    body = AtualizarProjetoBody(
        finalidade="processo_judicial", possui_benfeitoria=True,
        memoriais_selecionados=["MD-SUC"], composicao={"preset": "SIMPLIFICADO"},
        quadra_dados={"modo_planta": "gerada"}, art_trt={"tipo": "TRT"},
    )
    dados = body.model_dump(exclude_unset=True)
    assert dados["finalidade"] == "processo_judicial"
    assert dados["composicao"] == {"preset": "SIMPLIFICADO"}
    assert set(dados) >= {"finalidade", "possui_benfeitoria", "memoriais_selecionados",
                          "composicao", "quadra_dados", "art_trt"}


def test_preset_model_cross_modulo():
    pr = ComposicaoPreset(user_id="u1", modulo="onr", nome="Padrão ONR")
    assert pr.modulo == "onr" and pr.nome == "Padrão ONR"


# ── Composição / presets ────────────────────────────────────────────────────────
def test_composicao_default_bancaria_ativa_preset_banco():
    comp = GU.composicao_default("financiamento_bancario")
    assert comp["preset"] == "BANCO"
    # BANCO liga capa/apresentação/imagem/mapa/quadro/MD-PER/MD-SIT/ART; desliga sumário
    assert comp["pecas"]["capa"] is True
    assert comp["pecas"]["sumario"] is False
    assert comp["pecas"]["memorial_perimetrico"] is True
    assert comp["pecas"]["memorial_sucinto"] is False


def test_preset_simplificado_sem_capa_sem_sumario():
    pecas = GU.preset_pecas("SIMPLIFICADO")
    assert pecas["capa"] is False and pecas["sumario"] is False
    assert pecas["mapa_lote"] and pecas["memorial_perimetrico"] and pecas["art_trt"]


def test_definicao_capa_default_por_finalidade():
    assert "financiamento bancário" in GU.definicao_capa_default("financiamento_bancario").lower()
    assert GU.definicao_capa_default(None) == GU.DEFINICOES_CAPA[0]


def test_finalidade_texto_inclui_instituicao():
    proj = {"finalidade": "financiamento_bancario", "instituicao_financeira": "CAIXA ECONÔMICA FEDERAL"}
    txt = GU.finalidade_texto(proj)
    assert "financiamento bancário" in txt and "CAIXA" in txt
    # finalidade "outra" usa o texto livre
    assert GU.finalidade_texto({"finalidade": "outra", "finalidade_livre": "fim específico"}) == "fim específico"


def test_resolver_composicao_desabilita_pecas_sem_insumo():
    # projeto vazio (COMPLETO): só capa/sumário/apresentação/ART entram no PDF
    proj = {"finalidade": None}
    res = GU.resolver_composicao(proj)
    by = {i["chave"]: i for i in res["pecas"]}
    assert by["mapa_lote"]["habilitada"] is False and by["mapa_lote"]["motivo"]
    assert by["memorial_perimetrico"]["habilitada"] is False
    assert by["capa"]["no_pdf"] and by["art_trt"]["no_pdf"]
    # 4 peças sempre-disponíveis: capa(1)+sumário(1)+apresentação(1)+ART(2) = 5 páginas
    assert res["paginas_estimadas"] == 5


def test_resolver_composicao_habilita_com_insumos():
    proj = {
        "vertices": [
            {"ordem": 1, "coord_e": 223012.5, "coord_n": 9453766.0, "confrontante_lado": "Rua A"},
            {"ordem": 2, "coord_e": 223050.0, "coord_n": 9453800.0, "confrontante_lado": "Lote 07"},
            {"ordem": 3, "coord_e": 223000.0, "coord_n": 9453820.0, "confrontante_lado": "Lote 09"},
        ],
        "memoriais_selecionados": ["MD-PER"],
    }
    by = {i["chave"]: i for i in GU.resolver_composicao(proj)["pecas"]}
    assert by["mapa_lote"]["habilitada"] is True
    assert by["quadro_vertices"]["habilitada"] is True
    assert by["memorial_perimetrico"]["habilitada"] is True
    # MD-SIT não selecionado → peça de situação segue bloqueada
    assert by["memorial_situacao"]["habilitada"] is False


def test_md_con_exige_benfeitoria():
    base = {"memoriais_selecionados": ["MD-CON"]}
    by = {i["chave"]: i for i in GU.resolver_composicao(base)["pecas"]}
    assert by["memorial_area_construida"]["habilitada"] is False
    by2 = {i["chave"]: i for i in GU.resolver_composicao({**base, "possui_benfeitoria": True})["pecas"]}
    assert by2["memorial_area_construida"]["habilitada"] is True


# ── Validação (§13) ─────────────────────────────────────────────────────────────
def test_validar_bloqueia_projeto_vazio():
    v = GU.validar({"denominacao_imovel": ""})
    codigos = {b["codigo"] for b in v["bloqueios"]}
    assert v["ok"] is False
    assert {"E-POLIGONO", "E-MEMORIAL", "E-DENOM"} <= codigos


def test_validar_ok_com_avisos():
    proj = {
        "denominacao_imovel": "Lote 08",
        "vertices": [
            {"ordem": 1, "coord_e": 223012.5, "coord_n": 9453766.0, "confrontante_lado": "Rua A"},
            {"ordem": 2, "coord_e": 223050.0, "coord_n": 9453800.0, "confrontante_lado": "Lote 07"},
            {"ordem": 3, "coord_e": 223000.0, "coord_n": 9453820.0, "confrontante_lado": "Lote 09"},
        ],
        "memoriais_selecionados": ["MD-PER"],
        "area_declarada": 360.0, "area_calculada_m2": 500.0,  # > 0,5% → aviso
    }
    v = GU.validar(proj)
    assert v["ok"] is True and not v["bloqueios"]
    codigos = {a["codigo"] for a in v["avisos"]}
    assert "divergencia_area" in codigos
    assert "sem_matricula" in codigos  # sem upload matricula_imovel
    assert "art_pendente" in codigos   # ART ligada sem número/upload


def test_validar_esquina_nao_informada_com_md_sit():
    proj = {
        "denominacao_imovel": "Lote 08",
        "vertices": [{"ordem": i, "coord_e": 1000.0 + i, "coord_n": 9000000.0 + i,
                      "confrontante_lado": "x"} for i in range(1, 4)],
        "memoriais_selecionados": ["MD-SIT"],
    }
    codigos = {a["codigo"] for a in GU.validar(proj)["avisos"]}
    assert "esquina_nao_informada" in codigos


# ── Import de coordenadas (§5) ──────────────────────────────────────────────────
def test_import_csv_utm():
    csv = "vertice;E;N\nP1;223012.50;9453766.07\nP2;223050.00;9453800.00\nP3;223000.00;9453820.00\n"
    res = GU.importar_coordenadas(csv.encode("utf-8"), "lote.csv")
    assert res["sistema"] == "utm" and len(res["vertices"]) == 3
    v0 = res["vertices"][0]
    assert v0["de"] == "P1" and v0["coord_e"] == 223012.5 and v0["coord_n"] == 9453766.07


def test_import_csv_numero_br():
    csv = "P1\t223.012,50\t9.453.766,07\nP2\t223.050,00\t9.453.800,00\nP3\t223.000,00\t9.453.820,00\n"
    res = GU.importar_coordenadas(csv.encode("utf-8"), "lote.txt")
    assert len(res["vertices"]) == 3
    assert res["vertices"][0]["coord_e"] == 223012.5


def test_import_kml_geo_converte_utm():
    pytest.importorskip("pyproj")
    kml = ("<Placemark><Polygon><outerBoundaryIs><LinearRing><coordinates>"
           "-47.4665,-4.9376,0 -47.4660,-4.9370,0 -47.4670,-4.9360,0 -47.4665,-4.9376,0"
           "</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>")
    res = GU.importar_coordenadas(kml.encode("utf-8"), "lote.kml")
    assert res["sistema"] == "geo"
    assert len(res["vertices"]) == 3  # anel fechado → última duplicata removida
    v0 = res["vertices"][0]
    assert v0.get("coord_e") and 100_000 < v0["coord_e"] < 999_999
    assert v0.get("coord_n") and v0["coord_n"] > 9_000_000  # hemisfério sul


def test_opcoes_catalogo_completo():
    op = GU.opcoes()
    assert len(op["finalidades"]) == 7
    assert {"MD-PER", "MD-SIT", "MD-SUC", "MD-CON"} == {m["codigo"] for m in op["memoriais"]}
    chaves_upload = {u["chave"] for u in op["uploads"]}
    assert "mapa_coordenadas" in chaves_upload
    assert next(u for u in op["uploads"] if u["chave"] == "mapa_coordenadas")["obrigatorio"] is True
