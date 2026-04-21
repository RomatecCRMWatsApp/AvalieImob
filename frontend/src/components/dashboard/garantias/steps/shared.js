// @module Garantias/steps/shared — constantes e componentes base compartilhados entre todos os steps

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import {
  Tractor, Wheat, Beef, Wrench, Car, Package,
  Building2, User, FileSearch, Camera, BarChart2, DollarSign, ShieldCheck,
  ClipboardList, MapPin, Award,
} from 'lucide-react';

// ── Default empty form ──────────────────────────────────────────────────────
export const EMPTY = {
  numero: '',
  tipo_garantia: 'imovel_rural',
  finalidade: 'credito_rural',
  solicitante: { nome: '', cpf_cnpj: '', instituicao_financeira: '', telefone: '', email: '' },
  descricao_bem: '',
  endereco: '', municipio: '', uf: '', cep: '', gps_lat: '', gps_lng: '',
  matricula: '', cartorio: '', data_vistoria: '',
  // rural
  area_total_ha: 0, area_construida_m2: 0, uso_atual: '', benfeitorias: '', topografia: '', solo_vegetacao: '',
  // documentação rural específica
  certificacao_sigef: '', cadastro_incra: '', ccir: '', nirf_cib: '', car: '', perimetro_m: null,
  // documentos rurais (uploads)
  doc_mapa_sigef: [], doc_memorial_descritivo: [], doc_ccir: [], doc_itr: [], doc_car: [],
  // graos
  cultura: '', quantidade_toneladas: 0, sacas: 0, produtividade_sc_ha: 0, local_armazenagem: '', safra_referencia: '',
  // bovinos
  raca_tipo: '', quantidade_cabecas: 0, categoria: '', peso_medio_kg: 0, aptidao: '', local_rebanho: '',
  // equip/veic
  marca: '', modelo: '', ano_fabricacao: 0, numero_serie: '', potencia: '', horimetro_hodometro: '',
  // avaliacao
  estado_conservacao: 'bom', valor_unitario: 0, valor_total: 0,
  data_avaliacao: '', data_validade: '',
  metodologia: '', fundamentacao_legal: 'Res. CMN 4.676/2018 | ABNT NBR 14653-1:2019 | NBR 14653-2:2011',
  mercado_referencia: '', fatores_depreciacao: '', grau_fundamentacao: '',
  resultado_intervalo_inf: 0, resultado_intervalo_sup: 0, resultado_em_extenso: '',
  consideracoes: '', ressalvas: '',
  responsavel: { nome: '', creci: '', cnai: '', registro: '' },
  fotos: [], observacoes: '',
  status: 'rascunho',
  // bancarios CMN 4.676/2018
  modalidade_financeira: '',
  instituicao_financeira: '',
  valor_financiamento: 0,
  ltv_maximo: 80,
  prazo_financiamento_meses: 0,
  mutuario_nome: '',
  mutuario_cpf_cnpj: '',
  finalidade_credito: '',
  area_privativa_nbr12721: 0,
  padrao_construtivo_ibape: '',
  idade_real_anos: 0,
  idade_aparente_anos: 0,
  habite_se: false,
  onus_reais: false,
  onus_descricao: '',
  inscricao_iptu: '',
  valor_venal: 0,
  valor_liquidacao_forcada: 0,
  fator_desconto_vlf: 0,
  valor_1o_leilao: 0,
  valor_2o_leilao: 0,
  art_numero: '',
  art_data_registro: '',
  grau_precisao: 'II',
  validade_laudo_meses: 12,
  declaracao_conflito_interesse: false,
  declaracao_impedimentos: '',
  cri_numero: '',
  conformidade_plano_diretor: false,
  regularidade_construtiva: false,
  data_matricula: '',
  vistoria_horario: '',
  vistoria_responsavel_nome: '',
  vistoria_condicoes_obs: '',
  num_amostras: 0,
  coeficiente_variacao: 0,
  fator_homogeneizacao: '',
  infraestrutura_entorno: '',
  liquidez_mercado: '',
  valor_mercado: 0,
  valor_maximo_garantia: 0,
  campo_arbitrio_min: 0,
  campo_arbitrio_max: 0,
  responsavel_tipo: '',
  responsavel_crea_cau: '',
  responsavel_uf: '',
  responsavel_empresa_cpf: '',
};

// ── Detectores de modalidade ───────────────────────────────────────────────
export const isBancario = (form) =>
  ['sfh_fgts', 'sfi_bancario', 'alienacao_fiduciaria', 'hipoteca'].includes(form.modalidade_financeira);
export const isAlienacao = (form) => form.modalidade_financeira === 'alienacao_fiduciaria';
export const isSfhFgts   = (form) => form.modalidade_financeira === 'sfh_fgts';

// ── Step definitions ──────────────────────────────────────────────────────
export const STEPS_BANCARIO = [
  { id: 'modalidade',  label: 'Modalidade',  icon: Building2 },
  { id: 'mutuario',    label: 'Mutuário',    icon: User },
  { id: 'imovel',      label: 'Imóvel/Docs', icon: FileSearch },
  { id: 'vistoria',    label: 'Vistoria',    icon: Camera },
  { id: 'metodologia', label: 'Metodologia', icon: BarChart2 },
  { id: 'resultado',   label: 'Resultado',   icon: DollarSign },
  { id: 'declaracoes', label: 'Declarações', icon: ShieldCheck },
];

export const STEPS_RURAL = [
  { id: 'tipo',        label: 'Tipo',        icon: ClipboardList },
  { id: 'solicitante', label: 'Solicitante', icon: User },
  { id: 'bem',         label: 'Descrição',   icon: Package },
  { id: 'localizacao', label: 'Localização', icon: MapPin },
  { id: 'avaliacao',   label: 'Avaliação',   icon: BarChart2 },
  { id: 'resultado',   label: 'Resultado',   icon: DollarSign },
  { id: 'conclusao',   label: 'Conclusão',   icon: Award },
];

// ── Opções de seleção ──────────────────────────────────────────────────────
export const TIPO_OPTIONS = [
  { value: 'imovel_rural', label: 'Imóvel Rural',   desc: 'Terras, fazendas, sítios, gleba',         icon: Tractor },
  { value: 'graos_safra',  label: 'Grãos / Safra',  desc: 'Soja, milho, café, cana, etc.',           icon: Wheat },
  { value: 'bovinos',      label: 'Bovinos',         desc: 'Rebanho bovino, pecuária de corte/leite', icon: Beef },
  { value: 'equipamentos', label: 'Equipamentos',   desc: 'Maquinário agrícola, implementos',        icon: Wrench },
  { value: 'veiculos',     label: 'Veículos',        desc: 'Caminhões, tratores, utilitários',        icon: Car },
  { value: 'outros',       label: 'Outros',          desc: 'Demais bens dados em garantia',           icon: Package },
];

export const FINALIDADE_OPTIONS = [
  { value: 'credito_rural',        label: 'Crédito Rural' },
  { value: 'financiamento',        label: 'Financiamento' },
  { value: 'penhor',               label: 'Penhor' },
  { value: 'alienacao_fiduciaria', label: 'Alienação Fiduciária' },
  { value: 'outros',               label: 'Outros' },
];

export const MODALIDADE_OPTIONS = [
  { value: 'sfh_fgts',             label: 'SFH / FGTS',           desc: 'Sistema Financeiro Habitacional — Lei 4.380/1964 | Lei 8.036/1990' },
  { value: 'sfi_bancario',         label: 'SFI / Bancário',        desc: 'Sistema Financeiro Imobiliário — Lei 9.514/1997' },
  { value: 'alienacao_fiduciaria', label: 'Alienação Fiduciária',  desc: 'Lei 9.514/1997 art. 27 — VLF obrigatório' },
  { value: 'hipoteca',             label: 'Hipoteca',              desc: 'Garantia hipotecária sobre imóvel' },
  { value: 'credito_rural',        label: 'Crédito Rural',         desc: 'Financiamento agropecuário / rural' },
];

export const BANCOS_OPTIONS = [
  'Caixa Econômica Federal', 'Banco do Brasil', 'Bradesco', 'Itaú Unibanco',
  'Santander', 'BTG Pactual', 'Sicoob', 'Sicredi', 'Banrisul',
  'BRB', 'Daycoval', 'Safra', 'Votorantim', 'Outros',
];

export const UF_OPTIONS = [
  'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS',
  'MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO',
];

// ── Componentes base ──────────────────────────────────────────────────────
export const Field = ({ label, children, required, hint }) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">
      {label}{required && <span className="text-red-500 ml-0.5">*</span>}
    </label>
    {children}
    {hint && <p className="text-[11px] text-gray-400 mt-1">{hint}</p>}
  </div>
);

export const Input = ({ value, onChange, ...props }) => (
  <input
    value={value ?? ''}
    onChange={onChange}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
  />
);

export const Textarea = ({ value, onChange, rows = 3, ...props }) => (
  <textarea
    value={value ?? ''}
    onChange={onChange}
    rows={rows}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white resize-none"
  />
);

export const Select = ({ value, onChange, children, ...props }) => (
  <select
    value={value ?? ''}
    onChange={onChange}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
  >
    {children}
  </select>
);

export const SectionTitle = ({ children }) => (
  <h3 className="text-sm font-semibold text-emerald-800 uppercase tracking-wider mb-4 pb-2 border-b border-emerald-100">
    {children}
  </h3>
);

export const Checkbox = ({ checked, onChange, label }) => (
  <label className="flex items-center gap-2 cursor-pointer">
    <input
      type="checkbox"
      checked={!!checked}
      onChange={(e) => onChange(e.target.checked)}
      className="w-4 h-4 accent-emerald-700 rounded"
    />
    <span className="text-sm text-gray-700">{label}</span>
  </label>
);

// ── Alertas reutilizáveis ─────────────────────────────────────────────────
export const AlertaCRECI = () => (
  <div className="flex gap-3 p-4 rounded-xl border border-red-300 bg-red-50 mb-6">
    <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
    <div>
      <div className="text-sm font-bold text-red-700 mb-1">
        Aviso Legal — Res. CONFEA 1.025/2009 | Res. CMN 4.676/2018
      </div>
      <div className="text-xs text-red-700 leading-relaxed">
        A avaliação de garantia para fins bancários (SFH, SFI, Alienação Fiduciária) exige
        <strong> obrigatoriamente Engenheiro Civil ou Arquiteto com CREA/CAU ativo e ART/RRT registrada</strong>.
        O Corretor de Imóveis (CRECI) <strong>não está habilitado</strong> para emitir laudos com essa finalidade.
        O laudo sem ART não possui validade perante instituições financeiras.
      </div>
    </div>
  </div>
);

export const AlertaSFH = () => (
  <div className="flex gap-3 p-4 rounded-xl border border-amber-300 bg-amber-50 mt-4">
    <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
    <div className="text-xs text-amber-800 leading-relaxed">
      <strong>Regras SFH/FGTS (Lei 4.380/1964 | Lei 8.036/1990):</strong>
      <ul className="list-disc list-inside mt-1 space-y-0.5">
        <li>Valor máximo de avaliação conforme limite BACEN vigente</li>
        <li>Imóvel deve possuir Habite-se (não admitido sem regularização)</li>
        <li>Vedada aquisição de imóvel adquirido com FGTS nos últimos 3 anos (art. 20)</li>
        <li>Vedado imóvel com matrícula em Pessoa Jurídica para SFH/FGTS</li>
        <li>Validade do laudo: 12 meses (Circular BACEN 3.818/2016)</li>
      </ul>
    </div>
  </div>
);
