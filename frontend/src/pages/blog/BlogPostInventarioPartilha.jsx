import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getPostBySlug, getRelatedPosts } from '../../data/blogPosts';

const SLUG = 'avaliacao-imovel-inventario-partilha';

export default function BlogPostInventarioPartilha() {
  const post = getPostBySlug(SLUG);
  const relacionados = getRelatedPosts(SLUG);

  return (
    <BlogPostTemplate
      slug={SLUG}
      titulo={post.titulo}
      subtitulo="Como avaliar imóveis em inventário, partilha de divórcio e dissolução de sociedade — exigências legais, peso jurídico e custos."
      meta={post.meta}
      palavrasChave="avaliacao imovel inventario, avaliacao imovel partilha, divorcio avaliacao imovel, dissolucao sociedade avaliacao, perito judicial avaliacao, laudo inventario, NBR 14.653 partilha"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { p: 'Avaliar imóveis em processos de inventário, partilha por divórcio ou dissolução de sociedade é uma das demandas mais frequentes — e mais delicadas — da rotina do avaliador imobiliário. Diferente de uma avaliação comum, esses laudos vão parar nas mãos de juízes, advogados e às vezes peritos contrários, então o nível de rigor técnico precisa ser máximo.' },
        { p: 'Neste artigo vou explicar exatamente o que muda quando o laudo é destinado a inventário ou partilha, quais cuidados específicos tomar, qual grau de fundamentação adotar e como negociar honorários nesse tipo de trabalho.' },

        { h2: 'Quando a avaliação é necessária' },
        { p: 'Em qualquer processo onde haja divisão de patrimônio imobiliário entre 2 ou mais partes, é exigida avaliação técnica. Os 4 cenários mais comuns:' },

        { h3: '1. Inventário (sucessão)' },
        { p: 'Quando alguém falece, os bens precisam ser inventariados e divididos entre herdeiros. Pode ser:' },
        { lista: [
          'Inventário judicial: corre na Vara de Sucessões. Avaliação obrigatória, geralmente feita por perito judicial nomeado pelo juiz.',
          'Inventário extrajudicial: feito em cartório (Lei 11.441/2007). Mais rápido, mais barato, mas exige acordo entre todos os herdeiros e nenhum incapaz envolvido. Avaliação contratada pelas partes.',
          'Arrolamento: variação simplificada do inventário judicial pra patrimônios menores.',
        ]},

        { h3: '2. Partilha por divórcio' },
        { p: 'Quando o casal se separa e há bens em comum (especialmente imóveis), é preciso definir o valor de cada bem pra fazer a divisão. Pode ser:' },
        { lista: [
          'Divórcio consensual: ambos concordam com a partilha. Avaliação contratada em comum acordo.',
          'Divórcio litigioso: há disputa. Cada parte pode contratar seu próprio avaliador (assistente técnico) ou aguardar perito judicial nomeado pelo juiz.',
        ]},

        { h3: '3. Dissolução de sociedade' },
        { p: 'Quando sócios decidem encerrar uma empresa que possui imóveis, é necessário avaliar todos os bens pra calcular a quota de cada sócio. Comum em:' },
        { lista: [
          'Sociedades limitadas com imóveis no ativo',
          'Sociedade conjugal (regime de bens com comunhão)',
          'União estável dissolvida',
        ]},

        { h3: '4. Ações de adjudicação compulsória / divisão' },
        { p: 'Quando um imóvel pertence a múltiplos proprietários (condomínio voluntário) e um deles quer sair, pode pedir a venda judicial e divisão do produto. Exige avaliação prévia.' },

        { h2: 'Particularidades do laudo pra esses contextos' },

        { h3: 'Documentação ampliada' },
        { p: 'Diferente de uma avaliação comum, em inventário/partilha você precisa de mais documentos:' },
        { lista: [
          'Matrícula atualizada (emitida nos últimos 30 dias)',
          'Cópia da escritura ou contrato de compra e venda',
          'IPTU atualizado dos últimos 3 anos',
          'Registro de averbações e penhoras',
          'Ônus reais existentes (hipotecas, alienação fiduciária)',
          'Documentos do casal/sócios envolvidos',
          'Cópia da inicial da ação (se judicial)',
        ]},

        { h3: 'Vistoria presencial obrigatória' },
        { p: 'Em laudos pra inventário/partilha, a vistoria presencial é obrigatória. Não dá pra fazer baseado só em fotos do cliente. O avaliador precisa:' },
        { lista: [
          'Ir ao imóvel pessoalmente',
          'Documentar com fotos georreferenciadas (data, hora, GPS)',
          'Medir áreas com trena ou medidor a laser',
          'Conferir características declaradas vs. realidade',
          'Identificar qualquer fator de valorização ou depreciação',
        ]},
        { callout: 'Em ações litigiosas, a parte contrária frequentemente questiona a vistoria. Documentação fotográfica completa é sua proteção contra impugnações.', calloutTitulo: 'Importante' },

        { h3: 'Grau de Fundamentação mínimo: II' },
        { p: 'Em laudos pra inventário/partilha, busque sempre Grau II ou III de fundamentação. Grau I é praticamente proibido — pode ser invalidado pelo juiz.' },
        { lista: [
          'Pesquisa de mercado com 8+ amostras de qualidade',
          'Tratamento estatístico completo (média, IC, saneamento)',
          'Documentação de todas as fontes',
          'Justificativa técnica para escolhas metodológicas',
        ]},

        { h2: 'Quem está habilitado a fazer esses laudos' },

        { h3: 'Em inventário extrajudicial' },
        { lista: [
          'Engenheiros civis (com ART)',
          'Arquitetos (com RRT)',
          'Corretores credenciados (Resolução COFECI 1.066/2007)',
          'Engenheiros agrônomos (rurais)',
        ]},

        { h3: 'Em ação judicial — perícia oficial' },
        { p: 'Apenas o perito **nomeado pelo juiz** faz a perícia oficial. Geralmente:' },
        { lista: [
          'Engenheiro civil (mais comum em urbano)',
          'Engenheiro agrônomo (rural)',
          'Em raras ocasiões, arquitetos',
        ]},

        { h3: 'Em ação judicial — assistente técnico' },
        { p: 'Cada parte pode contratar seu próprio avaliador (assistente técnico) pra fiscalizar/contestar a perícia oficial. Atribuições:' },
        { lista: [
          'Acompanhar a vistoria do perito oficial',
          'Apresentar laudo divergente se discordar',
          'Formular quesitos pro perito oficial responder',
          'Apresentar parecer técnico contra-laudo',
        ]},
        { callout: 'Ser assistente técnico é uma especialidade lucrativa. Honorários costumam ser 50-70% do que recebe o perito oficial, mas com menos exposição ao juiz.', calloutTitulo: 'Oportunidade' },

        { h2: 'Como precificar o serviço' },
        { p: 'A precificação varia conforme:' },
        { lista: [
          'Valor estimado do imóvel',
          'Complexidade da avaliação (urbano simples vs. rural com benfeitorias)',
          'Distância para vistoria',
          'Prazo exigido',
          'Tipo de processo (consensual, litigioso, judicial)',
        ]},

        { h3: 'Tabelas de referência' },
        { p: 'Para avaliações de imóveis até R$ 1 milhão:' },
        { lista: [
          'Imóvel residencial urbano comum: R$ 800 a R$ 2.500',
          'Imóvel comercial / sala comercial: R$ 1.200 a R$ 3.500',
          'Imóvel rural pequeno (até 100 ha): R$ 2.000 a R$ 6.000',
          'Imóvel rural médio/grande: R$ 5.000 a R$ 25.000',
          'Perícia judicial completa: 1% a 3% do valor do imóvel (limitado pela tabela do juiz)',
        ]},

        { h2: 'Cuidados especiais em divórcio litigioso' },
        { p: 'Divórcio litigioso é um dos contextos mais complicados. Cuidados extras:' },
        { lista: [
          'Manter neutralidade total — nunca tomar partido',
          'Vistoriar com ambas as partes presentes (ou avisos formais documentados)',
          'Não aceitar informações verbais — só documentos oficiais',
          'Cuidado com tentativas de manipulação (fotos selecionadas, valores informados sem fonte)',
          'Documentar TUDO por escrito',
          'Ter ART/RRT vigente — sem isso o laudo pode ser invalidado',
        ]},

        { h2: 'Validade temporal do laudo' },
        { p: 'Laudos de avaliação não são eternos. Atenção aos prazos:' },
        { lista: [
          'Inventário extrajudicial: laudo válido por 6 meses (alguns cartórios aceitam até 12 meses)',
          'Inventário judicial: depende da fase processual — pode ser exigida atualização',
          'Divórcio: válido enquanto não houver mudança significativa no mercado',
          'Em inflações altas: válidade pode cair pra 3 meses',
        ]},

        { h2: 'Erros que podem invalidar o laudo' },
        { lista: [
          'Não emitir ART/RRT (engenheiros e arquitetos)',
          'Avaliar imóvel sem vistoria presencial',
          'Pesquisa de mercado insuficiente (menos de 5 amostras)',
          'Misturar avaliação de bens distintos em laudo único sem separar valores',
          'Não considerar ônus reais (hipoteca, alienação fiduciária)',
          'Não atualizar matrícula',
          'Conflito de interesses (avaliar imóvel de cliente recorrente em ação litigiosa)',
        ]},

        { h2: 'Como o AvalieImob facilita esses laudos' },
        { p: 'O sistema é otimizado especificamente pra laudos jurídicos:' },
        { lista: [
          'Templates específicos pra inventário, partilha, dissolução de sociedade',
          'Wizard guiado com todos os campos obrigatórios da NBR 14.653',
          'Cálculo automático de Grau de Fundamentação e Precisão',
          'Geração da planilha de homogeneização anexa ao laudo',
          'Exportação DOCX/PDF profissional pronto pra entregar ao advogado',
          'Espaço pra ART/RRT, número do processo, juízo e partes envolvidas',
          'IA especializada que sugere fundamentação técnica conforme a finalidade',
        ]},
        { cta: 'Teste o sistema completo do AvalieImob por 7 dias grátis.', ctaTexto: 'Começar grátis →' },

        { h2: 'Conclusão' },
        { p: 'Avaliação pra inventário e partilha exige mais rigor técnico que avaliação comum, porque o laudo será analisado por advogados, juízes e (em ações litigiosas) por peritos contrários. Sempre opte por Grau II ou III de fundamentação, nunca Grau I.' },
        { p: 'É um nicho de alta demanda e bem remunerado. Avaliadores que dominam essa especialidade — entendendo as exigências do CPC, da NBR 14.653 e da praxe forense local — conseguem honorários consistentemente acima da média e ainda criam relacionamento sólido com escritórios de advocacia, que se tornam fonte recorrente de trabalho.' },
      ]}
      servicosRelacionados={[
        { slug: 'ptam', titulo: 'PTAM — Parecer Técnico de Avaliação Mercadológica' },
        { slug: 'avaliacao-urbana', titulo: 'Avaliação de Imóveis Urbanos' },
        { slug: 'avaliacao-rural', titulo: 'Avaliação de Imóveis Rurais' },
      ]}
      postsRelacionados={relacionados}
    />
  );
}
