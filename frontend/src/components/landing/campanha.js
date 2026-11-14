// Identidade da campanha de captação (verde profundo + dourado) usada na página inicial.
export const VERDE = '#0C3320';
export const VERDE_2 = '#123F28';
export const DOURADO = '#C9A84C';
export const DOURADO_CLARO = '#E0C264';
export const CREME = '#F3F1E6';

export const WHATS_NUM = '5599991811246';
export const WHATS_FMT = '(99) 99181-1246';

// Cada botão leva um código na mensagem para saber de onde veio o contato.
export const whatsLink = (codigo, assunto) =>
  `https://wa.me/${WHATS_NUM}?text=${encodeURIComponent(
    `Oi! Vi o site do AvalieImob e quero um acesso de teste${assunto ? ` (${assunto})` : ''}. [${codigo}]`,
  )}`;

export const MODULOS = [
  {
    id: 'avaliacao',
    eyebrow: 'Para corretores e avaliadores',
    titulo: 'Um laudo com',
    destaque: 'a sua marca.',
    texto:
      'Clientes, imóveis e amostras de mercado conectados. A homogeneização é calculada pelo sistema, a IA redige o texto técnico e você revisa e decide. O PTAM sai em PDF com a sua marca, conforme a NBR 14.653.',
    itens: [
      'Tratamento por fatores ou inferência estatística (Grau III)',
      'Textos técnicos editáveis, com revisão do responsável',
      'Assinatura ICP-Brasil e link do laudo para o cliente',
    ],
    imagens: [
      { src: '/campanha/ptam-4.jpg', alt: 'Um laudo com a sua marca: PDF personalizado e assinatura ICP-Brasil' },
      { src: '/campanha/ptam-2.jpg', alt: 'Do cadastro à análise: clientes, imóveis e amostras em um só lugar' },
      { src: '/campanha/ptam-3.jpg', alt: 'IA que apoia, você que decide: cálculos automatizados e textos editáveis' },
      { src: '/campanha/ptam-5.jpg', alt: 'Teste o AvalieImob: faça seu próximo PTAM com mais praticidade' },
    ],
    cta: 'Testar o PTAM',
    codigo: 'SITE-PTAM',
    assunto: 'PTAM',
    escuro: false,
  },
  {
    id: 'topografia',
    eyebrow: 'Para agrimensores e topógrafos',
    titulo: 'Do memorial ao dossiê.',
    destaque: 'Sem espalhar o processo.',
    texto:
      'Suba o memorial do SIGEF e o sistema organiza vértices, área, perímetro e confrontantes. As peças do protocolo saem juntas e o dossiê vai assinado, com sumário clicável.',
    itens: [
      'Shapefile SIRGAS 2000 para o SIG-RI, KML e memorial',
      'Requerimento, DRL e laudo no mesmo processo',
      'Rural (SIGEF), lote urbano e arquivo ONR',
    ],
    imagens: [
      { src: '/campanha/geo-1.jpg', alt: 'Do memorial ao dossiê, sem espalhar o processo' },
      { src: '/campanha/geo-2.jpg', alt: 'Suba o memorial do SIGEF: vértices, área, perímetro e confrontantes' },
      { src: '/campanha/geo-3.jpg', alt: 'As peças certas no mesmo lugar: shapefile, KML, memorial, requerimento, DRL e laudo' },
      { src: '/campanha/geo-4.jpg', alt: 'Revise, assine, entregue: assinatura ICP-Brasil e dossiê com sumário clicável' },
      { src: '/campanha/geo-5.jpg', alt: 'Conheça o módulo de georreferenciamento' },
    ],
    cta: 'Testar o georreferenciamento',
    codigo: 'SITE-GEO',
    assunto: 'georreferenciamento',
    escuro: true,
  },
  {
    id: 'contratos',
    eyebrow: 'Para imobiliárias e corretores',
    titulo: 'Exclusividade',
    destaque: 'assinada pelo celular.',
    texto:
      'O contrato sai organizado, com os dados do imóvel, as condições da captação e a procuração no mesmo fluxo. Você envia o link, o cliente assina e tudo fica registrado com trilha de auditoria.',
    itens: [
      'Cláusulas editáveis e revisadas antes do envio',
      'Assinatura eletrônica pelo WhatsApp, com cônjuge anuente',
      'Contratos, propostas, recibos e PTAM em uma só plataforma',
    ],
    imagens: [
      { src: '/campanha/exc-1.jpg', alt: 'Exclusividade assinada pelo celular' },
      { src: '/campanha/exc-2.jpg', alt: 'Contrato organizado, cláusulas editáveis' },
      { src: '/campanha/exc-3.jpg', alt: 'Você envia o link, o cliente assina' },
      { src: '/campanha/exc-4.jpg', alt: 'Da captação à avaliação: contratos, propostas, recibos e PTAM' },
      { src: '/campanha/exc-5.jpg', alt: 'Sua próxima captação começa aqui' },
    ],
    cta: 'Testar os contratos',
    codigo: 'SITE-EXC',
    assunto: 'contratos',
    escuro: false,
  },
  {
    id: 'sig-ri',
    eyebrow: 'Provimento CNJ 195/2025 · SIG-RI',
    titulo: 'Seu shapefile urbano.',
    destaque: 'Pronto para o ONR.',
    texto:
      'Na retificação administrativa, no parcelamento e na regularização fundiária, o registro passa a exigir os dados no SIG-RI. Envie planta, memorial, ART/TRT e matrícula: o sistema extrai vértices, área, perímetro e proprietário, você confere e gera o pacote.',
    itens: [
      'Pacote .shp, .shx, .dbf e .prj em SIRGAS 2000, com os atributos do Provimento 195',
      'Validação antes de gerar: polígono, CPF/CNPJ, código IBGE e área',
      'Texto da descrição do polígono pronto para colar no portal do ONR',
    ],
    imagens: [
      { src: '/campanha/onr-1.jpg', alt: 'Provimento CNJ 195/2025: dados no SIG-RI são exigidos' },
      { src: '/campanha/onr-2.jpg', alt: 'Passo 1: envie os documentos e evite redigitar' },
      { src: '/campanha/onr-3.jpg', alt: 'Passo 2: o sistema extrai, você confere' },
      { src: '/campanha/onr-4.jpg', alt: 'Passo 3: shapefile urbano em um pacote (.shp, .shx, .dbf, .prj)' },
      { src: '/campanha/onr-5.jpg', alt: 'Atenda à exigência com mais praticidade: solicite seu acesso de teste' },
    ],
    cta: 'Testar o arquivo ONR',
    codigo: 'SITE-ONR',
    assunto: 'arquivo ONR / SIG-RI',
    escuro: true,
  },
];
