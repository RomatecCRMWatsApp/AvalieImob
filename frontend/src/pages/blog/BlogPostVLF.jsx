import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getPostBySlug, getRelatedPosts } from '../../data/blogPosts';

const SLUG = 'como-calcular-valor-liquidacao-forcada-vlf';

export default function BlogPostVLF() {
  const post = getPostBySlug(SLUG);
  const relacionados = getRelatedPosts(SLUG);

  return (
    <BlogPostTemplate
      slug={SLUG}
      titulo={post.titulo}
      subtitulo="Metodologia detalhada com fatores de liquidez, atratividade e prazo. Inclui exemplo prático com cálculo passo a passo para garantia bancária."
      meta={post.meta}
      palavrasChave="VLF, valor de liquidação forçada, garantia bancária, liquidação forçada imóvel, hipoteca, alienação fiduciária, laudo bancário, banco do brasil VLF, caixa VLF"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { p: 'O Valor de Liquidação Forçada (VLF) é um dos conceitos mais importantes — e mais mal compreendidos — na avaliação de garantias bancárias. Bancos e financeiras exigem o VLF em todos os laudos de avaliação de imóveis dados em garantia (hipoteca, alienação fiduciária, penhor mercantil), mas muitos avaliadores ainda calculam de forma incorreta, gerando laudos questionados e operações de crédito travadas.' },
        { p: 'Neste artigo, vou explicar exatamente o que é o VLF, qual a metodologia técnica para calculá-lo conforme práticas dos principais bancos brasileiros, os fatores que devem ser aplicados e um exemplo prático com cálculo passo a passo.' },

        { h2: 'O que é Valor de Liquidação Forçada (VLF)?' },
        { p: 'O Valor de Liquidação Forçada é o valor estimado que o imóvel obteria em uma situação de venda forçada — geralmente leilão judicial ou extrajudicial — em prazo curto. É distinto do Valor de Mercado, que pressupõe condições normais de transação (sem urgência, vendedor não compelido).' },
        { p: 'Em uma operação de crédito com garantia, o banco precisa saber qual valor recuperaria se o tomador deixasse de pagar e o imóvel tivesse que ser executado. Esse é o papel do VLF: representar o valor mínimo recuperável em cenário de inadimplência.' },

        { h3: 'Por que o VLF é menor que o Valor de Mercado?' },
        { p: 'Em uma venda forçada (leilão), o imóvel sofre desconto significativo por três fatores principais:' },
        { lista: [
          'Prazo curto: o leilão tem cronograma definido, sem possibilidade de aguardar a melhor oferta',
          'Negociação restrita: lances são submetidos em formato fechado, sem flexibilidade comercial',
          'Atratividade reduzida: imóveis em leilão carregam estigma negativo (problemas jurídicos, físicos), reduzindo o público comprador',
        ]},
        { p: 'Estatisticamente, o VLF representa entre 50% e 85% do Valor de Mercado, dependendo do tipo de imóvel, região e liquidez do mercado local.' },

        { h2: 'Metodologia de cálculo do VLF' },
        { p: 'A metodologia mais aceita pelos principais bancos brasileiros (BB, Caixa, Itaú, Bradesco, Santander) calcula o VLF aplicando três fatores ao Valor de Mercado:' },
        { callout: 'VLF = Valor de Mercado × Fator de Liquidez × Fator de Atratividade × Fator de Prazo', calloutTitulo: 'Fórmula básica' },

        { h3: 'Fator de Liquidez (FL)' },
        { p: 'Mede a velocidade típica de venda do imóvel no mercado local em condições normais. Quanto mais líquido (vende rápido), maior o fator (mais próximo de 1). Quanto menos líquido, menor o fator.' },
        { lista: [
          'Apartamento padrão em região central: FL = 0,90 a 0,95 (alta liquidez)',
          'Casa em bairro residencial estabelecido: FL = 0,85 a 0,90',
          'Sala comercial em centro empresarial: FL = 0,80 a 0,90',
          'Galpão industrial: FL = 0,70 a 0,85',
          'Terreno urbano de grande porte: FL = 0,65 a 0,80',
          'Imóvel rural de pequeno porte: FL = 0,75 a 0,85',
          'Fazenda de grande porte (acima de 500 ha): FL = 0,65 a 0,75',
          'Imóveis especiais (postos, hospitais, hotéis): FL = 0,55 a 0,70',
        ]},

        { h3: 'Fator de Atratividade (FA)' },
        { p: 'Mede características específicas do imóvel que o tornam mais ou menos desejável para o mercado em geral. Considera:' },
        { lista: [
          'Localização (zona valorizada vs. degradada)',
          'Estado de conservação (novo, regular, ruim)',
          'Padrão construtivo vs. demanda regional',
          'Vícios redibitórios visíveis',
          'Infraestrutura urbana ou rural disponível',
          'Pendências legais ou ambientais (processos, autuações)',
        ]},
        { p: 'Em geral o FA varia entre 0,80 e 0,98. Imóveis em ótimo estado e localização premium ficam próximos de 0,98. Imóveis com problemas ficam abaixo de 0,90.' },

        { h3: 'Fator de Prazo (FP)' },
        { p: 'Mede o impacto do prazo curto típico de venda forçada (leilão). Bancos costumam considerar:' },
        { lista: [
          'Prazo de 6 meses (1ª e 2ª praça): FP = 0,90',
          'Prazo de 12 meses: FP = 0,93',
          'Prazo de 18-24 meses: FP = 0,95',
          'Operação extrajudicial mais flexível: FP = 0,95 a 0,98',
        ]},

        { h2: 'Exemplo prático: cálculo de VLF passo a passo' },
        { p: 'Vamos calcular o VLF de um imóvel real para ilustrar a metodologia. Considere os seguintes dados:' },
        { callout: 'Imóvel: Apartamento de 80m², 3 dormitórios, 2 vagas, em bairro residencial estabelecido em São Luís/MA. Estado de conservação: bom. Idade aparente: 8 anos. Padrão: médio.', calloutTitulo: 'Dados do caso' },

        { h3: 'Passo 1 — Determinar o Valor de Mercado' },
        { p: 'Pelo método comparativo direto, com pesquisa de 8 amostras de apartamentos similares na região, chegou-se ao Valor de Mercado de R$ 350.000,00.' },

        { h3: 'Passo 2 — Definir o Fator de Liquidez (FL)' },
        { p: 'Apartamento padrão médio em bairro residencial estabelecido tem alta liquidez no mercado local. Tempo médio de venda: 90-120 dias.' },
        { p: 'FL = 0,90' },

        { h3: 'Passo 3 — Definir o Fator de Atratividade (FA)' },
        { p: 'O imóvel está em bom estado de conservação, sem vícios visíveis, em região com infraestrutura completa, sem pendências legais.' },
        { p: 'FA = 0,95' },

        { h3: 'Passo 4 — Definir o Fator de Prazo (FP)' },
        { p: 'O banco considera o cenário de leilão extrajudicial conforme Lei 9.514/97 (alienação fiduciária), com prazo total de 6 meses entre a notificação e a 2ª praça.' },
        { p: 'FP = 0,90' },

        { h3: 'Passo 5 — Calcular o VLF' },
        { callout: 'VLF = R$ 350.000,00 × 0,90 × 0,95 × 0,90\nVLF = R$ 350.000,00 × 0,7695\nVLF = R$ 269.325,00', calloutTitulo: 'Cálculo final' },
        { p: 'Neste exemplo, o VLF representa cerca de 77% do Valor de Mercado — dentro da faixa esperada para apartamentos urbanos. O banco usará o VLF (e não o Valor de Mercado) como base para calcular o LTV (Loan-to-Value) máximo do empréstimo.' },

        { h2: 'Como cada banco aplica o VLF na concessão de crédito' },
        { p: 'Os principais bancos brasileiros usam o VLF de formas ligeiramente distintas:' },

        { h3: 'Banco do Brasil' },
        { p: 'O BB tradicionalmente trabalha com LTV de até 70% sobre o VLF para crédito imobiliário, podendo chegar a 80% em modalidades específicas. Avaliadores credenciados PCA (Programa de Credenciamento de Avaliadores) recebem o modelo padrão.' },

        { h3: 'Caixa Econômica Federal' },
        { p: 'A Caixa, como principal agente de crédito habitacional via SBPE e FGTS, costuma trabalhar com LTV de 80% sobre o VLF para Pessoa Física e até 60% em operações comerciais. Tem padrão próprio de laudo.' },

        { h3: 'Itaú, Bradesco e Santander' },
        { p: 'Bancos privados de grande porte trabalham com LTV de 70% a 80% sobre o VLF, com modelos próprios de laudo. Avaliadores cadastrados nos bancos podem ter padrões específicos.' },

        { h3: 'Sicredi e cooperativas' },
        { p: 'Cooperativas de crédito tendem a ser mais conservadoras, com LTV de 60% a 70% sobre VLF. O Sicredi tem modelo próprio para crédito rural com penhor.' },

        { h2: 'Erros comuns ao calcular o VLF' },
        { lista: [
          'Confundir VLF com "valor venal" do IPTU — são conceitos completamente diferentes',
          'Usar fatores fixos sem analisar características específicas do imóvel',
          'Não considerar pendências legais ou ambientais que reduzem a atratividade',
          'Esquecer de mencionar a metodologia no laudo (cada fator deve ser justificado tecnicamente)',
          'Aplicar VLF em laudos onde ele não é solicitado (gera confusão para clientes privados)',
          'Calcular VLF para imóveis sem garantia bancária (uso desnecessário)',
          'Não atualizar a metodologia conforme mudanças do mercado local (mercados em queda exigem fatores mais conservadores)',
        ]},

        { h2: 'Quando o VLF é obrigatório no laudo?' },
        { p: 'O VLF é obrigatório nos seguintes casos:' },
        { lista: [
          'Garantia hipotecária (Lei 4.380/64)',
          'Alienação fiduciária de bem imóvel (Lei 9.514/97)',
          'Penhor mercantil rural (Decreto-Lei 167/1967, atualizado pela Lei 13.986/2020)',
          'Garantia em operações de crédito rural (Pronaf, Pronamp, custeio)',
          'Garantia em operações estruturadas (CRI, CRA, FIDC com lastro imobiliário)',
        ]},
        { p: 'Em laudos para outras finalidades (transação privada, partilha, ação judicial não-bancária), o VLF não é obrigatório, embora possa ser informado em separado para fins informativos.' },

        { h2: 'Como o AvalieImob automatiza o cálculo do VLF' },
        { p: 'No módulo de Avaliação de Garantias Bancárias do AvalieImob, o VLF é calculado automaticamente conforme você seleciona:' },
        { lista: [
          'Banco/credor (BB, Caixa, Itaú, Bradesco, Santander, Sicredi, BNB, BASA, etc.)',
          'Tipo de garantia (hipoteca, alienação fiduciária, penhor mercantil)',
          'Tipologia do imóvel (apartamento, casa, terreno, comercial, rural)',
          'Localização e características específicas do bem',
        ]},
        { p: 'O sistema sugere os fatores adequados (FL, FA, FP) com base em dados regionais e práticas do banco selecionado, mas você pode editá-los manualmente com justificativa técnica. Toda a metodologia fica registrada no laudo final.' },
        { cta: 'Teste o módulo de Avaliação de Garantias Bancárias por 7 dias grátis.', ctaTexto: 'Começar grátis →' },

        { h2: 'Conclusão' },
        { p: 'O Valor de Liquidação Forçada é um conceito técnico fundamental para qualquer avaliador que trabalhe com garantias bancárias. Calculá-lo corretamente exige aplicar três fatores principais — Liquidez, Atratividade e Prazo — sobre o Valor de Mercado, com fundamentação técnica adequada.' },
        { p: 'Erros no cálculo do VLF geram laudos questionados, operações travadas e prejuízo profissional. Por isso vale o investimento em ferramentas adequadas e em estudar as particularidades de cada banco — quem domina essa especialidade tem demanda constante e bem remunerada do mercado financeiro.' },
      ]}
      servicosRelacionados={[
        { slug: 'avaliacao-garantia', titulo: 'Avaliação de Garantias Bancárias' },
        { slug: 'avaliacao-urbana', titulo: 'Avaliação de Imóveis Urbanos' },
        { slug: 'ptam', titulo: 'PTAM — Parecer Técnico de Avaliação Mercadológica' },
      ]}
      postsRelacionados={relacionados}
    />
  );
}
