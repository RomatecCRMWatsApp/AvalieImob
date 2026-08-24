import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getPostBySlug, getRelatedPosts } from '../../data/blogPosts';

const SLUG = 'inferencia-estatistica-avaliacao-imoveis-tratamento-cientifico';

export default function BlogPostInferenciaEstatistica() {
  const post = getPostBySlug(SLUG);
  const relacionados = getRelatedPosts(SLUG);

  return (
    <BlogPostTemplate
      slug={SLUG}
      titulo={post.titulo}
      subtitulo="Regressão sobre a amostra de mercado, testes de pressupostos e intervalo de predição — o que a NBR cobra e o que derruba o Grau III."
      meta={post.meta}
      palavrasChave="inferencia estatistica avaliacao imoveis, tratamento cientifico NBR 14653, regressao linear avaliacao imovel, MCDDM, grau III fundamentacao, intervalo de predicao 80%, homocedasticidade avaliacao, pericia judicial avaliacao imovel"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { p: 'Existe uma diferença prática entre um laudo que resiste a uma contestação e um laudo que não resiste — e ela quase sempre está no tratamento dos dados. Quando a avaliação vai para uma perícia judicial, uma desapropriação ou uma servidão administrativa, a parte contrária tem advogado e assistente técnico. O que eles atacam primeiro é a fundamentação.' },
        { p: 'O tratamento por fatores — aquele em que se aplicam coeficientes de área, oferta, localização e conservação sobre cada amostra — resolve muito bem o dia a dia. Mas ele raramente alcança o Grau III da NBR 14.653, porque o grau mais alto exige demonstrar estatisticamente que o modelo explica o mercado. É aí que entra a inferência estatística.' },

        { h2: 'O que é o tratamento científico' },
        { p: 'No tratamento científico, em vez de corrigir amostra por amostra com fatores, você monta um modelo de regressão: o valor unitário do imóvel é explicado por um conjunto de variáveis independentes — área, distância ao centro, testada, padrão construtivo, presença de pavimentação, esquina, e o que mais o mercado daquela região precificar.' },
        { p: 'O modelo devolve, para cada variável, um coeficiente (quanto ela pesa no valor) e um nível de significância (a chance de aquele efeito ser mero acaso). Com o modelo estimado, você calcula o valor do imóvel avaliando e, principalmente, o intervalo dentro do qual esse valor deve estar.' },
        { p: 'A sigla que aparece nos laudos é MCDDM — Método Comparativo Direto de Dados de Mercado. Ela vale para os dois tratamentos: o comparativo é o método; por fatores ou por inferência é a forma de tratar os dados.' },

        { h2: 'O que a norma cobra para cada grau' },
        { p: 'A NBR 14.653-2 (imóveis urbanos) e a 14.653-3 (rurais) enquadram o laudo item a item. No tratamento científico, quatro deles são apurados diretamente do modelo:' },
        { lista: [
          'Quantidade mínima de dados efetivamente utilizados: 6(k+1) para Grau III, 4(k+1) para Grau II e 3(k+1) para Grau I — onde k é o número de variáveis independentes. Com 4 variáveis, o Grau III pede 30 dados de mercado',
          'Significância de cada variável (teste t bicaudal): até 10% no Grau III, 20% no Grau II, 30% no Grau I',
          'Significância do modelo como um todo (teste F): até 1% no Grau III, 2% no Grau II, 5% no Grau I',
          'Extrapolação: no Grau III o imóvel avaliando não pode ter nenhuma característica fora do intervalo da amostra',
        ]},
        { p: 'Repare no primeiro item: cada variável que você acrescenta ao modelo aumenta em seis o número de dados exigidos para o Grau III. Modelo enxuto com boa amostra vence modelo cheio de variáveis com amostra curta.' },

        { h2: 'Grau de Precisão é outra coisa' },
        { p: 'Fundamentação e Precisão são graus separados, e é comum confundi-los. A Precisão vem da amplitude do intervalo de predição de 80% em torno do valor central: até 30% do valor é Grau III, até 40% é Grau II, até 50% é Grau I.' },
        { p: 'Um detalhe técnico que faz diferença em contestação: o intervalo que define a Precisão é o de PREDIÇÃO (de uma nova observação), não o intervalo de confiança da média. O de confiança é sempre mais estreito, e usá-lo no lugar do outro infla artificialmente a precisão declarada do laudo.' },

        { h2: 'Os pressupostos — e por que eles derrubam laudos' },
        { p: 'Uma regressão só é válida se os resíduos se comportarem. São quatro verificações que todo laudo com tratamento científico deveria apresentar:' },
        { lista: [
          'Normalidade dos resíduos (Kolmogorov-Smirnov e Jarque-Bera): se os erros não se distribuem normalmente, o intervalo de predição calculado não vale',
          'Homocedasticidade (Breusch-Pagan e White): a dispersão dos erros precisa ser constante ao longo dos valores estimados. Quando cresce com o valor, o modelo erra mais nos imóveis caros — e não avisa',
          'Não-autocorrelação (Durbin-Watson, aceitável entre 1,5 e 2,5): os erros não podem estar relacionados entre si',
          'Ausência de multicolinearidade (matriz de correlação e VIF): duas variáveis que dizem quase a mesma coisa desestabilizam os coeficientes — o sinal pode até inverter',
        ]},
        { p: 'Um assistente técnico experiente vai direto nesses testes. Laudo que apresenta a regressão sem os pressupostos verificados é laudo com flanco aberto.' },

        { h2: 'Transformações: quando o mercado não é linear' },
        { p: 'Nem sempre a relação entre a variável e o valor é uma reta. Terreno maior costuma valer menos por metro quadrado, e a distância ao centro pesa mais nos primeiros quilômetros que nos últimos. Para isso existem as transformações: logaritmo natural, inverso, quadrado, raiz.' },
        { p: 'Há uma armadilha aqui. Quando a variável dependente é transformada em logaritmo, o valor que você obtém ao desfazer a transformação é a MEDIANA da distribuição condicional, não a média aritmética. O laudo precisa registrar isso — e os limites do intervalo devem ser destransformados um a um, nunca a amplitude.' },

        { h2: 'Saneamento da amostra: descartar exige justificar' },
        { p: 'Pontos com resíduo padronizado fora de ±2σ são discrepantes e merecem análise. Mas descartar dado porque ele atrapalha o modelo é manipulação; descartar porque a oferta estava desatualizada, porque o imóvel tinha benfeitoria não considerada ou porque a informação não foi confirmada é saneamento.' },
        { p: 'A diferença entre os dois está no registro. Todo dado descartado deve constar do laudo com o motivo — inclusive porque a quantidade de dados EFETIVAMENTE utilizados é o que conta para o enquadramento.' },

        { h2: 'Como isso funciona no AvalieImob' },
        { p: 'O AvalieImob traz o tratamento científico integrado ao fluxo do laudo. Você importa a amostra do seu banco de dados de mercado, define quais variáveis entram no modelo e qual transformação usar em cada uma, e o sistema estima a regressão por mínimos quadrados.' },
        { p: 'O que sai automaticamente:' },
        { lista: [
          'Tabela de coeficientes com erro-padrão, estatística t e significância de cada variável',
          'R², R² ajustado, teste F e erro-padrão da estimativa',
          'Os testes de pressupostos com semáforo — normalidade, homocedasticidade, autocorrelação e VIF',
          'Quatro gráficos de diagnóstico gerados pelo sistema: resíduos padronizados contra valores estimados, observado contra estimado, histograma dos resíduos com a curva normal sobreposta e Q-Q plot',
          'Valor central, intervalo de predição de 80% e campo de arbítrio, em valor unitário e total',
          'Enquadramento item a item na NBR, com a lista objetiva do que impede o Grau III quando ele não é alcançado',
        ]},
        { p: 'Os gráficos e todas essas seções entram no PTAM automaticamente quando o laudo é vinculado a um modelo homologado — não é preciso montar planilha à parte nem colar imagem no documento. O laudo sai com a amostra, o saneamento, a regressão, os pressupostos, os gráficos e o enquadramento, na ordem que a norma pede.' },
        { p: 'Um ponto de rigor: o modelo homologado é congelado no laudo. Se você versionar o modelo depois, o laudo já emitido continua reproduzindo exatamente os números que fundamentaram a assinatura.' },

        { h2: 'Quando usar cada tratamento' },
        { p: 'Não é o caso de abandonar o tratamento por fatores. A escolha depende da finalidade:' },
        { lista: [
          'Por fatores: transações particulares, garantias de menor porte, consultas de valor, situações em que a amostra é pequena por natureza do mercado',
          'Científico: perícia judicial, desapropriação, servidão administrativa, imóvel rural de grande porte, garantias bancárias relevantes, fundos imobiliários — em resumo, sempre que houver parte contrária ou exigência formal de Grau III',
        ]},
        { p: 'O critério prático é simples: se o laudo pode ser contestado por alguém com assistente técnico, vale o tratamento científico. E se a amostra disponível não sustenta o modelo, é melhor declarar Grau II com honestidade do que forçar um Grau III que não se sustenta na leitura dos testes.' },
      ]}
      relacionados={relacionados}
    />
  );
}
