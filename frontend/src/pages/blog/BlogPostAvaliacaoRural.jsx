import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getPostBySlug, getRelatedPosts } from '../../data/blogPosts';

const SLUG = 'avaliacao-imovel-rural-nbr-14653-3-guia-completo';

export default function BlogPostAvaliacaoRural() {
  const post = getPostBySlug(SLUG);
  const relacionados = getRelatedPosts(SLUG);

  return (
    <BlogPostTemplate
      slug={SLUG}
      titulo={post.titulo}
      subtitulo="Da terra nua às benfeitorias, semoventes e safras — tudo que o avaliador rural precisa saber para emitir laudos profissionais conforme NBR 14.653-3."
      meta={post.meta}
      palavrasChave="avaliação imóvel rural, NBR 14.653-3, avaliação fazenda, terra nua, penhor rural, avaliação semoventes, Pronaf, Pronamp, perícia rural, laudo agropecuário"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { p: 'A avaliação de imóveis rurais é uma das especialidades mais técnicas e mais lucrativas da avaliação imobiliária. Diferente da avaliação urbana — que envolve principalmente metragem e padrão construtivo — a rural exige conhecimento integrado de agronomia, edificações, zootecnia e legislação ambiental. O avaliador rural precisa saber valorar desde uma área de pastagem degradada até um plantel de gado de corte ou uma safra pendente.' },
        { p: 'Neste guia completo, você vai aprender exatamente como funciona a avaliação rural conforme a NBR 14.653-3 da ABNT, os componentes obrigatórios de um laudo rural, particularidades do penhor rural para crédito (Pronaf, Pronamp, custeio) e como o AvalieImob facilita esse processo.' },

        { h2: 'O que é NBR 14.653-3?' },
        { p: 'A NBR 14.653 é dividida em 7 partes. A parte 3 trata especificamente da Avaliação de Imóveis Rurais e estabelece a metodologia técnica obrigatória para avaliar:' },
        { lista: [
          'Terras nuas (com diferentes capacidades de uso do solo)',
          'Benfeitorias produtivas (casa-sede, currais, galpões, silos, açudes)',
          'Benfeitorias reprodutivas (irrigação, terraços, drenagens, calagem, correção do solo)',
          'Culturas perenes (cafezais, pomares, reflorestamentos)',
          'Culturas anuais e safras pendentes (soja, milho, algodão, cana)',
          'Semoventes (gado bovino, equino, ovino, caprino, suíno)',
          'Equipamentos agrícolas e pecuários (tratores, colheitadeiras, ordenhadeiras)',
          'Recursos hídricos e direitos minerários',
        ]},
        { p: 'É a referência técnica obrigatória para qualquer laudo de avaliação rural com peso jurídico — perícias judiciais, garantias bancárias, indenizações, partilhas e levantamentos patrimoniais.' },

        { h2: 'Componentes obrigatórios de um laudo rural' },

        { h3: '1. Identificação da propriedade rural' },
        { p: 'Diferente do urbano, a identificação rural envolve diversos cadastros que precisam estar atualizados:' },
        { lista: [
          'CCIR (Certificado de Cadastro de Imóvel Rural) — emitido pelo INCRA, identifica o imóvel rural na União',
          'CAR (Cadastro Ambiental Rural) — exigência do Código Florestal (Lei 12.651/2012), declara reserva legal e APP',
          'NIRF/CIB (Número do Imóvel na Receita Federal) — vinculado ao ITR (Imposto Territorial Rural)',
          'Matrícula no cartório de registro de imóveis',
          'Memoriais descritivos (especialmente em propriedades georreferenciadas pelo SIGEF)',
          'Módulos fiscais (varia por município — base para classificação de pequena, média ou grande propriedade)',
        ]},

        { h3: '2. Avaliação da terra nua' },
        { p: 'A terra nua (sem benfeitorias) é avaliada conforme sua capacidade de uso. A NBR 14.653-3 prevê classes de capacidade que vão de I (ótimo para qualquer uso) até VIII (preservação obrigatória):' },
        { lista: [
          'Classe I-IV: terras agricultáveis (lavouras anuais e perenes)',
          'Classe V-VI: terras com restrições (pastagem natural, silvicultura)',
          'Classe VII-VIII: preservação obrigatória, baixo valor econômico direto',
        ]},
        { p: 'Para calcular o valor por hectare, usa-se principalmente o método comparativo (com base em transações regionais) ou o método da capitalização da renda (para propriedades produtivas com fluxo de caixa estabelecido). O AvalieImob mantém base de dados regional de preços por estado para subsidiar a pesquisa.' },

        { h3: '3. Avaliação de benfeitorias' },
        { p: 'Benfeitorias rurais incluem todas as construções e melhorias incorporadas à propriedade. Avalia-se cada uma pelo método de custo de reprodução (quanto custaria refazer) descontando a depreciação física e funcional. Os principais tipos:' },
        { lista: [
          'Casa-sede e residências de funcionários',
          'Galpões (de máquinas, de ração, de armazenagem de grãos)',
          'Currais, mangueiras, bretes, troncos de contenção',
          'Silos verticais e horizontais',
          'Açudes, barragens, canais de irrigação',
          'Cercas (arame liso, arame farpado, cerca elétrica)',
          'Estradas internas, pontes, mata-burros',
          'Pivôs centrais de irrigação, sistemas de gotejamento',
        ]},
        { callout: 'Para benfeitorias antigas, use o método Ross-Heidecke para calcular depreciação combinando idade e estado de conservação. É o método aceito pela NBR 14.653-3.', calloutTitulo: 'Cálculo de depreciação' },

        { h3: '4. Avaliação de semoventes (rebanhos)' },
        { p: 'Semoventes são avaliados por categoria animal e função zootécnica. Cada categoria tem um valor de mercado específico que varia por região, raça e momento do ciclo produtivo:' },
        { lista: [
          'Bovinos: vacas em lactação, vacas paridas, bezerros, garrotes, novilhas, touros reprodutores',
          'Equinos: matrizes, garanhões, animais de serviço',
          'Suínos: matrizes, leitões, terminação, varrões',
          'Ovinos/Caprinos: matrizes, borregos, reprodutores',
        ]},
        { p: 'A avaliação de semoventes é especialmente importante para penhor rural pecuário, em que os animais são dados como garantia de operação de crédito. O laudo precisa identificar individualmente cada animal (brincos, marcas, idade) para evitar fraudes.' },

        { h3: '5. Avaliação de safras e culturas' },
        { p: 'Safras pendentes (ainda no campo) são avaliadas pela produção esperada, descontando custos remanescentes até a colheita. Use:' },
        { lista: [
          'Produtividade esperada (em sacas/ha ou ton/ha) baseada em históricos da propriedade ou regional',
          'Preço atual de mercado da commodity (CONAB, B3, cooperativa local)',
          'Estimativa de custos remanescentes (colheita, transporte, secagem)',
          'Estágio fenológico atual (germinação, vegetativo, reprodutivo)',
        ]},

        { h3: '6. Avaliação de equipamentos' },
        { p: 'Tratores, colheitadeiras, plantadeiras, pulverizadores e demais equipamentos são avaliados pelo método comparativo (com base em tabelas como FIPE Caminhões, AGRIANUAL, CESPE) ou pelo custo de reposição depreciado. Idade e estado de conservação são fatores críticos.' },

        { h2: 'Particularidades do penhor rural (Pronaf, Pronamp, custeio)' },
        { p: 'O penhor rural é uma garantia real específica do crédito rural brasileiro, prevista no Decreto-Lei 167/1967 e modernizado pela Lei 13.986/2020 (CPR — Cédula de Produto Rural). Bancos e cooperativas exigem laudos específicos para conceder crédito com penhor rural.' },

        { h3: 'Tipos de penhor rural mais comuns' },
        { lista: [
          'Penhor agrícola: máquinas, implementos, frutos pendentes, sementes',
          'Penhor pecuário: animais (bovinos, suínos, equinos, ovinos)',
          'Penhor mercantil rural: produtos beneficiados/armazenados',
          'Penhor de safras futuras: produção projetada (CPR financeira)',
        ]},

        { h3: 'Bancos que mais financiam crédito rural com penhor' },
        { lista: [
          'Banco do Brasil — maior agente do crédito rural no Brasil, exige laudo conforme padrão BB',
          'Sicredi — sistema cooperativo, com formato próprio de laudo',
          'Banco do Nordeste (BNB) — atua principalmente no Norte/Nordeste com FNE',
          'BASA — atua na Amazônia Legal com FNO',
          'Sicoob, Cresol, Unicred — outras cooperativas com modelo similar',
        ]},
        { p: 'O AvalieImob possui modelos específicos compatíveis com cada banco/cooperativa, com todos os campos obrigatórios já configurados.' },

        { h2: 'Erros comuns na avaliação rural' },
        { lista: [
          'Não conferir o CCIR e CAR — laudo com cadastros desatualizados pode ser invalidado',
          'Avaliar a propriedade com base apenas em áreas declaradas (sem georreferenciamento ou medição independente)',
          'Esquecer de descontar áreas de Reserva Legal e APP (Áreas de Preservação Permanente) do valor agricultável',
          'Não atualizar preços de commodities (use sempre cotação atual da CONAB ou cooperativa local)',
          'Misturar avaliação de terra nua com benfeitorias em uma única estimativa global (devem ser separadas)',
          'Não emitir ART (engenheiros agrônomos) ou RRT (arquitetos) — laudo sem responsabilidade técnica tem peso reduzido',
        ]},

        { h2: 'Perícia rural: ações judiciais comuns' },
        { p: 'Avaliadores rurais experientes podem atuar como peritos judiciais ou assistentes técnicos em diversas ações:' },
        { lista: [
          'Desapropriação por interesse social (reforma agrária via INCRA)',
          'Desapropriação por utilidade pública (rodovias, ferrovias, hidrelétricas)',
          'Indenização por servidão administrativa (linhas de transmissão, dutos)',
          'Partilha de bens em sucessão (inventário rural)',
          'Divisão e demarcação de propriedades',
          'Ações possessórias (esbulho, turbação, manutenção de posse)',
          'Indenização por danos ambientais',
        ]},

        { h2: 'Como o AvalieImob acelera a avaliação rural' },
        { p: 'A avaliação rural manual é um processo extremamente demorado — pode levar de 8 a 40 horas dependendo da complexidade da propriedade. O AvalieImob reduz drasticamente esse tempo:' },
        { lista: [
          'Wizard específico para imóveis rurais cobrindo todos os componentes (terra, benfeitorias, semoventes, safras, equipamentos)',
          'Banco de dados regional de preços de terra nua por estado e classe de capacidade',
          'Cálculo automático de depreciação Ross-Heidecke para benfeitorias',
          'Categorias zootécnicas pré-cadastradas para avaliação de semoventes',
          'Modelos específicos para BB, Caixa, Sicredi, BNB, BASA — penhor rural pronto',
          'Memorial fotográfico organizado por benfeitoria e talhão com geolocalização',
          'IA agropecuária especializada que conhece particularidades de cada bioma',
        ]},
        { cta: 'Teste o módulo de Avaliação Rural do AvalieImob por 7 dias grátis.', ctaTexto: 'Começar grátis →' },

        { h2: 'Conclusão' },
        { p: 'A avaliação de imóveis rurais é uma especialidade técnica que exige domínio integrado de várias áreas — agronomia, edificações rurais, zootecnia e legislação ambiental e fundiária. A NBR 14.653-3 padroniza esse processo em componentes obrigatórios: terra nua, benfeitorias, semoventes, safras e equipamentos.' },
        { p: 'Para avaliadores que dominam a área, há demanda crescente especialmente para penhor rural (com explosão do agronegócio brasileiro) e perícias judiciais (desapropriações, ações possessórias). Investir em ferramentas adequadas e estudar a NBR 14.653-3 a fundo é o caminho para se diferenciar no mercado.' },
      ]}
      servicosRelacionados={[
        { slug: 'avaliacao-rural', titulo: 'Avaliação de Imóveis Rurais — NBR 14.653-3' },
        { slug: 'avaliacao-garantia', titulo: 'Avaliação de Garantias Bancárias' },
        { slug: 'ptam', titulo: 'PTAM — Parecer Técnico de Avaliação Mercadológica' },
      ]}
      postsRelacionados={relacionados}
    />
  );
}
