# Testes do painel de validação SIG-RI/ONR (Prov. CNJ 195/2025 · NBR 17047):
# geometria (vértices/auto-interseção/CRS), cadastro (CPF-CNPJ/IBGE/ART),
# áreas (W-AREA-DIV bloqueante + justificativa) e warnings.
from services.geo_urbano import validacao_onr as V


def _quadra_utm(largura=12.0, profundidade=30.0, e0=223000.0, n0=9458000.0):
    cantos = [(e0, n0), (e0 + largura, n0), (e0 + largura, n0 + profundidade), (e0, n0 + profundidade)]
    return [{"ordem": i, "coord_e": e, "coord_n": n} for i, (e, n) in enumerate(cantos)]


def _proj(**over):
    p = {
        "vertices": _quadra_utm(),
        "municipio": "Açailândia", "uf": "MA", "codigo_ibge": "2100055",
        "cartorio": {"cns": "12.345-6"},
        "trt_numero": "TRT-2026-000123",
        "area_declarada_m2": 360.0,
        "partes": [{"papel": "requerente", "razao_social": "J & G Ltda", "cnpj": "11.222.333/0001-81"}],
        "matriculas": [],
    }
    p.update(over)
    return p


def _codigos(res):
    return {x["codigo"] for x in res["erros"]} | {x["codigo"] for x in res["warnings"]}


# ── DV de documentos ──────────────────────────────────────────────────────────
def test_validar_cnpj_e_doc():
    assert V.validar_cnpj("11.222.333/0001-81") is True
    assert V.validar_cnpj("11.222.333/0001-80") is False
    assert V.validar_cnpj("11.111.111/1111-11") is False
    assert V.doc_valido("11.222.333/0001-81") is True
    assert V.doc_valido("111.111.111-11") is False


# ── Projeto válido ────────────────────────────────────────────────────────────
def test_projeto_valido_pode_gerar():
    res = V.validar(_proj())
    assert res["erros"] == []
    assert res["pode_gerar"] is True
    assert abs(res["area_calculada_m2"] - 360.0) / 360.0 < 0.01


# ── Erros de geometria ────────────────────────────────────────────────────────
def test_e_vert_min():
    res = V.validar(_proj(vertices=[{"ordem": 0, "coord_e": 223000.0, "coord_n": 9458000.0},
                                    {"ordem": 1, "coord_e": 223012.0, "coord_n": 9458000.0}]))
    assert "E-VERT-MIN" in _codigos(res) and res["pode_gerar"] is False


def test_e_self_int_bowtie():
    verts = [{"ordem": 0, "coord_e": 223000.0, "coord_n": 9458000.0},
             {"ordem": 1, "coord_e": 223012.0, "coord_n": 9458030.0},
             {"ordem": 2, "coord_e": 223012.0, "coord_n": 9458000.0},
             {"ordem": 3, "coord_e": 223000.0, "coord_n": 9458030.0}]
    assert "E-SELF-INT" in _codigos(V.validar(_proj(vertices=verts)))


def test_e_crs_fora_do_brasil():
    verts = [{"ordem": 0, "latitude": "48°00'00\"N", "longitude": "02°00'00\"E"},
             {"ordem": 1, "latitude": "48°00'10\"N", "longitude": "02°00'00\"E"},
             {"ordem": 2, "latitude": "48°00'10\"N", "longitude": "02°00'10\"E"}]
    assert "E-CRS" in _codigos(V.validar(_proj(vertices=verts)))


# ── Erros de cadastro ─────────────────────────────────────────────────────────
def test_e_cpf_invalido():
    res = V.validar(_proj(partes=[{"papel": "requerente", "nome": "Fulano", "cpf": "123.456.789-00"}]))
    assert "E-CPF" in _codigos(res)


def test_e_ibge():
    assert "E-IBGE" in _codigos(V.validar(_proj(codigo_ibge="123")))          # < 7 díg
    assert "E-IBGE" in _codigos(V.validar(_proj(codigo_ibge="3500000")))      # SP em UF=MA
    assert "E-IBGE" not in _codigos(V.validar(_proj()))                        # 2100055/MA ok


def test_e_art_ausente():
    assert "E-ART" in _codigos(V.validar(_proj(trt_numero="")))


# ── Warnings ──────────────────────────────────────────────────────────────────
def test_w_cns_ausente():
    assert "W-CNS" in _codigos(V.validar(_proj(cartorio={})))


def test_w_area_div_bloqueia_e_justificativa_libera():
    p = _proj(area_declarada_m2=500.0)       # muito distante dos ~360 geodésicos
    res = V.validar(p)
    assert "W-AREA-DIV" in {w["codigo"] for w in res["warnings"]}
    assert res["pode_gerar"] is False and "W-AREA-DIV" in res["bloqueios_pendentes"]
    # RT justifica → libera
    p["onr_justificativas"] = [{"codigo": "W-AREA-DIV", "texto": "Divergência da matrícula antiga; prevalece o levantamento."}]
    res2 = V.validar(p)
    assert res2["pode_gerar"] is True and res2["bloqueios_pendentes"] == []
