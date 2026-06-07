// @module ptam/ptamStatus — Config visual + resolução do status automático do PTAM.
// Espelha utils/ptam_status.py do backend. O backend já envia `status_calculado`
// na listagem; o cálculo client-side abaixo é só fallback (itens em cache antigos).

export const STATUS_CONFIG = {
  rascunho: {
    label: 'Rascunho',
    className: 'bg-gray-100 text-gray-700 border border-gray-200',
  },
  concluido: {
    label: 'Concluído',
    className: 'bg-green-100 text-green-700 border border-green-200',
  },
  assinado: {
    label: 'Assinado',
    className: 'bg-indigo-900 text-white border border-indigo-800',
  },
};

const CAMPOS_VALOR = [
  'resultado_valor_total', 'total_indemnity', 'ponderancia_valor_final',
  'valor_total_metodo', 'resultado_valor_unitario',
];

// 12 seções (rótulo → campos alternativos) — espelho do backend.
const SECOES = [
  ['solicitante', 'solicitante_nome'],
  ['purpose', 'finalidade'],
  ['property_label', 'property_address', 'property_type', 'property_matricula'],
  ['regiao_infraestrutura', 'regiao_servicos_publicos', 'regiao_uso_predominante',
    'regiao_padrao_construtivo', 'regiao_tendencia_mercado', 'regiao_observacoes'],
  ['imovel_area_terreno', 'imovel_area_construida', 'imovel_area_a_considerar',
    'imovel_estado_conservacao', 'imovel_padrao_acabamento', 'property_description'],
  ['market_samples', 'impact_areas'],
  ['methodology'],
  ['calc_media', 'calc_mediana', 'calc_n_validas', 'resultado_valor_unitario', 'calc_grau_fundamentacao'],
  ['ponderancia_valor_final', 'ponderancia_media', 'resultado_valor_total', 'total_indemnity'],
  ['metodo_avaliacao', 'depreciacao_percentual', 'valor_total_metodo', 'valor_benfeitoria',
    'resultado_valor_total', 'total_indemnity'],
  ['resultado_valor_total', 'resultado_valor_unitario', 'total_indemnity'],
  ['conclusion_text', 'consideracoes_ressalvas', 'consideracoes_limitacoes', 'total_indemnity_words'],
];

function toFloat(v) {
  if (v == null || typeof v === 'boolean') return 0;
  if (typeof v === 'number') return v;
  if (typeof v === 'string') {
    let s = v.trim().replace(/R\$/g, '').replace(/[\s ]/g, '');
    if (!s) return 0;
    if (s.includes(',') && s.includes('.')) {
      s = s.lastIndexOf(',') > s.lastIndexOf('.') ? s.replace(/\./g, '').replace(',', '.') : s.replace(/,/g, '');
    } else if (s.includes(',')) {
      s = s.replace(/\./g, '').replace(',', '.');
    }
    const n = parseFloat(s);
    return Number.isNaN(n) ? 0 : n;
  }
  return 0;
}

function preenchido(v) {
  if (v == null) return false;
  if (typeof v === 'boolean') return v;
  if (typeof v === 'string') return v.trim() !== '';
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === 'object') return Object.keys(v).length > 0;
  if (typeof v === 'number') return v !== 0;
  return true;
}

function calcular(p) {
  if (p.icp_status === 'assinado' || p.d4sign_status === 'assinado') return 'assinado';
  const valor = CAMPOS_VALOR.some((c) => toFloat(p[c]) > 0);
  if (!valor) return 'rascunho';
  const completo = SECOES.every((campos) => campos.some((c) => preenchido(p[c])));
  return completo ? 'concluido' : 'rascunho';
}

/** % de seções preenchidas (0-100), usando as mesmas 12 seções do status. */
export function calcularProgressoPtam(p) {
  const d = p || {};
  const total = SECOES.length;
  const preenchidas = SECOES.reduce(
    (acc, campos) => acc + (campos.some((c) => preenchido(d[c])) ? 1 : 0),
    0,
  );
  return Math.round((preenchidas / total) * 100);
}

/** Resolve o status para o badge: usa status_calculado do backend, com fallback local. */
export function resolvePtamStatus(p) {
  const d = p || {};
  // Assinatura é o sinal mais forte e mais "fresco" no estado local (ex.: logo
  // após assinar, antes de um reload), então tem prioridade sobre status_calculado.
  if (d.icp_status === 'assinado' || d.d4sign_status === 'assinado') return 'assinado';
  const raw = String(d.status_calculado ?? '').toLowerCase().trim();
  if (raw === 'concluido' || raw === 'rascunho' || raw === 'assinado') return raw;
  return calcular(d);
}
