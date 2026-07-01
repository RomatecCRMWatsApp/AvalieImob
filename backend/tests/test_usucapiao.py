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


def test_extrair_tudo_usucapiao_cria_matricula_da_certidao(monkeypatch):
    """Bug: usucapião (sem planilha de mapa) devolvia 0 matrículas — a matrícula lida
    da certidão (OCR) era descartada por não haver registro p/ anexar. Deve CRIAR."""
    from services.geo_urbano import extractor as EX
    cert_txt = ("REGISTRO GERAL MATRÍCULA nº 4.686 Livro nº 2-AB fls. 15 "
                "Lote nº 08 Quadra nº 01 Área de 1.106,00 m² "
                "PROPRIETÁRIO(A): LINDAURA MARIA OLIVEIRA DA ROCHA, brasileira, "
                "inscrita no CPF: 123.456.789-00.")
    monkeypatch.setattr(EX, "ocr_pdf", lambda *a, **k: cert_txt)
    mem = _mk_pdf_prosa(
        "Imóvel: LOTE 08 QD 01 BARRA AZUL Área ( m²): 1.106,00 m² "
        "Inicia-se a descrição deste perímetro no vértice V1, de coordenadas N 1,00m e E 2,00m; "
        "deste, segue confrontando com Vizinho A, com os seguintes azimutes e distâncias: "
        "10°00'00\" e 5,00 m até o vértice V1, ponto inicial.")
    res = EX.extrair_tudo({"memorial_usucapiao": [mem],
                           "certidao_inteiro_teor": [b"%PDF-fake-cert"]})
    mats = res.get("matriculas") or []
    assert len(mats) == 1, f"esperava 1 matrícula, veio {len(mats)}"
    assert (mats[0].get("matricula") or "").replace(".", "") == "4686"
    assert mats[0].get("proprietario_registral", {}).get("nome")   # OCR trouxe o titular


def test_extrair_tudo_usucapiao_semeia_matricula_do_memorial(monkeypatch):
    """Certidão ilegível (OCR vazio): semeia 1 matrícula com a denominação do Memorial
    p/ o imóvel usucapiendo ter registro a conferir/preencher."""
    from services.geo_urbano import extractor as EX
    monkeypatch.setattr(EX, "ocr_pdf", lambda *a, **k: "")
    mem = _mk_pdf_prosa(
        "Imóvel: LOTE 08 QD 01 BARRA AZUL. "
        "Inicia-se a descrição deste perímetro no vértice V1, de coordenadas N 1,00m e E 2,00m; "
        "deste, segue confrontando com Vizinho A, com os seguintes azimutes e distâncias: "
        "10°00'00\" e 5,00 m até o vértice V1, ponto inicial.")
    res = EX.extrair_tudo({"memorial_usucapiao": [mem],
                           "certidao_inteiro_teor": [b"%PDF-fake"]})
    mats = res.get("matriculas") or []
    assert len(mats) == 1
    assert mats[0].get("denominacao")   # semeada do Memorial


def test_assinatura_herdeiro_possuidor_assina():
    """Usucapião de herança: a possuidora é cadastrada como HERDEIRO — deve assinar o
    requerimento (é a requerente/possuidora). Titular registral NÃO assina."""
    from services.geo_urbano.generators import pdf as PDF
    proj = {"partes": [
        {"papel": "titular_tabular", "tipo_pessoa": "fisica", "nome": "LAURINDA", "falecido": True},
        {"papel": "herdeiro", "tipo_pessoa": "fisica", "nome": "LINDAURA MARIA"},
        {"papel": "advogado", "tipo_pessoa": "fisica", "nome": "JULIETA", "oab": "11.164", "uf_oab": "MA"}]}
    ass = PDF._partes_assinatura(proj)
    nomes = [n for n, _ in ass]
    assert "LINDAURA MARIA" in nomes            # herdeira-possuidora assina
    assert "LAURINDA" not in nomes              # titular registral (falecida) NÃO assina
    assert "JULIETA" not in nomes               # advogada tem bloco próprio
    # requerente explícito + herdeiro → ambos assinam
    p2 = {"partes": [{"papel": "requerente", "tipo_pessoa": "fisica", "nome": "A"},
                     {"papel": "herdeiro", "tipo_pessoa": "fisica", "nome": "B"}]}
    assert {n for n, _ in PDF._partes_assinatura(p2)} == {"A", "B"}


def test_capa_nao_duplica_quadra_e_acha_requerente():
    from services.geo_urbano.generators import capa as C
    assert C._num_quadra("Quadra 01") == "01"   # não sai "Quadra Quadra 01"
    assert C._num_quadra("Qd 41") == "41" and C._num_quadra("07") == "07"
    proj = {"partes": [{"papel": "advogado", "nome": "Adv"},
                       {"papel": "requerente", "nome": "Lindaura Maria"}]}
    assert C._requerente_nome(proj) == "Lindaura Maria"
    # fallback: sem requerente, usa o titular tabular (espólio)
    assert C._requerente_nome({"partes": [{"papel": "titular_tabular", "nome": "Laurinda"}]}) == "Laurinda"


def test_assinatura_mapa_por_servico():
    """A peça 'mapa' resolve o UPLOAD certo por serviço — usucapião usa a planta, não o
    mapa de remembramento (cada módulo com sua nomenclatura)."""
    from routes.geo_urbano import _MAPA_UPLOADS_POR_SERVICO as U, _MAPA_LABEL_POR_SERVICO as Lb
    assert U["usucapiao"][0] == "planta_usucapiao"
    assert U["desdobro"][0] == "mapa_desdobro" and U["remembramento"][0] == "mapa_remembramento"
    assert "Usucap" not in Lb["remembramento"] and "usucapienda" in Lb["usucapiao"]


def test_requerimento_usucapiao_completo():
    """O Requerimento deve trazer DAS PARTES (com proprietário FALECIDO + advogado/OAB),
    o imóvel com descrição perimétrica (memorial), a soma de posses e a FUNDAMENTAÇÃO
    jurídico-técnica (art. 216-A + art. 1.238 + prazo da modalidade)."""
    from services.geo_urbano.generators import pdf as PDF
    import fitz
    proj = {
        "tipo_servico": "usucapiao", "modalidade_usucapiao": "extraordinaria",
        "situacao_registral": "matriculado", "denominacao_imovel": "LOTE 08 QD 01",
        "endereco": "ROD BR 010 KM 1418", "municipio": "Açailândia", "uf": "MA",
        "area_declarada_m2": 1106.0, "perimetro_m": 143.2, "valor_atribuido": 110600.0,
        "vertices": [
            {"ordem": 1, "de": "V1", "para": "V2", "coord_n": 9455020.51, "coord_e": 222460.41,
             "distancia_m": 22.89, "azimute": "166°01'06\"", "confrontante_lado": "Sr Ilzom"},
            {"ordem": 2, "de": "V2", "para": "V3", "coord_n": 9454998.30, "coord_e": 222465.94,
             "distancia_m": 49.37, "azimute": "258°41'52\"", "confrontante_lado": "ROD BR-010"},
            {"ordem": 3, "de": "V3", "para": "V1", "coord_n": 9454988.62, "coord_e": 222417.52,
             "distancia_m": 22.24, "azimute": "347°40'38\"", "confrontante_lado": "Sr José"}],
        "matriculas": [{"matricula": "4.686", "livro": "2-AB", "folhas": "195",
                        "natureza": "UM TERRENO", "quadra": "01", "lote_origem": "08"}],
        "posse": {"inicio": "2008", "natureza": "mansa, pacífica e ininterrupta"},
        "soma_posses": [{"possuidor_nome": "de cujus", "vinculo": "de_cujus", "inicio": "2008", "fim": "2018"},
                        {"possuidor_nome": "Lindaura", "vinculo": "proprio", "inicio": "2018"}],
        "partes": [
            {"papel": "requerente", "tipo_pessoa": "fisica", "nome": "Lindaura Maria", "cpf": "000"},
            {"papel": "titular_tabular", "tipo_pessoa": "fisica", "nome": "Laurinda Maria", "falecido": True},
            {"papel": "advogado", "tipo_pessoa": "fisica", "nome": "JULIETA CARVALHO", "oab": "11.164", "uf_oab": "MA"}],
    }
    txt = "".join(p.get_text() for p in fitz.open("pdf", PDF.gerar_pdf("requerimento_usucapiao", proj, "prime_i")))
    for termo in ["DAS PARTES", "REQUERENTE", "PROPRIETÁRIO REGISTRAL", "FALECIDO", "ADVOGADO",
                  "OAB/MA 11.164", "DO IMÓVEL", "Descrição perimétrica", "QUADRO DE VÉRTICES",
                  "DA POSSE", "soma-se a posse", "FUNDAMENTAÇÃO JURÍDICO", "art. 216-A",
                  "art. 1.238", "15 anos", "DO PEDIDO", "pede deferimento"]:
        assert termo in txt, f"faltou no requerimento: {termo}"


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
