import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, ChevronLeft, ChevronRight, Save, Loader2, Check,
  Tractor, Wheat, Beef, Wrench, Car, Package,
  User, MapPin, BarChart2, ClipboardList, DollarSign, Award,
  AlertTriangle, Building2, FileSearch, Camera, ShieldCheck
} from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { garantiasAPI, perfilAPI } from '../../../lib/api';
import ImageUploader from '../ptam/ImageUploader';

// ── Default empty form ──────────────────────────────────────────────────────
const EMPTY = {
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

// Detecta se é laudo bancario
const isBancario = (form) => ['sfh_fgts', 'sfi_bancario', 'alienacao_fiduciaria', 'hipoteca'].includes(form.modalidade_financeira);
const isAlienacao = (form) => form.modalidade_financeira === 'alienacao_fiduciaria';
const isSfhFgts = (form) => form.modalidade_financeira === 'sfh_fgts';

// ── Step definitions ─────────────────────────────────────────────────────────
const STEPS_BANCARIO = [
  { id: 'modalidade',  label: 'Modalidade',    icon: Building2 },
  { id: 'mutuario',    label: 'Mutuário',       icon: User },
  { id: 'imovel',      label: 'Imóvel/Docs',   icon: FileSearch },
  { id: 'vistoria',    label: 'Vistoria',       icon: Camera },
  { id: 'metodologia', label: 'Metodologia',   icon: BarChart2 },
  { id: 'resultado',   label: 'Resultado',      icon: DollarSign },
  { id: 'declaracoes', label: 'Declarações',    icon: ShieldCheck },
];

const STEPS_RURAL = [
  { id: 'tipo',        label: 'Tipo',          icon: ClipboardList },
  { id: 'solicitante', label: 'Solicitante',   icon: User },
  { id: 'bem',         label: 'Descrição',     icon: Package },
  { id: 'localizacao', label: 'Localização',   icon: MapPin },
  { id: 'avaliacao',   label: 'Avaliação',     icon: BarChart2 },
  { id: 'resultado',   label: 'Resultado',     icon: DollarSign },
  { id: 'conclusao',   label: 'Conclusão',     icon: Award },
];

const TIPO_OPTIONS = [
  { value: 'imovel_rural', label: 'Imóvel Rural',   desc: 'Terras, fazendas, sítios, gleba',     icon: Tractor },
  { value: 'graos_safra',  label: 'Grãos / Safra',  desc: 'Soja, milho, café, cana, etc.',       icon: Wheat },
  { value: 'bovinos',      label: 'Bovinos',         desc: 'Rebanho bovino, pecuária de corte/leite', icon: Beef },
  { value: 'equipamentos', label: 'Equipamentos',   desc: 'Maquinário agrícola, implementos',    icon: Wrench },
  { value: 'veiculos',     label: 'Veículos',        desc: 'Caminhões, tratores, utilitários',    icon: Car },
  { value: 'outros',       label: 'Outros',          desc: 'Demais bens dados em garantia',       icon: Package },
];

const FINALIDADE_OPTIONS = [
  { value: 'credito_rural',        label: 'Crédito Rural' },
  { value: 'financiamento',        label: 'Financiamento' },
  { value: 'penhor',               label: 'Penhor' },
  { value: 'alienacao_fiduciaria', label: 'Alienação Fiduciária' },
  { value: 'outros',               label: 'Outros' },
];

const MODALIDADE_OPTIONS = [
  { value: 'sfh_fgts',             label: 'SFH / FGTS', desc: 'Sistema Financeiro Habitacional — Lei 4.380/1964 | Lei 8.036/1990' },
  { value: 'sfi_bancario',         label: 'SFI / Bancário', desc: 'Sistema Financeiro Imobiliário — Lei 9.514/1997' },
  { value: 'alienacao_fiduciaria', label: 'Alienação Fiduciária', desc: 'Lei 9.514/1997 art. 27 — VLF obrigatório' },
  { value: 'hipoteca',             label: 'Hipoteca', desc: 'Garantia hipotecária sobre imóvel' },
  { value: 'credito_rural',        label: 'Crédito Rural', desc: 'Financiamento agropecuário / rural' },
];

const BANCOS_OPTIONS = [
  'Caixa Econômica Federal', 'Banco do Brasil', 'Bradesco', 'Itaú Unibanco',
  'Santander', 'BTG Pactual', 'Sicoob', 'Sicredi', 'Banrisul',
  'BRB', 'Daycoval', 'Safra', 'Votorantim', 'Outros',
];

const UF_OPTIONS = [
  'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS',
  'MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO',
];

// ── Helpers ──────────────────────────────────────────────────────────────────
const Field = ({ label, children, required, hint }) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">
      {label}{required && <span className="text-red-500 ml-0.5">*</span>}
    </label>
    {children}
    {hint && <p className="text-[11px] text-gray-400 mt-1">{hint}</p>}
  </div>
);

const Input = ({ value, onChange, ...props }) => (
  <input
    value={value ?? ''}
    onChange={onChange}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
  />
);

const Textarea = ({ value, onChange, rows = 3, ...props }) => (
  <textarea
    value={value ?? ''}
    onChange={onChange}
    rows={rows}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white resize-none"
  />
);

const Select = ({ value, onChange, children, ...props }) => (
  <select
    value={value ?? ''}
    onChange={onChange}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
  >
    {children}
  </select>
);

const SectionTitle = ({ children }) => (
  <h3 className="text-sm font-semibold text-emerald-800 uppercase tracking-wider mb-4 pb-2 border-b border-emerald-100">
    {children}
  </h3>
);

const Checkbox = ({ checked, onChange, label }) => (
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

// Alerta CRECI/CREA
const AlertaCRECI = () => (
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

// Alerta SFH/FGTS
const AlertaSFH = () => (
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

// ── STEPS BANCÁRIOS ────────────────────────────────────────────────────────────

// Step 1 — Modalidade Financeira
const StepModalidade = ({ form, set }) => (
  <div className="space-y-6">
    <AlertaCRECI />
    <SectionTitle>Modalidade Financeira</SectionTitle>
    <div className="grid md:grid-cols-2 gap-3">
      {MODALIDADE_OPTIONS.map(({ value, label, desc }) => (
        <button
          key={value}
          type="button"
          onClick={() => {
            set('modalidade_financeira', value);
            if (value === 'sfh_fgts') set('ltv_maximo', 80);
            if (value === 'sfh_fgts' || value === 'sfi_bancario' || value === 'alienacao_fiduciaria') {
              set('validade_laudo_meses', 12);
            }
          }}
          className={`flex flex-col items-start gap-1 p-4 rounded-xl border-2 text-left transition ${
            form.modalidade_financeira === value
              ? 'border-emerald-700 bg-emerald-50'
              : 'border-gray-200 hover:border-emerald-300 hover:bg-gray-50'
          }`}
        >
          <div className="font-semibold text-sm text-gray-900">{label}</div>
          <div className="text-[11px] text-gray-500 leading-tight">{desc}</div>
        </button>
      ))}
    </div>

    {isSfhFgts(form) && <AlertaSFH />}

    <SectionTitle>Instituição Financeira Credora</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Instituição Financeira" required>
        <Select value={form.instituicao_financeira} onChange={(e) => set('instituicao_financeira', e.target.value)}>
          <option value="">Selecionar banco...</option>
          {BANCOS_OPTIONS.map((b) => <option key={b} value={b}>{b}</option>)}
        </Select>
      </Field>
      <Field label="Valor do Financiamento (R$)" required>
        <Input
          type="number"
          value={form.valor_financiamento}
          onChange={(e) => set('valor_financiamento', parseFloat(e.target.value) || 0)}
        />
      </Field>
      <Field label="LTV Máximo (%)" hint="80% para SFH | 90% SFI conforme CMN 4.676/2018">
        <Input
          type="number"
          value={form.ltv_maximo}
          onChange={(e) => set('ltv_maximo', parseFloat(e.target.value) || 0)}
        />
      </Field>
      <Field label="Prazo do Financiamento (meses)">
        <Input
          type="number"
          value={form.prazo_financiamento_meses}
          onChange={(e) => set('prazo_financiamento_meses', parseInt(e.target.value) || 0)}
        />
      </Field>
    </div>

    <SectionTitle>Tipo e Finalidade do Bem</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Tipo de Bem em Garantia">
        <Select value={form.tipo_garantia} onChange={(e) => set('tipo_garantia', e.target.value)}>
          <option value="imovel_urbano">Imóvel Urbano</option>
          <option value="imovel_rural">Imóvel Rural</option>
          <option value="apartamento">Apartamento</option>
          <option value="casa">Casa</option>
          <option value="comercial">Imóvel Comercial</option>
          <option value="terreno">Terreno</option>
        </Select>
      </Field>
      <Field label="Finalidade do Crédito">
        <Select value={form.finalidade_credito} onChange={(e) => set('finalidade_credito', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="aquisicao">Aquisição</option>
          <option value="reforma">Reforma / Ampliação</option>
          <option value="construcao">Construção</option>
          <option value="refinanciamento">Refinanciamento</option>
        </Select>
      </Field>
    </div>
  </div>
);

// Step 2 — Mutuário / Garantidor
const StepMutuario = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Dados do Mutuário / Garantidor</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Nome do Mutuário / Garantidor" required>
        <Input
          value={form.mutuario_nome}
          onChange={(e) => set('mutuario_nome', e.target.value)}
          placeholder="Nome completo ou Razão Social"
        />
      </Field>
      <Field label="CPF / CNPJ" required>
        <Input
          value={form.mutuario_cpf_cnpj}
          onChange={(e) => set('mutuario_cpf_cnpj', e.target.value)}
          placeholder="000.000.000-00"
        />
      </Field>
    </div>

    <SectionTitle>Solicitante / Contato</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Nome do Solicitante">
        <Input
          value={form.solicitante?.nome}
          onChange={(e) => set('solicitante', { ...form.solicitante, nome: e.target.value })}
          placeholder="Ex.: Gerente de Crédito"
        />
      </Field>
      <Field label="Telefone">
        <Input
          value={form.solicitante?.telefone}
          onChange={(e) => set('solicitante', { ...form.solicitante, telefone: e.target.value })}
          placeholder="(00) 00000-0000"
        />
      </Field>
      <Field label="E-mail">
        <Input
          type="email"
          value={form.solicitante?.email}
          onChange={(e) => set('solicitante', { ...form.solicitante, email: e.target.value })}
          placeholder="email@banco.com.br"
        />
      </Field>
      <Field label="CPF/CNPJ do Solicitante">
        <Input
          value={form.solicitante?.cpf_cnpj}
          onChange={(e) => set('solicitante', { ...form.solicitante, cpf_cnpj: e.target.value })}
        />
      </Field>
    </div>
  </div>
);

// Step 3 — Imóvel e Documentação
const StepImovelDocs = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Endereço e Registro</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Endereço Completo" required className="md:col-span-2">
        <Input value={form.endereco} onChange={(e) => set('endereco', e.target.value)} placeholder="Rua, número, complemento..." />
      </Field>
      <Field label="Município" required>
        <Input value={form.municipio} onChange={(e) => set('municipio', e.target.value)} />
      </Field>
      <Field label="UF">
        <Select value={form.uf} onChange={(e) => set('uf', e.target.value)}>
          <option value="">Selecionar...</option>
          {UF_OPTIONS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
        </Select>
      </Field>
      <Field label="CEP">
        <Input value={form.cep} onChange={(e) => set('cep', e.target.value)} placeholder="00000-000" />
      </Field>
      <Field label="Matrícula do Imóvel" required hint="Certidão com no máximo 30 dias (CMN 4.676/2018)">
        <Input value={form.matricula} onChange={(e) => set('matricula', e.target.value)} />
      </Field>
      <Field label="Data da Certidão de Matrícula" hint="Máximo 30 dias de emissão">
        <Input type="date" value={form.data_matricula} onChange={(e) => set('data_matricula', e.target.value)} />
      </Field>
      <Field label="Cartório de Registro de Imóveis (CRI)" required>
        <Input value={form.cartorio} onChange={(e) => set('cartorio', e.target.value)} placeholder="Cartório de Registro de Imóveis de..." />
      </Field>
      <Field label="Número do CRI">
        <Input value={form.cri_numero} onChange={(e) => set('cri_numero', e.target.value)} />
      </Field>
    </div>

    <SectionTitle>Dados Fiscais</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Inscrição IPTU">
        <Input value={form.inscricao_iptu} onChange={(e) => set('inscricao_iptu', e.target.value)} />
      </Field>
      <Field label="Valor Venal (R$)" hint="Conforme carnê de IPTU">
        <Input type="number" value={form.valor_venal} onChange={(e) => set('valor_venal', parseFloat(e.target.value) || 0)} />
      </Field>
    </div>

    <SectionTitle>Características Físicas (NBR 14653-2:2011)</SectionTitle>
    <div className="grid md:grid-cols-3 gap-4">
      <Field label="Área do Terreno (m²)">
        <Input type="number" value={form.area_total_ha} onChange={(e) => set('area_total_ha', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Área Construída Total (m²)">
        <Input type="number" value={form.area_construida_m2} onChange={(e) => set('area_construida_m2', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Área Privativa NBR 12.721 (m²)" required hint="Conforme memorial da incorporadora / CRI">
        <Input type="number" value={form.area_privativa_nbr12721} onChange={(e) => set('area_privativa_nbr12721', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Padrão Construtivo IBAPE" required>
        <Select value={form.padrao_construtivo_ibape} onChange={(e) => set('padrao_construtivo_ibape', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="baixo">Baixo</option>
          <option value="normal">Normal</option>
          <option value="alto">Alto</option>
          <option value="luxo">Luxo</option>
        </Select>
      </Field>
      <Field label="Idade Real (anos)">
        <Input type="number" value={form.idade_real_anos} onChange={(e) => set('idade_real_anos', parseInt(e.target.value) || 0)} />
      </Field>
      <Field label="Idade Aparente (anos)">
        <Input type="number" value={form.idade_aparente_anos} onChange={(e) => set('idade_aparente_anos', parseInt(e.target.value) || 0)} />
      </Field>
      <Field label="Estado de Conservação">
        <Select value={form.estado_conservacao} onChange={(e) => set('estado_conservacao', e.target.value)}>
          <option value="otimo">Ótimo</option>
          <option value="bom">Bom</option>
          <option value="regular">Regular</option>
          <option value="precario">Precário</option>
        </Select>
      </Field>
    </div>

    <SectionTitle>Regularidade Jurídica</SectionTitle>
    <div className="space-y-3">
      <Checkbox
        checked={form.habite_se}
        onChange={(v) => set('habite_se', v)}
        label="Imóvel possui Habite-se / Carta de Habitação (obrigatório SFH/FGTS)"
      />
      <Checkbox
        checked={form.onus_reais}
        onChange={(v) => set('onus_reais', v)}
        label="Existência de ônus reais na matrícula"
      />
      {form.onus_reais && (
        <Field label="Descrição dos Ônus Reais">
          <Textarea value={form.onus_descricao} onChange={(e) => set('onus_descricao', e.target.value)} placeholder="Descreva as gravames, hipotecas, penhoras, etc." />
        </Field>
      )}
      <Checkbox
        checked={form.conformidade_plano_diretor}
        onChange={(v) => set('conformidade_plano_diretor', v)}
        label="Imóvel em conformidade com o Plano Diretor Municipal"
      />
      <Checkbox
        checked={form.regularidade_construtiva}
        onChange={(v) => set('regularidade_construtiva', v)}
        label="Regularidade construtiva (construção conforme aprovação)"
      />
    </div>

    {isSfhFgts(form) && (
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-800">
        <strong>SFH/FGTS:</strong> Imóvel não pode ter sido adquirido com FGTS nos últimos 3 anos (Lei 8.036/1990 art. 20). Matrícula não pode estar em nome de Pessoa Jurídica.
      </div>
    )}
  </div>
);

// Step 4 — Vistoria Técnica
const StepVistoria = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Vistoria Técnica</SectionTitle>
    <div className="grid md:grid-cols-3 gap-4">
      <Field label="Data da Vistoria" required>
        <Input type="date" value={form.data_vistoria} onChange={(e) => set('data_vistoria', e.target.value)} />
      </Field>
      <Field label="Horário">
        <Input type="time" value={form.vistoria_horario} onChange={(e) => set('vistoria_horario', e.target.value)} />
      </Field>
      <Field label="Responsável pela Vistoria" required hint="CREA/CAU obrigatório">
        <Input value={form.vistoria_responsavel_nome} onChange={(e) => set('vistoria_responsavel_nome', e.target.value)} placeholder="Nome do Engenheiro / Arquiteto" />
      </Field>
    </div>
    <Field label="Condições e Observações da Vistoria">
      <Textarea
        value={form.vistoria_condicoes_obs}
        onChange={(e) => set('vistoria_condicoes_obs', e.target.value)}
        rows={4}
        placeholder="Descreva as condições de acesso, condições climáticas, presença do proprietário, etc."
      />
    </Field>
    <Field label="Observações Gerais">
      <Textarea
        value={form.observacoes}
        onChange={(e) => set('observacoes', e.target.value)}
        rows={3}
        placeholder="Outras observações relevantes para a vistoria..."
      />
    </Field>

    <SectionTitle>Fotos da Vistoria</SectionTitle>
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 mb-3">
      Mínimo de 10 fotos obrigatórias: fachada, cômodos principais, área externa, entorno e número de RGI/matrícula.
    </div>
    <ImageUploader
      images={form.fotos}
      onImagesChange={(ids) => set('fotos', ids)}
      maxImages={20}
      label={`Fotos da Vistoria (${form.fotos?.length || 0}/20 — mínimo 10)`}
      accept="image/jpeg,image/jpg,image/png,image/webp"
    />
  </div>
);

// Step 5 — Análise e Metodologia
const StepMetodologia = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Caracterização do Imóvel</SectionTitle>
    <Field label="Características Construtivas">
      <Textarea
        value={form.descricao_bem}
        onChange={(e) => set('descricao_bem', e.target.value)}
        rows={4}
        placeholder="Estrutura, alvenaria, cobertura, instalações, acabamentos..."
      />
    </Field>
    <Field label="Infraestrutura do Entorno">
      <Textarea
        value={form.infraestrutura_entorno}
        onChange={(e) => set('infraestrutura_entorno', e.target.value)}
        rows={3}
        placeholder="Ruas pavimentadas, iluminação, saneamento, transporte público, comércio, serviços..."
      />
    </Field>
    <Field label="Liquidez e Absorção de Mercado">
      <Textarea
        value={form.liquidez_mercado}
        onChange={(e) => set('liquidez_mercado', e.target.value)}
        rows={3}
        placeholder="Tempo médio de venda, demanda, oferta, tendência do mercado local..."
      />
    </Field>

    <SectionTitle>Metodologia Avaliatória (NBR 14653-1:2019)</SectionTitle>
    <Field label="Método Utilizado" required hint="Método Comparativo Direto é prioritário conforme CMN 4.676/2018">
      <Select value={form.metodologia} onChange={(e) => set('metodologia', e.target.value)}>
        <option value="">Selecionar...</option>
        <option value="comparativo_direto">Método Comparativo Direto de Dados de Mercado (prioritário)</option>
        <option value="evolutivo">Método Evolutivo / Custo de Reprodução</option>
        <option value="renda">Método da Renda</option>
        <option value="involutivo">Método Involutivo</option>
      </Select>
    </Field>
    <Field label="Fundamentação Legal">
      <Input value={form.fundamentacao_legal} onChange={(e) => set('fundamentacao_legal', e.target.value)} />
    </Field>

    <SectionTitle>Tratamento de Amostras</SectionTitle>
    <div className="grid md:grid-cols-3 gap-4">
      <Field label="Número de Amostras" hint="Mínimo 3 (Grau III) | 5+ (Grau II)">
        <Input type="number" value={form.num_amostras} onChange={(e) => set('num_amostras', parseInt(e.target.value) || 0)} />
      </Field>
      <Field label="Coeficiente de Variação (%)" hint="Máximo 30% (NBR 14653-2)">
        <Input type="number" value={form.coeficiente_variacao} onChange={(e) => set('coeficiente_variacao', parseFloat(e.target.value) || 0)}
          className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 bg-white ${
            form.coeficiente_variacao > 30 ? 'border-red-400 focus:ring-red-400' : 'border-gray-200 focus:ring-emerald-500'
          }`}
        />
        {form.coeficiente_variacao > 30 && (
          <p className="text-xs text-red-600 mt-1">Coeficiente superior a 30% — revisar amostragem (NBR 14653-2)</p>
        )}
      </Field>
      <Field label="Grau de Precisão" required>
        <Select value={form.grau_precisao} onChange={(e) => set('grau_precisao', e.target.value)}>
          <option value="II">Grau II</option>
          <option value="III">Grau III</option>
        </Select>
      </Field>
    </div>
    <Field label="Fatores de Homogeneização Aplicados">
      <Textarea
        value={form.fator_homogeneizacao}
        onChange={(e) => set('fator_homogeneizacao', e.target.value)}
        rows={3}
        placeholder="Fator área, padrão construtivo, localização, estado de conservação, fator de oferta..."
      />
    </Field>
    <Field label="Mercado de Referência / Fontes">
      <Textarea
        value={form.mercado_referencia}
        onChange={(e) => set('mercado_referencia', e.target.value)}
        rows={3}
        placeholder="Anúncios, negócios realizados, pesquisas de campo, portais imobiliários..."
      />
    </Field>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Grau de Fundamentação (NBR 14653-1)">
        <Select value={form.grau_fundamentacao} onChange={(e) => set('grau_fundamentacao', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="I">Grau I</option>
          <option value="II">Grau II</option>
          <option value="III">Grau III</option>
        </Select>
      </Field>
    </div>
  </div>
);

// Step 6 — Resultado e Valores
const StepResultadoBancario = ({ form, set }) => {
  const vm = Number(form.valor_mercado) || 0;
  const ltv = Number(form.ltv_maximo) || 80;
  const descVlf = Number(form.fator_desconto_vlf) || 0;

  const valorMaxGarantia = vm * (ltv / 100);
  const vlf = vm * (1 - descVlf / 100);
  const v1Leilao = vm * 0.90; // Art. 27 §1 Lei 9.514/97 — não inferior a 90% do valor avaliação
  const v2Leilao = Math.max(vlf, vm * 0.50); // Art. 27 §2 — não inferior ao valor da dívida

  useEffect(() => {
    if (vm > 0) {
      set('valor_maximo_garantia', parseFloat(valorMaxGarantia.toFixed(2)));
      set('campo_arbitrio_min', parseFloat((vm * 0.85).toFixed(2)));
      set('campo_arbitrio_max', parseFloat((vm * 1.15).toFixed(2)));
    }
    if (isAlienacao(form) && vm > 0) {
      set('valor_liquidacao_forcada', parseFloat(vlf.toFixed(2)));
      set('valor_1o_leilao', parseFloat(v1Leilao.toFixed(2)));
      set('valor_2o_leilao', parseFloat(v2Leilao.toFixed(2)));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vm, ltv, descVlf]);

  const fmt = (v) => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

  return (
    <div className="space-y-6">
      <SectionTitle>Resultado da Avaliação</SectionTitle>
      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Valor de Mercado (R$)" required>
          <input
            type="number"
            value={form.valor_mercado}
            onChange={(e) => set('valor_mercado', parseFloat(e.target.value) || 0)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
          />
        </Field>
        <Field label="Valor por Extenso" required>
          <Input
            value={form.resultado_em_extenso}
            onChange={(e) => set('resultado_em_extenso', e.target.value)}
            placeholder="Ex.: Um milhão e duzentos mil reais"
          />
        </Field>
        <Field label="Intervalo Inferior — Campo de Arbítrio −15% (R$)">
          <Input
            type="number"
            value={form.campo_arbitrio_min}
            onChange={(e) => set('campo_arbitrio_min', parseFloat(e.target.value) || 0)}
          />
        </Field>
        <Field label="Intervalo Superior — Campo de Arbítrio +15% (R$)">
          <Input
            type="number"
            value={form.campo_arbitrio_max}
            onChange={(e) => set('campo_arbitrio_max', parseFloat(e.target.value) || 0)}
          />
        </Field>
      </div>

      {/* Painel resumo */}
      {vm > 0 && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 space-y-3">
          <div className="text-xs text-emerald-700 font-semibold uppercase tracking-wider">Resumo dos Valores</div>
          <div className="grid md:grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-xs text-gray-500">Valor de Mercado</div>
              <div className="text-2xl font-bold text-emerald-900">{fmt(vm)}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Valor Máximo de Garantia ({ltv}% LTV)</div>
              <div className="text-lg font-bold text-emerald-800">{fmt(valorMaxGarantia)}</div>
            </div>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Valor Máximo de Garantia — LTV (R$)" hint={`${ltv}% do valor de mercado`}>
          <Input
            type="number"
            value={form.valor_maximo_garantia}
            onChange={(e) => set('valor_maximo_garantia', parseFloat(e.target.value) || 0)}
          />
        </Field>
        <Field label="Grau de Precisão (NBR 14653-1)" required>
          <Select value={form.grau_precisao} onChange={(e) => set('grau_precisao', e.target.value)}>
            <option value="II">Grau II</option>
            <option value="III">Grau III</option>
          </Select>
        </Field>
      </div>

      {/* Alienação Fiduciária */}
      {isAlienacao(form) && (
        <div className="space-y-4">
          <SectionTitle>Alienação Fiduciária — Lei 9.514/1997</SectionTitle>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
            Valores calculados automaticamente com base no valor de mercado e fator de desconto. Revise e ajuste se necessário.
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Fator de Desconto VLF (%)" hint="Justifique tecnicamente o desconto aplicado">
              <Input
                type="number"
                value={form.fator_desconto_vlf}
                onChange={(e) => set('fator_desconto_vlf', parseFloat(e.target.value) || 0)}
              />
            </Field>
            <Field label="Valor de Liquidação Forçada — VLF (R$)" required>
              <Input
                type="number"
                value={form.valor_liquidacao_forcada}
                onChange={(e) => set('valor_liquidacao_forcada', parseFloat(e.target.value) || 0)}
              />
            </Field>
            <Field label="Valor do 1º Leilão (R$)" hint="Art. 27 Lei 9.514/97 — mínimo 90% do valor de avaliação">
              <Input
                type="number"
                value={form.valor_1o_leilao}
                onChange={(e) => set('valor_1o_leilao', parseFloat(e.target.value) || 0)}
              />
            </Field>
            <Field label="Valor do 2º Leilão (R$)" hint="Art. 27 §2 Lei 9.514/97 — mínimo valor da dívida ou VLF">
              <Input
                type="number"
                value={form.valor_2o_leilao}
                onChange={(e) => set('valor_2o_leilao', parseFloat(e.target.value) || 0)}
              />
            </Field>
          </div>
          {form.valor_mercado > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 grid grid-cols-3 gap-4 text-center text-xs">
              <div>
                <div className="text-gray-500 mb-1">VLF</div>
                <div className="font-bold text-amber-900">{fmt(form.valor_liquidacao_forcada)}</div>
              </div>
              <div>
                <div className="text-gray-500 mb-1">1º Leilão</div>
                <div className="font-bold text-amber-900">{fmt(form.valor_1o_leilao)}</div>
              </div>
              <div>
                <div className="text-gray-500 mb-1">2º Leilão</div>
                <div className="font-bold text-amber-900">{fmt(form.valor_2o_leilao)}</div>
              </div>
            </div>
          )}
          <Field label="Justificativa do Fator de Desconto VLF">
            <Textarea
              value={form.fatores_depreciacao}
              onChange={(e) => set('fatores_depreciacao', e.target.value)}
              rows={3}
              placeholder="Justifique tecnicamente o fator de desconto aplicado (liquidez, restrições, mercado, etc.)"
            />
          </Field>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Data de Avaliação" required>
          <Input type="date" value={form.data_avaliacao} onChange={(e) => set('data_avaliacao', e.target.value)} />
        </Field>
        <Field label="Data de Validade do Laudo" hint="12 meses para SFH/FGTS (Circ. BACEN 3.818/2016)">
          <Input type="date" value={form.data_validade} onChange={(e) => set('data_validade', e.target.value)} />
        </Field>
      </div>
    </div>
  );
};

// Step 7 — Declarações e Responsabilidade
const StepDeclaracoes = ({ form, set }) => (
  <div className="space-y-6">
    <AlertaCRECI />

    <SectionTitle>Responsável Técnico (CREA/CAU obrigatório)</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Tipo de Profissional" required>
        <Select value={form.responsavel_tipo} onChange={(e) => set('responsavel_tipo', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="engenheiro">Engenheiro Civil (CREA)</option>
          <option value="arquiteto">Arquiteto e Urbanista (CAU)</option>
        </Select>
      </Field>
      <Field label="Nome do Profissional" required>
        <Input
          value={form.responsavel?.nome}
          onChange={(e) => set('responsavel', { ...form.responsavel, nome: e.target.value })}
          placeholder="Nome completo"
        />
      </Field>
      <Field label="Número CREA ou CAU" required>
        <Input
          value={form.responsavel_crea_cau}
          onChange={(e) => set('responsavel_crea_cau', e.target.value)}
          placeholder="CREA-SP 123456789 ou CAU A000000-0"
        />
      </Field>
      <Field label="UF do Registro">
        <Select value={form.responsavel_uf} onChange={(e) => set('responsavel_uf', e.target.value)}>
          <option value="">Selecionar UF</option>
          {UF_OPTIONS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
        </Select>
      </Field>
      <Field label="Empresa / CPF" hint="Razão Social ou CPF do responsável">
        <Input
          value={form.responsavel_empresa_cpf}
          onChange={(e) => set('responsavel_empresa_cpf', e.target.value)}
        />
      </Field>
    </div>

    <SectionTitle>ART / RRT (Res. CONFEA 1.025/2009)</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Número da ART / RRT" required hint="Obrigatória para fins bancários">
        <Input
          value={form.art_numero}
          onChange={(e) => set('art_numero', e.target.value)}
          placeholder="Número do registro"
        />
      </Field>
      <Field label="Data de Registro da ART / RRT">
        <Input
          type="date"
          value={form.art_data_registro}
          onChange={(e) => set('art_data_registro', e.target.value)}
        />
      </Field>
    </div>

    <SectionTitle>Validade e Prazo</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Validade do Laudo (meses)" hint="12 meses para SFH/FGTS (Circ. BACEN 3.818/2016)">
        <Input
          type="number"
          value={form.validade_laudo_meses}
          onChange={(e) => set('validade_laudo_meses', parseInt(e.target.value) || 12)}
        />
      </Field>
    </div>

    <SectionTitle>Declarações Obrigatórias</SectionTitle>
    <div className="space-y-3">
      <Checkbox
        checked={form.declaracao_conflito_interesse}
        onChange={(v) => set('declaracao_conflito_interesse', v)}
        label="Declaro que não há conflito de interesse entre o profissional avaliador e as partes envolvidas na operação."
      />
    </div>
    <Field label="Declaração de Impedimentos / Restrições">
      <Textarea
        value={form.declaracao_impedimentos}
        onChange={(e) => set('declaracao_impedimentos', e.target.value)}
        rows={3}
        placeholder="Descreva impedimentos legais, relações de parentesco, vínculos ou restrições conhecidas. Se não houver, registre 'Nada a declarar'."
      />
    </Field>

    <SectionTitle>Ressalvas e Considerações Finais</SectionTitle>
    <Field label="Considerações">
      <Textarea
        value={form.consideracoes}
        onChange={(e) => set('consideracoes', e.target.value)}
        rows={3}
        placeholder="Pressupostos, limitações e considerações finais conforme NBR 14653-1:2019..."
      />
    </Field>
    <Field label="Ressalvas">
      <Textarea
        value={form.ressalvas}
        onChange={(e) => set('ressalvas', e.target.value)}
        rows={2}
        placeholder="Ressalvas aplicáveis..."
      />
    </Field>

    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Status do Laudo">
        <Select value={form.status} onChange={(e) => set('status', e.target.value)}>
          <option value="rascunho">Rascunho</option>
          <option value="em_andamento">Em Andamento</option>
          <option value="concluido">Concluído</option>
        </Select>
      </Field>
    </div>
  </div>
);

// ── STEPS RURAIS (modo original) ───────────────────────────────────────────────

const StepTipo = ({ form, set }) => {
  const tipo = form.tipo_garantia;
  return (
    <div className="space-y-6">
      <SectionTitle>Tipo de Garantia</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {TIPO_OPTIONS.map(({ value, label, desc, icon: Icon }) => (
          <button
            key={value}
            type="button"
            onClick={() => set('tipo_garantia', value)}
            className={`flex flex-col items-start gap-2 p-4 rounded-xl border-2 text-left transition ${
              tipo === value
                ? 'border-emerald-700 bg-emerald-50'
                : 'border-gray-200 hover:border-emerald-300 hover:bg-gray-50'
            }`}
          >
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${tipo === value ? 'bg-emerald-900' : 'bg-gray-100'}`}>
              <Icon className={`w-5 h-5 ${tipo === value ? 'text-white' : 'text-gray-600'}`} />
            </div>
            <div>
              <div className="font-semibold text-sm text-gray-900">{label}</div>
              <div className="text-[11px] text-gray-500 leading-tight mt-0.5">{desc}</div>
            </div>
          </button>
        ))}
      </div>

      <SectionTitle>Modalidade Financeira</SectionTitle>
      <div className="grid md:grid-cols-2 gap-3">
        {MODALIDADE_OPTIONS.map(({ value, label, desc }) => (
          <button
            key={value}
            type="button"
            onClick={() => set('modalidade_financeira', value)}
            className={`flex flex-col items-start gap-1 p-3 rounded-xl border-2 text-left transition ${
              form.modalidade_financeira === value
                ? 'border-emerald-700 bg-emerald-50'
                : 'border-gray-200 hover:border-emerald-300 hover:bg-gray-50'
            }`}
          >
            <div className="font-semibold text-sm text-gray-900">{label}</div>
            <div className="text-[11px] text-gray-500 leading-tight">{desc}</div>
          </button>
        ))}
      </div>

      <SectionTitle>Finalidade (Crédito Rural / Outros)</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {FINALIDADE_OPTIONS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => set('finalidade', value)}
            className={`px-4 py-2.5 rounded-lg border-2 text-sm font-medium transition ${
              form.finalidade === value
                ? 'border-emerald-700 bg-emerald-50 text-emerald-900'
                : 'border-gray-200 text-gray-700 hover:border-emerald-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {isBancario(form) && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-800">
          Modalidade bancária detectada. Avance pelo wizard para preencher os campos específicos da Res. CMN 4.676/2018.
        </div>
      )}
    </div>
  );
};

const StepSolicitante = ({ form, setNested }) => {
  const s = form.solicitante || {};
  return (
    <div className="space-y-6">
      <SectionTitle>Dados do Solicitante</SectionTitle>
      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Nome / Razão Social" required>
          <Input value={s.nome} onChange={(e) => setNested('solicitante', 'nome', e.target.value)} placeholder="Ex.: João da Silva" />
        </Field>
        <Field label="CPF / CNPJ">
          <Input value={s.cpf_cnpj} onChange={(e) => setNested('solicitante', 'cpf_cnpj', e.target.value)} placeholder="000.000.000-00" />
        </Field>
        <Field label="Instituição Financeira">
          <Input value={s.instituicao_financeira} onChange={(e) => setNested('solicitante', 'instituicao_financeira', e.target.value)} placeholder="Ex.: Banco do Brasil S.A." />
        </Field>
        <Field label="Telefone">
          <Input value={s.telefone} onChange={(e) => setNested('solicitante', 'telefone', e.target.value)} placeholder="(00) 00000-0000" />
        </Field>
        <Field label="E-mail">
          <Input value={s.email} onChange={(e) => setNested('solicitante', 'email', e.target.value)} placeholder="email@exemplo.com" type="email" />
        </Field>
      </div>
    </div>
  );
};

const StepBem = ({ form, set }) => {
  const tipo = form.tipo_garantia;
  return (
    <div className="space-y-6">
      <SectionTitle>Descrição do Bem</SectionTitle>
      <Field label="Descrição Geral" required>
        <Textarea value={form.descricao_bem} onChange={(e) => set('descricao_bem', e.target.value)} rows={4} placeholder="Descreva detalhadamente o bem dado em garantia..." />
      </Field>
      {tipo === 'imovel_rural' && (
        <div className="space-y-4">
          <SectionTitle>Dados do Imóvel Rural</SectionTitle>
          <div className="grid md:grid-cols-3 gap-4">
            <Field label="Área Total (ha — hectares)"><Input type="number" value={form.area_total_ha} onChange={(e) => set('area_total_ha', parseFloat(e.target.value) || 0)} /></Field>
            <Field label="Área Construída / Benfeitorias (m²)"><Input type="number" value={form.area_construida_m2} onChange={(e) => set('area_construida_m2', parseFloat(e.target.value) || 0)} /></Field>
            <Field label="Uso Atual">
              <Select value={form.uso_atual} onChange={(e) => set('uso_atual', e.target.value)}>
                <option value="">Selecionar...</option>
                <option value="pastagem">Pastagem</option><option value="lavoura">Lavoura</option>
                <option value="floresta">Floresta</option><option value="misto">Misto</option><option value="outros">Outros</option>
              </Select>
            </Field>
          </div>
          <Field label="Benfeitorias"><Textarea value={form.benfeitorias} onChange={(e) => set('benfeitorias', e.target.value)} placeholder="Casas, currais, armazéns, poços, cercas..." /></Field>
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Topografia"><Input value={form.topografia} onChange={(e) => set('topografia', e.target.value)} placeholder="Plana, ondulada, montanhosa..." /></Field>
            <Field label="Solo / Vegetação"><Input value={form.solo_vegetacao} onChange={(e) => set('solo_vegetacao', e.target.value)} placeholder="Latossolo vermelho, cerrado..." /></Field>
          </div>

          {/* ── Documentação Rural ── */}
          <div className="rounded-xl border-2 border-emerald-200 bg-emerald-50/50 p-5">
            <div className="text-sm font-semibold text-emerald-800 mb-4 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-600 inline-block" />
              Registros Rurais
              <span className="text-xs font-normal text-emerald-600 ml-1">— documentação específica de imóvel rural</span>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <Field label={<><strong>SIGEF</strong> — Sistema de Gestão Fundiária</>}>
                <Input value={form.certificacao_sigef || ''} onChange={(e) => set('certificacao_sigef', e.target.value)} placeholder="Código SIGEF" />
              </Field>
              <Field label={<><strong>INCRA</strong> — Cadastro no INCRA</>}>
                <Input value={form.cadastro_incra || ''} onChange={(e) => set('cadastro_incra', e.target.value)} placeholder="Número do cadastro INCRA" />
              </Field>
              <Field label={<><strong>CCIR</strong> — Certificado de Cadastro de Imóvel Rural</>}>
                <Input value={form.ccir || ''} onChange={(e) => set('ccir', e.target.value)} placeholder="Número do CCIR" />
              </Field>
              <Field label={<><strong>NIRF / CIB</strong> — Receita Federal / Cadastro Imobiliário Brasileiro</>}>
                <Input value={form.nirf_cib || ''} onChange={(e) => set('nirf_cib', e.target.value)} placeholder="Número do NIRF ou CIB" />
              </Field>
              <Field label={<><strong>CAR</strong> — Cadastro Ambiental Rural</>}>
                <Input value={form.car || ''} onChange={(e) => set('car', e.target.value)} placeholder="Ex: MA-2100055-XXXXXXXXXXXXXXXX" />
              </Field>
              <Field label="Perímetro (m)">
                <Input
                  type="number"
                  value={form.perimetro_m ?? ''}
                  onChange={(e) => set('perimetro_m', e.target.value === '' ? null : parseFloat(e.target.value) || null)}
                  placeholder="Perímetro total em metros"
                />
              </Field>
            </div>
          </div>
        </div>
      )}
      {tipo === 'graos_safra' && (
        <div className="space-y-4">
          <SectionTitle>Dados dos Grãos / Safra</SectionTitle>
          <div className="grid md:grid-cols-3 gap-4">
            <Field label="Cultura">
              <Select value={form.cultura} onChange={(e) => set('cultura', e.target.value)}>
                <option value="">Selecionar...</option>
                {['Soja','Milho','Café','Cana-de-açúcar','Algodão','Arroz','Feijão','Trigo','Sorgo','Outros'].map((c) => (
                  <option key={c} value={c.toLowerCase()}>{c}</option>
                ))}
              </Select>
            </Field>
            <Field label="Quantidade (toneladas)"><Input type="number" value={form.quantidade_toneladas} onChange={(e) => set('quantidade_toneladas', parseFloat(e.target.value) || 0)} /></Field>
            <Field label="Sacas (60 kg)"><Input type="number" value={form.sacas} onChange={(e) => set('sacas', parseFloat(e.target.value) || 0)} /></Field>
            <Field label="Produtividade (sc/ha)"><Input type="number" value={form.produtividade_sc_ha} onChange={(e) => set('produtividade_sc_ha', parseFloat(e.target.value) || 0)} /></Field>
            <Field label="Safra Referência"><Input value={form.safra_referencia} onChange={(e) => set('safra_referencia', e.target.value)} placeholder="Ex.: 2024/2025" /></Field>
            <Field label="Local de Armazenagem"><Input value={form.local_armazenagem} onChange={(e) => set('local_armazenagem', e.target.value)} /></Field>
          </div>
        </div>
      )}
      {tipo === 'bovinos' && (
        <div className="space-y-4">
          <SectionTitle>Dados do Rebanho Bovino</SectionTitle>
          <div className="grid md:grid-cols-3 gap-4">
            <Field label="Raça / Tipo"><Input value={form.raca_tipo} onChange={(e) => set('raca_tipo', e.target.value)} placeholder="Ex.: Nelore, Angus..." /></Field>
            <Field label="Quantidade (cabeças)"><Input type="number" value={form.quantidade_cabecas} onChange={(e) => set('quantidade_cabecas', parseInt(e.target.value) || 0)} /></Field>
            <Field label="Categoria">
              <Select value={form.categoria} onChange={(e) => set('categoria', e.target.value)}>
                <option value="">Selecionar...</option>
                <option value="boi_gordo">Boi Gordo</option><option value="vaca">Vaca</option>
                <option value="novilha">Novilha</option><option value="bezerro">Bezerro</option>
                <option value="touro">Touro</option><option value="misto">Misto</option>
              </Select>
            </Field>
            <Field label="Peso Médio (kg)"><Input type="number" value={form.peso_medio_kg} onChange={(e) => set('peso_medio_kg', parseFloat(e.target.value) || 0)} /></Field>
            <Field label="Aptidão">
              <Select value={form.aptidao} onChange={(e) => set('aptidao', e.target.value)}>
                <option value="">Selecionar...</option>
                <option value="corte">Corte</option><option value="leite">Leite</option><option value="misto">Misto</option>
              </Select>
            </Field>
            <Field label="Local do Rebanho"><Input value={form.local_rebanho} onChange={(e) => set('local_rebanho', e.target.value)} /></Field>
          </div>
        </div>
      )}
      {(tipo === 'equipamentos' || tipo === 'veiculos' || tipo === 'outros') && (
        <div className="space-y-4">
          <SectionTitle>Dados do {tipo === 'equipamentos' ? 'Equipamento' : tipo === 'veiculos' ? 'Veículo' : 'Bem'}</SectionTitle>
          <div className="grid md:grid-cols-3 gap-4">
            <Field label="Marca"><Input value={form.marca} onChange={(e) => set('marca', e.target.value)} /></Field>
            <Field label="Modelo"><Input value={form.modelo} onChange={(e) => set('modelo', e.target.value)} /></Field>
            <Field label="Ano de Fabricação"><Input type="number" value={form.ano_fabricacao} onChange={(e) => set('ano_fabricacao', parseInt(e.target.value) || 0)} /></Field>
            <Field label="Número de Série / Chassi"><Input value={form.numero_serie} onChange={(e) => set('numero_serie', e.target.value)} /></Field>
            {tipo === 'equipamentos' && <Field label="Potência"><Input value={form.potencia} onChange={(e) => set('potencia', e.target.value)} placeholder="Ex.: 150 cv" /></Field>}
            <Field label={tipo === 'equipamentos' ? 'Horímetro' : 'Hodômetro'}>
              <Input value={form.horimetro_hodometro} onChange={(e) => set('horimetro_hodometro', e.target.value)} />
            </Field>
          </div>
        </div>
      )}
    </div>
  );
};

const StepLocalizacao = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Localização</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Endereço">
        <Input value={form.endereco} onChange={(e) => set('endereco', e.target.value)} placeholder="Rua, número, complemento..." />
      </Field>
      <Field label="Município" required>
        <Input value={form.municipio} onChange={(e) => set('municipio', e.target.value)} />
      </Field>
      <Field label="UF">
        <Select value={form.uf} onChange={(e) => set('uf', e.target.value)}>
          <option value="">Selecionar UF</option>
          {UF_OPTIONS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
        </Select>
      </Field>
      <Field label="CEP"><Input value={form.cep} onChange={(e) => set('cep', e.target.value)} placeholder="00000-000" /></Field>
      <Field label="Matrícula / NIRF"><Input value={form.matricula} onChange={(e) => set('matricula', e.target.value)} /></Field>
      <Field label="Cartório de Registro"><Input value={form.cartorio} onChange={(e) => set('cartorio', e.target.value)} /></Field>
    </div>
    <SectionTitle>Coordenadas GPS</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Latitude"><Input value={form.gps_lat} onChange={(e) => set('gps_lat', e.target.value)} placeholder="-12.345678" /></Field>
      <Field label="Longitude"><Input value={form.gps_lng} onChange={(e) => set('gps_lng', e.target.value)} placeholder="-55.123456" /></Field>
    </div>
    <SectionTitle>Vistoria</SectionTitle>
    <Field label="Data da Vistoria"><Input type="date" value={form.data_vistoria} onChange={(e) => set('data_vistoria', e.target.value)} /></Field>
    <Field label="Observações da Vistoria">
      <Textarea value={form.observacoes} onChange={(e) => set('observacoes', e.target.value)} rows={3} />
    </Field>
  </div>
);

const StepAvaliacao = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Metodologia (NBR 14.653)</SectionTitle>
    <Field label="Metodologia Utilizada" required>
      <Select value={form.metodologia} onChange={(e) => set('metodologia', e.target.value)}>
        <option value="">Selecionar...</option>
        <option value="comparativo_direto">Método Comparativo Direto de Dados de Mercado</option>
        <option value="renda">Método da Renda</option>
        <option value="involutivo">Método Involutivo</option>
        <option value="evolutivo">Método Evolutivo / Custo de Reprodução</option>
        <option value="producao">Método da Capitalização da Renda (Agropecuária)</option>
        <option value="cotacao_mercado">Cotação de Mercado (grãos/bovinos)</option>
        <option value="outros">Outros</option>
      </Select>
    </Field>
    <Field label="Fundamentação Legal"><Input value={form.fundamentacao_legal} onChange={(e) => set('fundamentacao_legal', e.target.value)} /></Field>
    <Field label="Mercado de Referência">
      <Textarea value={form.mercado_referencia} onChange={(e) => set('mercado_referencia', e.target.value)} rows={3} />
    </Field>
    <Field label="Fatores de Depreciação / Homogeneização">
      <Textarea value={form.fatores_depreciacao} onChange={(e) => set('fatores_depreciacao', e.target.value)} rows={3} />
    </Field>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Grau de Fundamentação">
        <Select value={form.grau_fundamentacao} onChange={(e) => set('grau_fundamentacao', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="I">Grau I</option><option value="II">Grau II</option><option value="III">Grau III</option>
        </Select>
      </Field>
      <Field label="Estado de Conservação">
        <Select value={form.estado_conservacao} onChange={(e) => set('estado_conservacao', e.target.value)}>
          <option value="otimo">Ótimo</option><option value="bom">Bom</option>
          <option value="regular">Regular</option><option value="precario">Precário</option>
        </Select>
      </Field>
      <Field label="Data de Avaliação"><Input type="date" value={form.data_avaliacao} onChange={(e) => set('data_avaliacao', e.target.value)} /></Field>
      <Field label="Data de Validade"><Input type="date" value={form.data_validade} onChange={(e) => set('data_validade', e.target.value)} /></Field>
    </div>
  </div>
);

const StepResultadoRural = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Resultado da Avaliação</SectionTitle>
    <div className="grid md:grid-cols-3 gap-4">
      <Field label="Valor Unitário (R$)">
        <Input type="number" value={form.valor_unitario} onChange={(e) => set('valor_unitario', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Valor Total (R$)" required>
        <Input type="number" value={form.valor_total} onChange={(e) => set('valor_total', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Status">
        <Select value={form.status} onChange={(e) => set('status', e.target.value)}>
          <option value="rascunho">Rascunho</option>
          <option value="em_andamento">Em Andamento</option>
          <option value="concluido">Concluído</option>
        </Select>
      </Field>
      <Field label="Intervalo Inferior (R$)"><Input type="number" value={form.resultado_intervalo_inf} onChange={(e) => set('resultado_intervalo_inf', parseFloat(e.target.value) || 0)} /></Field>
      <Field label="Intervalo Superior (R$)"><Input type="number" value={form.resultado_intervalo_sup} onChange={(e) => set('resultado_intervalo_sup', parseFloat(e.target.value) || 0)} /></Field>
    </div>
    <Field label="Valor por Extenso"><Input value={form.resultado_em_extenso} onChange={(e) => set('resultado_em_extenso', e.target.value)} placeholder="Ex.: Um milhão e duzentos mil reais" /></Field>
    {form.valor_total > 0 && (
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
        <div className="text-xs text-emerald-700 font-semibold uppercase tracking-wider mb-1">Valor Total Avaliado</div>
        <div className="text-3xl font-bold text-emerald-900">
          {Number(form.valor_total).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
        </div>
      </div>
    )}
  </div>
);

const StepConclusao = ({ form, set, setNested }) => {
  const r = form.responsavel || {};
  return (
    <div className="space-y-6">
      <SectionTitle>Considerações Finais</SectionTitle>
      <Field label="Considerações"><Textarea value={form.consideracoes} onChange={(e) => set('consideracoes', e.target.value)} rows={4} /></Field>
      <Field label="Ressalvas"><Textarea value={form.ressalvas} onChange={(e) => set('ressalvas', e.target.value)} rows={3} /></Field>
      <SectionTitle>Responsável Técnico</SectionTitle>
      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Nome do Responsável" required><Input value={r.nome} onChange={(e) => setNested('responsavel', 'nome', e.target.value)} /></Field>
        <Field label="CRECI"><Input value={r.creci} onChange={(e) => setNested('responsavel', 'creci', e.target.value)} /></Field>
        <Field label="CNAI"><Input value={r.cnai} onChange={(e) => setNested('responsavel', 'cnai', e.target.value)} /></Field>
        <Field label="Registro Complementar (CREA/CAU)"><Input value={r.registro} onChange={(e) => setNested('responsavel', 'registro', e.target.value)} /></Field>
      </div>
    </div>
  );
};

// ── Main Wizard ───────────────────────────────────────────────────────────────
const GarantiaWizard = () => {
  const { id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();

  const isNew = !id || id === 'nova';
  const [form, setForm] = useState({ ...EMPTY });
  const [garantiaId, setGarantiaId] = useState(isNew ? null : id);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const debounceRef = useRef(null);

  const load = useCallback(async () => {
    if (!garantiaId) return;
    setLoading(true);
    try {
      const data = await garantiasAPI.get(garantiaId);
      setForm({ ...EMPTY, ...data });
    } catch (err) {
      console.warn(err);
      toast({ title: 'Erro ao carregar avaliação', variant: 'destructive' });
      nav('/dashboard/garantias');
    } finally {
      setLoading(false);
    }
  }, [garantiaId, nav, toast]);

  useEffect(() => { load(); }, [load]);

  // Pre-fill technician fields from profile when creating a new Garantia
  useEffect(() => {
    if (!isNew) return;
    perfilAPI.get().then((p) => {
      if (!p) return;
      const creci = (p.registros || []).find(r => r.tipo === 'CRECI' && r.status === 'ativo');
      const cnai  = (p.registros || []).find(r => r.tipo === 'CNAI'  && r.status === 'ativo');
      const crea  = (p.registros || []).find(r => r.tipo === 'CREA'  && r.status === 'ativo');
      const cau   = (p.registros || []).find(r => r.tipo === 'CAU'   && r.status === 'ativo');

      const registroCreaOuCau = crea
        ? `${crea.numero}`
        : cau ? `${cau.numero}` : '';
      const ufRegistro = crea?.uf || cau?.uf || '';
      const tipoProf = crea ? 'engenheiro' : cau ? 'arquiteto' : '';

      setForm(f => ({
        ...f,
        // Campos nested (rural e bancario compartilham responsavel.nome)
        responsavel: {
          ...f.responsavel,
          nome:     p.nome_completo || f.responsavel?.nome || '',
          creci:    creci ? `CRECI${creci.uf ? '/' + creci.uf : ''} ${creci.numero}` : f.responsavel?.creci || '',
          cnai:     cnai  ? `CNAI ${cnai.numero}` : f.responsavel?.cnai || '',
          registro: registroCreaOuCau || f.responsavel?.registro || '',
        },
        // Campos flat (bancario)
        responsavel_crea_cau:     registroCreaOuCau || f.responsavel_crea_cau,
        responsavel_uf:           ufRegistro        || f.responsavel_uf,
        responsavel_tipo:         tipoProf           || f.responsavel_tipo,
        responsavel_empresa_cpf:  p.empresa_cnpj || p.empresa_nome || f.responsavel_empresa_cpf,
        vistoria_responsavel_nome: p.nome_completo || f.vistoria_responsavel_nome,
        municipio: f.municipio || p.cidade || '',
        uf:        f.uf        || p.uf     || '',
      }));
    }).catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const save = useCallback(async (silent = false) => {
    setSaving(true);
    try {
      if (garantiaId) {
        await garantiasAPI.update(garantiaId, form);
      } else {
        const created = await garantiasAPI.create(form);
        setGarantiaId(created.id);
        setForm((f) => ({ ...f, numero: created.numero }));
        nav(`/dashboard/garantias/${created.id}`, { replace: true });
      }
      setLastSaved(new Date());
      if (!silent) toast({ title: 'Rascunho salvo' });
    } catch (err) {
      console.warn(err);
      if (!silent) toast({ title: 'Erro ao salvar', description: err.response?.data?.detail, variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  }, [form, garantiaId, nav, toast]);

  useEffect(() => {
    if (!garantiaId) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => save(true), 30000);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [form, garantiaId, save]);

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));
  const setNested = (obj, key, value) =>
    setForm((f) => ({ ...f, [obj]: { ...(f[obj] || {}), [key]: value } }));

  const isBancarioMode = isBancario(form);
  const STEPS = isBancarioMode ? STEPS_BANCARIO : STEPS_RURAL;

  if (loading) return (
    <div className="py-20 flex justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-emerald-800" />
    </div>
  );

  const totalSteps = STEPS.length;

  const renderStep = () => {
    if (isBancarioMode) {
      switch (step) {
        case 0: return <StepModalidade form={form} set={set} />;
        case 1: return <StepMutuario form={form} set={set} />;
        case 2: return <StepImovelDocs form={form} set={set} />;
        case 3: return <StepVistoria form={form} set={set} />;
        case 4: return <StepMetodologia form={form} set={set} />;
        case 5: return <StepResultadoBancario form={form} set={set} />;
        case 6: return <StepDeclaracoes form={form} set={set} />;
        default: return null;
      }
    }
    switch (step) {
      case 0: return <StepTipo form={form} set={set} />;
      case 1: return <StepSolicitante form={form} setNested={setNested} />;
      case 2: return <StepBem form={form} set={set} />;
      case 3: return <StepLocalizacao form={form} set={set} />;
      case 4: return <StepAvaliacao form={form} set={set} />;
      case 5: return <StepResultadoRural form={form} set={set} />;
      case 6: return <StepConclusao form={form} set={set} setNested={setNested} />;
      default: return null;
    }
  };

  const getStepClasses = (i) => {
    if (i === step) return 'bg-emerald-900 text-white';
    if (i < step) return 'bg-emerald-50 text-emerald-900 hover:bg-emerald-100';
    return 'text-gray-500 hover:bg-gray-50';
  };
  const getIconClasses = (i) => {
    if (i === step) return 'bg-white/20';
    if (i < step) return 'bg-emerald-200';
    return 'bg-gray-100';
  };

  return (
    <div className="max-w-5xl mx-auto pb-20">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <Button variant="ghost" onClick={() => nav('/dashboard/garantias')}>
          <ArrowLeft className="w-4 h-4 mr-1" />Voltar
        </Button>
        <div className="flex items-center gap-2">
          {isBancarioMode && (
            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full font-medium">
              Res. CMN 4.676/2018
            </span>
          )}
          {lastSaved && (
            <span className="text-xs text-gray-500">Salvo {lastSaved.toLocaleTimeString('pt-BR')}</span>
          )}
          <Button variant="outline" onClick={() => save(false)} disabled={saving}>
            <Save className="w-4 h-4 mr-1" />{saving ? 'Salvando...' : 'Salvar rascunho'}
          </Button>
        </div>
      </div>

      {/* Progress */}
      <div className="mb-2 flex items-center justify-between text-xs text-gray-500 px-1">
        <span>Passo {step + 1} de {totalSteps}</span>
        <span>{Math.round(((step + 1) / totalSteps) * 100)}% concluído</span>
      </div>
      <div className="mb-4 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-emerald-700 rounded-full transition-all duration-300"
          style={{ width: `${((step + 1) / totalSteps) * 100}%` }}
        />
      </div>

      {/* Stepper tabs */}
      <div className="bg-white rounded-xl border border-gray-200 p-3 mb-6">
        <div className="flex items-center gap-1 overflow-x-auto">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            return (
              <button
                key={s.id}
                onClick={() => setStep(i)}
                className={`flex-shrink-0 flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-xs font-medium transition ${getStepClasses(i)}`}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${getIconClasses(i)}`}>
                  {i < step ? <Check className="w-3 h-3" /> : <Icon className="w-3 h-3" />}
                </div>
                <span className="whitespace-nowrap">{i + 1}. {s.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Step content */}
      <div className="bg-white rounded-xl border border-gray-200 p-8">
        {renderStep()}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between mt-6">
        <Button variant="outline" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>
          <ChevronLeft className="w-4 h-4 mr-1" />Anterior
        </Button>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => save(false)} disabled={saving}>
            <Save className="w-4 h-4 mr-1" />{saving ? 'Salvando...' : 'Salvar'}
          </Button>
          {step < totalSteps - 1 ? (
            <Button
              className="bg-emerald-900 hover:bg-emerald-800 text-white"
              onClick={() => { save(true); setStep(step + 1); }}
            >
              Próximo<ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          ) : (
            <Button
              className="bg-amber-500 hover:bg-amber-400 text-emerald-950 font-semibold"
              onClick={() => { set('status', 'concluido'); save(false); }}
              disabled={saving}
            >
              <Check className="w-4 h-4 mr-1" />Concluir Avaliação
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default GarantiaWizard;
