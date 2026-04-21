// @module Semoventes/steps/shared — constantes e componentes base compartilhados entre todos os steps

import React from 'react';
import {
  Beef, PawPrint, Bird,
  ClipboardList, User, Layers, Tag, ShieldCheck, Home,
  Camera, BarChart2, DollarSign, Award,
} from 'lucide-react';

// ── Constantes ────────────────────────────────────────────────────────────
export const UF_OPTIONS = [
  'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS',
  'MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO',
];

export const TIPO_OPTIONS = [
  { value: 'bovino',        label: 'Bovino',         desc: 'Corte, leite ou misto',       icon: Beef },
  { value: 'equino',        label: 'Equino',         desc: 'Cavalos, burros, mulas',      icon: PawPrint },
  { value: 'suino',         label: 'Suíno',          desc: 'Plantel suíno',               icon: PawPrint },
  { value: 'ovino_caprino', label: 'Ovino/Caprino',  desc: 'Ovinos e caprinos',           icon: PawPrint },
  { value: 'aves',          label: 'Aves',            desc: 'Frango, peru, codorna, etc.', icon: Bird },
];

export const MODALIDADE_OPTIONS = [
  { value: 'pronaf',              label: 'PRONAF' },
  { value: 'pronamp',             label: 'PRONAMP' },
  { value: 'acc',                 label: 'ACC (Adiantamento Cambial)' },
  { value: 'credito_rural_livre', label: 'Crédito Rural Livre' },
  { value: 'moderfrota',          label: 'MODERFROTA' },
  { value: 'abc',                 label: 'ABC (Agricultura de Baixo Carbono)' },
];

export const CATEGORIA_OPTIONS_BOVINO = [
  { value: 'reprodutores',      label: 'Reprodutores (Touros)' },
  { value: 'matrizes',          label: 'Matrizes (Vacas)' },
  { value: 'novilhas',          label: 'Novilhas' },
  { value: 'garrotes_bezerros', label: 'Garrotes / Bezerros' },
  { value: 'bois_engorda',      label: 'Bois de Engorda' },
];

export const CATEGORIA_OPTIONS_EQUINO = [
  { value: 'garanhao', label: 'Garanhão' },
  { value: 'egua',     label: 'Égua' },
  { value: 'potro',    label: 'Potro/Potranca' },
  { value: 'capao',    label: 'Capão' },
  { value: 'muar',     label: 'Muar/Jumento' },
];

export const CATEGORIA_OPTIONS_SUINO = [
  { value: 'reprodutor_suino', label: 'Reprodutor' },
  { value: 'matriz_suina',     label: 'Matriz' },
  { value: 'leitao',           label: 'Leitão' },
  { value: 'terminacao',       label: 'Terminação' },
];

export const CATEGORIA_OPTIONS_OVINO = [
  { value: 'carneiro', label: 'Carneiro/Bode' },
  { value: 'ovelha',   label: 'Ovelha/Cabra' },
  { value: 'cordeiro', label: 'Cordeiro/Cabrito' },
];

export const CATEGORIA_OPTIONS_AVES = [
  { value: 'matrizes_aves', label: 'Matrizes' },
  { value: 'frangos_corte', label: 'Frangos de Corte' },
  { value: 'poedeiras',     label: 'Poedeiras' },
  { value: 'perus',         label: 'Perus' },
  { value: 'outros_aves',   label: 'Outros' },
];

export const getCategoriaOptions = (tipo) => {
  switch (tipo) {
    case 'bovino':        return CATEGORIA_OPTIONS_BOVINO;
    case 'equino':        return CATEGORIA_OPTIONS_EQUINO;
    case 'suino':         return CATEGORIA_OPTIONS_SUINO;
    case 'ovino_caprino': return CATEGORIA_OPTIONS_OVINO;
    case 'aves':          return CATEGORIA_OPTIONS_AVES;
    default:              return CATEGORIA_OPTIONS_BOVINO;
  }
};

export const STEPS = [
  { id: 'tipo',        label: 'Tipo',        icon: ClipboardList },
  { id: 'devedor',     label: 'Devedor',     icon: User },
  { id: 'rebanho',     label: 'Rebanho',     icon: Layers },
  { id: 'rastreab',    label: 'Rastreab.',   icon: Tag },
  { id: 'sanitaria',   label: 'Sanitária',   icon: ShieldCheck },
  { id: 'infraestrut', label: 'Infraest.',   icon: Home },
  { id: 'vistoria',    label: 'Vistoria',    icon: Camera },
  { id: 'mercado',     label: 'Mercado',     icon: BarChart2 },
  { id: 'resultado',   label: 'Resultado',   icon: DollarSign },
  { id: 'declaracoes', label: 'Declarações', icon: Award },
];

export const EMPTY_CATEGORIA = {
  categoria: '',
  quantidade: 0,
  raca: '',
  faixa_etaria: '',
  peso_medio_kg: 0,
  registro_genealogico: '',
  valor_unitario: 0,
  valor_total: 0,
  taxa_prenhez: null,
  producao_leite: null,
  arrobas_estimadas: null,
  estagio: null,
  aptidao: null,
  fase: null,
};

export const EMPTY = {
  numero_laudo: '',
  tipo_semovente: 'bovino',
  status: 'rascunho',
  instituicao_financeira: '',
  modalidade_credito: 'credito_rural_livre',
  valor_credito: 0,
  devedor_nome: '',
  devedor_cpf_cnpj: '',
  propriedade_nome: '',
  propriedade_municipio: '',
  propriedade_uf: '',
  matricula_imovel: '',
  cri_cartorio: '',
  categorias: [],
  total_cabecas: 0,
  total_ua: 0,
  lotacao_ua_ha: 0,
  brincos_sisbov: false,
  brinco_inicio: '',
  brinco_fim: '',
  marcacao_ferro: false,
  marcacao_descricao: '',
  microchip: false,
  situacao_esisbov: '',
  vacina_aftosa_data: '',
  vacina_aftosa_orgao: '',
  vacina_brucelose_data: '',
  teste_tuberculose: 'nao_realizado',
  teste_tuberculose_data: '',
  vermifugacao_data: '',
  vermifugacao_produto: '',
  mortalidade_percentual: 0,
  area_livre_aftosa: false,
  gta_em_dia: false,
  capacidade_suporte_ua_ha: 0,
  disponibilidade_agua: '',
  instalacoes: '',
  estado_conservacao_instalacoes: '',
  capacidade_confinamento: 0,
  cotacao_arroba_data: '',
  cotacao_arroba_valor: 0,
  cotacao_fonte: '',
  cotacao_bezerro: 0,
  cotacao_vaca: 0,
  cotacao_touro_po: 0,
  valor_mercado_total: 0,
  fator_liquidez: 0.65,
  valor_garantia_aceito: 0,
  ltv_recomendado: 65,
  validade_laudo_meses: 6,
  seguro_recomendado_valor: 0,
  vistoria_data: '',
  vistoria_horario: '',
  contagem_fisica_presencial: false,
  condicao_corporal_media: 3,
  fotos: [],
  responsavel_nome: '',
  crmv_numero: '',
  crmv_uf: '',
  especialidade: '',
  art_crmv_numero: '',
  art_data_registro: '',
  declaracao_contagem_presencial: false,
  declaracao_sem_conflito: false,
  declaracao_penhor_registrado: false,
  restricoes_ressalvas: '',
};

// ── Componentes base ──────────────────────────────────────────────────────
export const Field = ({ label, children, required, hint }) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">
      {label}{required && <span className="text-red-500 ml-0.5">*</span>}
    </label>
    {children}
    {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
  </div>
);

export const Inp = ({ value, onChange, ...props }) => (
  <input
    value={value ?? ''}
    onChange={onChange}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
  />
);

export const Sel = ({ value, onChange, children, ...props }) => (
  <select
    value={value ?? ''}
    onChange={onChange}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
  >
    {children}
  </select>
);

export const Txta = ({ value, onChange, rows = 3, ...props }) => (
  <textarea
    value={value ?? ''}
    onChange={onChange}
    rows={rows}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white resize-none"
  />
);

export const SectionTitle = ({ children }) => (
  <h3 className="text-sm font-semibold text-emerald-800 uppercase tracking-wider mb-4 pb-2 border-b border-emerald-100">
    {children}
  </h3>
);

export const CheckRow = ({ label, checked, onChange, hint }) => (
  <label className="flex items-start gap-3 cursor-pointer">
    <input
      type="checkbox"
      checked={!!checked}
      onChange={(e) => onChange(e.target.checked)}
      className="mt-0.5 w-4 h-4 rounded border-gray-300 text-emerald-700 focus:ring-emerald-500"
    />
    <div>
      <span className="text-sm text-gray-800">{label}</span>
      {hint && <p className="text-xs text-gray-400 mt-0.5">{hint}</p>}
    </div>
  </label>
);

export const fmtCurrency = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
