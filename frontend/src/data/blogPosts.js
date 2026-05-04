// @module data/blogPosts — metadata central dos artigos do blog
// Usado pelo indice (Blog.jsx) e por cada artigo para listar "Continue lendo".
// Ordem: mais recente primeiro.

export const BLOG_POSTS = [
  {
    slug: 'como-fazer-ptam-passo-a-passo-nbr-14653',
    titulo: 'Como fazer um PTAM passo a passo conforme NBR 14.653',
    meta: 'Aprenda como fazer um PTAM (Parecer Técnico de Avaliação Mercadológica) do zero, conforme NBR 14.653 da ABNT. Wizard de 6 etapas com exemplo prático.',
    categoria: 'Tutorial',
    dataPublicacao: '2026-04-15',
    dataAtualizacao: '2026-05-04',
    tempoLeitura: '12 min',
    resumo: 'Um PTAM bem estruturado precisa cobrir 6 etapas obrigatórias da NBR 14.653: identificação do imóvel, vistoria, pesquisa de mercado, escolha do método avaliatório, cálculo do valor e conclusão. Veja o passo a passo completo com exemplo prático.',
  },
  {
    slug: 'diferenca-ptam-laudo-avaliacao-imobiliaria',
    titulo: 'Qual a diferença entre PTAM e Laudo de Avaliação Imobiliária?',
    meta: 'Entenda a diferença entre PTAM e Laudo Técnico de Avaliação. Quando usar cada um, custo, validade jurídica e exigências legais conforme NBR 14.653 e COFECI 1.066/2007.',
    categoria: 'Conceitos',
    dataPublicacao: '2026-04-22',
    dataAtualizacao: '2026-05-04',
    tempoLeitura: '8 min',
    resumo: 'PTAM e Laudo de Avaliação são documentos similares mas com finalidades, profundidade técnica e peso jurídico diferentes. Saiba quando emitir cada um e os requisitos legais para corretores, engenheiros e arquitetos.',
  },
  {
    slug: 'avaliacao-imovel-rural-nbr-14653-3-guia-completo',
    titulo: 'Avaliação de imóvel rural: guia completo NBR 14.653-3',
    meta: 'Guia completo para avaliação de imóveis rurais conforme NBR 14.653-3: terra nua, benfeitorias, semoventes, safras, equipamentos. Para penhor rural, Pronaf, Pronamp e perícia.',
    categoria: 'Avaliação Rural',
    dataPublicacao: '2026-04-29',
    dataAtualizacao: '2026-05-04',
    tempoLeitura: '15 min',
    resumo: 'Avaliar imóveis rurais exige conhecimento técnico em terra nua, benfeitorias produtivas e reprodutivas, semoventes, safras e equipamentos. Veja como cada componente é avaliado conforme NBR 14.653-3 e o que bancos exigem para penhor rural.',
  },
  {
    slug: 'como-calcular-valor-liquidacao-forcada-vlf',
    titulo: 'Como calcular o Valor de Liquidação Forçada (VLF) corretamente',
    meta: 'Aprenda como calcular o Valor de Liquidação Forçada (VLF) para garantias bancárias. Fatores de liquidez, atratividade e prazo. Exemplo prático com cálculo passo a passo.',
    categoria: 'Garantias Bancárias',
    dataPublicacao: '2026-05-03',
    dataAtualizacao: '2026-05-04',
    tempoLeitura: '10 min',
    resumo: 'O Valor de Liquidação Forçada (VLF) é exigido por bancos em laudos de garantia. Representa o valor estimado em venda forçada (leilão), considerando fatores de liquidez, atratividade e prazo. Veja como calcular conforme metodologia BB, Caixa e Itaú.',
  },
];

export function getPostBySlug(slug) {
  return BLOG_POSTS.find(p => p.slug === slug);
}

export function getRelatedPosts(currentSlug, limit = 3) {
  return BLOG_POSTS.filter(p => p.slug !== currentSlug).slice(0, limit);
}
