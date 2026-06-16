import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getPostBySlug, getRelatedPosts } from '../../data/blogPosts';

const SLUG = 'precificar-georreferenciamento-demarcacao-averbacao-proposta';

export default function BlogPostPropostasConsultoria() {
  const post = getPostBySlug(SLUG);
  const relacionados = getRelatedPosts(SLUG);

  return (
    <BlogPostTemplate
      slug={SLUG}
      titulo={post.titulo}
      subtitulo="Como separar honorários técnicos, emolumentos de cartório e taxas — e montar propostas de georreferenciamento, demarcação, desmembramento e averbação."
      meta={post.meta}
      palavrasChave="precificar georreferenciamento, proposta de honorários agrimensura, demarcação de lotes, desmembramento, remembramento, averbação de construção, emolumentos TJMA, INCRA SIGEF, ART TRT, proposta de consultoria"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { p: 'Precificar serviços de agrimensura e regularização fundiária é onde muitos profissionais erram — para mais ou para menos. O segredo é separar com clareza três blocos: os honorários técnicos (seu trabalho), os emolumentos de cartório (taxas de registro) e as taxas de órgãos públicos. Misturar tudo gera propostas confusas e margens imprevisíveis.' },
        { p: 'Neste guia, mostro como estruturar propostas para os principais serviços e quais componentes não podem faltar.' },

        { h2: 'Os três blocos de toda proposta' },
        { lista: [
          'Honorários técnicos — sua remuneração pelo serviço (campo, escritório, ART/TRT, complexidade)',
          'Emolumentos de cartório — taxas do Registro de Imóveis, tabeladas (ex.: Tabela do TJMA), pagas ao cartório',
          'Taxas de órgãos — INCRA/SIGEF, prefeitura, taxas ambientais quando aplicáveis',
        ]},
        { callout: 'Honorários são seus; emolumentos e taxas são repasses. Deixe os três blocos explícitos na proposta — o cliente entende o que paga a você e o que é taxa de terceiros, e você protege sua margem.', calloutTitulo: 'Regra de ouro' },

        { h2: 'Georreferenciamento (INCRA / SIGEF)' },
        { p: 'A precificação parte da área (hectares), do número de vértices, das diárias de campo e do deslocamento, com um fator de complexidade do imóvel. Some a ART/TRT e a assessoria. Os custos de cartório e a certificação SIGEF entram como itens informativos (repasse).' },
        { lista: [
          'Honorários técnicos: (área × R$/ha + vértices × R$/vértice + diárias + deslocamento) × complexidade',
          'Piso mínimo por trabalho (ex.: 2 salários mínimos sobre o núcleo técnico)',
          'ART/TRT do responsável técnico',
          'Opcionais: CCIR, CAR, ITR, anuência de confrontantes, retificação',
        ]},

        { h2: 'Demarcação de lotes (urbana e rural)' },
        { p: 'Inclui a locação topográfica e a materialização dos marcos. Precifique por marcos (tipo e quantidade — concreto, tubo, madeira), área, deslocamento e adicional de campo (insalubridade/periculosidade quando cabível), aplicando a complexidade.' },

        { h2: 'Desmembramento e remembramento' },
        { p: 'Aqui os emolumentos pesam: cada matrícula afetada gera taxa de cartório (tabelada pelo valor venal). Separe o projeto técnico (honorários) dos emolumentos por matrícula e da eventual taxa de prefeitura (no desmembramento urbano).' },

        { h2: 'Averbação de construção' },
        { p: 'A averbação registra a edificação na matrícula. Os componentes típicos são a vistoria/medição, a ART/TRT, o cálculo do INSS por aferição indireta (quando aplicável), os emolumentos do cartório e, em alguns municípios, a taxa de habite-se/prefeitura.' },

        { h2: 'Parcelamento e fechamento' },
        { p: 'Estruture o pagamento em parcelas (ex.: 40/30/30 ou 50/50), com a última absorvendo eventuais resíduos de arredondamento. Deixe claro o que está incluído e o que é opcional — assim a proposta vira contrato sem retrabalho.' },

        { h2: 'Como o AvalieImob monta a proposta automaticamente' },
        { p: 'No módulo de Propostas de Consultoria, você seleciona o tipo de serviço e informa os dados (área, vértices, matrículas, valor venal, diárias). O motor calcula honorários, emolumentos (tabela TJMA) e taxas separadamente, sugere o parcelamento e gera a proposta numerada — pronta para enviar.' },
        { lista: [
          'Georreferenciamento, demarcação urbana e rural',
          'Desmembramento e remembramento',
          'Averbação de construção (residencial e comercial)',
          'Cálculo separado de honorários, emolumentos e taxas',
        ]},
        { cta: 'Monte propostas de consultoria com cálculo automático. Teste 7 dias grátis.', ctaTexto: 'Começar grátis →' },

        { h2: 'Conclusão' },
        { p: 'Uma boa proposta de consultoria é transparente: separa o que é honorário do que é repasse, justifica a complexidade e fecha com parcelamento claro. Quando esse cálculo é automatizado, você responde o cliente na hora, com consistência — e fecha mais trabalhos sem deixar dinheiro na mesa.' },
      ]}
      servicosRelacionados={[
        { slug: 'avaliacao-rural', titulo: 'Avaliação de Imóveis Rurais' },
        { slug: 'ptam', titulo: 'PTAM — Parecer Técnico de Avaliação Mercadológica' },
      ]}
      postsRelacionados={relacionados}
    />
  );
}
