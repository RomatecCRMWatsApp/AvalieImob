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
