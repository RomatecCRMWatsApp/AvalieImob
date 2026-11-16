import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getPostBySlug, getRelatedPosts } from '../../data/blogPosts';

const SLUG = 'como-emitir-art-rrt-trt-avaliacao-imobiliaria';

export default function BlogPostART_RRT_TRT() {
  const post = getPostBySlug(SLUG);
  const relacionados = getRelatedPosts(SLUG);

  return (
    <BlogPostTemplate
      slug={SLUG}
      titulo={post.titulo}
      subtitulo="Guia completo: ART no CREA (engenheiros), RRT no CAU (arquitetos) e TRT no CFT (técnicos). Quando emitir, valores, prazos e consequências de não emitir."
      meta={post.meta}
      palavrasChave="emitir ART avaliacao, ART CREA, RRT CAU, TRT CFT, ART online, RRT online, TRT online, ART de avaliacao imobiliaria, responsabilidade tecnica avaliador, avaliador credenciado"
      dataPublicacao={post.dataPublicacao}
      dataAtualizacao={post.dataAtualizacao}
      tempoLeitura={post.tempoLeitura}
      categoria={post.categoria}
      resumo={post.resumo}
      conteudo={[
        { p: 'Emitir o documento de Responsabilidade Técnica é uma etapa obrigatória — e às vezes negligenciada — em quase todos os laudos de avaliação imobiliária com peso jurídico. Engenheiros emitem ART no CREA, arquitetos emitem RRT no CAU e técnicos em agrimensura emitem TRT no CFT. Cada um tem seu fluxo, seus valores e suas particularidades.' },
        { p: 'Neste guia completo vou explicar exatamente quando você precisa emitir cada documento, como fazer passo a passo em cada conselho, qual o custo e o que acontece se o laudo não tiver o registro de responsabilidade.' },

        { h2: 'O que é responsabilidade técnica?' },
        { p: 'Responsabilidade técnica é o documento oficial onde o profissional declara, ao seu conselho de classe, que assume a responsabilidade legal e técnica por um trabalho. Em caso de erro, falha ou má-fé, esse documento é a base pra que o cliente, o juiz ou o conselho profissional possam acionar o profissional.' },
        { p: 'Em laudos de avaliação imobiliária, a responsabilidade técnica:' },
        { lista: [
          'Garante que o profissional é habilitado a fazer aquele trabalho',
          'Cria base legal pra responsabilização em caso de erro',
          'Permite que o conselho rastreie quem faz o quê (estatísticas, fiscalização)',
          'Aumenta o peso jurídico do laudo (sem ART/RRT/TRT, o laudo pode ser questionado)',
        ]},

        { h2: 'ART — Anotação de Responsabilidade Técnica (CREA)' },
        { p: 'Aplicável a: **engenheiros civis, agrônomos, florestais, eletricistas e demais engenharias**. Emitida no CREA (Conselho Regional de Engenharia e Agronomia) do estado onde o profissional é registrado.' },

        { h3: 'Quando emitir ART de avaliação' },
        { p: 'Você deve emitir ART em todos os laudos de avaliação com finalidade técnica/jurídica/bancária:' },
        { lista: [
          'PTAM (Parecer Técnico de Avaliação Mercadológica)',
          'Laudo Técnico de Avaliação Imobiliária',
          'Avaliação de Garantias Bancárias',
          'Avaliação de Imóveis Rurais (NBR 14.653-3)',
          'Perícias judiciais',
          'Avaliação de imóveis para inventário/partilha',
          'Avaliação para desapropriação',
        ]},
        { p: 'Não precisa emitir ART em:' },
        { lista: [
          'Consultas verbais informais ao cliente',
          'Pesquisas de mercado simples (sem laudo formal)',
          'Estudo de viabilidade preliminar (até virar laudo)',
        ]},

        { h3: 'Como emitir ART no CREA passo a passo' },
        { listaOrd: [
          'Acesse o portal do CREA do seu estado (ex: CREA-MA, CREA-SP, CREA-RJ)',
          'Faça login com seu usuário e senha (geralmente o mesmo do registro profissional)',
          'No menu, procure "ART" ou "Anotação de Responsabilidade Técnica"',
          'Clique em "Emitir nova ART"',
          'Selecione o tipo: "Múltipla Mensal" (se você emite várias por mês) ou "Comum" (única)',
          'Preencha os campos: contratante (nome, CPF/CNPJ), endereço da obra/imóvel, descrição da atividade, valor do contrato',
          'Selecione a atividade no catálogo do CONFEA: "62.06 - Avaliação de bens" ou similar',
          'Confirma os dados, gera boleto, paga',
          'Após pagamento confirmado (geralmente 1-2 dias), a ART fica disponível pra download em PDF',
          'Anexa o PDF da ART ao laudo final',
        ]},

        { h3: 'Custo da ART (referência 2026)' },
        { lista: [
          'ART Comum (única): R$ 100 a R$ 240 (varia por estado e por valor do contrato)',
          'ART Múltipla Mensal: R$ 100 a R$ 200/mês (cobre múltiplas avaliações no mês)',
          'ART de cargo/função (anual): R$ 200 a R$ 400/ano',
        ]},
        { callout: 'Se você emite mais de 5-8 ARTs por mês, vale muito a pena migrar pra ART Múltipla — paga uma só vez no mês e cobre todas as avaliações daquele mês.', calloutTitulo: 'Dica financeira' },

        { h2: 'RRT — Registro de Responsabilidade Técnica (CAU)' },
        { p: 'Aplicável a: **arquitetos e urbanistas**. Emitido no CAU (Conselho de Arquitetura e Urbanismo) — o sistema é nacional, único pra todos os estados.' },

        { h3: 'Quando emitir RRT' },
        { p: 'Mesmas situações que ART, sempre que o arquiteto fizer:' },
        { lista: [
          'Avaliação imobiliária (urbana ou rural)',
          'Perícias judiciais',
          'Laudos técnicos formais',
        ]},

        { h3: 'Como emitir RRT no CAU passo a passo' },
        { listaOrd: [
          'Acesse o SICCAU (Sistema de Informação e Comunicação do CAU): https://siccau.caubr.gov.br/',
          'Faça login com CPF e senha',
          'Menu lateral → "RRT"',
          'Clique em "Preencher RRT"',
          'Selecione o tipo: "Simples" (uma atividade) ou "Múltiplo Mensal"',
          'Preencha: contratante, descrição da atividade, valor do contrato, endereço',
          'Selecione a atividade: "Avaliação imobiliária" ou "Laudo de avaliação"',
          'Gera boleto, paga (compensação 1-2 dias úteis)',
          'Faz download do PDF da RRT após pagamento confirmado',
          'Anexa ao laudo',
        ]},

        { h3: 'Custo da RRT (referência 2026)' },
        { lista: [
          'RRT Simples: R$ 95 a R$ 175 (varia conforme valor do contrato)',
          'RRT Múltiplo Mensal: R$ 88/mês (preço fixo nacional)',
          'RRT Cargo/Função: anual, valores variáveis',
        ]},

        { h2: 'TRT — Termo de Responsabilidade Técnica (CFT)' },
        { p: 'Aplicável a: **técnicos em agrimensura, edificações, geomensura, mineração e demais técnicos industriais**. Emitido no CFT (Conselho Federal dos Técnicos Industriais) — sistema nacional, mas registro pelos CRTs estaduais.' },

        { h3: 'Quando emitir TRT' },
        { p: 'Técnicos em agrimensura podem emitir TRT pra:' },
        { lista: [
          'Avaliação de imóveis rurais (mais comum pra técnicos em agrimensura)',
          'Levantamentos topográficos',
          'Georreferenciamento de imóveis rurais (SIGEF/INCRA)',
          'Avaliação de imóveis urbanos (dentro das atribuições do técnico)',
        ]},
        { callout: 'Atenção: técnicos têm atribuições mais restritas que engenheiros. Avaliações de grande porte (acima de 1.000 ha rural ou imóveis urbanos comerciais grandes) geralmente exigem engenheiro. Consulte sempre a Resolução CFT que define atribuições específicas.', calloutTitulo: 'Limite de atribuições' },

        { h3: 'Como emitir TRT no CFT passo a passo' },
        { listaOrd: [
          'Acesse o portal do CFT: https://cft.org.br/',
          'Faça login com CPF e senha (acesso via SisCFT)',
          'Menu → "TRT" ou "Termos"',
          'Clique em "Emitir novo TRT"',
          'Selecione o tipo: "Simples" ou "Mensal" (múltiplo)',
          'Preencha contratante, descrição, valor, atividade',
          'Confirme atividade no catálogo CFT (avaliação de bens imóveis)',
          'Gera boleto, paga, aguarda compensação',
          'Faz download do PDF',
        ]},

        { h3: 'Custo do TRT (referência 2026)' },
        { lista: [
          'TRT Simples: R$ 65 a R$ 130',
          'TRT Mensal Múltiplo: R$ 60 a R$ 100/mês',
        ]},

        { h2: 'Comparativo entre ART, RRT e TRT' },
        { lista: [
          'ART (CREA): para engenheiros — abrange todas as engenharias e agronomia',
          'RRT (CAU): para arquitetos — sistema nacional unificado, valores ligeiramente menores que ART',
          'TRT (CFT): para técnicos industriais e em agrimensura — atribuições mais restritas, valores menores',
        ]},

        { h2: 'O que acontece se você não emitir' },
        { p: 'Trabalhar sem emitir o documento de responsabilidade técnica gera consequências sérias:' },

        { h3: '1. Multa do conselho profissional' },
        { p: 'CREA, CAU e CFT fiscalizam. Se descobrirem laudo sem ART/RRT/TRT, multa pode ser de R$ 500 a R$ 10.000 por ocorrência.' },

        { h3: '2. Suspensão do registro profissional' },
        { p: 'Reincidência pode levar à suspensão temporária ou cancelamento do registro — você fica impedido de trabalhar legalmente.' },

        { h3: '3. Laudo invalidado em juízo' },
        { p: 'Em ações judiciais, advogados da parte contrária frequentemente questionam laudos sem responsabilidade técnica registrada. O juiz pode invalidar o documento, e você perde o trabalho.' },

        { h3: '4. Responsabilização civil pessoal' },
        { p: 'Sem ART/RRT/TRT, em caso de erro técnico que cause prejuízo ao cliente, você responde pessoalmente em ação civil — sem proteção do conselho.' },

        { h2: 'Erros comuns ao emitir' },
        { lista: [
          'Esquecer de mencionar a finalidade específica do laudo (ex: "avaliação para inventário judicial Processo nº...")',
          'Não anotar o número correto da NBR aplicada (14.653-1, 14.653-2 ou 14.653-3)',
          'Endereço incompleto do imóvel',
          'Valor do contrato menor que o real (gera multa do conselho)',
          'Atividade selecionada errada no catálogo (ex: marcar "projeto" em vez de "avaliação")',
          'Não pagar boleto antes do prazo — ART/RRT/TRT vence se não pago',
          'Anexar ao laudo um PDF rasurado/cortado da ART',
        ]},

        { h2: 'Boas práticas' },
        { lista: [
          'Emite ART/RRT/TRT ANTES de iniciar o trabalho, não depois',
          'Use modalidade Múltipla Mensal se você faz mais de 5 avaliações/mês',
          'Mantenha cópia digital de TODAS as ARTs/RRTs/TRTs por no mínimo 5 anos',
          'Inclua o número da ART/RRT/TRT no rodapé do laudo, em todas as páginas',
          'Mantenha anuidade do conselho em dia — sem isso você não consegue emitir',
          'Atualize seu registro profissional anualmente (algumas atribuições caducam)',
        ]},

        { h2: 'Como o AvalieImob facilita esse fluxo' },
        { p: 'No AvalieImob você gerencia ART/RRT/TRT junto com o laudo:' },
        { lista: [
          'Campos específicos pra ART (CREA), RRT (CAU) ou TRT (CFT) no cabeçalho do laudo',
          'Numeração automática registrada no documento',
          'Upload do PDF da ART/RRT/TRT junto ao laudo final',
          'Histórico de todas as responsabilidades técnicas emitidas pelo profissional',
          'Lembrete de renovação anual da anuidade do conselho',
          'Templates específicos por categoria profissional (engenheiro, arquiteto, técnico)',
        ]},
        { cta: 'Teste o sistema completo do AvalieImob por 7 dias grátis.', ctaTexto: 'Começar grátis →' },

        { h2: 'Conclusão' },
        { p: 'ART (CREA), RRT (CAU) e TRT (CFT) são documentos obrigatórios pra qualquer profissional que assina laudos técnicos no Brasil. Não é burocracia inútil — é o que dá peso jurídico ao seu trabalho e protege legalmente tanto o cliente quanto você mesmo.' },
        { p: 'Cada categoria tem seu sistema, seu fluxo e seu valor. O essencial é nunca emitir um laudo sem o documento correspondente, e manter histórico organizado pra eventual fiscalização ou questionamento futuro. Quem trabalha com responsabilidade técnica em dia constrói carreira sólida e tranquila — quem ignora se expõe a multas, suspensões e ações civis.' },
      ]}
      servicosRelacionados={[
        { slug: 'ptam', titulo: 'PTAM — Parecer Técnico de Avaliação Mercadológica' },
        { slug: 'laudo-tecnico', titulo: 'Laudo Técnico de Avaliação' },
        { slug: 'avaliacao-rural', titulo: 'Avaliação de Imóveis Rurais' },
      ]}
      postsRelacionados={relacionados}
    />
  );
}
