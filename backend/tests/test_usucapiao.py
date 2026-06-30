# Testes do serviço de Usucapião Extrajudicial (Geo Urbano) — modelo, modalidades,
# validação de posse, checklist dinâmica, anuentes, geradores e dossiê.
import io
import pytest
from pypdf import PdfReader
from models.geo_urbano import GeoUrbanoProjeto


def _paginas(data: bytes) -> int:
    assert data[:5] == b"%PDF-"
    return len(PdfReader(io.BytesIO(data)).pages)


def test_modelo_usucapiao_valido():
    p = GeoUrbanoProjeto(
        denominacao_imovel="Lote 12 — Quadra 8 — Vila São Francisco",
        tipo_servico="usucapiao",
        modalidade_usucapiao="extraordinaria",
        situacao_registral="nao_matriculado",
        valor_atribuido=85000.0,
        soma_posses=[
            {"possuidor_nome": "Maria das Dores", "vinculo": "de_cujus",
             "inicio": "2008", "fim": "2018"},
            {"possuidor_nome": "João Filho", "vinculo": "proprio",
             "inicio": "2018", "fim": "atual"},
        ],
        provas_posse=[{"tipo": "iptu", "ano": "2010", "descricao": "Carnê de IPTU 2010"}],
        anuentes=[{"papel": "confrontante", "nome": "Vizinho Norte",
                   "lado": "fundo", "tipo": "particular", "canal": "presencial"}],
        checklist=[{"bloco": "A", "chave": "requerimento", "label": "Requerimento",
                    "obrigatorio": True, "status": "pendente"}],
        partes=[{"papel": "advogado", "tipo_pessoa": "fisica", "nome": "Dra. Ana",
                 "oab": "OAB/MA 12345"}],
    )
    assert p.modalidade_usucapiao == "extraordinaria"
    assert p.posse.natureza.startswith("mansa")
    assert len(p.soma_posses) == 2 and p.soma_posses[0].vinculo == "de_cujus"
    assert len(p.provas_posse) == 1 and p.provas_posse[0].tipo == "iptu"
    assert p.anuentes[0].anuencia.status == "pendente"
    assert p.partes[0].oab == "OAB/MA 12345"


from services.geo_urbano import usucapiao as USU


def test_modalidades_catalogo():
    assert set(USU.MODALIDADES) == {
        "extraordinaria", "ordinaria", "especial_urbana", "especial_rural",
        "familiar", "coletiva", "outra",
    }
    assert USU.MODALIDADES["extraordinaria"]["prazo_anos"] == 15
    assert USU.MODALIDADES["especial_urbana"]["area_max_m2"] == 250.0
    assert USU.MODALIDADES["ordinaria"]["exige_justo_titulo"] is True


def test_validar_posse_soma_alcanca_prazo():
    proj = {"modalidade_usucapiao": "extraordinaria",
            "soma_posses": [
                {"vinculo": "de_cujus", "inicio": "2008", "fim": "2018"},
                {"vinculo": "proprio", "inicio": "2018", "fim": "atual"}]}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["anos_cobertos"] == 18
    assert r["prazo_exigido"] == 15
    assert r["prazo_ok"] is True
    assert r["faltam_anos"] == 0


def test_validar_posse_soma_nao_alcanca():
    proj = {"modalidade_usucapiao": "extraordinaria",
            "soma_posses": [{"vinculo": "proprio", "inicio": "2018", "fim": "atual"}]}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["anos_cobertos"] == 8
    assert r["prazo_ok"] is False
    assert r["faltam_anos"] == 7


def test_validar_posse_area_excede():
    proj = {"modalidade_usucapiao": "especial_urbana", "area_declarada_m2": 320.0,
            "posse": {"inicio": "2015"}}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["area_ok"] is False
    assert r["area_max"] == 250.0


def test_validar_posse_tema_815_nao_trava_modulo_municipal():
    # STF Tema 815: especial urbana NÃO se condiciona ao módulo mínimo municipal.
    proj = {"modalidade_usucapiao": "especial_urbana", "area_declarada_m2": 120.0,
            "lote_minimo_municipal_m2": 250.0, "posse": {"inicio": "2018"}}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["area_ok"] is True
    assert r["ignora_modulo_municipal"] is True
    assert any("815" in a or "módulo" in a.lower() for a in r["avisos"])


def test_validar_posse_ordinaria_exige_justo_titulo():
    proj = {"modalidade_usucapiao": "ordinaria",
            "posse": {"inicio": "2010"}}
    r = USU.validar_posse(proj, ano_ref=2026)
    assert r["exige_justo_titulo"] is True
    assert r["justo_titulo_ok"] is False
    proj["posse"]["justo_titulo"] = "Cessão de direitos hereditários, fls. 12"
    r2 = USU.validar_posse(proj, ano_ref=2026)
    assert r2["justo_titulo_ok"] is True


def _chaves(items):
    return {i["chave"] for i in items}


def test_checklist_base_e_ordinaria_justo_titulo():
    base = USU.checklist_para({"modalidade_usucapiao": "extraordinaria",
                               "situacao_registral": "nao_matriculado"})
    ch = _chaves(base)
    assert {"requerimento", "ata_notarial", "procuracao_oab", "planta_memorial",
            "art_trt"} <= ch
    assert "justo_titulo" not in ch          # extraordinária dispensa
    ord_ = USU.checklist_para({"modalidade_usucapiao": "ordinaria"})
    assert "justo_titulo" in _chaves(ord_)   # ordinária exige


def test_checklist_herdeiro_adiciona_obito_partilha():
    proj = {"modalidade_usucapiao": "extraordinaria",
            "soma_posses": [{"vinculo": "de_cujus", "inicio": "2008", "fim": "2018"}]}
    ch = _chaves(USU.checklist_para(proj))
    assert {"certidao_obito", "formal_partilha"} <= ch


def test_checklist_rural_adiciona_ccir_car():
    ch = _chaves(USU.checklist_para({"modalidade_usucapiao": "especial_rural"}))
    assert {"ccir", "car", "georef_sigef"} <= ch


def test_checklist_preserva_status_existente():
    proj = {"modalidade_usucapiao": "extraordinaria",
            "checklist": [{"chave": "requerimento", "status": "anexado", "upload_id": "img-1"}]}
    item = next(i for i in USU.checklist_para(proj) if i["chave"] == "requerimento")
    assert item["status"] == "anexado" and item["upload_id"] == "img-1"


def test_anuentes_de_funde_confrontantes_e_titular():
    proj = {
        "situacao_registral": "matriculado_terceiro",
        "matriculas": [{"matricula": "12.345",
                        "proprietario_registral": {"nome": "Antigo Dono", "doc": "111"}}],
        "matricula_usucapienda_id": None,
        "confrontantes": [{"confrontante": "Vizinho Sul", "lado": "frente",
                           "tipo": "particular", "medida_m": 12.0}],
        "anuentes": [],
    }
    out = USU.anuentes_de(proj)
    papeis = {a["papel"] for a in out}
    assert "confrontante" in papeis and "titular_tabular" in papeis
    tit = next(a for a in out if a["papel"] == "titular_tabular")
    assert tit["nome"] == "Antigo Dono"


from services.geo_urbano.generators import pdf as GPDF


def _pdf_text(data: bytes) -> str:
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)


def _proj_usucapiao():
    return {
        "denominacao_imovel": "Lote 12 — Quadra 8 — Vila São Francisco",
        "tipo_servico": "usucapiao", "modalidade_usucapiao": "extraordinaria",
        "situacao_registral": "nao_matriculado", "municipio": "Açailândia", "uf": "MA",
        "tema": "prime_i", "endereco": "Rua Safira, nº 147, Vila São Francisco",
        "area_declarada_m2": 360.0, "valor_atribuido": 85000.0,
        "posse": {"inicio": "2008", "origem": "ocupação para moradia",
                  "natureza": "mansa, pacífica, ininterrupta, com animus domini"},
        "soma_posses": [
            {"possuidor_nome": "Maria das Dores", "vinculo": "de_cujus", "inicio": "2008", "fim": "2018"},
            {"possuidor_nome": "João Filho", "vinculo": "proprio", "inicio": "2018", "fim": "atual"}],
        "partes": [
            {"papel": "requerente", "tipo_pessoa": "fisica", "nome": "João Filho",
             "cpf": "012.345.678-90", "estado_civil": "solteiro", "profissao": "lavrador"},
            {"papel": "advogado", "tipo_pessoa": "fisica", "nome": "Dra. Ana Souza",
             "oab": "OAB/MA 12345"}],
        "confrontantes": [
            {"confrontante": "Vizinho Norte", "lado": "fundo", "tipo": "particular", "medida_m": 12.0}],
        "cartorio": {"nome": "Cartório do 1º Ofício Extrajudicial da Comarca de Açailândia/MA",
                     "endereco": "Rua Bom Jesus, 236 — Centro — Açailândia/MA"},
    }


def test_requerimento_usucapiao_render():
    data = GPDF.gerar_pdf("requerimento_usucapiao", _proj_usucapiao(), "prime_i")
    assert _paginas(data) >= 1
    txt = _pdf_text(data)
    assert "USUCAPIÃO" in txt.upper()
    assert "1.238" in txt                      # fundamento da extraordinária
    assert "Maria das Dores" in txt            # possuidor somado
    assert "OAB/MA 12345" in txt               # advogado


def test_ata_notarial_render():
    data = GPDF.gerar_pdf("ata_notarial", _proj_usucapiao(), "prime_i")
    assert _paginas(data) >= 1
    txt = _pdf_text(data).upper()
    assert "ATA NOTARIAL" in txt
    assert "POSSE" in txt


def test_edital_usucapiao_render():
    data = GPDF.gerar_pdf("edital_usucapiao", _proj_usucapiao(), "prime_i")
    assert _paginas(data) >= 1
    assert "EDITAL" in _pdf_text(data).upper()


def test_declaracao_anuencia_render():
    proj = _proj_usucapiao()
    anuente = {"papel": "confrontante", "nome": "Vizinho Norte", "lado": "fundo",
               "medida_m": 12.0, "doc": "CPF 111.222.333-44"}
    data = GPDF.declaracao_anuencia(proj, anuente, "prime_i")
    assert _paginas(data) >= 1
    txt = _pdf_text(data)
    assert "ANUÊNCIA" in txt.upper() and "Vizinho Norte" in txt


def test_notificacao_render():
    proj = _proj_usucapiao()
    anuente = {"papel": "confrontante", "nome": "Vizinho Norte", "lado": "fundo"}
    data = GPDF.notificacao(proj, anuente, "prime_i")
    assert _paginas(data) >= 1
    assert "NOTIFICA" in _pdf_text(data).upper()


from services.geo_urbano.seed import build_seed_usucapiao
from services.geo_urbano.generators import dossie as DOSSIE


def test_seed_usucapiao_valido():
    doc = build_seed_usucapiao("u-test")
    m = GeoUrbanoProjeto(**doc)
    assert m.tipo_servico == "usucapiao"
    assert m.modalidade_usucapiao == "extraordinaria"
    assert any(p.vinculo == "de_cujus" for p in m.soma_posses)   # caso herdeiro
    # a soma de posses alcança o prazo da extraordinária (15 anos)
    r = USU.validar_posse(doc, ano_ref=2026)
    assert r["prazo_ok"] is True


def test_dossie_usucapiao_ordem_e_render():
    assert DOSSIE.ORDEM_DOSSIE_USUCAPIAO[0][0] == "requerimento_usucapiao"
    doc = build_seed_usucapiao("u-test")
    secoes = [
        ("Requerimento de Usucapião", [GPDF.gerar_pdf("requerimento_usucapiao", doc, "prime_i")]),
        ("Minuta de Ata Notarial", [GPDF.gerar_pdf("ata_notarial", doc, "prime_i")]),
        ("Memorial Descritivo", [GPDF.gerar_pdf("memorial_descritivo", doc, "prime_i")]),
        ("Edital", [GPDF.gerar_pdf("edital_usucapiao", doc, "prime_i")]),
    ]
    doss = DOSSIE.gerar_dossie_ordenado(doc, secoes)
    assert _paginas(doss) >= 6   # capa + sumário + 4 peças


def _mk_pdf_prosa(texto):
    """PDF com o texto quebrado em linhas (~90 chars) — espelha o Memorial em prosa."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    palavras, linhas, atual = texto.split(" "), [], ""
    for w in palavras:
        if len(atual) + len(w) + 1 > 90:
            linhas.append(atual); atual = w
        else:
            atual = f"{atual} {w}".strip()
    if atual:
        linhas.append(atual)
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    y = 800
    for ln in linhas:
        c.drawString(40, y, ln); y -= 13
    c.showPage(); c.save()
    return buf.getvalue()


def test_parse_memorial_usucapiao_prosa():
    from services.geo_urbano import extractor as EX
    texto = (
        "MEMORIAL DESCRITIVO Imóvel: LOTE 08 QD 01 BARRA AZUL Proprietário(a): FULANA "
        "Área ( m²): 1.106,00 m² Perímetro (m): 143,20 m LOC. CARTOGRAFICA: 01.57.001.0008.00004 - 184 "
        "DESCRIÇÃO DO PERÍMETRO Inicia-se a descrição deste perímetro no vértice FQNS-P-001, de "
        "coordenadas N 9.455.020,51m e E 222.460,41m; deste, segue confrontando com Srª Ilzom Teófilo, "
        "inscrito no CPF: 333.682.953-49, com os seguintes azimutes e distâncias: 166°01'06\" e 22,89 m "
        "até o vértice FQNS-P-002, de coordenadas N 9.454.998,30m e E 222.465,94m; 258°41'52\" e 49,37 m "
        "até o vértice FQNS-P-007, de coordenadas N 9.454.988,62m e E 222.417,52m; deste, segue "
        "confrontando com ROD. BR-010 KM 1418, com os seguintes azimutes e distâncias: 347°40'38\" e "
        "22,24 m até o vértice FQNS-P-006, de coordenadas N 9.455.010,35m e E 222.412,78m; deste, segue "
        "confrontando com Sr José Genivaldo, inscrito no CPF: 146.899.793-91, com os seguintes azimutes "
        "e distâncias: 77°57'39\" e 48,70 m até o vértice FQNS-P-001, ponto inicial."
    )
    r = EX.parse_memorial_usucapiao(_mk_pdf_prosa(texto))
    v = r["vertices"]
    assert len(v) == 4
    assert r["area_declarada_m2"] == 1106.0 and r["perimetro_m"] == 143.2
    assert v[0]["de"] == "FQNS-P-001" and v[0]["para"] == "FQNS-P-002"
    assert v[0]["coord_n"] == 9455020.51 and v[0]["coord_e"] == 222460.41
    assert v[2]["confrontante_lado"].startswith("ROD")
    assert v[3]["para"] == "FQNS-P-001"   # polígono fecha
    assert r.get("cmi_resultante") == "01.57.001.0008.00004"


def test_extrair_tudo_usa_memorial_usucapiao():
    from services.geo_urbano import extractor as EX
    texto = (
        "Inicia-se a descrição deste perímetro no vértice V1, de coordenadas N 9.455.020,51m e E "
        "222.460,41m; deste, segue confrontando com Vizinho A, inscrito no CPF: 111, com os seguintes "
        "azimutes e distâncias: 166°01'06\" e 22,89 m até o vértice V2, de coordenadas N 9.454.998,30m "
        "e E 222.465,94m; deste, segue confrontando com Vizinho B, com os seguintes azimutes e "
        "distâncias: 258°41'52\" e 49,37 m até o vértice V1, ponto inicial. Área ( m²): 500,00 m²"
    )
    res = EX.extrair_tudo({"memorial_usucapiao": [_mk_pdf_prosa(texto)]})
    assert len(res.get("vertices", [])) == 2
    assert res.get("area_declarada_m2") == 500.0
    assert not any("não enviado" in a for a in res.get("avisos", []))


def test_pecas_proprietario_tipo_aware():
    from services.geo_urbano import assinatura_proprietario as PROP
    usu = PROP.pecas_proprietario({"tipo_servico": "usucapiao"})
    chaves = [c for c, _ in usu]
    assert chaves == ["requerimento_usucapiao", "art_trt"]   # sem Superintendência; Ata fora
    rem = PROP.pecas_proprietario({"tipo_servico": "remembramento"})
    assert [c for c, _ in rem][0] == "requerimento_cartorio"


def test_seed_juridico_nao_destrutivo():
    proj = {
        "tipo_servico": "usucapiao", "modalidade_usucapiao": "extraordinaria",
        "uploads": {
            "prova_posse": [{"id": "u1", "filename": "iptu2010.pdf"}],
            "art_trt": [{"id": "u2", "filename": "art.pdf"}],
            "planta_usucapiao": [{"id": "u3", "filename": "planta.pdf"}],
        },
        "vertices": [{"ordem": 1, "confrontante_lado": "Rua Safira"},
                     {"ordem": 2, "confrontante_lado": "Lote 13"}],
        "provas_posse": [], "confrontantes": [],
    }
    sets = USU.seed_juridico(proj)
    assert any(p["upload_id"] == "u1" for p in sets["provas_posse"])
    assert {c["confrontante"] for c in sets["confrontantes"]} == {"Rua Safira", "Lote 13"}
    chk = {c["chave"]: c["status"] for c in sets["checklist"]}
    assert chk.get("planta_memorial") == "anexado" and chk.get("art_trt") == "anexado"
    # idempotente: já preenchido → não sobrescreve provas/confrontantes
    proj["provas_posse"] = [{"tipo": "luz", "ano": "2014"}]
    proj["confrontantes"] = [{"confrontante": "Vizinho X"}]
    sets2 = USU.seed_juridico(proj)
    assert "provas_posse" not in sets2 and "confrontantes" not in sets2
