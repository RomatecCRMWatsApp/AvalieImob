// @module utils/areaConversao — Conversão de áreas (m² / hectare / alqueire mineiro) — NBR 14653
//
// Regra fixa: usar exclusivamente ALQUEIRE MINEIRO (4,84 ha = 48.400 m²).
// NÃO usar alqueire paulista (2,42 ha) nem baiano (9,68 ha).

export const M2_PER_HA = 10000;   // 1 ha = 10.000 m²
export const M2_PER_ALQ = 48400;  // 1 alqueire mineiro = 4,84 ha = 48.400 m²

/** @typedef {'m2' | 'ha' | 'alq'} UnidadeArea */

/**
 * Converte um valor na unidade informada para m².
 * @param {number} val
 * @param {UnidadeArea} unit
 * @returns {number}
 */
export function toM2(val, unit) {
  const n = Number(val) || 0;
  if (unit === 'ha') return n * M2_PER_HA;
  if (unit === 'alq') return n * M2_PER_ALQ;
  return n;
}

/**
 * Converte m² para a unidade informada.
 * @param {number} m2
 * @param {UnidadeArea} unit
 * @returns {number}
 */
export function fromM2(m2, unit) {
  const n = Number(m2) || 0;
  if (unit === 'ha') return n / M2_PER_HA;
  if (unit === 'alq') return n / M2_PER_ALQ;
  return n;
}

/**
 * Formata número no padrão pt-BR com casas decimais fixas.
 * @param {number} n
 * @param {number} dec
 * @returns {string}
 */
export function fmtBR(n, dec) {
  return (Number(n) || 0).toLocaleString('pt-BR', {
    minimumFractionDigits: dec,
    maximumFractionDigits: dec,
  });
}

// ── Apresentação rural (hectare como grandeza principal) ───────────────────
// Regra: o sistema SEMPRE armazena área em m² e valor unitário em R$/m².
// Estas funções apenas convertem para exibição quando o imóvel é rural.

/**
 * Formata área em hectares: "XX,XX ha".
 * @param {number} areaM2  área em m²
 * @param {number} [decimals=2]
 * @returns {string}
 */
export function formatHa(areaM2, decimals = 2) {
  return fmtBR((Number(areaM2) || 0) / M2_PER_HA, decimals) + ' ha';
}

/**
 * Formata valor monetário pt-BR: "R$ XX.XXX,XX".
 * @param {number} v
 * @returns {string}
 */
export function formatBRL(v) {
  return (Number(v) || 0).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
}

/**
 * Formata valor unitário por hectare a partir do R$/m²: "R$ XX.XXX,XX/ha".
 * R$/ha = R$/m² × 10.000.
 * @param {number} vrUnitM2  valor unitário em R$/m²
 * @returns {string}
 */
export function formatRsHa(vrUnitM2) {
  return formatBRL((Number(vrUnitM2) || 0) * M2_PER_HA) + '/ha';
}

/**
 * Formata valor unitário por m²: "R$ X,XX/m²".
 * @param {number} vrUnitM2
 * @returns {string}
 */
export function formatRsM2(vrUnitM2) {
  return formatBRL(Number(vrUnitM2) || 0) + '/m²';
}

/**
 * Área dupla para exibição rural: "XX,XX ha (XXX.XXX m²)".
 * @param {number} areaM2
 * @param {number} [decimals=2]
 * @returns {string}
 */
export function formatAreaRural(areaM2, decimals = 2) {
  const a = Number(areaM2) || 0;
  const ha = fmtBR(a / M2_PER_HA, decimals);
  const m2 = a.toLocaleString('pt-BR', { maximumFractionDigits: 0 });
  return `${ha} ha (${m2} m²)`;
}
