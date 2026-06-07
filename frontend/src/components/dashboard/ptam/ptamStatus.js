// @module ptam/ptamStatus — Config visual + resolução do status do PTAM.
// Espelha utils/ptam_status.py do backend. A conclusão é EXCLUSIVAMENTE manual:
// o avaliador marca `concluido_manual` na etapa 12. O sistema nunca conclui sozinho.
//   Prioridade: assinado > concluido (manual) > rascunho.

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

// 12 seções (rótulo → campos alternativos) — espelho do backend. Usadas só para
// a barra de progresso (% de andamento) no círculo âmbar dos rascunhos.
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

function preenchido(v) {
  if (v == null) return false;
  if (typeof v === 'boolean') return v;
  if (typeof v === 'string') return v.trim() !== '';
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === 'object') return Object.keys(v).length > 0;
  if (typeof v === 'number') return v !== 0;
  return true;
}

/** % de seções preenchidas (0-100), usado no círculo âmbar do rascunho. */
export function calcularProgressoPtam(p) {
  const d = p || {};
  const total = SECOES.length;
  const preenchidas = SECOES.reduce(
    (acc, campos) => acc + (campos.some((c) => preenchido(d[c])) ? 1 : 0),
    0,
  );
  return Math.round((preenchidas / total) * 100);
}

/**
 * Resolve o status do badge/círculo. Conclusão é exclusivamente manual:
 *   - assinado            → assinatura ICP/D4Sign (sempre prevalece)
 *   - concluido_manual=true → concluído (decisão do avaliador na etapa 12)
 *   - qualquer outro caso  → rascunho
 */
export function resolvePtamStatus(p) {
  const d = p || {};
  if (d.icp_status === 'assinado' || d.d4sign_status === 'assinado') return 'assinado';
  if (String(d.status_calculado ?? '').toLowerCase().trim() === 'assinado') return 'assinado';
  if (d.concluido_manual === true) return 'concluido';
  return 'rascunho';
}
