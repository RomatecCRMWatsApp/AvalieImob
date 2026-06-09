// @module dashboard/amostras/amostraOptions — Listas de opções, conversões e helpers
// compartilhados pelos modais (Urbano/Rural) e pela página de Amostras de Mercado v2.
import { M2_PER_HA, M2_PER_ALQ } from '../../../utils/areaConversao';

export const TIPOS_URBANO = [
  'Casa', 'Apartamento', 'Terreno', 'Sala Comercial', 'Galpão', 'Loja', 'Chácara Urbana', 'Outro',
];

export const TIPOS_RURAL = [
  'Fazenda', 'Sítio', 'Gleba', 'Chácara Rural', 'Terra Nua', 'Área de Preservação', 'Outro',
];

export const TIPO_AMOSTRA_URBANO = ['Oferta de Mercado', 'Consolidada / Comercializada', 'Aluguel'];
export const TIPO_AMOSTRA_RURAL = ['Oferta de Mercado', 'Consolidada / Comercializada'];

export const PADRAO_CONSTRUTIVO = ['Simples', 'Normal', 'Bom', 'Alto', 'Luxo'];
export const ESTADO_CONSERVACAO = ['Novo', 'Bom', 'Regular', 'Precário', 'Em Ruínas'];

export const TOPOGRAFIA = ['Plano', 'Suave Ondulado', 'Ondulado', 'Forte Ondulado', 'Montanhoso', 'Escarpado'];
export const SOLO = ['Argiloso', 'Arenoso', 'Misto', 'Rochoso', 'Orgânico'];
export const RECURSOS_HIDRICOS = ['Nenhum', 'Nascente', 'Rio / córrego', 'Açude / represa', 'Irrigação'];
export const VEGETACAO = ['Pastagem', 'Pastagem Degradada', 'Capoeira', 'Mata Nativa', 'Reflorestamento', 'Lavoura', 'Mista'];
export const ATIVIDADE_PRINCIPAL = ['Pecuária', 'Agricultura', 'Misto', 'Extrativismo', 'Piscicultura', 'Inativo'];
export const BENFEITORIAS_RURAL = ['Nenhuma', 'Simples', 'Médio', 'Bom', 'Alto'];
export const SEDE_CASA = ['Nenhuma', 'Simples', 'Normal', 'Bom'];

// Ambientes do imóvel urbano (campo, rótulo). Só vão ao laudo quando > 0.
export const AMBIENTES = [
  ['sala_estar', 'Sala de Estar'],
  ['sala_jantar_copa', 'Sala Jantar/Copa'],
  ['cozinha', 'Cozinha'],
  ['quarto_social', 'Quarto Social'],
  ['suite_simples', 'Suíte Simples'],
  ['suite_master', 'Suíte Master'],
  ['banheiro_social', 'Banheiro Social'],
  ['lavabo', 'Lavabo'],
  ['area_servico', 'Área de Serviço'],
  ['varanda_sacada', 'Varanda/Sacada'],
  ['varanda_gourmet', 'Varanda Gourmet'],
  ['escritorio', 'Escritório'],
  ['despensa', 'Despensa'],
  ['piscina', 'Piscina'],
  ['garagem', 'Garagem'],
];

export const hoje = () => new Date().toISOString().split('T')[0];

export const num = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};

export const fmtBRL = (v) =>
  (num(v)).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export const fmtNum = (v, dec = 2) =>
  (num(v)).toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec });

// R$/m² em tempo real (urbano).
export const calcRsM2 = (valor, area) => {
  const a = num(area);
  return a > 0 ? num(valor) / a : 0;
};

// R$/ha em tempo real (rural).
export const calcRsHa = (valor, areaM2) => {
  const a = num(areaM2);
  return a > 0 ? num(valor) / (a / M2_PER_HA) : 0;
};

export const m2ToHa = (areaM2) => (num(areaM2) > 0 ? num(areaM2) / M2_PER_HA : 0);
export const m2ToAlq = (areaM2) => (num(areaM2) > 0 ? num(areaM2) / M2_PER_ALQ : 0);
