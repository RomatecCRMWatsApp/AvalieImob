// @module data/blogPosts — metadata central dos artigos do blog
// Usado pelo indice (Blog.jsx) e por cada artigo para listar "Continue lendo".
// Ordem: mais recente primeiro.
//
// Cada artigo mora em data/blog/<slug>.json — FONTE ÚNICA: o componente renderiza o arquivo,
// o servidor (services/seo_html) entrega o mesmo texto no HTML inicial e a metadata abaixo
// vem do próprio arquivo (sem segunda cópia de título/descrição).
// ARTIGO NOVO: crie o JSON (slug = nome do arquivo), importe aqui e acrescente o slug
// em backend/services/seo_html.BLOG_SLUGS.
import a_checklist_vistoria_avaliacao_imobiliaria_ptam from './blog/checklist-vistoria-avaliacao-imobiliaria-ptam.json';
import a_ficha_resumo_contrato_locacao_comercial from './blog/ficha-resumo-contrato-locacao-comercial.json';
import a_inferencia_estatistica_avaliacao_imoveis_tratamento_cientifico from './blog/inferencia-estatistica-avaliacao-imoveis-tratamento-cientifico.json';
import a_contrato_exclusividade_procuracao_corretor_imoveis from './blog/contrato-exclusividade-procuracao-corretor-imoveis.json';
import a_assinatura_icp_brasil_laudos_contratos_validade_juridica from './blog/assinatura-icp-brasil-laudos-contratos-validade-juridica.json';
import a_precificar_georreferenciamento_demarcacao_averbacao_proposta from './blog/precificar-georreferenciamento-demarcacao-averbacao-proposta.json';
import a_como_emitir_art_rrt_trt_avaliacao_imobiliaria from './blog/como-emitir-art-rrt-trt-avaliacao-imobiliaria.json';
import a_avaliacao_imovel_inventario_partilha from './blog/avaliacao-imovel-inventario-partilha.json';
import a_metodo_comparativo_direto_passo_a_passo from './blog/metodo-comparativo-direto-passo-a-passo.json';
import a_grau_fundamentacao_precisao_nbr_14653 from './blog/grau-fundamentacao-precisao-nbr-14653.json';
import a_como_fazer_ptam_passo_a_passo_nbr_14653 from './blog/como-fazer-ptam-passo-a-passo-nbr-14653.json';
import a_diferenca_ptam_laudo_avaliacao_imobiliaria from './blog/diferenca-ptam-laudo-avaliacao-imobiliaria.json';
import a_avaliacao_imovel_rural_nbr_14653_3_guia_completo from './blog/avaliacao-imovel-rural-nbr-14653-3-guia-completo.json';
import a_como_calcular_valor_liquidacao_forcada_vlf from './blog/como-calcular-valor-liquidacao-forcada-vlf.json';

const meta_ = (a) => ({
  slug: a.slug, titulo: a.titulo, meta: a.meta, categoria: a.categoria,
  dataPublicacao: a.dataPublicacao, dataAtualizacao: a.dataAtualizacao,
  tempoLeitura: a.tempoLeitura, resumo: a.resumo,
});

export const BLOG_POSTS = [
  a_checklist_vistoria_avaliacao_imobiliaria_ptam,
  a_ficha_resumo_contrato_locacao_comercial,
  a_inferencia_estatistica_avaliacao_imoveis_tratamento_cientifico,
  a_contrato_exclusividade_procuracao_corretor_imoveis,
  a_assinatura_icp_brasil_laudos_contratos_validade_juridica,
  a_precificar_georreferenciamento_demarcacao_averbacao_proposta,
  a_como_emitir_art_rrt_trt_avaliacao_imobiliaria,
  a_avaliacao_imovel_inventario_partilha,
  a_metodo_comparativo_direto_passo_a_passo,
  a_grau_fundamentacao_precisao_nbr_14653,
  a_como_fazer_ptam_passo_a_passo_nbr_14653,
  a_diferenca_ptam_laudo_avaliacao_imobiliaria,
  a_avaliacao_imovel_rural_nbr_14653_3_guia_completo,
  a_como_calcular_valor_liquidacao_forcada_vlf,
].map(meta_);

export function getPostBySlug(slug) {
  return BLOG_POSTS.find(p => p.slug === slug);
}

export function getRelatedPosts(currentSlug, limit = 3) {
  return BLOG_POSTS.filter(p => p.slug !== currentSlug).slice(0, limit);
}
