# @module services.georef.generators.textos — Builders de conteúdo (texto/dados).
#
# Cada builder recebe o `projeto` (dict do Mongo) e devolve o conteúdo estruturado
# do documento, consumido tanto pelo renderer PDF quanto pelo DOCX (fonte única).
#
# Base normativa citada: Lei 6.015/1973 (art. 176 §§3º–5º), Lei 10.267/2001,
# Decreto 4.449/2002, IN INCRA 82/2015, Lei 4.947/1966 (art. 22), NBR 13133,
# Provimento CNJ 195/2025 (SIG-RI/IERI-e) e Decreto 12.689/2025 (prazo até 2029).
from datetime import datetime, timezone, timedelta

_MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

LEI_POR_SERVICO = {
    "georreferenciamento": "averbação da descrição georreferenciada na matrícula",
    "desmembramento": "desmembramento e abertura de novas matrículas",
    "remembramento": "remembramento/unificação de matrículas",
    "desdobro": "desdobro de área",
    "retificacao": "retificação administrativa de área (art. 213 da Lei 6.015/1973)",
    "certificacao": "certificação da poligonal junto ao INCRA/SIGEF",
}

# Ação pedida no Requerimento, por tipo de serviço.
ACAO_REQUERIMENTO = {
    "georreferenciamento": "a AVERBAÇÃO da descrição georreferenciada",
    "desmembramento": "o DESMEMBRAMENTO, com a abertura das matrículas das parcelas resultantes",
    "remembramento": "o REMEMBRAMENTO (unificação) das matrículas",
    "desdobro": "o DESDOBRO da área",
    "retificacao": "a RETIFICAÇÃO administrativa da área (art. 213 da Lei nº 6.015/1973)",
    "certificacao": "a averbação da certificação georreferenciada",
}


def _parcelas_resumo(projeto):
    """Linhas 'Parte II — DENOM: área X ha, perímetro Y m' quando há multi-parcela."""
    from services.georef.parcelas import parcelas_do_projeto, tem_multiparcela
    if not tem_multiparcela(projeto):
        return None
    out = []
    for p in parcelas_do_projeto(projeto):
        out.append(
            f"{p['rotulo']} — {p.get('denominacao') or 'parcela'}: área {_ha(p.get('area_ha'))} ha, "
            f"perímetro {_m(p.get('perimetro_m'))} m"
        )
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _im(projeto):
    return projeto.get("imovel") or {}


def _rt(projeto):
    return projeto.get("responsavel_tecnico") or {}


def _v(d, k, default="—"):
    val = d.get(k)
    return val if (val not in (None, "")) else default


def _ha(v):
    try:
        return f"{float(v):.4f}".replace(".", ",")
    except (TypeError, ValueError):
        return "—"


def _m(v):
    try:
        return f"{float(v):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return "—"


def data_extenso(municipio=None, uf=None) -> str:
    """'Açailândia/MA, 25 de junho de 2026' (data atual em UTC-3)."""
    agora = datetime.now(timezone.utc) - timedelta(hours=3)
    local = f"{municipio or '___'}/{uf or '__'}"
    return f"{local}, {agora.day} de {_MESES[agora.month - 1]} de {agora.year}"


def _art_trt(im, rt):
    return rt.get("art_trt") or im.get("certificacao_sigef") or "—"


def _rt_assinatura_linhas(im, rt):
    """Bloco de qualificação do RT (reuso em DRL/Laudo/Requerimento)."""
    return [
        rt.get("nome") or "—",
        f"{rt.get('formacao') or '—'} — Conselho {rt.get('conselho') or '—'}",
        f"Credenciado INCRA {rt.get('credenciamento_incra') or '—'} — ART/TRT {_art_trt(im, rt)}",
        f"Avaliador CNAI {rt.get('cnai') or '—'} — {rt.get('creci') or '—'}",
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Requerimento ao Cartório
# ──────────────────────────────────────────────────────────────────────────────
def render_requerimento(projeto) -> dict:
    im, rt = _im(projeto), _rt(projeto)
    nac = (im.get("proprietario_nacionalidade") or "brasileira").lower()
    acao = ACAO_REQUERIMENTO.get(projeto.get("tipo_servico"),
                                 "a AVERBAÇÃO da descrição georreferenciada")

    comarca = im.get("cartorio_municipio") or im.get("municipio") or "___"
    comarca_uf = im.get("cartorio_uf") or im.get("uf") or ""
    destinatario = (
        "EXCELENTÍSSIMO(A) SENHOR(A) OFICIAL DO CARTÓRIO DE REGISTRO DE IMÓVEIS\n"
        f"DA COMARCA DE {comarca}" + (f"/{comarca_uf}" if comarca_uf else "")
    )

    corpo = (
        f"{_v(im, 'proprietario_nome')}, {nac}, "
        f"{im.get('proprietario_estado_civil') or '[estado civil]'}, "
        f"{im.get('proprietario_profissao') or '[profissão]'}, "
        f"inscrito(a) no CPF/CNPJ sob o nº {_v(im, 'proprietario_cpf_cnpj')}, residente e "
        f"domiciliado(a) em {im.get('proprietario_endereco') or '[endereço]'}, na qualidade de "
        f"proprietário(a) do imóvel rural denominado \"{_v(im, 'denominacao')}\", matrícula nº "
        f"{_v(im, 'matricula')} (cujos dados constam da CERTIDÃO DE INTEIRO TEOR em anexo), "
        f"Livro {im.get('livro') or '2'}, Código INCRA/SNCR nº "
        f"{_v(im, 'cod_incra')}, com área de {_ha(im.get('area_ha'))} ha e perímetro de "
        f"{_m(im.get('perimetro_m'))} m, situado no Município de {_v(im, 'municipio')}/"
        f"{_v(im, 'uf')}, vem, respeitosamente, REQUERER {acao} "
        f"do referido imóvel, nos termos do art. 176, §§ 3º e 4º, da Lei nº "
        f"6.015/1973, da Lei nº 10.267/2001, do Decreto nº 4.449/2002 e do Provimento CNJ nº "
        f"195/2025, conforme certificação do INCRA/SIGEF sob o código "
        f"{_v(im, 'certificacao_sigef')}, instruindo o presente com:"
    )

    itens = [
        f"Certidão de inteiro teor da matrícula nº {_v(im, 'matricula')}, atualizada, "
        "de onde foram extraídos os dados registrais do imóvel;",
        "Planta e memorial descritivo georreferenciados, assinados por profissional "
        "habilitado, com a respectiva ART/TRT;",
        "Certificado de Cadastro de Imóvel Rural (CCIR) vigente;",
    ]
    if requer_drl(projeto.get("tipo_servico")):
        itens.append(
            "Declaração(ões) de Reconhecimento de Limites (DRL) firmada(s) pelos confrontantes;")
    itens.append(
        "Arquivo geoespacial (shapefile, SIRGAS 2000) para alimentação do SIG-RI, nos termos "
        "do Provimento CNJ nº 195/2025.")
    documentos = [f"{chr(97 + i)}) {t}" for i, t in enumerate(itens)]

    fecho = (
        "Requer, ainda, a inserção das coordenadas geodésicas no Sistema de Informações "
        "Geográficas do Registro de Imóveis (SIG-RI), por profissional técnico habilitado, "
        "vinculada ao número de prenotação a ser fornecido."
    )

    rt_linha = (
        f"Responsável Técnico: {rt.get('nome') or '—'} — {rt.get('formacao') or '—'} — "
        f"{rt.get('conselho') or '—'} — Cód. Cred. INCRA {rt.get('credenciamento_incra') or '—'} "
        f"— ART/TRT {_art_trt(im, rt)}."
    )

    return {
        "titulo": "REQUERIMENTO DE AVERBAÇÃO DE GEORREFERENCIAMENTO",
        "destinatario": destinatario,
        "corpo": corpo,
        # Termos em NEGRITO no corpo: a denominação do imóvel e a ação requerida.
        "corpo_negrito": [_v(im, "denominacao"), f"REQUERER {acao}"],
        "documentos": documentos,
        "fecho": fecho,
        "rt_linha": rt_linha,
        "parcelas": _parcelas_resumo(projeto),
        "data": data_extenso(im.get("municipio"), im.get("uf")),
        "assinatura": [
            _v(im, "proprietario_nome"),
            f"CPF/CNPJ {_v(im, 'proprietario_cpf_cnpj')}",
        ],
    }


# ──────────────────────────────────────────────────────────────────────────────
# DRL — Declaração de Reconhecimento de Limites (1 por confrontante)
# ──────────────────────────────────────────────────────────────────────────────
def render_drl(projeto, conf) -> dict:
    im, rt = _im(projeto), _rt(projeto)
    vidx = {v.get("codigo"): v for v in (projeto.get("vertices") or [])}

    linhas = []
    for cod in conf.get("segmentos") or []:
        v = vidx.get(cod)
        if not v:
            continue
        linhas.append([
            v.get("codigo") or "—",
            v.get("longitude_dms") or "—",
            v.get("latitude_dms") or "—",
            v.get("vante_codigo") or "—",
            v.get("azimute") or "—",
            _m(v.get("distancia")),
        ])

    via_publica = (conf.get("tipo") == "via_publica")

    cabecalho = [
        f"Imóvel objeto: {_v(im, 'denominacao')} — Matrícula {_v(im, 'matricula')} — "
        f"INCRA/SNCR {_v(im, 'cod_incra')}",
        f"Proprietário: {_v(im, 'proprietario_nome')}, CPF/CNPJ {_v(im, 'proprietario_cpf_cnpj')}",
        f"Município/UF: {_v(im, 'municipio')}/{_v(im, 'uf')} — Sistema Geodésico: "
        f"{im.get('sistema_geodesico') or 'SIRGAS 2000'}",
        f"Responsável Técnico: {rt.get('nome') or '—'} — {rt.get('formacao') or '—'} — "
        f"{rt.get('conselho') or '—'} — Cód. Cred. INCRA {rt.get('credenciamento_incra') or '—'} "
        f"— ART/TRT {_art_trt(im, rt)}",
        f"CONFRONTANTE: {conf.get('nome') or conf.get('descricao') or '—'}",
        f"Imóvel confrontante: {conf.get('imovel') or conf.get('descricao') or '—'} — "
        f"Matrícula {conf.get('matricula') or '—'} — CNS {conf.get('cns') or '—'} — "
        f"INCRA {conf.get('incra') or '—'}",
    ]

    if via_publica:
        corpo = (
            "Declara o Responsável Técnico, sob as penas da lei, que a linha divisória comum "
            "abaixo descrita confronta com BEM PÚBLICO / via pública, dispensada a anuência de "
            "confrontante particular, em conformidade com o art. 176 da Lei nº 6.015/1973, a Lei "
            "nº 10.267/2001 e o Provimento CNJ nº 195/2025, inexistindo litígio ou sobreposição "
            "quanto à referida divisa."
        )
        assinaturas = [
            (_v(im, "proprietario_nome"), f"Proprietário — CPF/CNPJ {_v(im, 'proprietario_cpf_cnpj')}"),
            (rt.get("nome") or "—", f"Responsável Técnico — {rt.get('conselho') or '—'}"),
        ]
    else:
        corpo = (
            "O(A) confrontante acima identificado(a) DECLARA, para os devidos fins de direito e em "
            "atendimento ao art. 176 da Lei nº 6.015/1973, à Lei nº 10.267/2001 e ao Provimento CNJ "
            "nº 195/2025, que RECONHECE como corretos e verdadeiros os limites e confrontações da "
            "linha divisória comum com o imóvel objeto, definida pelos vértices e segmentos "
            "georreferenciados (SIRGAS 2000) abaixo, anuindo expressamente com a descrição "
            "apresentada e declarando inexistir litígio, dúvida ou sobreposição quanto à referida "
            "divisa."
        )
        assinaturas = [
            (conf.get("nome") or "Confrontante",
             f"Confrontante — CPF/CNPJ {conf.get('cpf_cnpj') or '____'}"),
            (_v(im, "proprietario_nome"), f"Proprietário — CPF/CNPJ {_v(im, 'proprietario_cpf_cnpj')}"),
            (rt.get("nome") or "—", f"Responsável Técnico — {rt.get('conselho') or '—'}"),
        ]

    return {
        "titulo": "DECLARAÇÃO DE RECONHECIMENTO DE LIMITES (DRL)",
        "cabecalho": cabecalho,
        "corpo": corpo,
        "tabela_header": ["Vértice", "Longitude", "Latitude", "Vante", "Azimute", "Dist.(m)"],
        "tabela": linhas,
        "assinaturas": assinaturas,
        "via_publica": via_publica,
        "data": data_extenso(im.get("municipio"), im.get("uf")),
    }


# A DRL (anuência dos confrontantes) só se aplica a serviços que ESTABELECEM/
# reconhecem limites com vizinhos. Desmembramento e Remembramento DISPENSAM DRL
# (atuam dentro de limites já certificados). Georref, Retificação, Certificação e
# Desdobro EXIGEM. (Confirmado pelo RT — José Romário.)
DRL_DISPENSA = {"desmembramento", "remembramento"}


def requer_drl(tipo_servico) -> bool:
    """True se o tipo de serviço exige DRL dos confrontantes."""
    return (tipo_servico or "") not in DRL_DISPENSA


def confrontantes_para_drl(projeto):
    """Confrontantes que geram DRL (exclui o próprio imóvel).

    Retorna [] quando o tipo de serviço DISPENSA DRL (desmembramento/remembramento),
    fazendo o Dossiê e a tela não listarem/gerarem DRL para esses casos.
    """
    if not requer_drl(projeto.get("tipo_servico")):
        return []
    return [c for c in (projeto.get("confrontantes") or []) if c.get("tipo") != "proprio"]


# ──────────────────────────────────────────────────────────────────────────────
# Memorial Descritivo (recomposição padrão)
# ──────────────────────────────────────────────────────────────────────────────
def render_memorial(projeto) -> dict:
    im, rt = _im(projeto), _rt(projeto)
    linhas = []
    for v in projeto.get("vertices") or []:
        linhas.append([
            v.get("codigo") or "—",
            v.get("longitude_dms") or "—",
            v.get("latitude_dms") or "—",
            _m(v.get("altitude")) if v.get("altitude") is not None else "—",
            v.get("vante_codigo") or "—",
            v.get("azimute") or "—",
            _m(v.get("distancia")),
        ])
    cabecalho = [
        ("Denominação", _v(im, "denominacao")),
        ("Proprietário(a)", _v(im, "proprietario_nome")),
        ("CPF/CNPJ", _v(im, "proprietario_cpf_cnpj")),
        ("Matrícula", _v(im, "matricula")),
        ("Código INCRA/SNCR", _v(im, "cod_incra")),
        ("Natureza da Área", _v(im, "natureza_area")),
        ("Município/UF", f"{_v(im, 'municipio')}/{_v(im, 'uf')}"),
        ("Cartório (CNS)", f"({im.get('cartorio_cns') or '—'}) {im.get('cartorio_nome') or '—'}"),
        ("Sistema Geodésico", im.get("sistema_geodesico") or "SIRGAS 2000"),
        ("Área (SGL)", f"{_ha(im.get('area_ha'))} ha"),
        ("Perímetro", f"{_m(im.get('perimetro_m'))} m"),
        ("Responsável Técnico", f"{rt.get('nome') or '—'} — {rt.get('conselho') or '—'} — "
                                f"Cód. INCRA {rt.get('credenciamento_incra') or '—'}"),
        ("Certificação SIGEF", _v(im, "certificacao_sigef")),
    ]
    return {
        "titulo": "MEMORIAL DESCRITIVO",
        "cabecalho": cabecalho,
        "tabela_header": ["Vértice", "Longitude", "Latitude", "Alt.(m)", "Vante", "Azimute", "Dist.(m)"],
        "tabela": linhas,
        "rt_assinatura": _rt_assinatura_linhas(im, rt),
        "data": data_extenso(im.get("municipio"), im.get("uf")),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Laudo Técnico de Agrimensura (peça de embasamento)
# ──────────────────────────────────────────────────────────────────────────────
def render_laudo_tecnico(projeto) -> dict:
    im, rt = _im(projeto), _rt(projeto)
    tipo_servico = projeto.get("tipo_servico") or "georreferenciamento"
    finalidade = LEI_POR_SERVICO.get(tipo_servico, tipo_servico)

    identificacao = (
        f"Imóvel: {_v(im, 'denominacao')} — Matrícula nº {_v(im, 'matricula')} (dados conforme "
        f"certidão de inteiro teor em anexo), Livro {im.get('livro') or '2'}, "
        f"{im.get('cartorio_nome') or '—'} (CNS {im.get('cartorio_cns') or '—'}).\n"
        f"Código INCRA/SNCR: {_v(im, 'cod_incra')}. Natureza: {im.get('natureza_area') or 'Particular'}. "
        f"Município/UF: {_v(im, 'municipio')}/{_v(im, 'uf')}.\n"
        f"Proprietário: {_v(im, 'proprietario_nome')}, CPF/CNPJ {_v(im, 'proprietario_cpf_cnpj')}.\n"
        f"Área (SGL): {_ha(im.get('area_ha'))} ha. Perímetro: {_m(im.get('perimetro_m'))} m. "
        f"Sistema Geodésico: {im.get('sistema_geodesico') or 'SIRGAS 2000'}.\n"
        f"Responsável Técnico: {rt.get('nome') or '—'} — {rt.get('formacao') or '—'} — Conselho "
        f"{rt.get('conselho') or '—'} — Cód. Credenciado INCRA {rt.get('credenciamento_incra') or '—'} "
        f"— ART/TRT {_art_trt(im, rt)}."
    )
    # Desmembramento/remembramento: o laudo abrange TODAS as parcelas resultantes.
    from services.georef.parcelas import tem_multiparcela as _tem_multi, parcelas_do_projeto as _parts
    if _tem_multi(projeto):
        _np = len(_parts(projeto))
        identificacao += (
            f"\nObjeto de {str(tipo_servico).upper()} em {_np} parcelas resultantes, todas "
            f"discriminadas no quadro PARCELAS RESULTANTES (área e perímetro de cada parte)."
        )

    objeto = (
        f"O presente Laudo Técnico tem por objeto o serviço de {tipo_servico} do imóvel rural "
        f"acima identificado, com vistas à {finalidade}, mediante levantamento georreferenciado da "
        f"poligonal e respectiva descrição perimetral, certificado junto ao INCRA/SIGEF sob o "
        f"código {_v(im, 'certificacao_sigef')}."
    )

    justificativa = (
        "1. Do que está sendo feito. Procedeu-se ao levantamento georreferenciado dos vértices "
        "definidores dos limites do imóvel, vinculados ao Sistema Geodésico Brasileiro (SIRGAS "
        f"2000), resultando em poligonal de {_ha(im.get('area_ha'))} ha e perímetro de "
        f"{_m(im.get('perimetro_m'))} m, com descrição de confrontações, azimutes e distâncias, "
        "ora consolidada em memorial descritivo e planta.\n\n"
        "2. Por que está sendo feito. O serviço atende à exigência legal de descrição do imóvel "
        "rural por meio de georreferenciamento, instituída pela Lei nº 10.267/2001 e regulamentada "
        "pelo Decreto nº 4.449/2002, bem como às diretrizes do Provimento CNJ nº 195/2025, que "
        "instituiu o Sistema de Informações Geográficas do Registro de Imóveis (SIG-RI), "
        "determinando o lançamento da poligonal, por profissional técnico habilitado, no Mapa do "
        "Registro de Imóveis do Brasil (ONR), com vistas ao controle da unicidade matricial, à "
        "prevenção de sobreposições e ao fortalecimento da segurança jurídica registral. "
        "Observa-se, ainda, o Decreto nº 12.689/2025, que disciplina o cronograma de "
        "obrigatoriedade do georreferenciamento de imóveis rurais.\n\n"
        "3. Fundamentos jurídicos. Lei nº 6.015/1973 (art. 176, §§ 3º a 5º); Lei nº 10.267/2001; "
        "Decreto nº 4.449/2002; IN INCRA nº 82/2015; Lei nº 4.947/1966 (art. 22); Provimento CNJ "
        "nº 195/2025 e Decreto nº 12.689/2025.\n\n"
        "4. Fundamentos técnicos. NBR 13133 (execução de levantamento topográfico); Manual Técnico "
        "de Posicionamento e Manual Técnico de Limites e Confrontações do INCRA; precisão "
        "posicional dos vértices conforme norma do INCRA para o Sistema Geodésico Brasileiro."
    )

    metodologia = (
        "Sistema Geodésico de Referência: SIRGAS 2000 (EPSG:4674).\n"
        "Método de levantamento: posicionamento por satélites GNSS, com rastreio em modo RTK e/ou "
        "pós-processamento (PPP/relativo estático), a partir de base de apoio georreferenciada.\n"
        "Precisão posicional: melhor ou igual ao limite fixado pelo INCRA para vértices de limite "
        "(≤ 0,50 m), conforme tipo de vértice (M — marco; P — ponto; V — virtual; O — outros).\n"
        "Pós-processamento e cálculo de área/perímetro em software técnico; descrição perimetral "
        "por azimutes geodésicos e distâncias entre vértices.\n"
        f"Certificação SIGEF: a poligonal foi submetida ao INCRA e certificada (não sobreposição), "
        f"sob o código {_v(im, 'certificacao_sigef')}."
    )

    resultado_tabela = [
        [v.get("codigo") or "—", v.get("longitude_dms") or "—", v.get("latitude_dms") or "—",
         (_m(v.get("altitude")) if v.get("altitude") is not None else "—"),
         v.get("vante_codigo") or "—", v.get("azimute") or "—", _m(v.get("distancia"))]
        for v in (projeto.get("vertices") or [])
    ]

    cadeia = [
        [a.get("ordem"), a.get("ato") or "—", a.get("tipo") or "—", a.get("data") or "—",
         a.get("partes") or "—"]
        for a in (im.get("cadeia_dominial") or [])
    ] or None

    confrontacoes = [
        [c.get("nome") or c.get("descricao") or "—", c.get("imovel") or "—",
         c.get("matricula") or "—", c.get("cns") or "—", ", ".join(c.get("segmentos") or [])]
        for c in (projeto.get("confrontantes") or [])
    ]

    # Parcelas resultantes (desmembramento/remembramento)
    from services.georef.parcelas import parcelas_do_projeto, tem_multiparcela
    parcelas_tabela = None
    if tem_multiparcela(projeto):
        parcelas_tabela = [
            [p["rotulo"], p.get("denominacao") or "—", _ha(p.get("area_ha")),
             _m(p.get("perimetro_m")), str(len(p.get("vertices") or []))]
            for p in parcelas_do_projeto(projeto)
        ]

    conclusao = (
        f"Diante do exposto, ATESTA-SE que o levantamento georreferenciado do imóvel "
        f"{_v(im, 'denominacao')}, matrícula nº {_v(im, 'matricula')}, foi executado em "
        f"conformidade com a NBR 13133 e com as normas técnicas do INCRA, encontrando-se a "
        f"poligonal certificada no SIGEF (ausência de sobreposição com outras parcelas do cadastro "
        f"georreferenciado). O imóvel apresenta área de {_ha(im.get('area_ha'))} ha e perímetro de "
        f"{_m(im.get('perimetro_m'))} m, com limites e confrontações reconhecidos. Conclui-se pela "
        f"aptidão técnica do imóvel à {finalidade} e à alimentação do SIG-RI, nos termos do "
        f"Provimento CNJ nº 195/2025, ressalvada a competência de qualificação jurídica do Oficial "
        f"de Registro de Imóveis."
    )

    return {
        "titulo": f"LAUDO TÉCNICO DE AGRIMENSURA — {str(tipo_servico).upper()}",
        "identificacao": identificacao,
        "identificacao_negrito": [_v(im, "denominacao")],   # denominação em negrito
        "objeto": objeto,
        "justificativa": justificativa,
        "metodologia": metodologia,
        "resultado_header": ["Vértice", "Longitude", "Latitude", "Alt.(m)", "Vante", "Azimute", "Dist.(m)"],
        "resultado_tabela": resultado_tabela,
        "cadeia_header": ["#", "Ato", "Tipo", "Data", "Partes"],
        "cadeia_tabela": cadeia,
        "cadeia_nota": (None if cadeia else
                        f"Cadeia dominial conforme certidão de matrícula nº "
                        f"{im.get('certidao_numero') or im.get('matricula') or '—'}, anexa."),
        "confrontacoes_header": ["Confrontante", "Imóvel", "Matrícula", "CNS", "Segmentos"],
        "confrontacoes_tabela": confrontacoes,
        "parcelas_header": ["Parcela", "Denominação", "Área (ha)", "Perímetro (m)", "Nº vértices"],
        "parcelas_tabela": parcelas_tabela,
        "conclusao": conclusao,
        "rt_assinatura": _rt_assinatura_linhas(im, rt),
        "data": data_extenso(im.get("municipio"), im.get("uf")),
    }
