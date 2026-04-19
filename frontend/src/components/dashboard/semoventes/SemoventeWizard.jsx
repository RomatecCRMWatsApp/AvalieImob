import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, ChevronLeft, ChevronRight, Save, Loader2, Check,
  Beef, PawPrint, Bird, AlertTriangle, Plus, Trash2,
  ClipboardList, User, Layers, Tag, ShieldCheck, Home,
  Camera, BarChart2, DollarSign, Award
} from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { semoventesAPI } from '../../../lib/api';
import ImageUploader from '../ptam/ImageUploader';

// ── Constants ────────────────────────────────────────────────────────────────
const UF_OPTIONS = [
  'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS',
  'MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO',
];

const TIPO_OPTIONS = [
  { value: 'bovino',        label: 'Bovino',         desc: 'Corte, leite ou misto',       icon: Beef },
  { value: 'equino',        label: 'Equino',         desc: 'Cavalos, burros, mulas',      icon: PawPrint },
  { value: 'suino',         label: 'Suíno',          desc: 'Plantel suíno',               icon: PawPrint },
  { value: 'ovino_caprino', label: 'Ovino/Caprino',  desc: 'Ovinos e caprinos',           icon: PawPrint },
  { value: 'aves',          label: 'Aves',            desc: 'Frango, peru, codorna, etc.', icon: Bird },
];

const MODALIDADE_OPTIONS = [
  { value: 'pronaf',            label: 'PRONAF' },
  { value: 'pronamp',           label: 'PRONAMP' },
  { value: 'acc',               label: 'ACC (Adiantamento Cambial)' },
  { value: 'credito_rural_livre', label: 'Crédito Rural Livre' },
  { value: 'moderfrota',        label: 'MODERFROTA' },
  { value: 'abc',               label: 'ABC (Agricultura de Baixo Carbono)' },
];

const CATEGORIA_OPTIONS_BOVINO = [
  { value: 'reprodutores',     label: 'Reprodutores (Touros)' },
  { value: 'matrizes',         label: 'Matrizes (Vacas)' },
  { value: 'novilhas',         label: 'Novilhas' },
  { value: 'garrotes_bezerros', label: 'Garrotes / Bezerros' },
  { value: 'bois_engorda',     label: 'Bois de Engorda' },
];

const CATEGORIA_OPTIONS_EQUINO = [
  { value: 'garanhao',   label: 'Garanhão' },
  { value: 'egua',       label: 'Égua' },
  { value: 'potro',      label: 'Potro/Potranca' },
  { value: 'capao',      label: 'Capão' },
  { value: 'muar',       label: 'Muar/Jumento' },
];

const CATEGORIA_OPTIONS_SUINO = [
  { value: 'reprodutor_suino', label: 'Reprodutor' },
  { value: 'matriz_suina',    label: 'Matriz' },
  { value: 'leitao',          label: 'Leitão' },
  { value: 'terminacao',      label: 'Terminação' },
];

const CATEGORIA_OPTIONS_OVINO = [
  { value: 'carneiro',  label: 'Carneiro/Bode' },
  { value: 'ovelha',    label: 'Ovelha/Cabra' },
  { value: 'cordeiro',  label: 'Cordeiro/Cabrito' },
];

const CATEGORIA_OPTIONS_AVES = [
  { value: 'matrizes_aves',  label: 'Matrizes' },
  { value: 'frangos_corte',  label: 'Frangos de Corte' },
  { value: 'poedeiras',      label: 'Poedeiras' },
  { value: 'perus',          label: 'Perus' },
  { value: 'outros_aves',    label: 'Outros' },
];

const getCategoriaOptions = (tipo) => {
  switch (tipo) {
    case 'bovino': return CATEGORIA_OPTIONS_BOVINO;
    case 'equino': return CATEGORIA_OPTIONS_EQUINO;
    case 'suino': return CATEGORIA_OPTIONS_SUINO;
    case 'ovino_caprino': return CATEGORIA_OPTIONS_OVINO;
    case 'aves': return CATEGORIA_OPTIONS_AVES;
    default: return CATEGORIA_OPTIONS_BOVINO;
  }
};

const STEPS = [
  { id: 'tipo',         label: 'Tipo',          icon: ClipboardList },
  { id: 'devedor',      label: 'Devedor',       icon: User },
  { id: 'rebanho',      label: 'Rebanho',       icon: Layers },
  { id: 'rastreab',     label: 'Rastreab.',     icon: Tag },
  { id: 'sanitaria',    label: 'Sanitária',     icon: ShieldCheck },
  { id: 'infraestrut',  label: 'Infraest.',     icon: Home },
  { id: 'vistoria',     label: 'Vistoria',      icon: Camera },
  { id: 'mercado',      label: 'Mercado',       icon: BarChart2 },
  { id: 'resultado',    label: 'Resultado',     icon: DollarSign },
  { id: 'declaracoes',  label: 'Declarações',   icon: Award },
];

const EMPTY_CATEGORIA = {
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

const EMPTY = {
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

// ── Base components ───────────────────────────────────────────────────────────
const Field = ({ label, children, required, hint }) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">
      {label}{required && <span className="text-red-500 ml-0.5">*</span>}
    </label>
    {children}
    {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
  </div>
);

const Inp = ({ value, onChange, ...props }) => (
  <input
    value={value ?? ''}
    onChange={onChange}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
  />
);

const Sel = ({ value, onChange, children, ...props }) => (
  <select
    value={value ?? ''}
    onChange={onChange}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
  >
    {children}
  </select>
);

const Txta = ({ value, onChange, rows = 3, ...props }) => (
  <textarea
    value={value ?? ''}
    onChange={onChange}
    rows={rows}
    {...props}
    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white resize-none"
  />
);

const SectionTitle = ({ children }) => (
  <h3 className="text-sm font-semibold text-emerald-800 uppercase tracking-wider mb-4 pb-2 border-b border-emerald-100">
    {children}
  </h3>
);

const CheckRow = ({ label, checked, onChange, hint }) => (
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

const fmtCurrency = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

// ── Step 1 — Tipo e Modalidade ────────────────────────────────────────────────
const Step1Tipo = ({ form, set }) => (
  <div className="space-y-6">
    {/* CRMV Alert */}
    <div className="flex items-start gap-3 bg-red-50 border-2 border-red-300 rounded-xl px-4 py-4">
      <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
      <div>
        <div className="font-bold text-red-800 text-sm">ALERTA LEGAL — CRMV OBRIGATÓRIO</div>
        <p className="text-sm text-red-700 mt-1">
          Avaliação de semoventes para penhor rural exige obrigatoriamente <strong>Médico Veterinário com CRMV ativo</strong>.
          Laudo sem CRMV/CZO é <strong>nulo</strong> para fins bancários.
          (CFMV Res. 722/2002 · Dec.-Lei 167/1967 arts. 9-19 · MCR BACEN Cap. 6)
        </p>
      </div>
    </div>

    <SectionTitle>Espécie Animal</SectionTitle>
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      {TIPO_OPTIONS.map(({ value, label, desc, icon: Icon }) => (
        <button
          key={value}
          type="button"
          onClick={() => set('tipo_semovente', value)}
          className={`flex flex-col items-start gap-2 p-4 rounded-xl border-2 text-left transition ${
            form.tipo_semovente === value
              ? 'border-emerald-700 bg-emerald-50'
              : 'border-gray-200 hover:border-emerald-300 hover:bg-gray-50'
          }`}
        >
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${form.tipo_semovente === value ? 'bg-emerald-900' : 'bg-gray-100'}`}>
            <Icon className={`w-5 h-5 ${form.tipo_semovente === value ? 'text-white' : 'text-gray-600'}`} />
          </div>
          <div>
            <div className="font-semibold text-sm text-gray-900">{label}</div>
            <div className="text-[11px] text-gray-500 leading-tight mt-0.5">{desc}</div>
          </div>
        </button>
      ))}
    </div>

    <SectionTitle>Operação Bancária</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Instituição Financeira" required>
        <Inp value={form.instituicao_financeira} onChange={(e) => set('instituicao_financeira', e.target.value)} placeholder="Ex.: Banco do Brasil S.A." />
      </Field>
      <Field label="Modalidade de Crédito" required>
        <Sel value={form.modalidade_credito} onChange={(e) => set('modalidade_credito', e.target.value)}>
          {MODALIDADE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </Sel>
      </Field>
      <Field label="Valor do Crédito (R$)">
        <Inp type="number" value={form.valor_credito} onChange={(e) => set('valor_credito', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Status">
        <Sel value={form.status} onChange={(e) => set('status', e.target.value)}>
          <option value="rascunho">Rascunho</option>
          <option value="em_andamento">Em Andamento</option>
          <option value="concluido">Concluído</option>
        </Sel>
      </Field>
    </div>
  </div>
);

// ── Step 2 — Devedor e Propriedade ───────────────────────────────────────────
const Step2Devedor = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Dados do Devedor</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Nome / Razão Social" required>
        <Inp value={form.devedor_nome} onChange={(e) => set('devedor_nome', e.target.value)} placeholder="Nome completo ou razão social" />
      </Field>
      <Field label="CPF / CNPJ">
        <Inp value={form.devedor_cpf_cnpj} onChange={(e) => set('devedor_cpf_cnpj', e.target.value)} placeholder="000.000.000-00" />
      </Field>
    </div>

    <SectionTitle>Propriedade Rural</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Nome da Fazenda / Propriedade" required>
        <Inp value={form.propriedade_nome} onChange={(e) => set('propriedade_nome', e.target.value)} placeholder="Ex.: Fazenda Santa Rosa" />
      </Field>
      <Field label="Município" required>
        <Inp value={form.propriedade_municipio} onChange={(e) => set('propriedade_municipio', e.target.value)} placeholder="Ex.: Sorriso" />
      </Field>
      <Field label="UF">
        <Sel value={form.propriedade_uf} onChange={(e) => set('propriedade_uf', e.target.value)}>
          <option value="">Selecionar UF</option>
          {UF_OPTIONS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
        </Sel>
      </Field>
      <Field label="Matrícula do Imóvel" hint="Res. CMN 4.676/2018 — informação obrigatória para penhor">
        <Inp value={form.matricula_imovel} onChange={(e) => set('matricula_imovel', e.target.value)} placeholder="Nº matrícula" />
      </Field>
      <Field label="CRI / Cartório de Registro">
        <Inp value={form.cri_cartorio} onChange={(e) => set('cri_cartorio', e.target.value)} placeholder="Ex.: 1º CRI de Sorriso/MT" />
      </Field>
    </div>
  </div>
);

// ── Step 3 — Rebanho por Categoria ───────────────────────────────────────────
const Step3Rebanho = ({ form, set }) => {
  const categorias = form.categorias || [];
  const catOptions = getCategoriaOptions(form.tipo_semovente);

  const addCategoria = () => {
    set('categorias', [...categorias, { ...EMPTY_CATEGORIA }]);
  };

  const removeCategoria = (idx) => {
    const updated = categorias.filter((_, i) => i !== idx);
    recalcTotals(updated);
  };

  const updateCategoria = (idx, field, value) => {
    const updated = categorias.map((c, i) => {
      if (i !== idx) return c;
      const next = { ...c, [field]: value };
      // auto-calc valor_total
      if (field === 'valor_unitario' || field === 'quantidade') {
        const qty = field === 'quantidade' ? (parseInt(value) || 0) : (parseInt(next.quantidade) || 0);
        const vu = field === 'valor_unitario' ? (parseFloat(value) || 0) : (parseFloat(next.valor_unitario) || 0);
        next.valor_total = qty * vu;
      }
      if (field === 'quantidade') next.quantidade = parseInt(value) || 0;
      return next;
    });
    recalcTotals(updated);
  };

  const recalcTotals = (cats) => {
    const totalCabecas = cats.reduce((s, c) => s + (parseInt(c.quantidade) || 0), 0);
    const totalUA = cats.reduce((s, c) => {
      const kg = parseFloat(c.peso_medio_kg) || 0;
      const qty = parseInt(c.quantidade) || 0;
      return s + (kg > 0 ? (qty * kg) / 450 : 0);
    }, 0);
    set('categorias', cats);
    set('total_cabecas', totalCabecas);
    set('total_ua', Math.round(totalUA * 10) / 10);
    const totalVM = cats.reduce((s, c) => s + (parseFloat(c.valor_total) || 0), 0);
    set('valor_mercado_total', Math.round(totalVM * 100) / 100);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <SectionTitle>Composição do Rebanho</SectionTitle>
        <Button size="sm" onClick={addCategoria} className="bg-emerald-900 hover:bg-emerald-800 text-white">
          <Plus className="w-3.5 h-3.5 mr-1" />Adicionar Categoria
        </Button>
      </div>

      {categorias.length === 0 ? (
        <div className="text-center py-10 border-2 border-dashed border-emerald-200 rounded-xl text-gray-500">
          <Layers className="w-8 h-8 mx-auto mb-2 text-emerald-300" />
          <p className="text-sm">Clique em "Adicionar Categoria" para inserir o rebanho</p>
        </div>
      ) : (
        <div className="space-y-4">
          {categorias.map((cat, idx) => {
            const isBovino = form.tipo_semovente === 'bovino';
            const isEquino = form.tipo_semovente === 'equino';
            const isMatriz = cat.categoria === 'matrizes' || cat.categoria === 'matriz_suina' || cat.categoria === 'ovelha';
            const isEngorda = cat.categoria === 'bois_engorda';
            return (
              <div key={idx} className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-semibold text-emerald-800">Categoria {idx + 1}</span>
                  <button onClick={() => removeCategoria(idx)} className="text-red-400 hover:text-red-600">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <div className="grid md:grid-cols-3 gap-3">
                  <Field label="Categoria" required>
                    <Sel value={cat.categoria} onChange={(e) => updateCategoria(idx, 'categoria', e.target.value)}>
                      <option value="">Selecionar...</option>
                      {catOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </Sel>
                  </Field>
                  <Field label="Quantidade (cabeças)">
                    <Inp type="number" value={cat.quantidade} onChange={(e) => updateCategoria(idx, 'quantidade', e.target.value)} />
                  </Field>
                  <Field label="Raça">
                    <Inp value={cat.raca} onChange={(e) => updateCategoria(idx, 'raca', e.target.value)} placeholder="Ex.: Nelore, Angus..." />
                  </Field>
                  <Field label="Faixa Etária">
                    <Inp value={cat.faixa_etaria} onChange={(e) => updateCategoria(idx, 'faixa_etaria', e.target.value)} placeholder="Ex.: 2-3 anos" />
                  </Field>
                  <Field label="Peso Médio (kg)" hint="Usado para calcular UA">
                    <Inp type="number" value={cat.peso_medio_kg} onChange={(e) => updateCategoria(idx, 'peso_medio_kg', parseFloat(e.target.value) || 0)} />
                  </Field>
                  <Field label="Reg. Genealógico">
                    <Inp value={cat.registro_genealogico} onChange={(e) => updateCategoria(idx, 'registro_genealogico', e.target.value)} placeholder="PO, PC, PN..." />
                  </Field>
                  <Field label="Valor Unitário (R$)">
                    <Inp type="number" value={cat.valor_unitario} onChange={(e) => updateCategoria(idx, 'valor_unitario', parseFloat(e.target.value) || 0)} />
                  </Field>
                  <Field label="Valor Total (R$)">
                    <div className="flex items-center h-9 px-3 rounded-lg border border-gray-200 bg-emerald-50 text-sm font-semibold text-emerald-900">
                      {fmtCurrency(cat.valor_total)}
                    </div>
                  </Field>
                  {/* Matrizes */}
                  {isMatriz && (
                    <>
                      <Field label="Taxa de Prenhez (%)">
                        <Inp type="number" value={cat.taxa_prenhez ?? ''} onChange={(e) => updateCategoria(idx, 'taxa_prenhez', parseFloat(e.target.value) || null)} />
                      </Field>
                      <Field label="Produção de Leite (L/dia)">
                        <Inp type="number" value={cat.producao_leite ?? ''} onChange={(e) => updateCategoria(idx, 'producao_leite', parseFloat(e.target.value) || null)} />
                      </Field>
                    </>
                  )}
                  {/* Engorda */}
                  {isEngorda && (
                    <>
                      <Field label="Arrobas Estimadas (@)">
                        <Inp type="number" value={cat.arrobas_estimadas ?? ''} onChange={(e) => updateCategoria(idx, 'arrobas_estimadas', parseFloat(e.target.value) || null)} />
                      </Field>
                      <Field label="Estágio">
                        <Sel value={cat.estagio ?? ''} onChange={(e) => updateCategoria(idx, 'estagio', e.target.value)}>
                          <option value="">Selecionar...</option>
                          <option value="confinamento">Confinamento</option>
                          <option value="semiconfinamento">Semiconfinamento</option>
                          <option value="pastagem">Pastagem</option>
                        </Sel>
                      </Field>
                    </>
                  )}
                  {/* Equino aptidao */}
                  {isEquino && (
                    <Field label="Aptidão">
                      <Sel value={cat.aptidao ?? ''} onChange={(e) => updateCategoria(idx, 'aptidao', e.target.value)}>
                        <option value="">Selecionar...</option>
                        <option value="corrida">Corrida</option>
                        <option value="trabalho">Trabalho</option>
                        <option value="esporte">Esporte</option>
                        <option value="lazer">Lazer</option>
                      </Sel>
                    </Field>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Totais */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
          <div className="text-xs text-emerald-600 font-semibold uppercase tracking-wider">Total Cabeças</div>
          <div className="text-2xl font-bold text-emerald-900 mt-1">{form.total_cabecas || 0}</div>
        </div>
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
          <div className="text-xs text-emerald-600 font-semibold uppercase tracking-wider">Total UA</div>
          <div className="text-2xl font-bold text-emerald-900 mt-1">{(form.total_ua || 0).toFixed(1)}</div>
          <div className="text-[10px] text-emerald-600 mt-0.5">1 UA = 450 kg</div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-center">
          <div className="text-xs text-amber-700 font-semibold uppercase tracking-wider">Valor de Mercado</div>
          <div className="text-lg font-bold text-amber-900 mt-1">{fmtCurrency(form.valor_mercado_total)}</div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Lotação (UA/ha)">
          <Inp type="number" value={form.lotacao_ua_ha} onChange={(e) => set('lotacao_ua_ha', parseFloat(e.target.value) || 0)} />
        </Field>
      </div>
    </div>
  );
};

// ── Step 4 — Rastreabilidade ──────────────────────────────────────────────────
const Step4Rastreabilidade = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Rastreabilidade — SISBOV / IN MAPA 78/2022</SectionTitle>
    <div className="space-y-4">
      <CheckRow
        label="Brincos SISBOV (e-SISBOV)"
        checked={form.brincos_sisbov}
        onChange={(v) => set('brincos_sisbov', v)}
        hint="IN MAPA 78/2022 — Sistema Brasileiro de Identificação e Certificação de Bovinos"
      />
      {form.brincos_sisbov && (
        <div className="grid md:grid-cols-2 gap-4 ml-7">
          <Field label="Brinco Início (nº)">
            <Inp value={form.brinco_inicio} onChange={(e) => set('brinco_inicio', e.target.value)} placeholder="Ex.: 076-BR-XXXXXXX" />
          </Field>
          <Field label="Brinco Fim (nº)">
            <Inp value={form.brinco_fim} onChange={(e) => set('brinco_fim', e.target.value)} placeholder="Ex.: 076-BR-YYYYYYY" />
          </Field>
          <Field label="Situação no e-SISBOV" className="md:col-span-2">
            <Sel value={form.situacao_esisbov} onChange={(e) => set('situacao_esisbov', e.target.value)}>
              <option value="">Selecionar...</option>
              <option value="certificado">Certificado</option>
              <option value="em_processo">Em Processo de Certificação</option>
              <option value="nao_certificado">Não Certificado</option>
            </Sel>
          </Field>
        </div>
      )}

      <CheckRow
        label="Marcação a Ferro"
        checked={form.marcacao_ferro}
        onChange={(v) => set('marcacao_ferro', v)}
      />
      {form.marcacao_ferro && (
        <div className="ml-7">
          <Field label="Descrição da Marcação">
            <Inp value={form.marcacao_descricao} onChange={(e) => set('marcacao_descricao', e.target.value)} placeholder="Sigla, lado, posição..." />
          </Field>
        </div>
      )}

      <CheckRow
        label="Microchip / Transponder eletrônico"
        checked={form.microchip}
        onChange={(v) => set('microchip', v)}
      />
    </div>
  </div>
);

// ── Step 5 — Situação Sanitária ───────────────────────────────────────────────
const Step5Sanitaria = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Situação Sanitária — IN MAPA 48/2020</SectionTitle>

    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Data Vacina Aftosa" hint="Obrigatória em todo o território nacional">
        <Inp type="date" value={form.vacina_aftosa_data} onChange={(e) => set('vacina_aftosa_data', e.target.value)} />
      </Field>
      <Field label="Órgão / Campanha Aftosa">
        <Inp value={form.vacina_aftosa_orgao} onChange={(e) => set('vacina_aftosa_orgao', e.target.value)} placeholder="Ex.: INDEA-MT Campanha Mai/2024" />
      </Field>
      <Field label="Data Vacina Brucelose">
        <Inp type="date" value={form.vacina_brucelose_data} onChange={(e) => set('vacina_brucelose_data', e.target.value)} />
      </Field>
      <Field label="Teste de Tuberculose">
        <Sel value={form.teste_tuberculose} onChange={(e) => set('teste_tuberculose', e.target.value)}>
          <option value="nao_realizado">Não Realizado</option>
          <option value="negativo">Negativo</option>
          <option value="positivo">Positivo</option>
          <option value="inconclusivo">Inconclusivo</option>
        </Sel>
      </Field>
      {form.teste_tuberculose !== 'nao_realizado' && (
        <Field label="Data do Teste de Tuberculose">
          <Inp type="date" value={form.teste_tuberculose_data} onChange={(e) => set('teste_tuberculose_data', e.target.value)} />
        </Field>
      )}
      <Field label="Data Vermifugação">
        <Inp type="date" value={form.vermifugacao_data} onChange={(e) => set('vermifugacao_data', e.target.value)} />
      </Field>
      <Field label="Produto Vermífugo">
        <Inp value={form.vermifugacao_produto} onChange={(e) => set('vermifugacao_produto', e.target.value)} placeholder="Nome comercial / princípio ativo" />
      </Field>
      <Field label="Mortalidade Estimada (%)" hint="Nos últimos 12 meses">
        <Inp type="number" value={form.mortalidade_percentual} onChange={(e) => set('mortalidade_percentual', parseFloat(e.target.value) || 0)} />
      </Field>
    </div>

    <div className="space-y-3">
      <CheckRow
        label="Área Livre de Febre Aftosa"
        checked={form.area_livre_aftosa}
        onChange={(v) => set('area_livre_aftosa', v)}
        hint="Conforme portaria estadual vigente"
      />
      <CheckRow
        label="GTA (Guia de Trânsito Animal) em dia"
        checked={form.gta_em_dia}
        onChange={(v) => set('gta_em_dia', v)}
        hint="Obrigatória para movimentação e penhor"
      />
    </div>
  </div>
);

// ── Step 6 — Infraestrutura ───────────────────────────────────────────────────
const Step6Infraestrutura = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Infraestrutura da Propriedade</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Capacidade de Suporte (UA/ha)">
        <Inp type="number" value={form.capacidade_suporte_ua_ha} onChange={(e) => set('capacidade_suporte_ua_ha', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Disponibilidade de Água">
        <Sel value={form.disponibilidade_agua} onChange={(e) => set('disponibilidade_agua', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="abundante">Abundante (rios, represas, poços artesianos)</option>
          <option value="suficiente">Suficiente</option>
          <option value="limitada">Limitada (dependente de chuvas)</option>
          <option value="critica">Crítica</option>
        </Sel>
      </Field>
      <Field label="Instalações Existentes" hint="Curral, balança, brete, embarcadouro, etc.">
        <Txta
          value={form.instalacoes}
          onChange={(e) => set('instalacoes', e.target.value)}
          rows={3}
          placeholder="Descreva as instalações presentes na propriedade..."
        />
      </Field>
      <Field label="Estado de Conservação das Instalações">
        <Sel value={form.estado_conservacao_instalacoes} onChange={(e) => set('estado_conservacao_instalacoes', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="otimo">Ótimo</option>
          <option value="bom">Bom</option>
          <option value="regular">Regular</option>
          <option value="precario">Precário</option>
        </Sel>
      </Field>
      <Field label="Capacidade de Confinamento (cabeças)">
        <Inp type="number" value={form.capacidade_confinamento} onChange={(e) => set('capacidade_confinamento', parseInt(e.target.value) || 0)} />
      </Field>
    </div>
  </div>
);

// ── Step 7 — Vistoria Técnica ─────────────────────────────────────────────────
const Step7Vistoria = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Vistoria Técnica Presencial</SectionTitle>

    <div className="flex items-start gap-3 bg-amber-50 border border-amber-300 rounded-xl px-4 py-3">
      <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
      <p className="text-sm text-amber-800">
        A contagem física presencial do rebanho é <strong>obrigatória</strong> para laudos de penhor rural
        conforme Dec.-Lei 167/1967 art. 9 e MCR BACEN Cap. 6.
      </p>
    </div>

    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Data da Vistoria" required>
        <Inp type="date" value={form.vistoria_data} onChange={(e) => set('vistoria_data', e.target.value)} />
      </Field>
      <Field label="Horário">
        <Inp type="time" value={form.vistoria_horario} onChange={(e) => set('vistoria_horario', e.target.value)} />
      </Field>
    </div>

    <CheckRow
      label="Contagem Física Presencial Realizada"
      checked={form.contagem_fisica_presencial}
      onChange={(v) => set('contagem_fisica_presencial', v)}
      hint="Obrigatória — o Médico Veterinário deve ter contado fisicamente os animais no local"
    />

    <Field label={`Condição Corporal Média: ${form.condicao_corporal_media || 3}/5`} hint="Escala de 1 (muito magro) a 5 (obeso)">
      <input
        type="range"
        min="1"
        max="5"
        step="0.5"
        value={form.condicao_corporal_media || 3}
        onChange={(e) => set('condicao_corporal_media', parseFloat(e.target.value))}
        className="w-full accent-emerald-700"
      />
      <div className="flex justify-between text-xs text-gray-400 mt-1">
        <span>1 — Muito Magro</span>
        <span>3 — Médio</span>
        <span>5 — Obeso</span>
      </div>
    </Field>

    <Field
      label="Fotos da Vistoria"
      required
      hint="Mínimo de 20 fotos exigido: geral do rebanho, marcações, instalações, documentos sanitários"
    >
      <div className={`mb-2 text-xs font-semibold ${(form.fotos || []).length < 20 ? 'text-amber-600' : 'text-emerald-700'}`}>
        {(form.fotos || []).length}/20 fotos {(form.fotos || []).length < 20 ? '— adicione mais ' + (20 - (form.fotos || []).length) + ' para cumprir o mínimo' : '— mínimo atingido ✓'}
      </div>
      <ImageUploader
        images={form.fotos || []}
        onImagesChange={(ids) => set('fotos', ids)}
        maxImages={60}
        label=""
      />
    </Field>
  </div>
);

// ── Step 8 — Análise de Mercado ───────────────────────────────────────────────
const Step8Mercado = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Cotações de Mercado</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Cotação da Arroba (@) — R$/@ boi gordo">
        <Inp type="number" value={form.cotacao_arroba_valor} onChange={(e) => set('cotacao_arroba_valor', parseFloat(e.target.value) || 0)} placeholder="Ex.: 295.50" />
      </Field>
      <Field label="Data de Referência da Cotação">
        <Inp type="date" value={form.cotacao_arroba_data} onChange={(e) => set('cotacao_arroba_data', e.target.value)} />
      </Field>
      <Field label="Fonte da Cotação" hint="B3, CEPEA/ESALQ, SCOT Consultoria, bolsa local">
        <Inp value={form.cotacao_fonte} onChange={(e) => set('cotacao_fonte', e.target.value)} placeholder="Ex.: CEPEA/ESALQ — 19/04/2026" />
      </Field>
      <Field label="Cotação Bezerro (R$/cabeça)">
        <Inp type="number" value={form.cotacao_bezerro} onChange={(e) => set('cotacao_bezerro', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Cotação Vaca (R$/cabeça)">
        <Inp type="number" value={form.cotacao_vaca} onChange={(e) => set('cotacao_vaca', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Cotação Touro PO (R$/cabeça)">
        <Inp type="number" value={form.cotacao_touro_po} onChange={(e) => set('cotacao_touro_po', parseFloat(e.target.value) || 0)} />
      </Field>
    </div>
  </div>
);

// ── Step 9 — Resultado da Avaliação ──────────────────────────────────────────
const Step9Resultado = ({ form, set }) => {
  const vm = parseFloat(form.valor_mercado_total) || 0;
  const fl = parseFloat(form.fator_liquidez) || 0.65;
  const valorGarantia = Math.round(vm * fl * 100) / 100;

  const handleFatorLiquidez = (v) => {
    const fl2 = parseFloat(v) || 0.65;
    set('fator_liquidez', fl2);
    set('valor_garantia_aceito', Math.round(vm * fl2 * 100) / 100);
  };

  return (
    <div className="space-y-6">
      <SectionTitle>Planilha de Avaliação por Categoria</SectionTitle>

      {/* Tabela resumo das categorias */}
      {(form.categorias || []).length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-emerald-900 text-white">
                <th className="px-3 py-2 text-left font-semibold">Categoria</th>
                <th className="px-3 py-2 text-right font-semibold">Qtd</th>
                <th className="px-3 py-2 text-left font-semibold">Raça</th>
                <th className="px-3 py-2 text-right font-semibold">Vl. Unit.</th>
                <th className="px-3 py-2 text-right font-semibold">Vl. Total</th>
              </tr>
            </thead>
            <tbody>
              {form.categorias.map((c, i) => (
                <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="px-3 py-2 capitalize">{c.categoria.replace(/_/g, ' ')}</td>
                  <td className="px-3 py-2 text-right">{c.quantidade}</td>
                  <td className="px-3 py-2">{c.raca || '—'}</td>
                  <td className="px-3 py-2 text-right">{fmtCurrency(c.valor_unitario)}</td>
                  <td className="px-3 py-2 text-right font-semibold">{fmtCurrency(c.valor_total)}</td>
                </tr>
              ))}
              <tr className="bg-emerald-50 font-bold border-t-2 border-emerald-300">
                <td className="px-3 py-2 text-emerald-900">TOTAL</td>
                <td className="px-3 py-2 text-right text-emerald-900">{form.total_cabecas}</td>
                <td className="px-3 py-2"></td>
                <td className="px-3 py-2"></td>
                <td className="px-3 py-2 text-right text-emerald-900">{fmtCurrency(form.valor_mercado_total)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-gray-400 italic">Nenhuma categoria cadastrada — retorne ao Step 3 para adicionar o rebanho.</p>
      )}

      <SectionTitle>Fator de Liquidez e Garantia</SectionTitle>
      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <Field
            label={`Fator de Liquidez: ${(form.fator_liquidez * 100).toFixed(0)}%`}
            hint="MCR BACEN Cap. 6 — semoventes têm liquidez menor que imóveis. Padrão: 65%"
          >
            <input
              type="range"
              min="0.60"
              max="0.75"
              step="0.01"
              value={form.fator_liquidez || 0.65}
              onChange={(e) => handleFatorLiquidez(e.target.value)}
              className="w-full accent-emerald-700"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>60%</span>
              <span>65% (padrão)</span>
              <span>75%</span>
            </div>
          </Field>
        </div>
        <div className="space-y-3">
          <Field label="LTV Recomendado (%)" hint="Loan-To-Value">
            <Inp type="number" value={form.ltv_recomendado} onChange={(e) => set('ltv_recomendado', parseFloat(e.target.value) || 65)} />
          </Field>
          <Field label="Validade do Laudo (meses)">
            <Inp type="number" value={form.validade_laudo_meses} onChange={(e) => set('validade_laudo_meses', parseInt(e.target.value) || 6)} />
          </Field>
        </div>
      </div>

      {/* Cards de resultado */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
          <div className="text-xs text-emerald-700 font-semibold uppercase tracking-wider mb-1">Valor de Mercado</div>
          <div className="text-2xl font-bold text-emerald-900">{fmtCurrency(form.valor_mercado_total)}</div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
          <div className="text-xs text-amber-700 font-semibold uppercase tracking-wider mb-1">Fator Liquidez</div>
          <div className="text-2xl font-bold text-amber-900">{((form.fator_liquidez || 0.65) * 100).toFixed(0)}%</div>
        </div>
        <div className="bg-emerald-900 rounded-xl p-5">
          <div className="text-xs text-emerald-200 font-semibold uppercase tracking-wider mb-1">Valor da Garantia</div>
          <div className="text-2xl font-bold text-white">{fmtCurrency(valorGarantia)}</div>
        </div>
      </div>

      <Field label="Seguro Recomendado (R$)" hint="Valor de seguro agrícola/pecuário recomendado">
        <Inp type="number" value={form.seguro_recomendado_valor} onChange={(e) => set('seguro_recomendado_valor', parseFloat(e.target.value) || 0)} />
      </Field>
    </div>
  );
};

// ── Step 10 — Declarações e Responsável ──────────────────────────────────────
const Step10Declaracoes = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Restrições e Ressalvas</SectionTitle>
    <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-900 space-y-2">
      <p><strong>Ressalvas padrão para laudos de semoventes:</strong></p>
      <ul className="list-disc list-inside space-y-1 text-xs">
        <li>O valor avaliado é válido na data da vistoria e sujeito a variações de mercado.</li>
        <li>Flutuações nas cotações de commodities podem afetar significativamente o valor do rebanho.</li>
        <li>Riscos sanitários (doenças, epidemias) não contemplados nesta avaliação.</li>
        <li>A avaliação não garante a existência futura dos animais nem sua condição de saúde.</li>
        <li>Validade: {form.validade_laudo_meses || 6} meses da data de emissão — após este prazo nova vistoria é necessária.</li>
      </ul>
    </div>
    <Field label="Restrições e Ressalvas Adicionais">
      <Txta
        value={form.restricoes_ressalvas}
        onChange={(e) => set('restricoes_ressalvas', e.target.value)}
        rows={4}
        placeholder="Insira restrições ou ressalvas específicas a este laudo..."
      />
    </Field>

    <SectionTitle>Declarações Obrigatórias</SectionTitle>
    <div className="space-y-4">
      <CheckRow
        label="Declaro que realizei contagem física presencial dos animais no local da vistoria"
        checked={form.declaracao_contagem_presencial}
        onChange={(v) => set('declaracao_contagem_presencial', v)}
        hint="Obrigatório — Dec.-Lei 167/1967 art. 9"
      />
      <CheckRow
        label="Declaro não possuir conflito de interesses com o devedor, credor ou intermediários"
        checked={form.declaracao_sem_conflito}
        onChange={(v) => set('declaracao_sem_conflito', v)}
      />
      <CheckRow
        label="Declaro que o penhor rural está registrado ou será registrado conforme a lei"
        checked={form.declaracao_penhor_registrado}
        onChange={(v) => set('declaracao_penhor_registrado', v)}
        hint="Lei 8.171/1991 · Dec.-Lei 167/1967 arts. 9-19"
      />
    </div>

    <SectionTitle>Responsável Técnico — CRMV Obrigatório</SectionTitle>
    <div className="flex items-start gap-3 bg-red-50 border-2 border-red-300 rounded-xl px-4 py-3 mb-4">
      <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
      <p className="text-sm text-red-800">
        <strong>Laudo sem CRMV ativo é nulo</strong> para fins de penhor rural bancário.
        (CFMV Res. 722/2002 · Circ. BACEN 3.818/2016)
      </p>
    </div>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Nome do Médico Veterinário" required>
        <Inp value={form.responsavel_nome} onChange={(e) => set('responsavel_nome', e.target.value)} placeholder="Nome completo" />
      </Field>
      <Field label="CRMV Nº" required>
        <Inp value={form.crmv_numero} onChange={(e) => set('crmv_numero', e.target.value)} placeholder="00000" />
      </Field>
      <Field label="CRMV UF" required>
        <Sel value={form.crmv_uf} onChange={(e) => set('crmv_uf', e.target.value)}>
          <option value="">Selecionar UF</option>
          {UF_OPTIONS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
        </Sel>
      </Field>
      <Field label="Especialidade">
        <Inp value={form.especialidade} onChange={(e) => set('especialidade', e.target.value)} placeholder="Ex.: Clínica de Ruminantes, Sanidade Animal..." />
      </Field>
      <Field label="Nº ART/CRMV" hint="Art. de Responsabilidade Técnica">
        <Inp value={form.art_crmv_numero} onChange={(e) => set('art_crmv_numero', e.target.value)} placeholder="Nº ART" />
      </Field>
      <Field label="Data de Registro da ART">
        <Inp type="date" value={form.art_data_registro} onChange={(e) => set('art_data_registro', e.target.value)} />
      </Field>
    </div>
  </div>
);

// ── Main Wizard ───────────────────────────────────────────────────────────────
const SemoventeWizard = () => {
  const { id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();

  const isNew = !id || id === 'nova';
  const [form, setForm] = useState({ ...EMPTY });
  const [semoventeId, setSemoventeId] = useState(isNew ? null : id);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const debounceRef = useRef(null);

  const load = useCallback(async () => {
    if (!semoventeId) return;
    setLoading(true);
    try {
      const data = await semoventesAPI.get(semoventeId);
      setForm({ ...EMPTY, ...data });
    } catch (err) {
      console.warn(err);
      toast({ title: 'Erro ao carregar laudo', variant: 'destructive' });
      nav('/dashboard/semoventes');
    } finally {
      setLoading(false);
    }
  }, [semoventeId, nav, toast]);

  useEffect(() => { load(); }, [load]);

  const save = useCallback(async (silent = false) => {
    setSaving(true);
    try {
      if (semoventeId) {
        await semoventesAPI.update(semoventeId, form);
      } else {
        const created = await semoventesAPI.create(form);
        setSemoventeId(created.id);
        setForm((f) => ({ ...f, numero_laudo: created.numero_laudo }));
        nav(`/dashboard/semoventes/${created.id}`, { replace: true });
      }
      setLastSaved(new Date());
      if (!silent) toast({ title: 'Rascunho salvo' });
    } catch (err) {
      console.warn(err);
      if (!silent) toast({ title: 'Erro ao salvar', description: err.response?.data?.detail, variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  }, [form, semoventeId, nav, toast]);

  // Auto-save every 30s when editing existing record
  useEffect(() => {
    if (!semoventeId) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => save(true), 30000);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [form, semoventeId, save]);

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  if (loading) return (
    <div className="py-20 flex justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-emerald-800" />
    </div>
  );

  const totalSteps = STEPS.length;

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

  const renderStep = () => {
    switch (step) {
      case 0: return <Step1Tipo form={form} set={set} />;
      case 1: return <Step2Devedor form={form} set={set} />;
      case 2: return <Step3Rebanho form={form} set={set} />;
      case 3: return <Step4Rastreabilidade form={form} set={set} />;
      case 4: return <Step5Sanitaria form={form} set={set} />;
      case 5: return <Step6Infraestrutura form={form} set={set} />;
      case 6: return <Step7Vistoria form={form} set={set} />;
      case 7: return <Step8Mercado form={form} set={set} />;
      case 8: return <Step9Resultado form={form} set={set} />;
      case 9: return <Step10Declaracoes form={form} set={set} />;
      default: return null;
    }
  };

  return (
    <div className="max-w-5xl mx-auto pb-20">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => nav('/dashboard/semoventes')}>
            <ArrowLeft className="w-4 h-4 mr-1" />Voltar
          </Button>
          {form.numero_laudo && (
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
              {form.numero_laudo}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {lastSaved && (
            <span className="text-xs text-gray-500">Salvo {lastSaved.toLocaleTimeString('pt-BR')}</span>
          )}
          <Button variant="outline" onClick={() => save(false)} disabled={saving}>
            <Save className="w-4 h-4 mr-1" />{saving ? 'Salvando...' : 'Salvar rascunho'}
          </Button>
        </div>
      </div>

      {/* Progress bar */}
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
            const done = i < step;
            return (
              <button
                key={s.id}
                onClick={() => setStep(i)}
                className={`flex-shrink-0 flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-xs font-medium transition ${getStepClasses(i)}`}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${getIconClasses(i)}`}>
                  {done ? <Check className="w-3 h-3" /> : <Icon className="w-3 h-3" />}
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
        <Button
          variant="outline"
          onClick={() => setStep(Math.max(0, step - 1))}
          disabled={step === 0}
        >
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
              <Check className="w-4 h-4 mr-1" />Concluir Laudo
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SemoventeWizard;
