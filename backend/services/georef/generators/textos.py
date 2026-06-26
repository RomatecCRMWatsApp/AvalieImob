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

# Finalidade no TÍTULO do requerimento (dinâmica por tipo de serviço).
FINALIDADE_TITULO = {
    "georreferenciamento": "para fim de averbação",
    "desmembramento": "para fim de desmembramento",
    "remembramento": "para fim de remembramento",
    "desdobro": "para fim de desdobro",
    "retificacao": "para fim de retificação de área",
    "certificacao": "para fim de certificação",
}


def _certificacao_bloco(im):
    """Linhas do bloco DA CERTIFICAÇÃO E CADASTRO (omite os campos vazios)."""
    pares = [
        ("Matrícula nº", im.get("matricula")),
        ("CNS/UNIF do cartório", im.get("cartorio_cns")),
        ("CCIR/INCRA nº", im.get("cod_incra") or im.get("incra_matricula")),
        ("CAR (Cadastro Ambiental Rural) nº", im.get("car")),
        ("NIRF/ITR nº", im.get("nirf")),
        ("Código de Certificação SIGEF", im.get("certificacao_sigef")),
    ]
    return [f"{lbl}: {v}" for lbl, v in pares if v not in (None, "") and str(v) != "—"]


def _parcelas_tabela(projeto):
    """Linhas da tabela de parcelas: [Parcela, Denominação, Área, Perímetro, Código SIGEF]."""
    from services.georef.parcelas import parcelas_do_projeto, tem_multiparcela
    if not tem_multiparcela(projeto):
        return None
    return [
        [p.get("rotulo") or "—", p.get("denominacao") or "—", _ha(p.get("area_ha")),
         _m(p.get("perimetro_m")), p.get("certificacao_sigef") or "—"]
        for p in parcelas_do_projeto(projeto)
    ]


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


# Dados do imóvel ATUAL / de ORIGEM (o que será desmembrado): preferem a MATRÍCULA
# (certidão de inteiro teor) e caem no SIGEF (parcela/Parte I) quando não houver.
def _denom_atual(im):
    return im.get("denominacao_matricula") or im.get("denominacao")


def _area_atual(im):
    v = im.get("area_matricula")
    return v if v not in (None, "") else im.get("area_ha")


def _perim_atual(im):
    v = im.get("perimetro_matricula")
    return v if v not in (None, "") else im.get("perimetro_m")


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

    # Comarca: serventia/comarca da CERTIDÃO (cartorio_municipio) → município registral
    # da matrícula → município do imóvel (memorial). A cidade da tabela CNS não entra
    # aqui (pode estar desatualizada — ver enriquecer_cartorio).
    comarca = (im.get("cartorio_municipio") or im.get("municipio_matricula")
               or im.get("municipio") or "___")
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
        f"proprietário(a) do imóvel rural denominado \"{_denom_atual(im) or '—'}\", matrícula nº "
        f"{_v(im, 'matricula')} (cujos dados constam da CERTIDÃO DE INTEIRO TEOR em anexo), "
        f"Livro {im.get('livro') or '2'}, Código INCRA/SNCR nº "
        f"{_v(im, 'cod_incra')}, com área de {_ha(_area_atual(im))} ha e perímetro de "
        f"{_m(_perim_atual(im))} m, situado no Município de {_v(im, 'municipio')}/"
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

    finalidade_tit = FINALIDADE_TITULO.get(projeto.get("tipo_servico"), "para fim de averbação")
    return {
        "titulo": f"REQUERIMENTO DE GEORREFERENCIAMENTO {finalidade_tit}",
        "destinatario": destinatario,
        "corpo": corpo,
        # Termos em NEGRITO no corpo: a denominação do imóvel e a ação requerida.
        "corpo_negrito": [_denom_atual(im) or "—", f"REQUERER {acao}"],
        "documentos": documentos,
        "certificacao_bloco": _certificacao_bloco(im),
        "parcelas_header": ["Parcela", "Denominação", "Área (ha)", "Perímetro (m)", "Código SIGEF"],
        "parcelas_tabela": _parcelas_tabela(projeto),
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

    # Partes (principal + parcelas) — fonte única, cada uma com seus próprios dados.
    from services.georef.parcelas import parcelas_do_projeto, tem_multiparcela
    multi = tem_multiparcela(projeto)
    partes = parcelas_do_projeto(projeto) if multi else []
    # Laudo SEPARADO: descreve UMA parcela isolada (o imóvel = a parcela; a matriz é só
    # citada como origem). `_parcela_isolada` = {"rotulo": "Parte II"}.
    parc_iso = projeto.get("_parcela_isolada")
    rot_iso = (parc_iso or {}).get("rotulo") or "Parcela"

    _tem_mat = im.get("area_matricula") not in (None, "")
    _area_lbl = "Área registral (matrícula)" if _tem_mat else "Área (SGL)"
    if parc_iso:
        # IDENTIFICAÇÃO da PARCELA (área/perímetro/SIGEF próprios) + matriz de origem.
        identificacao = (
            f"Imóvel (parcela): {rot_iso} — {im.get('denominacao') or '—'}, resultante do "
            f"{tipo_servico} da Matrícula nº {_v(im, 'matricula')}.\n"
            f"Código INCRA/SNCR: {_v(im, 'cod_incra')}. Natureza: {im.get('natureza_area') or 'Particular'}. "
            f"Município/UF: {_v(im, 'municipio')}/{_v(im, 'uf')}.\n"
            f"Proprietário: {_v(im, 'proprietario_nome')}, CPF/CNPJ {_v(im, 'proprietario_cpf_cnpj')}.\n"
            f"Área da parcela: {_ha(im.get('area_ha'))} ha. Perímetro: {_m(im.get('perimetro_m'))} m. "
            f"Sistema Geodésico: {im.get('sistema_geodesico') or 'SIRGAS 2000'}.\n"
            f"Certificação SIGEF (parcela): {_v(im, 'certificacao_sigef')}.\n"
            f"Imóvel de origem (matriz): Matrícula nº {_v(im, 'matricula')} — "
            f"{im.get('denominacao_matricula') or '—'}, área registral {_ha(im.get('area_matricula'))} ha, "
            f"{im.get('cartorio_nome') or '—'} (CNS {im.get('cartorio_cns') or '—'}).\n"
            f"Responsável Técnico: {rt.get('nome') or '—'} — {rt.get('formacao') or '—'} — Conselho "
            f"{rt.get('conselho') or '—'} — Cód. Credenciado INCRA {rt.get('credenciamento_incra') or '—'} "
            f"— ART/TRT {_art_trt(im, rt)}."
        )
    else:
        identificacao = (
            f"Imóvel: {_denom_atual(im) or '—'} — Matrícula nº {_v(im, 'matricula')} (dados conforme "
            f"certidão de inteiro teor em anexo), Livro {im.get('livro') or '2'}, "
            f"{im.get('cartorio_nome') or '—'} (CNS {im.get('cartorio_cns') or '—'}).\n"
            f"Código INCRA/SNCR: {_v(im, 'cod_incra')}. Natureza: {im.get('natureza_area') or 'Particular'}. "
            f"Município/UF: {_v(im, 'municipio')}/{_v(im, 'uf')}.\n"
            f"Proprietário: {_v(im, 'proprietario_nome')}, CPF/CNPJ {_v(im, 'proprietario_cpf_cnpj')}.\n"
            f"{_area_lbl}: {_ha(_area_atual(im))} ha. Perímetro: {_m(_perim_atual(im))} m. "
            f"Sistema Geodésico: {im.get('sistema_geodesico') or 'SIRGAS 2000'}.\n"
            f"Responsável Técnico: {rt.get('nome') or '—'} — {rt.get('formacao') or '—'} — Conselho "
            f"{rt.get('conselho') or '—'} — Cód. Credenciado INCRA {rt.get('credenciamento_incra') or '—'} "
            f"— ART/TRT {_art_trt(im, rt)}."
        )
    # Desmembramento/remembramento: o laudo abrange TODAS as parcelas resultantes.
    if multi:
        identificacao += (
            f"\nObjeto de {str(tipo_servico).upper()} em {len(partes)} parcelas resultantes, todas "
            f"discriminadas no quadro PARCELAS RESULTANTES e descritas, uma a uma, nas seções de "
            f"Resultado (poligonal) e Confrontações deste laudo."
        )

    # OBJETO — multi: lista TODOS os SIGEF; parcela isolada: descreve a parcela; senão padrão.
    if parc_iso:
        objeto = (
            f"O presente Laudo Técnico tem por objeto a descrição georreferenciada da {rot_iso} "
            f"({im.get('denominacao') or '—'}), parcela resultante do {tipo_servico} do imóvel rural "
            f"matriz (Matrícula nº {_v(im, 'matricula')}), com levantamento da poligonal e respectiva "
            f"descrição perimetral, certificada junto ao INCRA/SIGEF sob o código "
            f"{_v(im, 'certificacao_sigef')}."
        )
    elif multi:
        sigef_lista = "; ".join(
            f"{p['rotulo']} — {p.get('certificacao_sigef') or '—'}" for p in partes)
        cert_matriz = im.get("certificacao_matricula")
        frase_matriz = (
            f" A poligonal da matriz de origem encontra-se certificada sob o código "
            f"{cert_matriz}." if cert_matriz else "")
        objeto = (
            f"O presente Laudo Técnico tem por objeto o serviço de {tipo_servico} do imóvel rural "
            f"acima identificado (Matrícula nº {_v(im, 'matricula')}), com a sua divisão em "
            f"{len(partes)} parcelas resultantes, georreferenciadas e certificadas junto ao "
            f"INCRA/SIGEF sob os seguintes códigos de certificação: {sigef_lista}.{frase_matriz} "
            f"Cada parcela é descrita individualmente nas seções de Resultado e Confrontações."
        )
    else:
        objeto = (
            f"O presente Laudo Técnico tem por objeto o serviço de {tipo_servico} do imóvel rural "
            f"acima identificado, com vistas à {finalidade}, mediante levantamento georreferenciado da "
            f"poligonal e respectiva descrição perimetral, certificado junto ao INCRA/SIGEF sob o "
            f"código {_v(im, 'certificacao_sigef')}."
        )

    teor_matricula = (
        f"O imóvel objeto deste laudo encontra-se registrado sob a Matrícula nº "
        f"{_v(im, 'matricula')}, Livro {im.get('livro') or '2'}, do "
        f"{im.get('cartorio_nome') or '—'} (CNS {im.get('cartorio_cns') or '—'}), sob a "
        f"denominação \"{_denom_atual(im) or '—'}\", com área registral de "
        f"{_ha(_area_atual(im))} ha e perímetro de {_m(_perim_atual(im))} m, situado no "
        f"Município de {_v(im, 'municipio')}/{_v(im, 'uf')}. Os dados de identificação, área e "
        f"confrontações reportam-se à certidão de inteiro teor da matrícula em anexo, ora "
        f"juntada, dispensada a transcrição integral da cadeia dominial."
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

    def _vrow(v):
        return [v.get("codigo") or "—", v.get("longitude_dms") or "—", v.get("latitude_dms") or "—",
                (_m(v.get("altitude")) if v.get("altitude") is not None else "—"),
                v.get("vante_codigo") or "—", v.get("azimute") or "—", _m(v.get("distancia"))]

    def _crow(c):
        return [c.get("nome") or c.get("descricao") or "—", c.get("imovel") or "—",
                c.get("matricula") or "—", c.get("cns") or "—", ", ".join(c.get("segmentos") or [])]

    # Poligonal e confrontações do imóvel (Parte I, quando multi). No modo unificado,
    # cada parcela ganha sua PRÓPRIA subseção (resultado_parcelas/confrontacoes_parcelas).
    resultado_tabela = [_vrow(v) for v in (projeto.get("vertices") or [])]
    confrontacoes = [_crow(c) for c in (projeto.get("confrontantes") or [])]

    cadeia = [
        [a.get("ordem"), a.get("ato") or "—", a.get("tipo") or "—", a.get("data") or "—",
         a.get("partes") or "—"]
        for a in (im.get("cadeia_dominial") or [])
    ] or None

    # Parcelas resultantes (desmembramento/remembramento) — quadro-resumo + subseções.
    parcelas_tabela = None
    observacao_areas = None
    resultado_parcelas = None
    confrontacoes_parcelas = None
    if multi:
        parcelas_tabela = [
            [p["rotulo"], p.get("denominacao") or "—", _ha(p.get("area_ha")),
             _m(p.get("perimetro_m")), p.get("certificacao_sigef") or "—"]
            for p in partes
        ]
        # Uma subseção de poligonal por parcela (cada uma com seus próprios vértices).
        resultado_parcelas = [{
            "rotulo": p["rotulo"],
            "denominacao": p.get("denominacao") or "—",
            "area_ha": _ha(p.get("area_ha")),
            "perimetro_m": _m(p.get("perimetro_m")),
            "certificacao_sigef": p.get("certificacao_sigef") or "—",
            "tabela": [_vrow(v) for v in (p.get("vertices") or [])],
        } for p in partes]
        # Uma tabela de confrontações por parcela (cada parcela tem confrontantes próprios).
        confrontacoes_parcelas = [{
            "rotulo": p["rotulo"],
            "denominacao": p.get("denominacao") or "—",
            "tabela": [_crow(c) for c in (p.get("confrontantes") or [])],
        } for p in partes]
        # Conferência de áreas: Σ(partes) ≈ área registral da matrícula (tolerância 1%).
        soma = sum((float(p.get("area_ha")) for p in partes if p.get("area_ha") not in (None, "")))
        try:
            area_orig = float(_area_atual(im)) if _area_atual(im) not in (None, "") else None
        except (TypeError, ValueError):
            area_orig = None
        confere = None
        if area_orig and area_orig > 0:
            dif = abs(soma - area_orig)
            confere = dif <= area_orig * 0.01
            if confere:
                observacao_areas = (
                    f"Conferência de áreas: a soma das parcelas resultantes ({_ha(soma)} ha) "
                    f"confere com a área registral da matrícula ({_ha(area_orig)} ha), dentro "
                    f"da tolerância técnica admitida."
                )
            else:
                observacao_areas = (
                    f"OBSERVAÇÃO TÉCNICA: a soma das parcelas resultantes ({_ha(soma)} ha) "
                    f"diverge da área registral da matrícula ({_ha(area_orig)} ha) em {_ha(dif)} ha. "
                    f"Recomenda-se conferir os memoriais e a certidão antes do protocolo — a diferença "
                    f"pode decorrer de retificação concomitante ou de arredondamento de área."
                )

    # CONCLUSÃO — multi-parcela atesta TODAS as parcelas (área/perímetro/SIGEF de cada),
    # cita a conferência da soma com a matriz e a abertura das novas matrículas.
    if parc_iso:
        conclusao = (
            f"Diante do exposto, ATESTA-SE que o levantamento georreferenciado da {rot_iso} "
            f"({im.get('denominacao') or '—'}), parcela resultante do {tipo_servico} da matrícula nº "
            f"{_v(im, 'matricula')}, foi executado em conformidade com a NBR 13133 e com as normas "
            f"técnicas do INCRA, apresentando área de {_ha(im.get('area_ha'))} ha e perímetro de "
            f"{_m(im.get('perimetro_m'))} m, com a poligonal certificada no SIGEF (ausência de "
            f"sobreposição), e limites e confrontações reconhecidos. Conclui-se pela aptidão técnica à "
            f"abertura da matrícula da parcela e à alimentação do SIG-RI, nos termos do Provimento CNJ "
            f"nº 195/2025, ressalvada a competência de qualificação jurídica do Oficial de Registro de "
            f"Imóveis."
        )
    elif multi:
        partes_txt = "; ".join(
            f"{p['rotulo']} ({p.get('denominacao') or '—'}) — área {_ha(p.get('area_ha'))} ha, "
            f"perímetro {_m(p.get('perimetro_m'))} m, certificação SIGEF {p.get('certificacao_sigef') or '—'}"
            for p in partes)
        if confere is True:
            soma_txt = (f"A soma das áreas das parcelas ({_ha(soma)} ha) confere com a área "
                        f"registral da matrícula ({_ha(_area_atual(im))} ha), dentro da tolerância técnica. ")
        elif confere is False:
            soma_txt = (f"Registra-se que a soma das áreas das parcelas ({_ha(soma)} ha) diverge da "
                        f"área registral da matrícula ({_ha(_area_atual(im))} ha) — vide observação técnica. ")
        else:
            soma_txt = ""
        conclusao = (
            f"Diante do exposto, ATESTA-SE que o levantamento georreferenciado do imóvel "
            f"{_denom_atual(im) or '—'}, matrícula nº {_v(im, 'matricula')}, e de cada uma das "
            f"{len(partes)} parcelas resultantes foi executado em conformidade com a NBR 13133 e com "
            f"as normas técnicas do INCRA. As parcelas resultantes são: {partes_txt}. {soma_txt}"
            f"Todas as poligonais encontram-se certificadas no SIGEF, sem sobreposição com outras "
            f"parcelas do cadastro georreferenciado, com limites e confrontações reconhecidos. "
            f"Conclui-se pela aptidão técnica do imóvel à {finalidade}, com a abertura das matrículas "
            f"das parcelas resultantes e a alimentação do SIG-RI, nos termos do Provimento CNJ nº "
            f"195/2025, ressalvada a competência de qualificação jurídica do Oficial de Registro de Imóveis."
        )
    else:
        conclusao = (
            f"Diante do exposto, ATESTA-SE que o levantamento georreferenciado do imóvel "
            f"{_denom_atual(im) or '—'}, matrícula nº {_v(im, 'matricula')}, foi executado em "
            f"conformidade com a NBR 13133 e com as normas técnicas do INCRA, encontrando-se a "
            f"poligonal certificada no SIGEF (ausência de sobreposição com outras parcelas do cadastro "
            f"georreferenciado). O imóvel apresenta área registral de {_ha(_area_atual(im))} ha e perímetro de "
            f"{_m(_perim_atual(im))} m, com limites e confrontações reconhecidos. Conclui-se pela "
            f"aptidão técnica do imóvel à {finalidade} e à alimentação do SIG-RI, nos termos do "
            f"Provimento CNJ nº 195/2025, ressalvada a competência de qualificação jurídica do Oficial "
            f"de Registro de Imóveis."
        )

    titulo = f"LAUDO TÉCNICO DE AGRIMENSURA — {str(tipo_servico).upper()}"
    if parc_iso:
        titulo += f" ({rot_iso})"
    return {
        "titulo": titulo,
        "identificacao": identificacao,
        # denominação em negrito: a da parcela (isolada) ou a da matriz (demais casos)
        "identificacao_negrito": [(im.get("denominacao") if parc_iso else _denom_atual(im)) or "—"],
        "objeto": objeto,
        "teor_matricula": teor_matricula,
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
        "confrontacoes_parcelas": confrontacoes_parcelas,   # multi: 1 tabela por parcela
        "parcelas_header": ["Parcela", "Denominação", "Área (ha)", "Perímetro (m)", "Código SIGEF"],
        "parcelas_tabela": parcelas_tabela,
        "resultado_parcelas": resultado_parcelas,           # multi: 1 poligonal por parcela
        "multiparcela": multi,
        "observacao_areas": observacao_areas,
        "conclusao": conclusao,
        "rt_assinatura": _rt_assinatura_linhas(im, rt),
        "data": data_extenso(im.get("municipio"), im.get("uf")),
    }
