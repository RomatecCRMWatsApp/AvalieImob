# @module seed_contratos — Biblioteca de cláusulas padrão Romatec (PCV e outros)
"""
15 cláusulas jurídicas padrão para Promessa de Compra e Venda de Imóvel.
Baseadas no CC/2002, Lei 13.786/2018 e prática notarial do Maranhão.
"""
from datetime import datetime

_NOW = datetime.utcnow()

TEMPLATE_PCV = {
    "id": "tpl_pcv_romatec",
    "nome": "Promessa de Compra e Venda de Imóvel",
    "slug": "compra_venda",
    "categoria": "compra_venda",
    "ativo": True,
    "created_at": _NOW,
}

CLAUSULAS_PCV = [
    {
        "id": "cl_pcv_01",
        "tipo_contrato": "compra_venda",
        "numero": 1,
        "titulo": "DAS PARTES",
        "categoria": "partes",
        "opcional": False,
        "ordem": 1,
        "conteudo": (
            "Pelo presente instrumento particular de Promessa de Compra e Venda, "
            "de um lado como PROMITENTE VENDEDOR(A) e de outro como PROMITENTE COMPRADOR(A), "
            "as partes acima qualificadas, doravante denominadas simplesmente VENDEDOR e COMPRADOR, "
            "têm entre si justo e contratado o presente negócio imobiliário, "
            "que se regerá pelas cláusulas e condições seguintes."
        ),
        "base_legal": "CC art. 104, 481",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_02",
        "tipo_contrato": "compra_venda",
        "numero": 2,
        "titulo": "DO OBJETO",
        "categoria": "objeto",
        "opcional": False,
        "ordem": 2,
        "conteudo": (
            "O presente contrato tem como objeto o imóvel descrito e caracterizado no preâmbulo, "
            "com todas as suas acessões, benfeitorias e instalações que o integram, "
            "livre e desembaraçado de quaisquer ônus, dívidas, hipotecas, penhoras, "
            "arrestos, sequestros, servidões não declaradas, ações reais e pessoais reipersecutórias, "
            "ressalvado o expressamente consignado neste instrumento."
        ),
        "base_legal": "CC art. 481, 502",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_03",
        "tipo_contrato": "compra_venda",
        "numero": 3,
        "titulo": "DO PREÇO E DAS CONDIÇÕES DE PAGAMENTO",
        "categoria": "preco_pagamento",
        "opcional": False,
        "ordem": 3,
        "conteudo": (
            "O preço total da presente negociação é o constante deste instrumento, "
            "ajustado pelas partes de forma livre e espontânea, "
            "a ser pago nas condições e formas estabelecidas no quadro de pagamento. "
            "O pagamento será realizado conforme acordado, mediante recibo comprobatório "
            "em cada parcela quitada. Nenhuma parcela será considerada paga sem a emissão do respectivo recibo."
        ),
        "base_legal": "CC art. 315, 317, 481",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_04",
        "tipo_contrato": "compra_venda",
        "numero": 4,
        "titulo": "DO SINAL E DAS ARRAS CONFIRMATÓRIAS",
        "categoria": "arras",
        "opcional": True,
        "ordem": 4,
        "conteudo": (
            "O COMPRADOR pagará ao VENDEDOR, como sinal e princípio de pagamento, "
            "o valor constante neste instrumento a título de arras confirmatórias, "
            "nos termos do art. 417 do Código Civil. "
            "As arras confirmatórias se integrarão ao valor do contrato, "
            "sem excluir a responsabilidade por eventuais perdas e danos. "
            "Caso o COMPRADOR se arrependa do negócio, perderá o sinal em favor do VENDEDOR. "
            "Caso o VENDEDOR se arrependa, restituirá o sinal em dobro ao COMPRADOR, "
            "nos termos do art. 418 CC."
        ),
        "base_legal": "CC art. 417-420",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_05",
        "tipo_contrato": "compra_venda",
        "numero": 5,
        "titulo": "DA IMISSÃO NA POSSE",
        "categoria": "posse",
        "opcional": False,
        "ordem": 5,
        "conteudo": (
            "A imissão na posse do imóvel objeto do presente contrato ocorrerá "
            "nas condições especificadas neste instrumento, "
            "ficando a entrega das chaves e documentos condicionada ao cumprimento "
            "das obrigações pecuniárias pelo COMPRADOR. "
            "O VENDEDOR declara que entregará o imóvel nas condições avençadas, "
            "em perfeito estado de conservação e limpeza, "
            "sem débitos de IPTU, taxas condominiais, contas de água, energia elétrica "
            "e demais encargos até a data da entrega."
        ),
        "base_legal": "CC art. 491",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_06",
        "tipo_contrato": "compra_venda",
        "numero": 6,
        "titulo": "DAS OBRIGAÇÕES DO VENDEDOR",
        "categoria": "obrigacoes_vendedor",
        "opcional": True,
        "ordem": 6,
        "conteudo": (
            "São obrigações do VENDEDOR: "
            "(i) entregar o imóvel nas condições e no prazo avençados; "
            "(ii) apresentar certidões negativas de débitos fiscais e trabalhistas; "
            "(iii) providenciar o desembaraço de quaisquer ônus reais que recaiam sobre o imóvel; "
            "(iv) firmar a escritura pública definitiva tão logo seja regularizada a documentação e "
            "integralmente pago o preço; "
            "(v) responder por evicção e vícios redibitórios nos termos da lei."
        ),
        "base_legal": "CC art. 441, 447, 502",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_07",
        "tipo_contrato": "compra_venda",
        "numero": 7,
        "titulo": "DAS OBRIGAÇÕES DO COMPRADOR",
        "categoria": "obrigacoes_comprador",
        "opcional": True,
        "ordem": 7,
        "conteudo": (
            "São obrigações do COMPRADOR: "
            "(i) pagar o preço ajustado nas datas e formas convencionadas; "
            "(ii) comparecer para assinatura da escritura pública definitiva quando convocado; "
            "(iii) pagar o ITBI e demais despesas cartorárias relativas à transmissão do imóvel; "
            "(iv) assumir todos os encargos fiscais e condominiais a partir da data de imissão na posse; "
            "(v) não ceder os direitos deste contrato a terceiros sem anuência expressa do VENDEDOR."
        ),
        "base_legal": "CC art. 491",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_08",
        "tipo_contrato": "compra_venda",
        "numero": 8,
        "titulo": "DA ESCRITURA PÚBLICA DEFINITIVA",
        "categoria": "escritura",
        "opcional": False,
        "ordem": 8,
        "conteudo": (
            "A escritura pública de compra e venda definitiva será lavrada no Cartório de Notas "
            "de livre escolha das partes, no prazo estabelecido neste contrato, "
            "contado da data da quitação integral do preço ou do implemento da condição avençada. "
            "As despesas com a lavratura da escritura, registro no CRI, ITBI e demais encargos "
            "correrão por conta do COMPRADOR, salvo disposição expressa em contrário. "
            "O não comparecimento injustificado de qualquer das partes para assinatura da escritura "
            "no prazo avençado sujeitará o inadimplente às penalidades previstas neste instrumento."
        ),
        "base_legal": "CC art. 108, 215; Lei 6.015/73",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_09",
        "tipo_contrato": "compra_venda",
        "numero": 9,
        "titulo": "DA COMISSÃO DE CORRETAGEM",
        "categoria": "corretagem",
        "opcional": True,
        "ordem": 9,
        "conteudo": (
            "A comissão de corretagem pelo presente negócio imobiliário é devida "
            "ao(à) Corretor(a) de Imóveis identificado(a) neste instrumento, "
            "nos termos dos artigos 722 a 729 do Código Civil e da Resolução COFECI nº 957/2006, "
            "no percentual e condições especificados. "
            "A comissão é devida desde a aproximação das partes e celebração do presente contrato, "
            "independentemente da lavratura da escritura pública definitiva, "
            "salvo expressa disposição em contrário. "
            "A responsabilidade pelo pagamento recai sobre a parte indicada neste instrumento."
        ),
        "base_legal": "CC art. 722-729; COFECI 957/2006",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_10",
        "tipo_contrato": "compra_venda",
        "numero": 10,
        "titulo": "DOS VÍCIOS REDIBITÓRIOS E EVICÇÃO",
        "categoria": "vicios_evicção",
        "opcional": True,
        "ordem": 10,
        "conteudo": (
            "O VENDEDOR responde pelos vícios ocultos que tornem o imóvel impróprio ao uso "
            "ou lhe diminuam o valor, nos termos dos artigos 441 a 446 do Código Civil. "
            "O COMPRADOR terá o prazo de 1 (um) ano para reclamar vícios ocultos em imóvel usado "
            "e de 1 (um) ano em imóvel construído, contados da tradição. "
            "O VENDEDOR responde igualmente pela evicção, garantindo ao COMPRADOR "
            "o exercício de seus direitos em face de terceiros que pleiteiem direitos sobre o imóvel, "
            "na forma dos artigos 447 a 457 do Código Civil."
        ),
        "base_legal": "CC art. 441-446, 447-457",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_11",
        "tipo_contrato": "compra_venda",
        "numero": 11,
        "titulo": "DAS PENALIDADES E MULTAS",
        "categoria": "penalidades",
        "opcional": True,
        "ordem": 11,
        "conteudo": (
            "O inadimplemento de qualquer obrigação constante deste contrato sujeitará "
            "a parte faltosa ao pagamento de multa de 10% (dez por cento) sobre o valor total do contrato, "
            "acrescida de juros de mora de 1% (um por cento) ao mês, "
            "correção monetária pelo IPCA e honorários advocatícios de 10% (dez por cento). "
            "A constituição em mora operar-se-á de pleno direito pelo simples vencimento da obrigação, "
            "independentemente de notificação judicial ou extrajudicial, "
            "na forma do art. 397 do Código Civil."
        ),
        "base_legal": "CC art. 389, 395, 397, 408-416",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_12",
        "tipo_contrato": "compra_venda",
        "numero": 12,
        "titulo": "DAS DISPOSIÇÕES GERAIS",
        "categoria": "disposicoes_gerais",
        "opcional": False,
        "ordem": 12,
        "conteudo": (
            "O presente contrato obriga as partes e seus herdeiros e sucessores a qualquer título. "
            "A tolerância de uma das partes quanto ao inadimplemento de cláusulas por outra "
            "não importa em novação ou alteração do contrato. "
            "Qualquer alteração deste instrumento somente será válida se formalizada "
            "por meio de termo aditivo escrito e assinado por ambas as partes. "
            "O presente instrumento é firmado em caráter irrevogável e irretratável, "
            "nos termos do art. 472 do Código Civil."
        ),
        "base_legal": "CC art. 472",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_13",
        "tipo_contrato": "compra_venda",
        "numero": 13,
        "titulo": "DAS NOTIFICAÇÕES",
        "categoria": "notificacoes",
        "opcional": False,
        "ordem": 13,
        "conteudo": (
            "As notificações e comunicações entre as partes serão realizadas preferencialmente "
            "por escrito, mediante mensagem eletrônica (e-mail) ou aplicativo de mensagens instantâneas "
            "(WhatsApp) para os contatos indicados neste instrumento, "
            "considerando-se recebida a comunicação no primeiro dia útil subsequente ao envio. "
            "Para comunicações de natureza judicial ou extrajudicial que exijam prova de recebimento, "
            "serão utilizados os endereços físicos informados neste instrumento, "
            "por via de notificação extrajudicial com aviso de recebimento (AR), "
            "nos termos do art. 221 do CPC."
        ),
        "base_legal": "CPC art. 221; CC art. 107",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_14",
        "tipo_contrato": "compra_venda",
        "numero": 14,
        "titulo": "DA MEDIAÇÃO E RESOLUÇÃO DE CONFLITOS",
        "categoria": "mediacao",
        "opcional": True,
        "ordem": 14,
        "conteudo": (
            "Antes de recorrer ao Poder Judiciário, as partes concordam em submeter "
            "eventuais controvérsias oriundas deste contrato à mediação extrajudicial, "
            "na forma da Lei 13.140/2015, com prazo de 60 (sessenta) dias para tentativa de acordo. "
            "O mediador será escolhido de comum acordo entre as partes ou, "
            "na ausência de consenso, indicado pelo Centro de Mediação e Arbitragem "
            "da Câmara de Comércio da cidade sede do foro eleito. "
            "Os custos da mediação serão rateados igualmente entre as partes."
        ),
        "base_legal": "Lei 13.140/2015; CPC art. 165",
        "created_at": _NOW,
    },
    {
        "id": "cl_pcv_15",
        "tipo_contrato": "compra_venda",
        "numero": 15,
        "titulo": "DO FORO",
        "categoria": "foro",
        "opcional": False,
        "ordem": 15,
        "conteudo": (
            "Para dirimir quaisquer controvérsias oriundas do presente instrumento, "
            "as partes elegem o Foro da Comarca de Açailândia, Estado do Maranhão, "
            "renunciando a qualquer outro, por mais privilegiado que seja, "
            "inclusive o do domicílio de qualquer das partes, "
            "nos termos do art. 63 do Código de Processo Civil."
        ),
        "base_legal": "CPC art. 63",
        "created_at": _NOW,
    },
]
