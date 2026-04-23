// Empty PTAM state matching the backend model (all 10 sections)
export const EMPTY_PTAM = {
  // Seção 1 — Identificação do Solicitante
  numero_ptam: '',  // gerado automaticamente pelo backend — readonly
  number: '',
  solicitante: '',
  solicitante_nome: '',
  solicitante_cpf_cnpj: '',
  solicitante_endereco: '',
  solicitante_telefone: '',
  solicitante_email: '',

  // Seção 2 — Objetivo da Avaliação
  purpose: '',
  finalidade: '',
  finalidade_outros: '',
  judicial_process: '',
  judicial_action: '',
  forum: '',
  requerente: '',
  requerido: '',
  judge: '',

  // Seção 3 — Identificação do Imóvel
  property_label: '',
  property_type: '',
  property_address: '',
  property_neighborhood: '',
  property_city: '',
  property_state: '',
  property_cep: '',
  property_matricula: '',
  property_cartorio: '',
  property_gps_lat: '',
  property_gps_lng: '',
  property_owner: '',
  proprietarios: [{ nome: '', cpf_cnpj: '', percentual: '' }],
  property_area_ha: 0,
  property_area_sqm: 0,
  property_confrontations: '',
  property_description: '',
  fotos_imovel: [],
  fotos_documentos: [],

  // Seção 4 — Caracterização da Região
  regiao_infraestrutura: '',
  regiao_servicos_publicos: '',
  regiao_uso_predominante: '',
  regiao_padrao_construtivo: '',
  regiao_tendencia_mercado: '',
  regiao_observacoes: '',
  // Vistoria Técnica (15 sub-seções PTAM nº 7010)
  vistoria_date: '',
  vistoria_responsavel: '',
  vistoria_condicoes: '',
  vistoria_objective: '',
  vistoria_methodology: '',
  topography: '',
  soil_vegetation: '',
  uso_atual: '',
  cobertura_vegetal: '',
  hidrografia: '',
  benfeitorias: '',
  infraestrutura_interna: '',
  accessibility: '',
  urban_context: '',
  conservation_state: '',
  situacao_fundiaria: '',
  passivo_ambiental: '',
  potencial_exploratorio: '',
  aspectos_legais: '',
  restricoes_uso: '',
  vistoria_synthesis: '',

  // Áreas (Área 01 e Área 02 — PTAM nº 7010)
  area_01_tipo: '',
  area_01_dados: '',
  area_01_valor: null,
  area_02_tipo: '',
  area_02_dados: '',
  area_02_valor: null,

  // Seção 5 — Caracterização do Imóvel
  imovel_area_terreno: 0,
  imovel_area_construida: 0,
  imovel_area_a_considerar: null,  // obrigatório — área usada no cálculo do valor final
  imovel_idade: 0,
  imovel_estado_conservacao: '',
  imovel_padrao_acabamento: '',
  imovel_num_quartos: 0,
  imovel_num_banheiros: 0,
  imovel_num_vagas: 0,
  imovel_piscina: false,
  imovel_caracteristicas_adicionais: '',

  // Seção 6 — Amostras de Mercado
  market_samples: [],
  market_analysis: '',

  // Seção 7 — Metodologia
  methodology: 'Método Comparativo Direto de Dados de Mercado',
  methodology_justification: '',

  // Seção 8 — Cálculos e Tratamento Estatístico
  calc_media: 0,
  calc_mediana: 0,
  calc_desvio_padrao: 0,
  calc_coef_variacao: 0,
  calc_grau_fundamentacao: '',
  calc_fatores_homogeneizacao: '',
  calc_observacoes: '',

  // Seção 9 — Resultado da Avaliação
  resultado_valor_unitario: 0,
  resultado_valor_total: 0,
  resultado_intervalo_inf: 0,
  resultado_intervalo_sup: 0,
  resultado_data_referencia: '',
  resultado_prazo_validade: '',
  total_indemnity: 0,
  total_indemnity_words: '',

  // Seção 10 — Considerações Finais
  consideracoes_ressalvas: '',
  consideracoes_pressupostos: '',
  consideracoes_limitacoes: '',
  responsavel_nome: '',
  responsavel_creci: '',
  responsavel_cnai: '',
  conclusion_text: '',
  conclusion_date: '',
  conclusion_city: '',

  // ── Campos NBR 14653 normatizados (novos) ──────────────────────────────────
  // Documentação analisada (checklist — Seção 2)
  documentos_analisados: [],
  // Zoneamento conforme Plano Diretor (Seção 5)
  zoneamento: '',
  // Vistoria técnica detalhada
  vistoria_responsavel: '',
  vistoria_condicoes: '',
  // Grau de precisão (NBR 14653-1 item 9)
  grau_precisao: 'I',
  // Campo de arbítrio ±15% (NBR 14653-1 item 9.2.4)
  campo_arbitrio_min: 0,
  campo_arbitrio_max: 0,
  // Prazo de validade do laudo
  prazo_validade_meses: 6,
  // Tipo de profissional responsável
  tipo_profissional: 'corretor',
  // Número de registro profissional (CRECI/CREA/CAU)
  registro_profissional: '',
  // Número da ART ou RRT
  art_rrt_numero: '',

  // ── Campos Rurais (visíveis apenas quando property_type === 'rural') ────────
  certificacao_sigef: '',    // SIGEF — Sistema de Gestão Fundiária
  cadastro_incra: '',         // Número de cadastro no INCRA
  ccir: '',                   // Certificado de Cadastro de Imóvel Rural
  nirf_cib: '',               // NIRF / CIB — Receita Federal / Cadastro Imobiliário Brasileiro
  car: '',                    // Cadastro Ambiental Rural (ex: MA-XXXXXXX)
  perimetro_m: null,          // Perímetro em metros
  // Documentos rurais (uploads)
  doc_mapa_sigef: [],          // Mapa Georreferenciado / Certificado SIGEF
  doc_memorial_descritivo: [], // Memorial Descritivo Topográfico / SIGEF
  doc_ccir: [],                // CCIR — Certificado de Cadastro de Imóvel Rural
  doc_itr: [],                 // ITR — últimos 5 exercícios (até 5 arquivos)
  doc_car: [],                 // CAR — Cadastro Ambiental Rural

  // Legacy impact areas (desapropriação)
  impact_areas: [],

  // Seção Método de Avaliação / Depreciação e Valorização
  metodo_avaliacao: null,          // ross_heidecke | linha_reta | fatores_terreno | nbr_rural | renda
  metodo_params: {},               // parâmetros do método selecionado
  depreciacao_percentual: null,
  valor_depreciacao: null,
  valor_benfeitoria: null,
  valor_terreno_calc: null,
  valor_total_metodo: null,

  // Seção Ponderância — Cálculo de Ponderância (filtragem 50%/150%)
  ponderancia_media: null,
  ponderancia_limite_inf: null,
  ponderancia_limite_sup: null,
  ponderancia_eliminadas: [],
  ponderancia_valor_final: null,

  status: 'Rascunho',
};

export const PTAM_STEPS = [
  { id: 'solicitante',        label: 'Solicitante',       icon: 'User' },
  { id: 'objetivo',           label: 'Objetivo',           icon: 'Target' },
  { id: 'imovel_id',          label: 'Imóvel',             icon: 'Building2' },
  { id: 'regiao',             label: 'Região',              icon: 'Map' },
  { id: 'caracterizacao',     label: 'Caracterização',     icon: 'ClipboardList' },
  { id: 'amostras',           label: 'Amostras',            icon: 'BarChart2' },
  { id: 'metodologia',        label: 'Metodologia',         icon: 'BookOpen' },
  { id: 'calculos',           label: 'Cálculos',            icon: 'Calculator' },
  { id: 'ponderancia',        label: 'Ponderância',         icon: 'Filter' },
  { id: 'metodo_avaliacao',   label: 'Dep./Valoriz.',       icon: 'TrendingDown' },
  { id: 'resultado',          label: 'Resultado',           icon: 'TrendingUp' },
  { id: 'conclusao',          label: 'Conclusão',           icon: 'CheckCircle2' },
];

// ── Factory helpers ────────────────────────────────────────────────────────────

export const emptyMarketSample = () => ({
  _key: `ms_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
  address: '',
  neighborhood: '',
  area: 0,
  value: 0,
  value_per_sqm: 0,
  source: '',
  collection_date: '',
  contact_phone: '',
  notes: '',
  foto: null,
  tipo_amostra: 'oferta',
});

/** Legacy — impact area factory kept for backward compat */
export const emptyImpactArea = () => ({
  _key: `ia_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
  name: 'Área de Impacto 01',
  classification: 'Rural',
  area_sqm: 0,
  unit_value: 0,
  total_value: 0,
  majoration_note: '',
  samples: [],
  notes: '',
});

/** Legacy — impact sample factory */
export const emptySample = () => ({
  _key: `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
  number: 0,
  neighborhood: '',
  area_total: 0,
  value: 0,
  value_per_sqm: 0,
  description: '',
  source: '',
});

// ── Statistical helpers ────────────────────────────────────────────────────────

/**
 * Compute descriptive statistics from the market_samples array.
 * Returns { media, mediana, desvio_padrao, coef_variacao }.
 * @deprecated Use computeStatsNBR for complete NBR 14653-2 compliance
 */
export const computeStats = (samples) => {
  const result = computeStatsNBR(samples);
  return {
    media: result.media_final,
    mediana: result.mediana,
    desvio_padrao: result.desvio_padrao,
    coef_variacao: result.coef_variacao,
  };
};

/**
 * Compute complete statistical analysis according to NBR 14653-2.
 * Includes outlier filtering (sanitation), precision grade, and foundation grade.
 * @param {Array} samples - Array of market samples with value_per_sqm
 * @returns {Object} Complete statistical analysis
 */
export const computeStatsNBR = (samples) => {
  // 1. Filtrar amostras com value_per_sqm > 0
  const validSamples = (samples || [])
    .map((s, idx) => ({ ...s, _originalIndex: idx }))
    .filter((s) => Number(s.value_per_sqm || 0) > 0);

  const n_total = validSamples.length;

  if (n_total === 0) {
    return {
      n_total: 0,
      n_validas: 0,
      indices_saneadas: [],
      media_inicial: 0,
      media_final: 0,
      mediana: 0,
      desvio_padrao: 0,
      coef_variacao: 0,
      limite_inf_saneamento: 0,
      limite_sup_saneamento: 0,
      limite_inf_ptam: 0,
      limite_sup_ptam: 0,
      grau_precisao: 'fora',
      grau_fundamentacao: 'insuficiente',
      texto_grau_precisao: 'Amostras insuficientes',
      texto_grau_fundamentacao: 'Mínimo 3 amostras necessárias',
    };
  }

  // 2. Calcular média inicial
  const somaInicial = validSamples.reduce((acc, s) => acc + Number(s.value_per_sqm), 0);
  const media_inicial = somaInicial / n_total;

  // Limites de saneamento (±10% da média inicial)
  const limite_inf_saneamento = media_inicial * 0.90;
  const limite_sup_saneamento = media_inicial * 1.10;

  // 3. SANEAMENTO: eliminar amostras fora do intervalo [90%, 110%]
  const amostrasSaneadas = [];
  const amostrasValidas = [];

  validSamples.forEach((s) => {
    const vpm = Number(s.value_per_sqm);
    if (vpm >= limite_inf_saneamento && vpm <= limite_sup_saneamento) {
      amostrasValidas.push(s);
    } else {
      amostrasSaneadas.push(s._originalIndex);
    }
  });

  const n_validas = amostrasValidas.length;
  const indices_saneadas = amostrasSaneadas;

  // Se não houver amostras válidas após saneamento
  if (n_validas === 0) {
    return {
      n_total,
      n_validas: 0,
      indices_saneadas,
      media_inicial: Math.round(media_inicial * 100) / 100,
      media_final: 0,
      mediana: 0,
      desvio_padrao: 0,
      coef_variacao: 0,
      limite_inf_saneamento: Math.round(limite_inf_saneamento * 100) / 100,
      limite_sup_saneamento: Math.round(limite_sup_saneamento * 100) / 100,
      limite_inf_ptam: 0,
      limite_sup_ptam: 0,
      grau_precisao: 'fora',
      grau_fundamentacao: 'insuficiente',
      texto_grau_precisao: 'Todas as amostras foram eliminadas no saneamento',
      texto_grau_fundamentacao: 'Nenhuma amostra válida após saneamento',
    };
  }

  // 4. Estatísticas finais (pós-saneamento)
  const valoresFinais = amostrasValidas.map((s) => Number(s.value_per_sqm));
  const somaFinal = valoresFinais.reduce((acc, v) => acc + v, 0);
  const media_final = somaFinal / n_validas;

  // 5. MEDIANA final (pós-saneamento)
  const sorted = [...valoresFinais].sort((a, b) => a - b);
  const mediana =
    n_validas % 2 === 0
      ? (sorted[n_validas / 2 - 1] + sorted[n_validas / 2]) / 2
      : sorted[Math.floor(n_validas / 2)];

  // 6. DESVIO PADRÃO amostral (divisor n-1, não n)
  const variance =
    n_validas > 1
      ? valoresFinais.reduce((acc, v) => acc + Math.pow(v - media_final, 2), 0) / (n_validas - 1)
      : 0;
  const desvio_padrao = Math.sqrt(variance);

  // 7. COEFICIENTE DE VARIAÇÃO: (desvio_padrao / media_final) * 100
  const coef_variacao = media_final > 0 ? (desvio_padrao / media_final) * 100 : 0;

  // 8. LIMITES PTAM (±5% da média final)
  const limite_inf_ptam = media_final * 0.95;
  const limite_sup_ptam = media_final * 1.05;

  // 9. GRAU DE PRECISÃO (NBR 14.653-2 tabela 2)
  let grau_precisao;
  let texto_grau_precisao;
  if (coef_variacao <= 10) {
    grau_precisao = 'III';
    texto_grau_precisao = 'Grau III — Coeficiente de variação ≤ 10% (precisão máxima)';
  } else if (coef_variacao <= 20) {
    grau_precisao = 'II';
    texto_grau_precisao = 'Grau II — Coeficiente de variação ≤ 20%';
  } else if (coef_variacao <= 30) {
    grau_precisao = 'I';
    texto_grau_precisao = 'Grau I — Coeficiente de variação ≤ 30%';
  } else {
    grau_precisao = 'fora';
    texto_grau_precisao = 'Fora dos limites — CV > 30% (laudo sem validade técnica)';
  }

  // 10. GRAU DE FUNDAMENTAÇÃO (NBR 14.653-2 tabela 1)
  let grau_fundamentacao;
  let texto_grau_fundamentacao;
  if (n_validas >= 10) {
    grau_fundamentacao = 'III';
    texto_grau_fundamentacao = 'Grau III — Mínimo 10 dados de mercado verificados e visitados';
  } else if (n_validas >= 6) {
    grau_fundamentacao = 'II';
    texto_grau_fundamentacao = 'Grau II — Mínimo 6 dados de mercado verificados';
  } else if (n_validas >= 3) {
    grau_fundamentacao = 'I';
    texto_grau_fundamentacao = 'Grau I — Mínimo 3 dados de mercado';
  } else {
    grau_fundamentacao = 'insuficiente';
    texto_grau_fundamentacao = 'Insuficiente — Mínimo 3 amostras válidas necessárias para PTAM';
  }

  // 11. Retornar objeto completo
  return {
    n_total,
    n_validas,
    indices_saneadas,
    media_inicial: Math.round(media_inicial * 100) / 100,
    media_final: Math.round(media_final * 100) / 100,
    mediana: Math.round(mediana * 100) / 100,
    desvio_padrao: Math.round(desvio_padrao * 100) / 100,
    coef_variacao: Math.round(coef_variacao * 100) / 100,
    limite_inf_saneamento: Math.round(limite_inf_saneamento * 100) / 100,
    limite_sup_saneamento: Math.round(limite_sup_saneamento * 100) / 100,
    limite_inf_ptam: Math.round(limite_inf_ptam * 100) / 100,
    limite_sup_ptam: Math.round(limite_sup_ptam * 100) / 100,
    grau_precisao,
    grau_fundamentacao,
    texto_grau_precisao,
    texto_grau_fundamentacao,
  };
};

// ── Legacy helpers (kept for backward compat with PtamWizard save logic) ──────

export const computeImpactTotals = (areas) =>
  (areas || []).map((a) => ({
    ...a,
    total_value: Number(a.area_sqm || 0) * Number(a.unit_value || 0),
  }));

export const sumIndemnity = (areas) =>
  (areas || []).reduce(
    (acc, a) => acc + Number(a.area_sqm || 0) * Number(a.unit_value || 0),
    0
  );
