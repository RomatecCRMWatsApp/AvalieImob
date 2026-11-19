import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getPostBySlug, getRelatedPosts } from '../../data/blogPosts';

const SLUG = 'checklist-vistoria-avaliacao-imobiliaria-ptam';

export default function BlogPostChecklistVistoria() {
  const post = getPostBySlug(SLUG);
  const relacionados = getRelatedPosts(SLUG);

  return (
    <BlogPostTemplate
      slug={SLUG}
      titulo={post.titulo}
      subtitulo="O que conferir antes de ir ao imóvel, o que anotar em campo e como registrar divergências e limitações para sustentar o parecer."
      meta={post.meta}
      palavrasChave="checklist de vistoria, vistoria para avaliação imobiliária, vistoria PTAM, relatório fotográfico, caracterização do imóvel, corretor avaliador"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { h2: 'Qual é a finalidade da visita' },
        { p: 'Na avaliação, a vistoria existe para caracterizar o imóvel: saber o que ele é, como está e onde está, porque são esses dados que sustentam a comparação com o mercado.' },
        { p: 'Ela é diferente da vistoria de entrada ou de saída de locação, que registra o estado do imóvel para comparar no fim do contrato. Os registros podem ser parecidos, mas a pergunta é outra.' },

        { h2: 'Antes de ir ao imóvel' },
        { lista: [
          'Reúna os documentos disponíveis: matrícula, carnê de IPTU ou boletim de cadastro, planta e habite-se, se houver.',
          'Anote a área de cada documento e de onde ela veio. Áreas diferentes entre documentos são comuns e precisam ser registradas.',
          'Confirme o endereço e a localização no mapa.',
          'Agende o acesso com quem tem autorização para abrir o imóvel.',
          'Liste o que está faltando. Ter os documentos em mãos não prova, sozinho, que o imóvel está regular.',
        ]},

        { h2: 'O que registrar em campo' },
        { tabela: { cabecalho: ['Item', 'O que anotar'], linhas: [
          ['Identificação', 'Endereço conferido no local, número, acesso, confrontantes visíveis'],
          ['Áreas', 'Área medida ou informada, indicando a fonte de cada número'],
          ['Construção', 'Tipo, número de pavimentos, ambientes, padrão de acabamento, idade aparente'],
          ['Conservação', 'Estado aparente de cada ambiente e sinais visíveis de problema (fissuras, infiltração, umidade)'],
          ['Benfeitorias', 'Muros, garagem, piscina, área de lazer, edículas'],
          ['Infraestrutura', 'Pavimentação, água, esgoto, energia, iluminação pública, transporte'],
          ['Vizinhança', 'Uso predominante, comércio e serviços próximos, fatores que valorizam ou desvalorizam'],
        ] } },

        { h2: 'Como organizar as fotos' },
        { p: 'Cada foto deve dizer o que mostra. Use legenda com o ambiente ou o aspecto registrado, a data e, quando o aparelho permitir, a localização.' },
        { p: 'Não existe número certo de fotos. Fotografe o suficiente para que outra pessoa entenda o imóvel sem ter ido lá: fachada, cada ambiente, áreas externas, vizinhança e qualquer detalhe que você citar no parecer.' },

        { h2: 'Como tratar divergências e limitações' },
        { p: 'No relatório, separe três origens de informação:' },
        { lista: [
          'observado: o que você viu ou mediu;',
          'informado: o que o cliente ou o morador disse;',
          'documental: o que está em matrícula, cadastro ou planta.',
        ]},
        { p: 'Quando houver ambiente sem acesso, escreva isso. Quando a área medida não bater com a da matrícula, registre os dois números e a diferença. Não escolha um deles por suposição.' },
        { callout: 'Área construída informada no cadastro municipal: 120,00 m². Área medida na vistoria: 141,50 m². A diferença corresponde a uma ampliação nos fundos (área de serviço coberta), sem averbação localizada na matrícula. Para o cálculo foi adotada a área ________, pelo motivo ________.', calloutTitulo: 'Exemplo fictício — registro de divergência' },

        { h2: 'Quando pedir apoio especializado' },
        { p: 'Registrar uma fissura ou uma infiltração aparente faz parte da caracterização. Dizer se ela compromete a estrutura é outro trabalho, que exige profissional habilitado para esse diagnóstico. Quando o problema puder afetar o valor de forma relevante, recomende a avaliação especializada e anote a limitação no parecer.' },

        { h2: 'Checklist final antes de elaborar o parecer' },
        { lista: [
          'Identificação do imóvel conferida com os documentos',
          'Cada área com a sua fonte',
          'Data da vistoria anotada',
          'Fotos com legenda, sem ambiente importante faltando',
          'Divergências e acessos negados registrados',
          'Lista do que ainda falta, com quem vai providenciar',
        ]},
        { p: 'Com a vistoria organizada, o próximo passo é montar o parecer. O guia de PTAM mostra o que vai em cada seção.', link: '/blog/como-fazer-ptam-passo-a-passo-nbr-14653', linkTexto: 'Ler o guia de PTAM passo a passo →' },

        { h2: 'Dúvidas frequentes' },
        { h3: 'Posso fazer o PTAM sem visitar o imóvel?' },
        { p: 'Fotos ou descrição fornecidas pelo cliente, sem vistoria do avaliador, não determinam automaticamente o Grau I. O documento deve identificar os elementos utilizados, as limitações de acesso, as justificativas e a metodologia, conforme as referências aplicáveis. Qualquer exceção de vistoria precisa ser confirmada pelo profissional responsável com acesso à norma aplicável.' },
        { h3: 'Como registrar uma área divergente?' },
        { p: 'Anote as duas áreas com a fonte de cada uma e explique qual foi adotada no cálculo e por quê.' },
        { h3: 'Preciso de equipamento especial?' },
        { p: 'Trena ou medidor a laser, celular com câmera e localização, e o checklist. Instrumentos de diagnóstico ficam com o especialista.' },

        { cta: 'No Kit TVI da AvalieImob, o modelo de vistoria para PTAM guarda os itens, as fotos com localização e as observações. Depois, você importa a vistoria direto para o PTAM. Teste por 7 dias grátis.', ctaTexto: 'Começar grátis →', ctaPos: 'meio' },
        { callout: 'A Resolução COFECI nº 1.066/2007 e o Ato Normativo nº 001/2011 tratam do conteúdo do PTAM elaborado por corretor, incluindo a caracterização do imóvel e a data da vistoria. Este checklist é uma organização didática desses registros, não uma certificação de conformidade.', calloutTitulo: 'Referências' },
      ]}
      servicosRelacionados={[
        { slug: 'ptam', titulo: 'PTAM — Parecer Técnico de Avaliação Mercadológica' },
        { slug: 'avaliacao-urbana', titulo: 'Avaliação de Imóveis Urbanos' },
      ]}
      postsRelacionados={relacionados}
    />
  );
}
