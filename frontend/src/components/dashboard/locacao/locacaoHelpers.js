// ── locacaoHelpers.js ─────────────────────────────────────────────────────
// State default e definição dos 10 steps do wizard de Avaliação de Locação

export const EMPTY_LOCACAO = {
  // Seção 1 — Identificação do Solicitante
  numero_locacao: '',
  solicitante_nome: '',
  solicitante_cpf: '',
  solicitante_telefone: '',
  solicitante_email: '',
  solicitante_endereco: '',

  // Seção 2 — Objetivo
  objetivo: '',
  objetivo_outros: '',
  tipo_locacao: 'residencial',
  base_legal_locacao: 'Lei 8.245/1991 (Lei do Inquilinato) — Art. 565 a 578 do Código Civil',

  // Seção 3 — Identificação do Imóvel
  imovel_endereco: '',
  imovel_bairro: '',
  imovel_cidade: '',
  imovel_estado: '',
  imovel_cep: '',
  imovel_matricula: '',
  imovel_cartorio: '',
  imovel_tipo: '',
  imovel_area_terreno: 0,
  imovel_area_construida: 0,
  imovel_idade: 0,
  imovel_estado_conservacao: '',
  imovel_padrao_acabamento: '',
  imovel_num_quartos: 0,
  imovel_num_banheiros: 0,
  imovel_num_vagas: 0,
  imovel_piscina: false,
  imovel_caracteristicas: '',

  // Seção 4 — Caracterização da Região
  regiao_infraestrutura: '',
  regiao_servicos_publicos: '',
  regiao_uso_predominante: '',
  regiao_padrao_construtivo: '',
  regiao_tendencia_mercado: '',
  regiao_observacoes: '',
  zoneamento: '',

  // Seção 5 — Pesquisa de Mercado
  market_samples: [],
  market_analysis: '',

  // Seção 6 — Cálculos
  methodology: 'Método Comparativo Direto de Dados de Mercado',
  methodology_justification: '',
  calc_media: 0,
  calc_mediana: 0,
  calc_desvio_padrao: 0,
  calc_coef_variacao: 0,
  calc_grau_fundamentacao: '',
  calc_fatores_homogeneizacao: '',
  calc_observacoes: '',

  // Seção 7 — Garantia
  prazo_locacao: '',
  garantia_locacao: '',
  fator_locacao: null,
  grau_precisao: 'I',
  campo_arbitrio_min: 0,
  campo_arbitrio_max: 0,

  // Seção 8 — Responsável Técnico
  responsavel_nome: '',
  responsavel_creci: '',
  responsavel_cnai: '',
  registro_profissional: '',
  tipo_profissional: 'corretor',
  art_rrt_numero: '',
  prazo_validade_meses: 6,
  conclusion_city: '',
  conclusion_date: '',

  // Seção 9 — Fotos
  fotos_imovel: [],
  fotos_documentos: [],
  documentos_analisados: [],

  // Seção 10 — Resultado
  valor_locacao_estimado: null,
  valor_locacao_minimo: null,
  valor_locacao_maximo: null,
  valor_locacao_por_extenso: '',
  resultado_data_referencia: '',
  resultado_prazo_validade: '',
  consideracoes_ressalvas: '',
  consideracoes_pressupostos: '',
  consideracoes_limitacoes: '',
  conclusion_text: '',

  // Meta
  status: 'Rascunho',
};

export const LOCACAO_STEPS = [
  { id: 0,  icon: 'User',       label: 'Solicitante',       short: '1' },
  { id: 1,  icon: 'Target',     label: 'Objetivo',          short: '2' },
  { id: 2,  icon: 'Home',       label: 'Imóvel',            short: '3' },
  { id: 3,  icon: 'MapPin',     label: 'Região',            short: '4' },
  { id: 4,  icon: 'Search',     label: 'Pesq. Mercado',     short: '5' },
  { id: 5,  icon: 'Calculator', label: 'Cálculos',          short: '6' },
  { id: 6,  icon: 'Shield',     label: 'Garantia',          short: '7' },
  { id: 7,  icon: 'Award',      label: 'Responsável',       short: '8' },
  { id: 8,  icon: 'Camera',     label: 'Fotos',             short: '9' },
  { id: 9,  icon: 'CheckCircle',label: 'Resultado',         short: '10' },
];

export const TIPO_LOCACAO_OPTIONS = [
  { value: 'residencial',    label: 'Residencial' },
  { value: 'comercial',      label: 'Comercial' },
  { value: 'galpao',         label: 'Galpão / Industrial' },
  { value: 'ponto_comercial',label: 'Ponto Comercial' },
  { value: 'misto',          label: 'Misto' },
];

export const OBJETIVO_OPTIONS = [
  { value: 'fixacao',     label: 'Fixação de Aluguel' },
  { value: 'revisao',     label: 'Revisão de Aluguel (Art. 19 Lei 8.245/91)' },
  { value: 'renovatoria', label: 'Ação Renovatória (Art. 51 Lei 8.245/91)' },
  { value: 'outros',      label: 'Outros' },
];

export const GARANTIA_OPTIONS = [
  { value: 'caucao',              label: 'Caução' },
  { value: 'fiador',             label: 'Fiador' },
  { value: 'seguro_fianca',      label: 'Seguro Fiança' },
  { value: 'titulo_capitalizacao',label: 'Título de Capitalização' },
  { value: 'nenhuma',            label: 'Nenhuma' },
];

export const IMOVEL_TIPO_OPTIONS = [
  { value: 'casa',          label: 'Casa' },
  { value: 'apartamento',   label: 'Apartamento' },
  { value: 'sala_comercial',label: 'Sala Comercial' },
  { value: 'galpao',        label: 'Galpão' },
  { value: 'loja',          label: 'Loja' },
  { value: 'terreno',       label: 'Terreno' },
];

export const CONSERVACAO_OPTIONS = [
  { value: 'otimo',  label: 'Ótimo' },
  { value: 'bom',    label: 'Bom' },
  { value: 'regular',label: 'Regular' },
  { value: 'ruim',   label: 'Ruim' },
  { value: 'pessimo',label: 'Péssimo' },
];

export const PADRAO_OPTIONS = [
  { value: 'alto',   label: 'Alto' },
  { value: 'medio',  label: 'Médio' },
  { value: 'simples',label: 'Simples' },
  { value: 'minimo', label: 'Mínimo' },
];

export const fmtCurrency = (v) => {
  if (v == null || isNaN(v)) return '—';
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v);
};

export const emptyLocacaoSample = () => ({
  address: '',
  neighborhood: '',
  area: 0,
  valor_aluguel: 0,
  valor_por_m2: 0,
  source: '',
  collection_date: '',
  contact_phone: '',
  notes: '',
  tipo_amostra: 'oferta',
});
