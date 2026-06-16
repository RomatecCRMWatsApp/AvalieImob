import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getPostBySlug, getRelatedPosts } from '../../data/blogPosts';

const SLUG = 'contrato-exclusividade-procuracao-corretor-imoveis';

export default function BlogPostContratoExclusividade() {
  const post = getPostBySlug(SLUG);
  const relacionados = getRelatedPosts(SLUG);

  return (
    <BlogPostTemplate
      slug={SLUG}
      titulo={post.titulo}
      subtitulo="Base legal, cláusulas essenciais, prazo e comissão — e como gerar o contrato com procuração e assinar tudo digitalmente."
      meta={post.meta}
      palavrasChave="contrato de exclusividade, contrato de corretagem, exclusividade corretor de imóveis, procuração corretor, art 726 código civil, COFECI, CRECI, comissão de corretagem, autorização de venda"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { p: 'O contrato de exclusividade é uma das ferramentas mais importantes — e mais subutilizadas — pelo corretor de imóveis. Bem redigido, ele garante a comissão em qualquer venda realizada durante a vigência, organiza a relação com o proprietário e profissionaliza o atendimento. Combinado com uma procuração, ainda permite ao corretor reunir toda a documentação do imóvel sem depender da disponibilidade do vendedor.' },
        { p: 'Neste artigo você vai entender a base legal, as cláusulas que não podem faltar, como definir prazo e comissão, e como gerar e assinar o contrato digitalmente.' },

        { h2: 'O que é o contrato de exclusividade de corretagem?' },
        { p: 'É o instrumento pelo qual o proprietário (contratante) autoriza um único corretor ou imobiliária (contratado) a intermediar a venda ou locação do imóvel por prazo determinado, com exclusividade. Durante a vigência, o proprietário não pode contratar outros corretores nem vender por conta própria sem que a comissão seja devida.' },

        { h2: 'Base legal' },
        { lista: [
          'Código Civil, art. 722 a 729 — disciplina o contrato de corretagem',
          'Código Civil, art. 726 — se a corretagem for ajustada com exclusividade, o corretor terá direito à remuneração integral ainda que o negócio se realize sem a sua mediação, salvo comprovada inércia ou ociosidade',
          'Lei 6.530/1978 e Decreto 81.871/1978 — regulamentam a profissão de corretor de imóveis',
          'Resolução COFECI 458/1995 e Código de Ética — deveres do corretor e do contrato escrito',
        ]},
        { callout: 'O art. 726 do Código Civil é o coração da exclusividade: com ele, a comissão é devida em qualquer venda durante a vigência — inclusive se o próprio dono vender por fora. Sem cláusula de exclusividade, o corretor só recebe se for a causa efetiva do negócio.', calloutTitulo: 'Por que a exclusividade protege o corretor' },

        { h2: 'Cláusulas essenciais do contrato' },
        { lista: [
          'Qualificação completa das partes (contratante e contratado/CRECI)',
          'Identificação do imóvel (endereço, matrícula, cartório, área, confrontações)',
          'Objeto e regime de exclusividade',
          'Prazo de vigência (determinado, com data inicial e final)',
          'Valor anunciado e percentual de comissão (art. 724 do CC)',
          'Cláusula de comissão devida em qualquer venda durante a vigência (art. 726)',
          'Cláusula penal por quebra de exclusividade',
          'Autorização de publicidade e captação',
          'Foro de eleição e disposições gerais',
        ]},

        { h3: 'Prazo: determinado é o ideal' },
        { p: 'O prazo determinado (por exemplo, 90 ou 180 dias a partir de uma data) é o mais seguro juridicamente. Evite prazo indeterminado: ele enfraquece a cláusula penal e dificulta comprovar a vigência em eventual disputa. Renove formalmente quando necessário.' },

        { h3: 'Comissão: deixe o percentual explícito' },
        { p: 'Registre o percentual (ex.: 5% ou 6% sobre o valor da venda) e deixe claro que a comissão é devida em qualquer venda realizada durante a vigência, conforme o art. 726. Em imóveis com saldo devedor (financiamento/alienação fiduciária), inclua cláusula prevendo que a comissão incide sobre o valor total da operação.' },

        { h2: 'Por que somar uma procuração ao contrato?' },
        { p: 'Uma procuração particular, limitada ao imóvel, autoriza o corretor a praticar atos necessários à venda sem precisar do vendedor a cada etapa:' },
        { lista: [
          'Obter certidões (negativas, ônus, ações reais e pessoais reipersecutórias)',
          'Solicitar segunda via de IPTU e a certidão de regularidade fiscal do imóvel',
          'Pedir o extrato de saldo devedor junto ao banco (imóvel financiado)',
          'Requerer documentos no cartório de registro de imóveis',
          'Reunir a documentação para a escritura e o financiamento do comprador',
        ]},
        { p: 'A procuração deve ser limitada à matrícula do imóvel, com poderes específicos e vigência vinculada ao contrato. Reconhecimento de firma é recomendável para atos perante cartórios e bancos (art. 654, §2º, do CC).' },

        { h2: 'Como o AvalieImob gera o contrato e a procuração' },
        { p: 'No módulo de Contratos do AvalieImob, você gera o contrato de exclusividade em um passo a passo guiado: qualifica as partes, identifica o imóvel (com ficha completa, fotos e documentos como anexos), define prazo e comissão, e o sistema redige as cláusulas — inclusive ajustando a ênfase com IA. A procuração particular é gerada junto, no mesmo padrão visual.' },
        { lista: [
          'Cláusulas prontas e editáveis, com aperfeiçoamento por IA',
          'Anexos de fotos e documentos do imóvel',
          'Mapa e coordenadas do imóvel no contrato',
          'Cartão e certidão de regularidade do corretor (CRECI) como anexos',
          'Assinatura eletrônica do cliente por link no WhatsApp e assinatura ICP-Brasil do corretor',
        ]},
        { cta: 'Gere contratos de exclusividade com procuração e assine digitalmente. Teste 7 dias grátis.', ctaTexto: 'Começar grátis →' },

        { h2: 'Conclusão' },
        { p: 'O contrato de exclusividade, ancorado no art. 726 do Código Civil, é o que garante a remuneração do corretor e profissionaliza a captação. Somado a uma procuração limitada ao imóvel, ele dá autonomia para reunir a documentação e fechar negócios com segurança. O segredo está em formalizar por escrito, com prazo determinado, comissão explícita e assinatura — algo que hoje se faz em minutos, de forma digital.' },
      ]}
      servicosRelacionados={[
        { slug: 'ptam', titulo: 'PTAM — Parecer Técnico de Avaliação Mercadológica' },
        { slug: 'avaliacao-urbana', titulo: 'Avaliação de Imóveis Urbanos' },
      ]}
      postsRelacionados={relacionados}
    />
  );
}
