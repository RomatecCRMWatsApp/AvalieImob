import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getPostBySlug, getRelatedPosts } from '../../data/blogPosts';

const SLUG = 'como-fazer-ptam-passo-a-passo-nbr-14653';

export default function BlogPostComoFazerPTAM() {
  const post = getPostBySlug(SLUG);
  const relacionados = getRelatedPosts(SLUG);

  return (
    <BlogPostTemplate
      slug={SLUG}
      titulo={post.titulo}
      subtitulo="Guia prático em 6 etapas, seguindo os requisitos da NBR 14.653 — identificação, vistoria, mercado, método, cálculo e conclusão."
      meta={post.meta}
      palavrasChave="como fazer PTAM, PTAM passo a passo, modelo PTAM, modelo de PTAM comentado, emitir PTAM, NBR 14.653, parecer técnico avaliação mercadológica, tutorial PTAM"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { p: 'Fazer um Parecer Técnico de Avaliação Mercadológica (PTAM) corretamente é uma das atividades mais importantes — e mais críticas — do trabalho do avaliador imobiliário. Um PTAM mal estruturado pode ser invalidado em juízo, rejeitado por bancos ou gerar prejuízo ao cliente. Por isso, este guia organiza o trabalho em 6 etapas, seguindo os requisitos da NBR 14.653 da ABNT.' },
        { p: 'Neste guia, você vai aprender exatamente como fazer um PTAM do zero, com exemplo prático de cada etapa, dicas de campo e os erros mais comuns que comprometem a aceitação do laudo. No fim, você verá como o AvalieImob ajuda a organizar esse processo. A responsabilidade técnica pelo laudo continua sendo do avaliador.' },

        { h2: 'O que é PTAM e quando ele é obrigatório?' },
        { p: 'PTAM é a sigla para Parecer Técnico de Avaliação Mercadológica. É o documento técnico que estabelece o valor de mercado de um imóvel (urbano ou rural), seguindo metodologia padronizada pela ABNT. É exigido em diversas situações:' },
        { lista: [
          'Transações bancárias (financiamento imobiliário, hipoteca, alienação fiduciária)',
          'Ações judiciais (partilha, divórcio, inventário, desapropriação, indenização)',
          'Operações imobiliárias estratégicas (compra e venda de grande porte, fusões, due diligence)',
          'Crédito rural (Pronaf, Pronamp, custeio agrícola — penhor rural)',
          'Levantamentos patrimoniais e contábeis',
          'Operações estruturadas (FIIs, securitização, fundos imobiliários)',
        ]},
        { p: 'Diferente de um laudo simples, o PTAM segue rigorosamente a NBR 14.653 e tem maior peso jurídico. Por isso a importância de fazê-lo corretamente desde o início.' },

        { h2: 'As 6 etapas de um PTAM' },
        { p: 'Para fins didáticos, organizamos os requisitos da NBR 14.653 em 6 etapas sequenciais. Negligenciar qualquer uma delas enfraquece a fundamentação do laudo. Vamos ver cada uma em detalhe.' },

        { h3: 'Etapa 1 — Identificação completa do imóvel' },
        { p: 'É a base de tudo. Sem identificação cartorial, fiscal e física precisa, o PTAM não tem valor jurídico. Você precisa coletar:' },
        { lista: [
          'Identificação cartorial: número da matrícula, cartório de registro, livro, folha, proprietário registrado',
          'Identificação fiscal: número de inscrição (IPTU para urbano ou ITR/CCIR/CAR para rural), valor venal, situação fiscal',
          'Identificação física: endereço completo, georreferenciamento (lat/long), área do terreno e área construída, padrão construtivo, idade aparente, estado de conservação',
          'Documentação fotográfica: fachada, ambientes internos, áreas externas, vícios construtivos visíveis, vizinhança',
        ]},
        { callout: 'Não pule a vistoria sem necessidade. Fotos ou descrição fornecidas pelo cliente, sem vistoria do avaliador, não determinam automaticamente o Grau I, mas o parecer precisa identificar os elementos utilizados, as limitações de acesso, as justificativas e a metodologia. Grau de fundamentação e grau de precisão são classificações distintas e não se definem apenas pela ausência de vistoria.', calloutTitulo: 'Dica de campo' },

        { h3: 'Etapa 2 — Vistoria técnica do imóvel' },
        { p: 'A vistoria é o momento em que você efetivamente verifica e mensura tudo que foi declarado no documento. É onde você vai detectar discrepâncias entre a matrícula e a realidade (área averbada vs. construída de fato), patologias construtivas, vícios redibitórios e fatores de depreciação ou valorização não óbvios.' },
        { p: 'Em uma vistoria bem feita, você documenta:' },
        { lista: [
          'Medição da área construída (com trena ou medidor a laser)',
          'Padrão de acabamento (grosseiro, simples, médio, alto, fino, luxo)',
          'Estado de conservação (novo, regular, reparos simples, reparos importantes, sem valor)',
          'Idade aparente vs. idade efetiva',
          'Vícios construtivos (rachaduras, infiltrações, fundações, instalações)',
          'Características funcionais (orientação solar, ventilação, iluminação)',
          'Características da localização (acesso, infraestrutura urbana, vizinhança)',
        ]},

        { h3: 'Etapa 3 — Pesquisa de mercado e amostras comparativas' },
        { p: 'Esta é a etapa mais técnica e mais importante. A pesquisa de mercado fornece os dados reais de oferta e venda de imóveis comparáveis, que serão usados para calcular o valor por método estatístico (comparativo direto de dados de mercado — o método mais usado).' },
        { p: 'Para uma amostragem com bom grau de fundamentação, você precisa:' },
        { listaOrd: [
          'Pesquisar pelo menos 5 a 12 imóveis comparáveis (idealmente vendidos, mas ofertas também são aceitas)',
          'Imóveis na mesma região (raio de 1-3 km em área urbana, 10-30 km em rural)',
          'Mesma tipologia (apartamento → apartamento, casa → casa, terreno → terreno)',
          'Documentar a fonte de cada amostra (anúncio com URL, contato do corretor, escritura, CRI)',
          'Coletar características-chave: área, padrão, idade, localização, valor, condições da oferta',
        ]},

        { h3: 'Etapa 4 — Escolha do método avaliatório' },
        { p: 'A NBR 14.653 prevê 6 métodos avaliatórios. A escolha depende da finalidade, da disponibilidade de dados e da tipologia do imóvel:' },
        { lista: [
          'Comparativo direto de dados de mercado: o mais usado. Compara o imóvel avaliando com amostras semelhantes do mercado.',
          'Capitalização da renda: ideal para imóveis locados ou que geram renda (lojas, salas, edifícios corporativos, hotéis).',
          'Evolutivo: soma o valor do terreno mais o valor das benfeitorias depreciadas. Usado quando não há comparáveis suficientes.',
          'Involutivo: estima o valor do terreno a partir do potencial de incorporação imobiliária. Usado para terrenos urbanos com potencial construtivo.',
          'Custo de reprodução: calcula quanto custaria reconstruir as benfeitorias hoje, descontando depreciação. Usado em imóveis especiais.',
          'Quantificação de custo: usado em obras em andamento ou para perícias específicas.',
        ]},
        { callout: 'Na maioria dos PTAMs urbanos com mercado ativo, usa-se o Método Comparativo Direto. Em rurais, frequentemente combina-se Comparativo (terra nua) com Custo (benfeitorias).', calloutTitulo: 'Regra de ouro' },

        { h3: 'Etapa 5 — Cálculo do valor com tratamento estatístico' },
        { p: 'Esta etapa transforma os dados brutos da pesquisa em um valor único de mercado. Envolve:' },
        { lista: [
          'Homogeneização das amostras: aplicação de fatores de transposição (atualização temporal), oferta (negociação), área, padrão, idade, conservação e localização',
          'Tratamento estatístico: cálculo da média, mediana, desvio padrão',
          'Saneamento de outliers: remoção de amostras discrepantes (Critério de Chauvenet)',
          'Quando a metodologia e os dados permitirem, estimativa intervalar com o intervalo calculado, o nível de confiança utilizado e os critérios de precisão aplicáveis',
          'Enquadramento no Grau de Fundamentação e Precisão (I, II ou III)',
        ]},
        { p: 'O grau de fundamentação depende do número de variáveis usadas, da qualidade das amostras e da metodologia aplicada. O grau exigido depende do contratante e da finalidade: confira a exigência do banco, do juízo ou de quem contratou o trabalho.' },
        { callout: 'Nos procedimentos documentados pelo Manual de Avaliação da SPU para o método comparativo direto, aparece o intervalo de confiança de 80%, cuja amplitude relativa participa do enquadramento da precisão. Esse percentual não significa "80% de acerto do preço", não é garantia de software e não deve ser aplicado automaticamente a todo PTAM. Os critérios devem ser conferidos na norma e no método efetivamente utilizados.', calloutTitulo: 'Sobre o intervalo de 80%' },

        { h3: 'Etapa 6 — Conclusão técnica e fundamentação' },
        { p: 'A última etapa é onde você consolida todo o trabalho técnico em uma conclusão clara. Um bom PTAM termina com:' },
        { lista: [
          'Valor de mercado conclusivo (em R$, por extenso e numérico)',
          'Intervalo de confiança (R$ X até R$ Y)',
          'Data de referência da avaliação',
          'Justificativa técnica para escolhas metodológicas',
          'Pressupostos e limitações da avaliação',
          'Anexos pertinentes: matrícula, IPTU/ITR, mapa, fotos, planilhas',
          'Identificação do corretor avaliador, breve currículo e assinatura',
        ]},

        { h2: 'Erros mais comuns que invalidam um PTAM' },
        { p: 'Em quase 10 anos avaliando imóveis e revisando laudos de outros profissionais, vejo os mesmos erros se repetirem. Os mais críticos:' },
        { lista: [
          'Pesquisa de mercado insuficiente para a metodologia adotada, ou amostras de regiões muito diferentes',
          'Não documentar fontes das amostras (sem fonte, a amostra é inválida)',
          'Pular a vistoria presencial e basear-se apenas em fotos do cliente',
          'Escolher o método errado para o tipo de imóvel',
          'Não fazer tratamento estatístico (apenas média simples)',
          'Trabalhar fora da própria atribuição profissional ou sem o registro exigido para o tipo de trabalho',
          'PTAM sem assinatura digital com certificado ICP-Brasil quando exigido',
        ]},

        { h2: 'Modelo comentado de PTAM: o que vai em cada seção' },
        { p: 'Um PTAM é organizado em seções que respondem, em ordem, quem pediu, para quê, qual imóvel, como foi avaliado, com quais dados e a que valor se chegou. A forma de apresentar pode variar; o conteúdo mínimo, não.' },
        { tabela: { cabecalho: ['Seção', 'Para que serve'], linhas: [
          ['Solicitante e finalidade', 'Diz quem pediu e para que o valor será usado. A finalidade muda o que precisa ser demonstrado.'],
          ['Identificação e caracterização', 'Matrícula, endereço, áreas com a fonte, construção, conservação, vizinhança e data da vistoria.'],
          ['Metodologia', 'Qual método foi usado e por que ele cabe neste imóvel.'],
          ['Pesquisa de mercado', 'Os imóveis comparados, com fonte, data, características e se o preço é de oferta ou de negócio fechado.'],
          ['Tratamento dos dados', 'Como os comparáveis foram ajustados e quais foram descartados, com o motivo.'],
          ['Conclusão', 'Valor, data de referência e limitações do trabalho.'],
          ['Corretor avaliador', 'Identificação, breve currículo e assinatura do profissional.'],
          ['Anexos', 'Fotos, documentos e planilhas que sustentam o parecer, conforme o caso.'],
        ] } },
        { p: 'A estrutura do PTAM deve identificar o solicitante e a finalidade, caracterizar o imóvel, explicar a metodologia e apresentar o valor com sua data de referência. O documento também deve identificar o corretor avaliador e conter seu breve currículo e assinatura. O art. 5º da Resolução COFECI nº 1.066/2007 estabelece os elementos mínimos.' },
        { p: 'Para o corretor inscrito no CNAI, também deve ser observada a forma e a tecnicidade do Anexo IV do Ato Normativo nº 001/2011. O cadastro, os registros profissionais e o selo têm funções próprias. Atender à estrutura do modelo não garante aceitação por banco, tribunal ou outro destinatário, que pode exigir documentação e habilitação específicas.' },
        { p: 'Mapa, matrícula atualizada e relatório fotográfico aparecem na resolução como recomendações gerais. Use-os sempre que possível, sem apresentá-los como requisito mínimo.' },

        { h3: 'Como documentar os comparáveis' },
        { p: 'Cada imóvel usado na comparação precisa ser identificável por quem ler o parecer. Para cada um, registre:' },
        { lista: [
          'a fonte (anúncio, imobiliária, cartório, informante) e como contatá-la;',
          'a data da coleta;',
          'se o preço é de oferta ou de negócio fechado;',
          'as características usadas na comparação: área, padrão, idade, localização.',
        ]},
        { p: 'A quantidade de comparáveis e o raio de busca dependem do mercado e do grau que se pretende alcançar. Não existe um número que sirva para todos os casos.' },

        { h3: 'Checklist de revisão do parecer' },
        { lista: [
          'A finalidade combina com o método e com os dados usados?',
          'A data de referência do valor está explícita?',
          'Cada área citada tem a sua fonte?',
          'Todos os comparáveis têm fonte, data e tipo de preço?',
          'Os descartes estão justificados?',
          'As limitações (acesso negado, documento faltando, divergência) estão escritas?',
          'A identificação do corretor avaliador, o breve currículo e a assinatura estão completos?',
        ]},

        { h3: 'O que um modelo não resolve' },
        { p: 'Um modelo organiza o trabalho, mas não garante que o parecer será aceito por banco ou tribunal, não define o grau de fundamentação e não substitui a habilitação do profissional. O que sustenta o PTAM são os dados coletados e a fundamentação de cada escolha.' },
        { p: 'Para conhecer como o sistema organiza essas seções, veja a página do módulo de PTAM.', link: '/ptam', linkTexto: 'Conhecer o módulo de PTAM →' },

        { h2: 'Como o AvalieImob automatiza todo este processo' },
        { p: 'Fazer um PTAM com planilhas e editor de texto exige conhecimento técnico e bastante trabalho de montagem. O AvalieImob organiza o processo inteiro num assistente guiado, sem você montar planilha nem formatar documento:' },
        { lista: [
          'Assistente guiado (13 passos, da identificação à conclusão) que segue os requisitos da NBR 14.653',
          'Homogeneização automática de amostras com todos os fatores de transposição',
          'Cálculo estatístico automatizado (média, desvio padrão, saneamento de amostras fora de ±10% da média, campo de arbítrio)',
          'Tratamento científico por regressão (inferência estatística) para quem precisa de Grau III',
          'Assistente de IA (Roma_IA) que ajuda a redigir e fundamentar os textos do laudo',
          'Campos de Grau de Fundamentação e Precisão no laudo (preenchidos automaticamente quando você usa o tratamento científico)',
          'Exportação direta em DOCX (Microsoft Word) ou PDF profissional',
          'Assinatura digital ICP-Brasil e assinatura do cliente via WhatsApp',
        ]},
        { p: 'Quer ver como o PTAM fica pronto antes de testar? Assista à demonstração em vídeo do PTAM em 12 passos.', link: '/#ptam-12-passos', linkTexto: 'Ver a demonstração do PTAM →' },
        { cta: 'Crie sua conta e teste por 7 dias grátis.', ctaTexto: 'Começar grátis →', ctaPos: 'meio' },

        { h2: 'Conclusão' },
        { p: 'Fazer um PTAM corretamente exige cumprir os requisitos da NBR 14.653 em cada uma das 6 etapas deste guia: identificação, vistoria, mercado, método, cálculo e conclusão. Cada etapa tem suas exigências técnicas e os atalhos cobram caro depois — em laudos rejeitados, perícias contrarias e prejuízo profissional.' },
        { p: 'O que diferencia um PTAM Grau I de um Grau III não é só o tempo gasto, mas a profundidade técnica em cada etapa. Dominar o processo e documentar cada escolha é o que sustenta o parecer; a ferramenta ajuda a organizar, mas a responsabilidade técnica continua sendo do avaliador.' },
      ]}
      servicosRelacionados={[
        { slug: 'ptam', titulo: 'PTAM — Parecer Técnico de Avaliação Mercadológica' },
        { slug: 'laudo-tecnico', titulo: 'Laudo Técnico de Avaliação' },
        { slug: 'avaliacao-urbana', titulo: 'Avaliação de Imóveis Urbanos' },
      ]}
      postsRelacionados={relacionados}
    />
  );
}
