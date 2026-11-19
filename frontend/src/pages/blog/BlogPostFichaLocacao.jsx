import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getPostBySlug, getRelatedPosts } from '../../data/blogPosts';

const SLUG = 'ficha-resumo-contrato-locacao-comercial';

export default function BlogPostFichaLocacao() {
  const post = getPostBySlug(SLUG);
  const relacionados = getRelatedPosts(SLUG);

  return (
    <BlogPostTemplate
      slug={SLUG}
      titulo={post.titulo}
      subtitulo="Como resumir um contrato de locação comercial sem distorcer o que ele diz: campos, fonte de cada informação e um exemplo fictício."
      meta={post.meta}
      palavrasChave="ficha-resumo de locação, resumo de contrato de locação, locação comercial, Lei 8.245/1991, garantia locatícia, ação renovatória, corretor de imóveis"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { h2: 'O que é uma ficha-resumo de locação' },
        { p: 'É um documento de trabalho que resume um contrato já assinado. Ela não cria obrigação nenhuma: só registra o que o contrato e seus aditivos dizem, com a indicação de onde cada dado está.' },
        { p: 'Isso a diferencia de um contrato-modelo. O contrato-modelo é o ponto de partida para redigir uma locação nova. A ficha-resumo é o retrato de uma locação que já existe.' },
        { p: 'Ela é útil em três situações comuns na rotina do corretor:' },
        { lista: [
          'na administração do imóvel, para lembrar vencimento, reajuste e fim da vigência;',
          'na venda de um imóvel alugado, para mostrar ao comprador quais condições ele vai assumir;',
          'na avaliação de um imóvel locado, para registrar o aluguel contratado e as condições que influenciam a análise.',
        ]},

        { h2: 'Quais campos registrar' },
        { p: 'Registre o que consta no documento. Quando uma informação não for encontrada, escreva "não localizado". Não deixe o campo em branco e não preencha por dedução.' },
        { tabela: { cabecalho: ['Grupo', 'Campos'], linhas: [
          ['Partes', 'Locador, locatário, fiadores ou outros garantidores, representantes que assinaram'],
          ['Imóvel', 'Endereço, matrícula, inscrição municipal, área e de onde veio essa área (contrato, matrícula ou medição)'],
          ['Uso', 'Atividade permitida, restrições de uso e sublocação'],
          ['Datas', 'Assinatura, início da vigência, início da cobrança, fim da vigência, aviso prévio previsto'],
          ['Valores', 'Aluguel mensal, dia de vencimento, índice e periodicidade de reajuste, carência, multa por atraso'],
          ['Encargos', 'Quem paga IPTU, condomínio, água e energia'],
          ['Garantia', 'Modalidade prevista no contrato e valor ou limite; divergências registradas como estão'],
          ['Seguros', 'Seguro-incêndio e outros seguros, em campo separado da garantia'],
          ['Benfeitorias', 'O que pode ser feito, se é indenizável e se há direito de retenção'],
          ['Encerramento', 'Multa por rescisão antecipada, devolução do imóvel, vistoria de saída'],
          ['Aditivos', 'Número, data e o que cada aditivo alterou'],
        ] } },

        { h3: 'Garantia locatícia: como registrar' },
        { p: 'A ficha deve registrar a modalidade de garantia prevista no contrato: caução, fiança, seguro de fiança locatícia ou cessão fiduciária de quotas de fundo de investimento. O art. 37 da Lei nº 8.245/1991 veda a exigência de mais de uma modalidade de garantia no mesmo contrato. Não confunda seguro-incêndio ou encargos da locação com seguro de fiança locatícia.' },
        { p: 'Se o documento mencionar modalidades acumuladas, registre a divergência e encaminhe-a à análise jurídica. A ficha-resumo não deve ocultar exigências existentes nem declarar sua validade. Quando não for possível identificar a garantia, registre "não identificado"; use "sem garantia" somente quando a ausência tiver sido efetivamente conferida.' },

        { h2: 'Como preencher sem distorcer o contrato' },
        { p: 'A regra que mais protege o corretor é a rastreabilidade: toda linha da ficha aponta para o documento e para a cláusula de origem. Se alguém questionar um dado, você mostra de onde ele veio em segundos.' },
        { listaOrd: [
          'Leia o contrato e todos os aditivos antes de começar.',
          'Preencha cada campo com o texto ou o número do documento, sem interpretar.',
          'Ao lado, anote a fonte: "Contrato, cláusula 4.1" ou "1º Aditivo, cláusula 2".',
          'Quando um aditivo mudar uma condição, registre as duas: a original e a alterada, com a data de cada uma.',
          'Anote a data em que você conferiu a ficha e quem conferiu.',
        ]},

        { h2: 'Exemplo comentado' },
        { callout: 'Os dados abaixo são inventados para ilustrar o preenchimento. Não correspondem a nenhum contrato real.', calloutTitulo: 'Exemplo fictício' },
        { tabela: { cabecalho: ['Informação', 'Conteúdo', 'Fonte'], linhas: [
          ['Locador', 'Locador A', 'Contrato, preâmbulo'],
          ['Locatário', 'Locatário B (loja de materiais de construção)', 'Contrato, preâmbulo'],
          ['Uso permitido', 'Comércio varejista; sublocação proibida', 'Contrato, cl. 3'],
          ['Vigência', '60 meses a partir da assinatura', 'Contrato, cl. 5.1'],
          ['Início da cobrança', '3 meses após a assinatura (carência para obras)', 'Contrato, cl. 6.2'],
          ['Aluguel', 'R$ 8.000,00/mês, vencimento dia 10', 'Contrato, cl. 6.1'],
          ['Aluguel alterado', 'R$ 8.640,00/mês a partir do 13º mês', '1º Aditivo, cl. 1'],
          ['Reajuste', 'Anual, pelo índice previsto no contrato', 'Contrato, cl. 7'],
          ['Garantia', 'Seguro de fiança locatícia', 'Contrato, cl. 12'],
          ['Seguro-incêndio', 'Contratado pelo locatário', 'Contrato, cl. 13'],
          ['Multa por rescisão', 'Não localizado', '—'],
        ] }, tabelaNota: 'Repare: a data de assinatura é diferente do início da cobrança; o aluguel original e o alterado aparecem lado a lado, cada um com sua fonte; a garantia e o seguro-incêndio estão em linhas separadas; e o campo sem informação está marcado como "não localizado", e não em branco.' },

        { h2: 'Como a ficha ajuda na avaliação de um imóvel locado' },
        { p: 'Quando o imóvel avaliado está alugado, o aluguel contratado entra na análise como informação, mas não prova o valor de venda. Ele pode estar acima ou abaixo do mercado, pode ter sido negociado com carência e pode estar desatualizado.' },
        { p: 'A ficha organiza esses dados para o avaliador. A pesquisa de mercado e a escolha fundamentada do método, conforme a NBR 14.653, continuam necessárias.' },

        { h3: 'Renovação da locação comercial' },
        { p: 'A renovação judicial da locação comercial não é automática. O art. 51 da Lei nº 8.245/1991 exige, cumulativamente, contrato escrito por prazo determinado; pelo menos cinco anos de contrato ou de contratos escritos sem interrupção; e exploração do comércio no mesmo ramo por pelo menos três anos ininterruptos.' },
        { p: 'A ação renovatória deve ser proposta entre um ano e seis meses antes do fim do contrato vigente. A ficha ajuda a organizar os documentos e as datas, mas não confirma, sozinha, o direito à renovação ou o atendimento de todos os requisitos. A análise jurídica deve considerar o caso concreto e as demais hipóteses legais.' },
        { p: 'Por isso, registre cada contrato e cada aditivo em linha própria, com as datas, a continuidade documentada e o ramo explorado. Ter vários arquivos não prova, por si só, que o prazo foi atendido.' },

        { h2: 'Erros comuns' },
        { lista: [
          'Somar encargos ao aluguel e registrar tudo como um valor só.',
          'Usar a data de assinatura como início da cobrança, ignorando a carência.',
          'Registrar o valor contratado como se fosse o valor recebido. Atrasos e acordos não aparecem no contrato.',
          'Tratar seguro-incêndio como garantia locatícia.',
          'Ler só o contrato e esquecer os aditivos.',
        ]},

        { h2: 'Dúvidas frequentes' },
        { h3: 'A ficha substitui o contrato?' },
        { p: 'Não. Ela é um resumo de consulta. Em caso de divergência, vale o contrato e seus aditivos.' },
        { h3: 'Posso entregar a ficha ao comprador do imóvel?' },
        { p: 'Pode servir de apoio, mas entregue junto a cópia do contrato e dos aditivos, com autorização das partes quando houver dados pessoais.' },
        { h3: 'O que fazer quando o contrato é omisso sobre um ponto?' },
        { p: 'Marque "não localizado". A interpretação de cláusula omissa é questão jurídica e deve ser levada ao advogado das partes.' },

        { cta: 'Na AvalieImob você gera contratos de locação residencial e comercial e faz a avaliação de aluguel do imóvel. Teste por 7 dias grátis.', ctaTexto: 'Começar grátis →', ctaPos: 'meio' },
        { callout: 'Este artigo tem caráter informativo e não substitui a orientação de advogado sobre o caso concreto. Referência: Lei nº 8.245/1991 (texto compilado no portal do Planalto).', calloutTitulo: 'Referências' },
      ]}
      servicosRelacionados={[
        { slug: 'avaliacao-urbana', titulo: 'Avaliação de Imóveis Urbanos' },
        { slug: 'ptam', titulo: 'PTAM — Parecer Técnico de Avaliação Mercadológica' },
      ]}
      postsRelacionados={relacionados}
    />
  );
}
