# @module services.geo_urbano.seed — caso-teste oficial J&G (Quadra 41 · PDN).
#
# Remembramento J&G — Quadra 41, Lotes 01 a 07, Parque das Nações, Açailândia/MA
# → 1 lote de 2.100,00 m². Valores do §13 da spec + códigos extraídos dos PDFs
# reais (mapa de remembramento / BCIs). Usado nos testes e no endpoint /seed.
from __future__ import annotations

from models.geo_urbano import (
    GeoUrbanoProjeto, Matricula, BCI, Vertice, Parte, IptuRegularidade,
    Confrontacao, CadeiaAto, Titular, calcular_completude,
)

_JG = ("J & G Indústria e Comércio Ltda-EPP", "28.804.226/0001-64")
_INCORP = ("INCORPORADORA BRASIL LTDA", "07.612.344/0001-09")

# (ordem, matricula, livro, folhas, lote, cod_imovel, loc_cart, frente_m, frente_conf,
#  [ (lado, medida, confrontante) D/E/Fundo ])
_LOTES = [
    (1, "34.161", "2-HN", "70", "01", "0000012424", "01.10.041.0001.00001", 15.0, "Rua Inglaterra",
     [("lateral_direita", 20.0, "Lote nº 02"), ("lateral_esquerda", 20.0, "Rua Venezuela"), ("fundo", 15.0, "Lote nº 24")]),
    (2, "34.162", "2-HN", "71", "02", "0002121673", "01.10.041.0002.00001", 15.0, "Rua Inglaterra",
     [("lateral_direita", 20.0, "Lote nº 03"), ("lateral_esquerda", 20.0, "Lote nº 01"), ("fundo", 15.0, "Lote nº 24")]),
    (3, "31.000", "2-GH", "66", "03", "0002120957", "01.10.041.0003.00001", 15.0, "Rua Inglaterra",
     [("lateral_direita", 20.0, "Lote nº 04"), ("lateral_esquerda", 20.0, "Lote nº 02"), ("fundo", 15.0, "Lote nº 05")]),
    (4, "31.001", "2-GH", "67", "04", "0000011252", "00.10.041.0004.00001", 15.0, "Rua Inglaterra",
     [("lateral_direita", 20.0, "Rua Suriname"), ("lateral_esquerda", 20.0, "Lote nº 03"), ("fundo", 15.0, "Lote nº 05")]),
    (5, "31.002", "2-GH", "68", "05", "0000011253", "00.10.041.0005.00001", 10.0, "Rua Suriname",
     [("lateral_direita", 30.0, "Lote nº 06"), ("lateral_esquerda", 30.0, "Lotes nº 03 e 04"), ("fundo", 10.0, "Lote nº 24")]),
    (6, "31.003", "2-GH", "69", "06", "0002120958", "00.10.041.0006.00001", 10.0, "Rua Suriname",
     [("lateral_direita", 30.0, "Lote nº 07"), ("lateral_esquerda", 30.0, "Lote nº 05"), ("fundo", 10.0, "Lote nº 23")]),
    (7, "31.004", "2-GH", "70", "07", "0000011254", "00.10.041.0007.00001", 10.0, "Rua Suriname",
     [("lateral_direita", 30.0, "Lote nº 08"), ("lateral_esquerda", 30.0, "Lote nº 06"), ("fundo", 10.0, "Lote nº 22")]),
]

# Vértices da poligonal resultante (mapa de remembramento — SIRGAS2000 / UTM 23S)
_VERTICES = [
    (1, "FQNS-P-PDN1", "FQNS-P-PDN2", 9453722.7409, 226466.3304, "150°03'29\"", 50.0, 1.00052614,
     "04°56'15,475979\"S", "47°27'59,462032\"W", "Rua Suriname"),
    (2, "FQNS-P-PDN2", "FQNS-P-PDN3", 9453707.7672, 226440.3345, "240°03'29\"", 30.0, 1.00052632,
     "04°56'15,960049\"S", "47°28'00,307186\"W", "Lote 08"),
    (3, "FQNS-P-PDN3", "FQNS-P-PDN4", 9453733.7632, 226425.3608, "330°03'29\"", 30.0, 1.00052642,
     "04°56'15,112398\"S", "47°28'00,789830\"W", "Lotes 22, 23 e 24"),
    (4, "FQNS-P-PDN4", "FQNS-P-PDN5", 9453718.7895, 226399.3648, "240°03'29\"", 30.0, 1.00052660,
     "04°56'15,596468\"S", "47°28'01,634984\"W", "Lote 24"),
    (5, "FQNS-P-PDN5", "FQNS-P-PDN6", 9453736.1202, 226389.3824, "330°03'29\"", 20.0, 1.00052666,
     "04°56'15,031367\"S", "47°28'01,956746\"W", "Rua Venezuela"),
    (6, "FQNS-P-PDN6", "FQNS-P-PDN1", 9453766.0675, 226441.3743, "60°03'29\"", 60.0, 1.00052631,
     "04°56'14,063228\"S", "47°28'00,266439\"W", "Rua Inglaterra"),
]

# Nº dos acordos de parcelamento de IPTU (§13): lotes 01,03,04,05,06,07
_ACORDOS = {1: "2026001084", 3: "2026001079", 4: "2026001080",
            5: "2026001081", 6: "2026001082", 7: "2026001083"}


def build_seed(user_id: str = "") -> dict:
    matriculas, bci_list, iptu_list = [], [], []
    for (ordem, mat, livro, folhas, lote, cod, loc, fr_m, fr_conf, conf_dei) in _LOTES:
        confs = [Confrontacao(lado="frente", medida_m=fr_m, confrontante=fr_conf)]
        confs += [Confrontacao(lado=l, medida_m=m, confrontante=c) for (l, m, c) in conf_dei]
        cadeia = []
        reg_ant = None
        if ordem == 1:
            reg_ant = "Matrícula nº 0.811 - AV-249, fls. 69, Livro 2-HN"
            cadeia = [CadeiaAto(ato="R-01/34.161", protocolo="60.686/2025", data="2025-11-14",
                                tipo="Compra e Venda",
                                transmitente=f"{_INCORP[0]} ({_INCORP[1]})",
                                adquirente=f"{_JG[0]} ({_JG[1]})")]
        m = Matricula(
            ordem=ordem, matricula=mat, livro=livro, folhas=folhas,
            cri="Cartório do 1º Ofício Extrajudicial da Comarca de Açailândia/MA",
            natureza="UM TERRENO", lote_origem=lote, quadra="41", loteamento="Parque das Nações",
            endereco=fr_conf if "Rua" in fr_conf else "Rua Inglaterra",
            cod_imovel=cod, loc_cartografica=loc, area_m2=300.0, confrontacoes=confs,
            registro_anterior=reg_ant,
            proprietario_registral=Titular(nome=_JG[0], doc=_JG[1]), cadeia=cadeia,
        )
        matriculas.append(m)

        # BCI — Lote 01 ainda em nome da INCORPORADORA (divergência); demais em J&G.
        dono = _INCORP if ordem == 1 else _JG
        bci_list.append(BCI(
            matricula_id=m.id, cod_imovel=cod, loc_cartografica=loc,
            inscricao_contribuinte=("7072" if ordem == 1 else "27552"),
            proprietario_cadastral=Titular(nome=dono[0], doc=dono[1]),
            natureza="Predio", situacao="Ativo",
            testada_principal_m=fr_m, profundidade_m=(15.0 if fr_m == 15.0 else 30.0),
            area_terreno_m2=300.0, area_edificada_m2=300.0,
            endereco=f"{m.endereco}, {lote}", bairro="Parque das Nações", data_cadastro="2018-05-10",
        ))

        # IPTU — Lote 02 com CND negativa; demais com guia paga (parcelamento).
        if ordem == 2:
            iptu_list.append(IptuRegularidade(
                matricula_id=m.id, via_regularidade="cnd", situacao="cnd_negativa",
                cnd_numero="0000001596", cnd_validade="2026-08-22"))
        else:
            iptu_list.append(IptuRegularidade(
                matricula_id=m.id, via_regularidade="guia_paga", situacao="debito_parcelado",
                acordo_numero=_ACORDOS.get(ordem), valor=394.00, vencimento="2026-07-24",
                exercicios=["2023", "2024", "2025"]))

    # A planilha §13 lista, por linha, a coordenada do vértice PARA — alinhamos cada
    # vértice à SUA posição (mesma correção da extração) p/ desenho/Memorial baterem.
    from services.geo_urbano.extractor import alinhar_coords_aos_vertices
    _vraw = [{"ordem": o, "de": de, "para": para, "coord_n": n, "coord_e": e, "azimute": az,
              "distancia_m": d, "fator_k": fk, "latitude": lat, "longitude": lon, "confrontante_lado": lado}
             for (o, de, para, n, e, az, d, fk, lat, lon, lado) in _VERTICES]
    alinhar_coords_aos_vertices(_vraw)
    vertices = [Vertice(**v) for v in _vraw]

    partes = [
        Parte(papel="requerente", tipo_pessoa="juridica", razao_social=_JG[0], cnpj=_JG[1],
              nire="21200977129", junta="JUCEMA 20250557690 (08/05/2025)",
              sede="Rua Suriname, nº 05, Qd. 41, Parque das Nações, Açailândia/MA, CEP 65.930-000"),
        Parte(papel="representante", tipo_pessoa="fisica",
              nome="Juscelino Oliveira e Silva Junior", cpf="027.460.033-17",
              rg="031092472006-0 SSP/MA", cnh="04862672405 DETRAN/MA",
              nacionalidade="brasileiro", estado_civil="solteiro", profissao="advogado",
              nascimento="1991-02-06",
              filiacao="filho de Juscelino Oliveira e Silva e Joselia Santos",
              endereco="Rua Safira, nº 147, Qd. 41, Lt. 23, Vila São Francisco, Açailândia/MA"),
    ]

    proj = GeoUrbanoProjeto(
        user_id=user_id,
        denominacao_imovel="Lote 01 (remembrado) — Quadra 41 — Parque das Nações",
        tipo_servico="remembramento", tema="prime_i", status="conferencia",
        municipio="Açailândia", uf="MA", bairro="Parque das Nações", loteamento="Parque das Nações",
        quadra="41", lote_resultante="01",
        endereco="Rua Venezuela, Qd. 41, Lt. 01, Parque das Nações, Açailândia/MA",
        cmi_resultante="01.10.041.0001.00001",
        cadastro_novo="QD 41 / LT 01", cadastro_antigo="QD 41 / LT 01,02,03,04,05,06 e 07",
        area_declarada_m2=2100.00, perimetro_m=220.00,
        matriculas=matriculas, bci=bci_list, vertices=vertices, partes=partes, iptu=iptu_list,
    )
    doc = proj.model_dump(mode="json")
    doc["completude"] = calcular_completude(doc)
    return doc


def build_seed_usucapiao(user_id: str = "") -> dict:
    """Caso-teste do HERDEIRO: usucapião extraordinária com soma da posse do de cujus
    (2008–2018) + posse própria do herdeiro (2018–atual) sobre lote urbano em
    Açailândia/MA, imóvel sem registro (pede abertura de matrícula)."""
    from models.geo_urbano import (
        GeoUrbanoProjeto, Parte, Posse, PossePeriodo, ProvaPosse,
        AnuenteUsucapiao, Confrontacao, calcular_completude,
    )
    partes = [
        Parte(papel="requerente", tipo_pessoa="fisica", nome="João Filho da Silva",
              cpf="012.345.678-90", rg="0123456 SSP/MA", nacionalidade="brasileiro",
              estado_civil="solteiro", profissao="lavrador",
              filiacao="filho de José da Silva e Maria das Dores da Silva",
              endereco="Rua Safira, nº 147, Vila São Francisco, Açailândia/MA"),
        Parte(papel="advogado", tipo_pessoa="fisica", nome="Dra. Ana Souza",
              oab="12345", uf_oab="MA",
              endereco="Av. Central, nº 100, Centro, Açailândia/MA"),
        Parte(papel="herdeiro", tipo_pessoa="fisica", nome="Pedro da Silva",
              cpf="098.765.432-10", nacionalidade="brasileiro", estado_civil="casado"),
        Parte(papel="testemunha", tipo_pessoa="fisica", nome="Carlos Pereira"),
    ]
    confs = [
        Confrontacao(lado="frente", medida_m=12.0, confrontante="Rua Safira"),
        Confrontacao(lado="lateral_direita", medida_m=30.0, confrontante="Lote 13"),
        Confrontacao(lado="lateral_esquerda", medida_m=30.0, confrontante="Lote 11"),
        Confrontacao(lado="fundo", medida_m=12.0, confrontante="Lote 20 (Vizinho Norte)"),
    ]
    proj = GeoUrbanoProjeto(
        user_id=user_id,
        denominacao_imovel="Lote 12 — Quadra 8 — Vila São Francisco",
        tipo_servico="usucapiao", tema="prime_i", status="conferencia",
        modalidade_usucapiao="extraordinaria", situacao_registral="nao_matriculado",
        municipio="Açailândia", uf="MA", bairro="Vila São Francisco", quadra="8",
        lote_resultante="12",
        endereco="Rua Safira, nº 147, Quadra 8, Lote 12, Vila São Francisco, Açailândia/MA",
        area_declarada_m2=360.00, perimetro_m=84.00, valor_atribuido=85000.00,
        posse=Posse(inicio="2008", origem="ocupação para moradia da família",
                    benfeitorias="casa de alvenaria com 3 cômodos", benfeitorias_data="2009"),
        soma_posses=[
            PossePeriodo(possuidor_nome="Maria das Dores da Silva", vinculo="de_cujus",
                         inicio="2008", fim="2018",
                         observacao="posse da genitora (de cujus), somada por sucessão"),
            PossePeriodo(possuidor_nome="João Filho da Silva", vinculo="proprio",
                         inicio="2018", fim="atual",
                         observacao="posse exclusiva do herdeiro (rompimento da composse)"),
        ],
        provas_posse=[
            ProvaPosse(tipo="iptu", ano="2010", descricao="Carnê de IPTU 2010"),
            ProvaPosse(tipo="luz", ano="2014", descricao="Fatura de energia 2014"),
            ProvaPosse(tipo="agua", ano="2020", descricao="Fatura de água 2020"),
        ],
        anuentes=[AnuenteUsucapiao(papel="confrontante", nome="Vizinho Norte",
                                   lado="fundo", medida_m=12.0, tipo="particular",
                                   canal="presencial")],
        partes=partes,
    )
    doc = proj.model_dump(mode="json")
    # confrontantes da poligonal (usados pela anuência/requerimento)
    doc["confrontantes"] = [
        {"id": c.lado, "lado": c.lado, "confrontante": c.confrontante, "medida_m": c.medida_m,
         "tipo": "particular"} for c in confs]
    doc["completude"] = calcular_completude(doc)
    return doc
