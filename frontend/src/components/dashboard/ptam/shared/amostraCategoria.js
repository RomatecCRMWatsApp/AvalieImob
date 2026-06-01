// @module ptam/shared/amostraCategoria — Mapeia o tipo de imóvel (property_type) para a
// categoria de campos dinâmicos da amostra de mercado (Aba 6). Módulo puro (sem JSX),
// com imports relativos para ser testável diretamente no Jest.
import { M2_PER_HA, M2_PER_ALQ, fmtBR } from '../../../../utils/areaConversao';

// Tipos de property_type considerados rurais (alinhado ao isRural do RuralDocSection).
const RURAL_TYPES = new Set(['rural', 'fazenda', 'sitio', 'chacara', 'terreno_rural']);

/**
 * @param {string} propertyType
 * @returns {boolean}
 */
export function isRuralImovel(propertyType) {
  return RURAL_TYPES.has((propertyType || '').toLowerCase());
}

/**
 * Categoria de campos dinâmicos da amostra.
 * @param {string} propertyType  valor de form.property_type
 * @returns {'terreno_urbano'|'casa_apto'|'galpao_comercial'|'terreno_rural'|'fazenda_sitio'|'outros'}
 */
export function amostraCategoria(propertyType) {
  const t = (propertyType || '').toLowerCase();
  if (t === 'casa' || t === 'apartamento') return 'casa_apto';
  if (t === 'terreno') return 'terreno_urbano';
  if (t === 'comercial' || t === 'industrial') return 'galpao_comercial';
  if (t === 'terreno_rural') return 'terreno_rural';
  if (t === 'rural' || t === 'fazenda' || t === 'sitio' || t === 'chacara') return 'fazenda_sitio';
  return 'outros';
}

/**
 * Valor unitário de referência: R$/ha para rural, R$/m² para urbano.
 * @param {number} areaM2
 * @param {number} valor
 * @param {boolean} rural
 * @returns {number} 0 quando não calculável
 */
export function valorUnitario(areaM2, valor, rural) {
  const a = Number(areaM2) || 0;
  const v = Number(valor) || 0;
  if (a <= 0 || v <= 0) return 0;
  const base = rural ? a / M2_PER_HA : a;
  return v / base;
}

/** Rótulo da unidade do valor unitário. */
export function unidadeValorLabel(rural) {
  return rural ? 'R$/ha' : 'R$/m²';
}

/** Conversões de área (string formatada pt-BR) a partir de m². */
export function conversoesArea(areaM2) {
  const a = Number(areaM2) || 0;
  return {
    ha: a > 0 ? fmtBR(a / M2_PER_HA, 4) : '—',
    alq: a > 0 ? fmtBR(a / M2_PER_ALQ, 4) : '—',
  };
}
