// @module utils/incraFaixa — Casamento da média da avaliação (R$/ha) com as faixas da tabela INCRA.

/**
 * Índice da faixa onde vr_min <= mediaHa <= vr_max.
 * Se não houver match exato, retorna o índice da faixa mais próxima (por distância
 * ao limite inferior ou superior).
 * @param {Array<{vr_min:number, vr_max:number}>} faixas
 * @param {number} mediaHa  média ponderada da avaliação em R$/ha
 * @returns {number} índice (0 quando lista vazia)
 */
export function getFaixaMatch(faixas, mediaHa) {
  const lista = Array.isArray(faixas) ? faixas : [];
  const m = Number(mediaHa) || 0;
  let closestIdx = 0;
  let closestDist = Infinity;
  for (let i = 0; i < lista.length; i++) {
    const f = lista[i] || {};
    const min = Number(f.vr_min) || 0;
    const max = Number(f.vr_max) || 0;
    if (m >= min && m <= max) return i; // dentro da faixa
    const dist = Math.min(Math.abs(m - min), Math.abs(m - max));
    if (dist < closestDist) {
      closestDist = dist;
      closestIdx = i;
    }
  }
  return closestIdx;
}

/**
 * True se a média está DENTRO do intervalo [vr_min, vr_max] da faixa indicada.
 * @param {Array} faixas
 * @param {number} idx
 * @param {number} mediaHa
 * @returns {boolean}
 */
export function faixaContemMedia(faixas, idx, mediaHa) {
  const f = (Array.isArray(faixas) ? faixas : [])[idx];
  if (!f) return false;
  const m = Number(mediaHa) || 0;
  return m >= (Number(f.vr_min) || 0) && m <= (Number(f.vr_max) || 0);
}
