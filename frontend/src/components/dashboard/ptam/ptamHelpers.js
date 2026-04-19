// Empty PTAM state matching the backend model
export const EMPTY_PTAM = {
  number: '', property_label: '', purpose: '', solicitante: '',
  judicial_process: '', judicial_action: '', forum: '', requerente: '', requerido: '', judge: '',
  property_address: '', property_city: '', property_matricula: '', property_owner: '',
  property_area_ha: 0, property_area_sqm: 0, property_confrontations: '', property_description: '',
  vistoria_date: '', vistoria_objective: '', vistoria_methodology: '',
  topography: '', soil_vegetation: '', benfeitorias: '', accessibility: '', urban_context: '',
  conservation_state: '', vistoria_synthesis: '',
  market_analysis: '', methodology: 'Método Comparativo Direto de Dados de Mercado',
  methodology_justification: '',
  impact_areas: [],
  total_indemnity: 0, total_indemnity_words: '', conclusion_text: '', conclusion_date: '', conclusion_city: '',
  status: 'Rascunho',
};

export const PTAM_STEPS = [
  { id: 'identification', label: 'Identificação', icon: 'FileText' },
  { id: 'property', label: 'Imóvel Avaliando', icon: 'Building2' },
  { id: 'vistoria', label: 'Vistoria', icon: 'ClipboardCheck' },
  { id: 'methodology', label: 'Metodologia', icon: 'BookOpen' },
  { id: 'impact', label: 'Áreas de Impacto', icon: 'Target' },
  { id: 'conclusion', label: 'Conclusão', icon: 'CheckCircle2' },
];

export const emptyImpactArea = () => ({
  _key: `ia_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
  name: 'Área de Impacto 01', classification: 'Rural',
  area_sqm: 0, unit_value: 0, total_value: 0,
  majoration_note: '', samples: [], notes: '',
});

export const emptySample = () => ({
  _key: `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
  number: 0, neighborhood: '', area_total: 0, value: 0, value_per_sqm: 0, description: '', source: '',
});

export const computeImpactTotals = (areas) => {
  return (areas || []).map((a) => ({
    ...a,
    total_value: Number(a.area_sqm || 0) * Number(a.unit_value || 0),
  }));
};

export const sumIndemnity = (areas) =>
  (areas || []).reduce((acc, a) => acc + Number(a.area_sqm || 0) * Number(a.unit_value || 0), 0);
