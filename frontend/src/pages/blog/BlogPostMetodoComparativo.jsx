import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getPostBySlug, getRelatedPosts } from '../../data/blogPosts';

const SLUG = 'metodo-comparativo-direto-passo-a-passo';

export default function BlogPostMetodoComparativo() {
  const post = getPostBySlug(SLUG);
  const relacionados = getRelatedPosts(SLUG);

  return (
    <BlogPostTemplate
      slug={SLUG}
      titulo={post.titulo}
      subtitulo="Da pesquisa de mercado à homogeneização — o método mais usado em 80% dos PTAMs urbanos, explicado com exemplo prático."
      meta={post.meta}
      palavrasChave="metodo comparativo direto, comparativo direto de dados de mercado, NBR 14.653, homogeneizacao amostras, fatores de homogeneizacao, avaliacao imobiliaria"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { p: 'O Método Comparativo Direto de Dados de Mercado é o método avaliatório mais usado no Brasil — está presente em mais de 80% dos PTAMs e laudos de imóveis urbanos. É também o método preferido pela NBR 14.653 quando há disponibilidade de amostras de mercado, justamente por ser baseado em transações reais (e não estimativas).' },
        { p: 'Mas apesar de ser o mais comum, é onde mais se vê erros técnicos: amostras mal documentadas, fatores de homogeneização aplicados de forma equivocada, tratamento estatístico incompleto. Este artigo mostra o passo a passo correto, com exemplo prático aplicado a um apartamento residencial.' },

        { h2: 'O que é o Método Comparativo Direto?' },
        { p: 'Conforme a NBR 14.653, o Método Comparativo Direto de Dados de Mercado é aquele que "identifica o valor de mercado do bem por meio de tratamento técnico dos atributos dos elementos comparáveis, constituintes da amostra".' },
        { p: 'Em linguagem prática: você coleta amostras de imóveis semelhantes ao avaliando, ajusta cada uma pelas diferenças (área, padrão, idade, localização), aplica tratamento estatístico e chega a um valor de mercado representativo. É o método mais intuitivo e o mais aceito pelo mercado.' },

        { h2: 'Quando usar o Método Comparativo Direto' },
        { p: 'Use sempre que houver disponibilidade de amostras semelhantes ao imóvel avaliando — geralmente:' },
        { lista: [
          'Apartamentos (alta liquidez, muitas amostras)',
          'Casas em bairros consolidados',
          'Salas comerciais em centros empresariais',
          'Terrenos urbanos em áreas com transações ativas',
          'Glebas urbanas com mercado estabelecido',
        ]},
        { p: 'Quando NÃO usar:' },
        { lista: [
          'Imóveis muito singulares (igrejas, hospitais, postos de combustível) — usar Custo de Reprodução',
          'Imóveis locados que geram renda — usar Capitalização da Renda',
          'Terrenos com potencial de incorporação — usar Involutivo',
          'Quando não há amostras suficientes (mínimo 5 para Grau I, 12+ para Grau III)',
        ]},

        { h2: 'Os 6 passos do Método Comparativo Direto' },

        { h3: 'Passo 1 — Pesquisa de mercado' },
        { p: 'Coleta amostras de imóveis vendidos ou ofertados na mesma região, com características similares ao avaliando. Para um laudo Grau III você precisa de no mínimo 12 amostras de qualidade.' },
        { p: 'Para cada amostra, documente:' },
        { lista: [
          'Endereço completo',
          'Fonte (anúncio, escritura, contato do corretor)',
          'Tipo de operação (venda concretizada vs. oferta)',
          'Área do terreno e área construída/privativa',
          'Padrão construtivo, idade aparente, conservação',
          'Valor de oferta ou venda',
          'Data da oferta',
          'Foto da fachada (preferencialmente do anúncio original)',
        ]},
        { callout: 'Amostras de OFERTA precisam de fator de oferta (geralmente 0,90 — desconto típico de negociação). Amostras de VENDA já estão no valor real, sem ajuste.', calloutTitulo: 'Atenção' },

        { h3: 'Passo 2 — Eliminação de amostras incompatíveis' },
        { p: 'Antes de calcular nada, exclua amostras que claramente não servem:' },
        { lista: [
          'Imóveis em situação fiscal/jurídica anormal (leilão, execução)',
          'Imóveis com características muito distintas (área 3x maior ou menor)',
          'Imóveis em regiões não comparáveis (zona industrial vs. zona residencial)',
          'Amostras antigas (>12 meses, salvo correção monetária)',
          'Amostras sem fonte verificável',
        ]},

        { h3: 'Passo 3 — Homogeneização das amostras' },
        { p: 'Esta é a etapa central. Você ajusta cada amostra para "homogeneizá-la" com o imóvel avaliando, aplicando fatores que corrigem as diferenças. Os principais fatores conforme NBR 14.653:' },
        { lista: [
          'Fator de transposição (atualização temporal): aplicado se a amostra é antiga',
          'Fator de oferta: aplicado em ofertas (típico 0,90)',
          'Fator de área: ajusta diferenças de tamanho (geralmente fórmula: (Área avaliando / Área amostra)^0,25)',
          'Fator de padrão: ajusta diferença de qualidade construtiva',
          'Fator de idade: corrige a depreciação (Ross-Heidecke)',
          'Fator de conservação: ajusta estado de manutenção',
          'Fator de localização: ajusta diferenças de bairro/zona',
        ]},
        { callout: 'A NBR 14.653 estabelece que TODOS os fatores combinados devem resultar em valor entre 0,5 e 2,0 do valor original. Se o fator final ficar fora desse intervalo, a amostra é descartada por ser muito diferente do avaliando.', calloutTitulo: 'Limites NBR' },

        { h3: 'Passo 4 — Cálculo do valor unitário homogeneizado' },
        { p: 'Para cada amostra, calcula o valor por m² (ou por unidade) homogeneizado:' },
        { callout: 'Valor unitário homogeneizado = Valor total da amostra × Fator de oferta × Fator de transposição × Fator de área × Fator de padrão × Fator de idade × Fator de conservação ÷ Área da amostra', calloutTitulo: 'Fórmula' },

        { h3: 'Passo 5 — Tratamento estatístico' },
        { p: 'Com os valores unitários homogeneizados de todas as amostras, aplica:' },
        { lista: [
          'Cálculo da média aritmética',
          'Cálculo do desvio padrão (medida de dispersão)',
          'Saneamento de outliers pelo Critério de Chauvenet (remove amostras estatisticamente discrepantes)',
          'Cálculo do intervalo de confiança a 80% (NBR padrão)',
          'Determinação do erro relativo (Grau de Precisão)',
        ]},

        { h3: 'Passo 6 — Conclusão do valor de mercado' },
        { p: 'Multiplica o valor unitário médio (após saneamento) pela área do imóvel avaliando:' },
        { callout: 'Valor de Mercado = Valor unitário homogeneizado médio × Área do avaliando', calloutTitulo: 'Fórmula final' },

        { h2: 'Exemplo prático: Apartamento em São Luís/MA' },

        { h3: 'Cenário' },
        { lista: [
          'Imóvel avaliando: apartamento de 80m², 3 dormitórios, padrão médio, 8 anos de idade, conservação boa',
          'Endereço: Bairro Renascença II, São Luís/MA',
          'Pesquisa: 8 amostras de apartamentos similares na mesma região',
        ]},

        { h3: 'Amostra de exemplo (1 das 8)' },
        { lista: [
          'Apartamento de 92m², 3 dormitórios, padrão médio-alto, 5 anos, em oferta',
          'Valor de oferta: R$ 420.000,00',
          'Mesma região, mesma tipologia',
        ]},

        { h3: 'Aplicação dos fatores' },
        { lista: [
          'Fator de oferta: 0,90 (desconto típico de 10%)',
          'Fator de transposição: 1,00 (oferta atual, sem ajuste)',
          'Fator de área: (80/92)^0,25 = 0,9655 (avaliando ligeiramente menor)',
          'Fator de padrão: 0,95 (avaliando padrão médio vs. amostra médio-alto)',
          'Fator de idade: 0,97 (avaliando 8 anos vs. amostra 5 anos — pequena depreciação extra)',
          'Fator de conservação: 1,00 (ambos em boa conservação)',
        ]},

        { h3: 'Cálculo do valor unitário homogeneizado' },
        { callout: 'Valor unitário = (R$ 420.000 × 0,90 × 1,00 × 0,9655 × 0,95 × 0,97 × 1,00) ÷ 92m²\nValor unitário = R$ 336.218 ÷ 92\nValor unitário = R$ 3.654/m²', calloutTitulo: 'Cálculo' },

        { h3: 'Resultado após processar as 8 amostras' },
        { p: 'Após aplicar os fatores em todas as 8 amostras e fazer o tratamento estatístico:' },
        { lista: [
          'Valor unitário médio homogeneizado: R$ 4.375/m²',
          'Desvio padrão: R$ 240/m²',
          'Saneamento Chauvenet: 1 amostra removida (outlier)',
          'Valor unitário ajustado (7 amostras): R$ 4.350/m²',
          'Intervalo de confiança 80%: R$ 4.150 a R$ 4.550/m² (amplitude 9,2%)',
        ]},

        { h3: 'Conclusão do laudo' },
        { callout: 'Valor de Mercado = R$ 4.350/m² × 80m² = R$ 348.000,00\nIntervalo de Confiança 80%: R$ 332.000 a R$ 364.000\nGrau de Precisão: III (amplitude 9,2% < 15%)', calloutTitulo: 'Resultado final' },

        { h2: 'Erros mais comuns no Método Comparativo' },
        { lista: [
          'Coletar poucas amostras (4 ou menos = Grau I baixo)',
          'Misturar amostras de regiões muito distintas',
          'Não documentar a fonte de cada amostra',
          'Aplicar fatores fora do intervalo NBR (0,5 a 2,0)',
          'Não fazer saneamento de outliers',
          'Usar média simples em vez de média de valores homogeneizados',
          'Esquecer o fator de oferta em amostras anunciadas',
        ]},

        { h2: 'Como o AvalieImob automatiza o Método Comparativo' },
        { p: 'No sistema, todo o cálculo é feito automaticamente:' },
        { lista: [
          'Wizard guiado de coleta de amostras com campos obrigatórios da NBR',
          'Aplicação automática de todos os fatores conforme atributos cadastrados',
          'Cálculo estatístico em tempo real (média, mediana, IC, Chauvenet)',
          'Validação dos limites NBR (avisa se fator final extrapola 0,5 a 2,0)',
          'Geração da planilha de homogeneização pronta pra anexar ao laudo',
          'IA especializada que sugere amostras adicionais quando o Grau de Precisão fica baixo',
        ]},
        { cta: 'Teste o sistema completo do AvalieImob por 7 dias grátis.', ctaTexto: 'Começar grátis →' },

        { h2: 'Conclusão' },
        { p: 'O Método Comparativo Direto é a base do trabalho do avaliador imobiliário urbano. Dominar a técnica — especialmente a homogeneização e o tratamento estatístico — é o que separa um laudo Grau I (questionável) de um Grau III (defendível em juízo).' },
        { p: 'A boa notícia é que ferramentas modernas automatizam o cálculo, deixando você focar no que realmente exige expertise: a interpretação técnica das amostras e a justificativa das escolhas metodológicas.' },
      ]}
      servicosRelacionados={[
        { slug: 'avaliacao-urbana', titulo: 'Avaliação de Imóveis Urbanos' },
        { slug: 'ptam', titulo: 'PTAM — Parecer Técnico de Avaliação Mercadológica' },
        { slug: 'laudo-tecnico', titulo: 'Laudo Técnico de Avaliação' },
      ]}
      postsRelacionados={relacionados}
    />
  );
}
