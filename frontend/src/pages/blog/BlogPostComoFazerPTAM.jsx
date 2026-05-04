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
      subtitulo="Guia prático com as 6 etapas obrigatórias da norma — identificação, vistoria, mercado, método, cálculo e conclusão."
      meta={post.meta}
      palavrasChave="como fazer PTAM, PTAM passo a passo, modelo PTAM, emitir PTAM, NBR 14.653, parecer técnico avaliação mercadológica, tutorial PTAM"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { p: 'Fazer um Parecer Técnico de Avaliação Mercadológica (PTAM) corretamente é uma das atividades mais importantes — e mais críticas — do trabalho do avaliador imobiliário. Um PTAM mal estruturado pode ser invalidado em juízo, rejeitado por bancos ou gerar prejuízo ao cliente. Por isso, a NBR 14.653 da ABNT padroniza um processo rigoroso de 6 etapas obrigatórias que todo PTAM precisa seguir.' },
        { p: 'Neste guia, você vai aprender exatamente como fazer um PTAM do zero, com exemplo prático de cada etapa, dicas de campo e os erros mais comuns que comprometem a aceitação do laudo. No fim, você verá como o sistema AvalieImob automatiza todo esse processo, garantindo conformidade total com a norma.' },

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

        { h2: 'As 6 etapas obrigatórias de um PTAM' },
        { p: 'A NBR 14.653 organiza o processo de avaliação em 6 etapas sequenciais. Pular ou negligenciar qualquer uma compromete a validade do laudo. Vamos ver cada uma em detalhe.' },

        { h3: 'Etapa 1 — Identificação completa do imóvel' },
        { p: 'É a base de tudo. Sem identificação cartorial, fiscal e física precisa, o PTAM não tem valor jurídico. Você precisa coletar:' },
        { lista: [
          'Identificação cartorial: número da matrícula, cartório de registro, livro, folha, proprietário registrado',
          'Identificação fiscal: número de inscrição (IPTU para urbano ou ITR/CCIR/CAR para rural), valor venal, situação fiscal',
          'Identificação física: endereço completo, georreferenciamento (lat/long), área do terreno e área construída, padrão construtivo, idade aparente, estado de conservação',
          'Documentação fotográfica: fachada, ambientes internos, áreas externas, vícios construtivos visíveis, vizinhança',
        ]},
        { callout: 'Não pule a vistoria presencial. PTAMs feitos só com fotos ou descrição do cliente são automaticamente Grau I (o menor) e podem ser questionados em juízo.', calloutTitulo: 'Dica de campo' },

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
        { callout: 'Em 80% dos PTAMs urbanos residenciais e comerciais, o método correto é o Comparativo Direto. Em rurais, frequentemente combina-se Comparativo (terra nua) com Custo (benfeitorias).', calloutTitulo: 'Regra de ouro' },

        { h3: 'Etapa 5 — Cálculo do valor com tratamento estatístico' },
        { p: 'Esta etapa transforma os dados brutos da pesquisa em um valor único de mercado. Envolve:' },
        { lista: [
          'Homogeneização das amostras: aplicação de fatores de transposição (atualização temporal), oferta (negociação), área, padrão, idade, conservação e localização',
          'Tratamento estatístico: cálculo da média, mediana, desvio padrão',
          'Saneamento de outliers: remoção de amostras discrepantes (Critério de Chauvenet)',
          'Determinação do intervalo de confiança (IC) — geralmente 80% conforme NBR',
          'Enquadramento no Grau de Fundamentação e Precisão (I, II ou III)',
        ]},
        { p: 'O grau de fundamentação depende do número de variáveis usadas, da qualidade das amostras e da metodologia aplicada. Grau III é o mais rigoroso (exigido em ações judiciais complexas e bancos de grande porte).' },

        { h3: 'Etapa 6 — Conclusão técnica e fundamentação' },
        { p: 'A última etapa é onde você consolida todo o trabalho técnico em uma conclusão clara. Um bom PTAM termina com:' },
        { lista: [
          'Valor de mercado conclusivo (em R$, por extenso e numérico)',
          'Intervalo de confiança (R$ X até R$ Y)',
          'Data de referência da avaliação',
          'Validade do parecer (geralmente 6 meses)',
          'Justificativa técnica para escolhas metodológicas',
          'Pressupostos e limitações da avaliação',
          'Anexos: matrícula, IPTU/ITR, fotos, planilhas estatísticas, ART/RRT',
          'Identificação do avaliador (nome, registro profissional, ART/RRT do CREA/CAU ou CRECI)',
        ]},

        { h2: 'Erros mais comuns que invalidam um PTAM' },
        { p: 'Em quase 10 anos avaliando imóveis e revisando laudos de outros profissionais, vejo os mesmos erros se repetirem. Os mais críticos:' },
        { lista: [
          'Pesquisa de mercado insuficiente (menos de 5 amostras, ou amostras de regiões muito diferentes)',
          'Não documentar fontes das amostras (sem fonte, a amostra é inválida)',
          'Pular a vistoria presencial e basear-se apenas em fotos do cliente',
          'Escolher o método errado para o tipo de imóvel',
          'Não fazer tratamento estatístico (apenas média simples)',
          'Não emitir ART/RRT no CREA/CAU (engenheiros e arquitetos) ou trabalhar fora da atribuição (corretores avaliando para fins judiciais)',
          'PTAM sem assinatura digital com certificado ICP-Brasil quando exigido',
        ]},

        { h2: 'Como o AvalieImob automatiza todo este processo' },
        { p: 'Fazer um PTAM manual (planilhas Excel + Word) leva de 4 a 8 horas e exige conhecimento técnico apurado. O AvalieImob reduz esse tempo para 30-60 minutos sem comprometer qualidade técnica:' },
        { lista: [
          'Wizard de 6 etapas que cobre exatamente os requisitos da NBR 14.653',
          'Homogeneização automática de amostras com todos os fatores de transposição',
          'Cálculo estatístico automatizado (média, mediana, IC, saneamento de outliers pelo Critério de Chauvenet)',
          'IA especializada em NBR 14.653 que sugere o método mais adequado e ajuda a fundamentar decisões',
          'Enquadramento automático no Grau de Fundamentação e Precisão',
          'Exportação direta em DOCX (Microsoft Word) ou PDF profissional',
          'Integração com D4Sign para assinatura digital com validade jurídica plena',
        ]},
        { cta: 'Crie sua conta gratuita e emita seu primeiro PTAM em minutos.', ctaTexto: 'Começar grátis →' },

        { h2: 'Conclusão' },
        { p: 'Fazer um PTAM corretamente exige seguir rigorosamente as 6 etapas previstas na NBR 14.653: identificação, vistoria, mercado, método, cálculo e conclusão. Cada etapa tem suas exigências técnicas e os atalhos cobram caro depois — em laudos rejeitados, perícias contrarias e prejuízo profissional.' },
        { p: 'O que diferencia um PTAM Grau I de um Grau III não é só o tempo gasto, mas a profundidade técnica em cada etapa. Avaliadores que dominam o processo e usam ferramentas adequadas conseguem emitir laudos Grau II ou III consistentemente, em metade do tempo dos colegas que ainda usam planilhas e modelos manuais.' },
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
