import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getPostBySlug, getRelatedPosts } from '../../data/blogPosts';

const SLUG = 'grau-fundamentacao-precisao-nbr-14653';

export default function BlogPostGrauFundamentacao() {
  const post = getPostBySlug(SLUG);
  const relacionados = getRelatedPosts(SLUG);

  return (
    <BlogPostTemplate
      slug={SLUG}
      titulo={post.titulo}
      subtitulo="Os 3 graus possíveis (I, II, III), como cada um é calculado, e qual escolher conforme a finalidade do laudo."
      meta={post.meta}
      palavrasChave="grau de fundamentacao, grau de precisao, NBR 14.653, fundamentacao laudo avaliacao, grau III avaliacao, intervalo de confianca avaliacao"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { p: 'Quando você emite um laudo de avaliação, o documento precisa ser enquadrado em um de três níveis técnicos previstos pela NBR 14.653 — os chamados Graus de Fundamentação e Precisão. Esse enquadramento não é uma formalidade burocrática: ele afeta diretamente a aceitação do laudo em juízo, em bancos e em órgãos públicos. Um laudo Grau I pode ser questionado em uma perícia complexa; um Grau III é praticamente inquestionável tecnicamente.' },
        { p: 'Neste artigo vou explicar exatamente como calcular o grau de fundamentação e o grau de precisão de um laudo, com tabela de pontuação detalhada, exemplo prático e dicas para alcançar o grau mais alto sem trabalho excessivo.' },

        { h2: 'O que é Grau de Fundamentação?' },
        { p: 'O Grau de Fundamentação mede a profundidade técnica usada na avaliação — quantidade de variáveis analisadas, qualidade das amostras de mercado, rigor do tratamento estatístico e abrangência do estudo. É um indicador da confiabilidade do método empregado.' },
        { p: 'Quanto mais alto o grau, mais robusto é o laudo perante questionamentos. Os três níveis são:' },
        { lista: [
          'Grau I: fundamentação básica — adequado para situações privadas, consultas internas, transações de baixo valor',
          'Grau II: fundamentação intermediária — exigido em garantias bancárias padrão e em ações judiciais não-complexas',
          'Grau III: fundamentação completa — obrigatório em perícias judiciais com disputa, garantias bancárias de grande porte, FIIs, fundos imobiliários',
        ]},

        { h2: 'O que é Grau de Precisão?' },
        { p: 'O Grau de Precisão mede a confiabilidade estatística do valor encontrado — ou seja, o tamanho do intervalo de confiança ao redor do valor de mercado conclusivo. Um laudo com intervalo apertado é mais preciso que um com intervalo largo.' },
        { p: 'A NBR 14.653 estabelece que o intervalo de confiança deve ser calculado a 80% (em casos especiais 95%). O grau é determinado conforme a amplitude desse intervalo:' },
        { lista: [
          'Grau I: amplitude até 50% do valor central',
          'Grau II: amplitude até 30% do valor central',
          'Grau III: amplitude até 15% do valor central',
        ]},
        { callout: 'Atenção: Grau de Fundamentação e Grau de Precisão são INDEPENDENTES. Você pode ter Fundamentação Grau III e Precisão Grau II, ou vice-versa. Ambos precisam aparecer no laudo.', calloutTitulo: 'Importante' },

        { h2: 'Como calcular o Grau de Fundamentação' },
        { p: 'A NBR 14.653-2 (Avaliação de Imóveis Urbanos) estabelece uma tabela de pontuação com 5 itens. Cada item recebe uma pontuação de 1 a 3, e a soma total define o grau:' },

        { h3: 'Tabela de pontuação' },
        { lista: [
          'Item 1 — Caracterização do imóvel avaliando: quantos atributos foram coletados (área, padrão, idade, localização, conservação, etc.)',
          'Item 2 — Quantidade mínima de dados de mercado: número de amostras coletadas (mais amostras = mais pontos)',
          'Item 3 — Identificação dos dados de mercado: completude da pesquisa (fonte, contato, preço, características)',
          'Item 4 — Intervalo admissível para os fatores: se os fatores de homogeneização estão dentro de limites aceitáveis',
          'Item 5 — Apresentação do laudo: estrutura, completude, conclusão técnica',
        ]},

        { h3: 'Pontuação por item (1 a 3 pontos cada)' },
        { p: '1 ponto = atende ao mínimo. 2 pontos = atende com qualidade intermediária. 3 pontos = atende plenamente, com excelência.' },
        { p: 'Soma final dos 5 itens (mínimo 5, máximo 15):' },
        { lista: [
          'Soma total entre 5 e 7 pontos: Grau I',
          'Soma total entre 8 e 11 pontos: Grau II',
          'Soma total entre 12 e 15 pontos: Grau III',
        ]},
        { callout: 'Mais um detalhe importante: a NBR exige que NENHUM dos 5 itens tenha pontuação 1 para o laudo ser Grau III. E para Grau II, no máximo 2 itens podem ter pontuação 1.', calloutTitulo: 'Restrição adicional' },

        { h2: 'Exemplo prático de cálculo' },
        { p: 'Vamos pontuar um laudo de avaliação de apartamento residencial em São Luís/MA:' },

        { h3: 'Cenário do laudo' },
        { lista: [
          'Imóvel: apartamento de 80m², 3 dormitórios, padrão médio, 8 anos',
          'Pesquisa de mercado: 8 amostras de apartamentos similares na região',
          'Vistoria presencial realizada com fotografia completa',
          'Método: comparativo direto de dados de mercado',
          'Tratamento estatístico aplicado com intervalo de confiança 80%',
        ]},

        { h3: 'Pontuação por item' },
        { lista: [
          'Item 1 (Caracterização): coletou 12 atributos do imóvel → 3 pontos',
          'Item 2 (Quantidade de dados): 8 amostras (mínimo Grau III é 5) → 3 pontos',
          'Item 3 (Identificação dos dados): todas com fonte, fotos, preço e contato → 3 pontos',
          'Item 4 (Fatores de homogeneização): todos dentro do intervalo NBR (0,5 a 2,0) → 3 pontos',
          'Item 5 (Apresentação): laudo completo com todos os anexos exigidos → 3 pontos',
        ]},
        { callout: 'Soma: 15 pontos → Grau III de Fundamentação ✓', calloutTitulo: 'Resultado' },

        { h2: 'Como calcular o Grau de Precisão' },
        { p: 'O Grau de Precisão sai do tratamento estatístico das amostras homogeneizadas. Após calcular a média e o desvio padrão, você obtém o intervalo de confiança a 80%:' },

        { h3: 'Fórmula simplificada' },
        { callout: 'IC 80% = Média ± (1,28 × Erro Padrão da Média)\nAmplitude = (Limite Superior - Limite Inferior) / Valor Central\n\nGrau III: Amplitude ≤ 15%\nGrau II: Amplitude ≤ 30%\nGrau I: Amplitude ≤ 50%', calloutTitulo: 'Cálculo do Grau de Precisão' },

        { h3: 'Exemplo' },
        { p: 'Continuando o caso do apartamento — após homogeneização das 8 amostras:' },
        { lista: [
          'Valor médio (central): R$ 350.000,00',
          'Erro padrão da média: R$ 15.000,00',
          'IC 80%: R$ 350.000 ± (1,28 × 15.000) = R$ 350.000 ± R$ 19.200',
          'Limite inferior: R$ 330.800,00',
          'Limite superior: R$ 369.200,00',
          'Amplitude: (369.200 - 330.800) / 350.000 = 38.400 / 350.000 = 10,97%',
        ]},
        { callout: 'Amplitude 10,97% → menor que 15% → Grau III de Precisão ✓', calloutTitulo: 'Resultado' },

        { h2: 'Como melhorar seu grau' },
        { p: 'Se você está caindo em Grau I ou II e quer subir para Grau III, ataque os pontos fracos:' },

        { h3: 'Para subir o Grau de Fundamentação' },
        { lista: [
          'Aumente o número de amostras (objetivo: 8+ amostras de qualidade)',
          'Documente cada amostra com fonte, foto, contato, valor e características completas',
          'Cuide para que os fatores de homogeneização não estourem 2,0 (limite NBR)',
          'Monte um laudo robusto com todos os anexos: matrícula, IPTU, fotos, planilhas estatísticas, ART/RRT',
          'Faça vistoria presencial e documente com fotos georreferenciadas',
        ]},

        { h3: 'Para subir o Grau de Precisão' },
        { lista: [
          'Mais amostras (estatisticamente, mais N = menor erro padrão)',
          'Amostras mais homogêneas (com pequena variação após homogeneização)',
          'Saneamento de outliers via Critério de Chauvenet',
          'Use método comparativo (geralmente mais preciso que evolutivo ou capitalização)',
          'Exclua amostras de regiões muito distintas do imóvel avaliando',
        ]},

        { h2: 'Quando cada grau é exigido' },
        { lista: [
          'Grau I: consultas privadas do cliente, transações entre familiares, levantamentos internos de imobiliária',
          'Grau II: garantias bancárias para Pessoa Física até R$ 500 mil, financiamentos imobiliários comuns, partilhas extrajudiciais',
          'Grau III: garantias bancárias acima de R$ 500 mil, FIIs e fundos imobiliários, perícias judiciais com disputa, desapropriações, ações de indenização',
        ]},
        { callout: 'Em caso de dúvida, sempre opte pelo Grau III. O custo extra de tempo é pequeno comparado ao risco de ter o laudo rejeitado em juízo ou pelo banco.', calloutTitulo: 'Regra de ouro' },

        { h2: 'Como o AvalieImob automatiza o cálculo' },
        { p: 'No AvalieImob, todo laudo é automaticamente enquadrado em Grau de Fundamentação e Precisão conforme você cadastra os dados:' },
        { lista: [
          'Pontuação automática dos 5 itens da tabela conforme amostras e atributos cadastrados',
          'Cálculo estatístico em tempo real (média, mediana, desvio padrão, IC 80%)',
          'Saneamento de outliers pelo Critério de Chauvenet aplicado automaticamente',
          'Indicador visual mostrando seu grau atual e o que falta pra subir um nível',
          'Sugestões da IA: "adicione mais 2 amostras pra subir pra Grau III"',
        ]},
        { cta: 'Teste o sistema completo do AvalieImob por 7 dias grátis.', ctaTexto: 'Começar grátis →' },

        { h2: 'Conclusão' },
        { p: 'Os Graus de Fundamentação e Precisão são o "selo de qualidade" do seu laudo de avaliação. Dominar esse cálculo é o que separa o avaliador iniciante do profissional consolidado — e é também o diferencial que justifica honorários mais altos no mercado.' },
        { p: 'Para a maioria dos laudos profissionais, busque Grau II como mínimo e Grau III sempre que possível. Em perícias judiciais, partilhas grandes e garantias bancárias de porte, Grau III é praticamente obrigatório. Use ferramentas que automatizam o cálculo e foque seu tempo na interpretação técnica e na conclusão.' },
      ]}
      servicosRelacionados={[
        { slug: 'ptam', titulo: 'PTAM — Parecer Técnico de Avaliação Mercadológica' },
        { slug: 'avaliacao-urbana', titulo: 'Avaliação de Imóveis Urbanos' },
        { slug: 'avaliacao-garantia', titulo: 'Avaliação de Garantias Bancárias' },
      ]}
      postsRelacionados={relacionados}
    />
  );
}
