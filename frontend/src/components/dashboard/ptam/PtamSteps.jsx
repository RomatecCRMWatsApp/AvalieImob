import React, { useEffect, useRef, useState } from 'react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Textarea } from '../../ui/textarea';
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from '../../ui/select';
import { Plus, Trash2, Sparkles, ChevronDown, Check, X } from 'lucide-react';
import { emptyMarketSample, emptyImpactArea, emptySample, computeStats } from './ptamHelpers';
import ImageUploader from './ImageUploader';

// ── Shared primitives ──────────────────────────────────────────────────────────

const Field = ({ label, children, full, half }) => (
  <div className={full ? 'col-span-2' : half ? 'col-span-1' : ''}>
    <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
    {children}
  </div>
);

const AiButton = ({ onClick, loading }) => (
  <Button
    type="button" size="sm" variant="ghost"
    className="text-emerald-700 hover:text-emerald-900 hover:bg-emerald-50"
    onClick={onClick} disabled={loading}
  >
    <Sparkles className="w-3.5 h-3.5 mr-1" />
    {loading ? '...' : 'Aperfeiçoar com IA'}
  </Button>
);

const SectionHeader = ({ title, subtitle }) => (
  <div className="mb-6">
    <h2 className="font-display text-xl font-bold text-gray-900">{title}</h2>
    {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
  </div>
);

const StatBox = ({ label, value, unit = '' }) => (
  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-center">
    <div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">{label}</div>
    <div className="text-2xl font-bold text-emerald-900">
      {typeof value === 'number' ? value.toLocaleString('pt-BR', { maximumFractionDigits: 2 }) : value}
    </div>
    {unit && <div className="text-xs text-gray-500 mt-0.5">{unit}</div>}
  </div>
);

// ── Step 1: Identificação do Solicitante ──────────────────────────────────────
export const StepSolicitante = ({ form, setForm }) => (
  <div>
    <SectionHeader
      title="1. Identificação do Solicitante"
      subtitle="Dados da parte que solicita a avaliação."
    />
    <div className="grid grid-cols-2 gap-4">
      <Field label="Número do PTAM">
        <Input
          value={form.numero_ptam || ''}
          readOnly
          disabled
          placeholder="Será gerado ao salvar"
          className="bg-gray-100 text-gray-500 cursor-not-allowed"
        />
      </Field>
      <Field label="Nome do Solicitante">
        <Input value={form.solicitante_nome} onChange={(e) => setForm({ ...form, solicitante_nome: e.target.value })} placeholder="Nome completo ou razão social" />
      </Field>
      <Field label="CPF / CNPJ">
        <Input value={form.solicitante_cpf_cnpj} onChange={(e) => setForm({ ...form, solicitante_cpf_cnpj: e.target.value })} placeholder="000.000.000-00" />
      </Field>
      <Field label="Telefone">
        <Input value={form.solicitante_telefone} onChange={(e) => setForm({ ...form, solicitante_telefone: e.target.value })} placeholder="(99) 99999-9999" />
      </Field>
      <Field label="E-mail">
        <Input type="email" value={form.solicitante_email} onChange={(e) => setForm({ ...form, solicitante_email: e.target.value })} placeholder="email@exemplo.com.br" />
      </Field>
      <Field label="Endereço do Solicitante" full>
        <Input value={form.solicitante_endereco} onChange={(e) => setForm({ ...form, solicitante_endereco: e.target.value })} placeholder="Rua, número, bairro, cidade – UF, CEP" />
      </Field>
    </div>
  </div>
);

// ── Step 2: Objetivo da Avaliação ─────────────────────────────────────────────

// Finalidades que exigem campos judiciais adicionais
const FINALIDADES_JUDICIAIS = new Set([
  'judicial_partilha', 'judicial_desapropriacao', 'judicial_indenizacao',
  'judicial_execucao', 'judicial_usucapiao', 'judicial_pericia',
  'desap_utilidade', 'desap_interesse_social', 'desap_reforma_agraria',
]);

// Dados de finalidades com nome + lei separados para formatação rica
const FINALIDADE_GRUPOS = [
  {
    label: 'Compra e Venda',
    items: [
      { value: 'cv_alienacao',    nome: 'Alienação',             lei: 'NBR 14653-2' },
      { value: 'cv_aquisicao',    nome: 'Aquisição',             lei: 'NBR 14653-2' },
      { value: 'cv_oferta',       nome: 'Oferta pública',        lei: 'NBR 14653-2' },
      { value: 'cv_dacao',        nome: 'Dação em pagamento',    lei: 'CC art. 356' },
    ],
  },
  {
    label: 'Garantia Bancária',
    items: [
      { value: 'gar_sfh',             nome: 'Financiamento SFH',           lei: 'Res. CMN 4.676/2018' },
      { value: 'gar_sfi',             nome: 'Financiamento SFI',           lei: 'Lei 9.514/97' },
      { value: 'gar_credito_rural',   nome: 'Crédito rural / penhor rural', lei: 'MCR BACEN' },
      { value: 'gar_refinanciamento', nome: 'Refinanciamento',             lei: 'Res. CMN 4.676/2018' },
      { value: 'gar_lci_cri',         nome: 'LCI / CRI',                   lei: 'Lei 10.931/2004' },
      { value: 'gar_ccb',             nome: 'CCB imobiliária',             lei: 'Lei 10.931/2004' },
    ],
  },
  {
    label: 'Judicial / Pericial',
    items: [
      { value: 'judicial_partilha',       nome: 'Partilha de bens — inventário / divórcio', lei: 'CPC art. 872' },
      { value: 'judicial_desapropriacao', nome: 'Desapropriação — utilidade pública',        lei: 'Dec.-Lei 3.365/41' },
      { value: 'judicial_indenizacao',    nome: 'Ação de indenização',                       lei: 'CC art. 944' },
      { value: 'judicial_execucao',       nome: 'Execução de sentença',                      lei: 'CPC art. 509' },
      { value: 'judicial_usucapiao',      nome: 'Usucapião',                                 lei: 'CC art. 1.238' },
      { value: 'judicial_pericia',        nome: 'Perícia judicial',                          lei: 'CPC art. 156' },
    ],
  },
  {
    label: 'Locação',
    items: [
      { value: 'loc_fixacao',    nome: 'Fixação de aluguel',  lei: 'Lei 8.245/91' },
      { value: 'loc_revisao',    nome: 'Revisão de aluguel',  lei: 'Lei 8.245/91 art. 19' },
      { value: 'loc_renovatoria',nome: 'Ação renovatória',    lei: 'Lei 8.245/91 art. 51' },
    ],
  },
  {
    label: 'Seguros',
    items: [
      { value: 'seg_reposicao', nome: 'Valor de reposição', lei: 'SUSEP / NBR 14653-2' },
      { value: 'seg_sinistro',  nome: 'Sinistro',           lei: 'SUSEP / NBR 14653-2' },
      { value: 'seg_risco',     nome: 'Valor em risco',     lei: 'SUSEP / NBR 14653-2' },
    ],
  },
  {
    label: 'Tributário / Fiscal',
    items: [
      { value: 'trib_itbi',     nome: 'Base de cálculo ITBI',                        lei: 'CTN art. 38' },
      { value: 'trib_itcmd',    nome: 'Base de cálculo ITCMD — herança / doação',    lei: 'CTN art. 35' },
      { value: 'trib_ir',       nome: 'Imposto de renda — ganho de capital',         lei: 'Lei 8.981/95 art. 21' },
      { value: 'trib_iptu_itr', nome: 'IPTU / ITR progressivo',                     lei: 'CTN art. 32 / CF art. 153' },
    ],
  },
  {
    label: 'Incorporação e Registro',
    items: [
      { value: 'inc_registro', nome: 'Registro de incorporação imobiliária', lei: 'Lei 4.591/64' },
      { value: 'inc_afetacao', nome: 'Patrimônio de afetação',               lei: 'Lei 13.786/2018' },
      { value: 'inc_permuta',  nome: 'Permuta',                              lei: 'NBR 14653-2' },
    ],
  },
  {
    label: 'Execução de Garantia',
    items: [
      { value: 'exec_fid_1',       nome: 'Alienação fiduciária — 1º leilão', lei: 'Lei 9.514/97 art. 27' },
      { value: 'exec_fid_2',       nome: 'Alienação fiduciária — 2º leilão', lei: 'Lei 9.514/97 art. 27 §2' },
      { value: 'exec_hipoteca',    nome: 'Execução hipotecária',             lei: 'Lei 9.514/97' },
      { value: 'exec_consolidacao',nome: 'Consolidação da propriedade',      lei: 'Lei 9.514/97 art. 26' },
    ],
  },
  {
    label: 'Desapropriação',
    items: [
      { value: 'desap_utilidade',       nome: 'Desapropriação por utilidade pública', lei: 'Dec.-Lei 3.365/41' },
      { value: 'desap_interesse_social',nome: 'Desapropriação por interesse social',  lei: 'Lei 4.132/62' },
      { value: 'desap_reforma_agraria', nome: 'Reforma agrária',                      lei: 'LC 76/93' },
    ],
  },
  {
    label: 'Regularização Fundiária',
    items: [
      { value: 'reurb_s_e',       nome: 'REURB-S / REURB-E',       lei: 'Lei 13.465/2017' },
      { value: 'reurb_demarcacao',nome: 'Demarcação urbanística',   lei: 'Lei 13.465/2017 art. 19' },
    ],
  },
  {
    label: 'Outros',
    items: [
      { value: 'outros_contab',    nome: 'Contabilidade / balanço patrimonial', lei: 'CPC 28 / IFRS 13' },
      { value: 'outros_fii',       nome: 'Fundo de investimento imobiliário — FII', lei: 'Lei 8.668/93' },
      { value: 'outros_ma',        nome: 'Fusão e aquisição — M&A',             lei: 'NBR 14653-2' },
      { value: 'outros_bts',       nome: 'Locação built to suit',               lei: 'Lei 8.245/91 art. 54-A' },
      { value: 'outros_diligencia',nome: 'Due diligence imobiliária',           lei: 'NBR 14653-2' },
      { value: 'outros',           nome: 'Outro',                               lei: 'especificar' },
    ],
  },
];

// Mapeia value → { nome, lei } para lookup rápido
const FINALIDADE_MAP = Object.fromEntries(
  FINALIDADE_GRUPOS.flatMap((g) => g.items.map((it) => [it.value, it]))
);

// Dropdown customizado com formatação rica: nome bold + lei italic gray
function FinalidadeSelect({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const selected = FINALIDADE_MAP[value] || null;

  // Fecha ao clicar fora
  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div ref={ref} className="relative w-full">
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex h-9 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {selected ? (
          <span className="flex items-baseline gap-1.5 truncate">
            <span className="font-semibold text-gray-900">{selected.nome}</span>
            <span className="italic text-gray-400 text-xs">{selected.lei}</span>
          </span>
        ) : (
          <span className="text-muted-foreground">Selecione a finalidade...</span>
        )}
        <ChevronDown className="h-4 w-4 shrink-0 opacity-50 ml-2" />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-white shadow-lg">
          <div className="max-h-80 overflow-y-auto py-1">
            {FINALIDADE_GRUPOS.map((grupo) => (
              <div key={grupo.label}>
                {/* Cabeçalho do grupo */}
                <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-gray-400 bg-gray-50 border-b border-gray-100 sticky top-0">
                  {grupo.label}
                </div>
                {/* Itens do grupo */}
                {grupo.items.map((item) => {
                  const isSelected = value === item.value;
                  return (
                    <button
                      key={item.value}
                      type="button"
                      onClick={() => { onChange(item.value); setOpen(false); }}
                      className={`flex w-full items-center justify-between px-4 py-2 text-left hover:bg-emerald-50 focus:outline-none focus:bg-emerald-50 transition-colors ${isSelected ? 'bg-emerald-50' : ''}`}
                    >
                      <span className="flex-1 min-w-0">
                        <span className="block font-semibold text-sm text-gray-900 leading-tight">{item.nome}</span>
                        <span className="block italic text-xs text-gray-400 leading-tight mt-0.5">{item.lei}</span>
                      </span>
                      {isSelected && <Check className="h-4 w-4 text-emerald-600 shrink-0 ml-2" />}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export const StepObjetivo = ({ form, setForm, onAi, aiLoading }) => {
  const isJudicial = FINALIDADES_JUDICIAIS.has(form.finalidade);
  return (
    <div>
      <SectionHeader
        title="2. Objetivo da Avaliação"
        subtitle="Descreva a finalidade e o contexto legal da avaliação (NBR 14653, Res. CMN 4.676/2018, MCR BACEN, COFECI)."
      />
      <div className="grid grid-cols-2 gap-4">
        <Field label="Finalidade da avaliação" full>
          <FinalidadeSelect value={form.finalidade} onChange={(v) => setForm({ ...form, finalidade: v })} />
        </Field>
        {form.finalidade === 'outros' && (
          <Field label="Especifique a finalidade" full>
            <Input value={form.finalidade_outros} onChange={(e) => setForm({ ...form, finalidade_outros: e.target.value })} />
          </Field>
        )}
        <Field label="Descrição do objetivo" full>
          <Textarea
            value={form.purpose}
            onChange={(e) => setForm({ ...form, purpose: e.target.value })}
            rows={4}
            placeholder="Descreva o objetivo da avaliação de forma técnica..."
          />
          <div className="mt-1 flex justify-end">
            <AiButton onClick={() => onAi('purpose')} loading={aiLoading === 'purpose'} />
          </div>
        </Field>
        {isJudicial && (
          <>
            <Field label="Processo judicial">
              <Input value={form.judicial_process} onChange={(e) => setForm({ ...form, judicial_process: e.target.value })} placeholder="Nº do processo" />
            </Field>
            <Field label="Tipo de ação">
              <Input value={form.judicial_action} onChange={(e) => setForm({ ...form, judicial_action: e.target.value })} placeholder="Ex: Inventário, Desapropriação" />
            </Field>
            <Field label="Fórum / Vara">
              <Input value={form.forum} onChange={(e) => setForm({ ...form, forum: e.target.value })} />
            </Field>
            <Field label="Juiz(a)">
              <Input value={form.judge} onChange={(e) => setForm({ ...form, judge: e.target.value })} />
            </Field>
            <Field label="Requerente" full>
              <Input value={form.requerente} onChange={(e) => setForm({ ...form, requerente: e.target.value })} />
            </Field>
            <Field label="Requerido" full>
              <Input value={form.requerido} onChange={(e) => setForm({ ...form, requerido: e.target.value })} />
            </Field>
          </>
        )}
      </div>
    </div>
  );
};

// ── Proprietários do Imóvel ───────────────────────────────────────────────────

const emptyProprietario = () => ({ nome: '', cpf_cnpj: '', percentual: '' });

const ProprietariosSection = ({ form, setForm }) => {
  const proprietarios = form.proprietarios && form.proprietarios.length > 0
    ? form.proprietarios
    : [emptyProprietario()];

  const update = (idx, field, value) => {
    const next = proprietarios.map((p, i) => i === idx ? { ...p, [field]: value } : p);
    setForm({ ...form, proprietarios: next });
  };

  const add = () => setForm({ ...form, proprietarios: [...proprietarios, emptyProprietario()] });

  const remove = (idx) => {
    if (proprietarios.length <= 1) return;
    setForm({ ...form, proprietarios: proprietarios.filter((_, i) => i !== idx) });
  };

  return (
    <div className="col-span-2 mt-2">
      <div className="rounded-xl border-2 border-amber-200 bg-amber-50/40 p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-sm font-semibold text-amber-900 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
              Proprietário(s) do Imóvel
            </div>
            <p className="text-xs text-amber-700 mt-0.5">
              Para inventários e partilhas, adicione todos os proprietários.
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            onClick={add}
            className="bg-amber-700 hover:bg-amber-800 text-white text-xs"
          >
            <Plus className="w-3.5 h-3.5 mr-1" /> Adicionar Proprietário
          </Button>
        </div>

        <div className="space-y-3">
          {proprietarios.map((p, idx) => (
            <div key={idx} className="flex items-start gap-3 bg-white rounded-lg border border-amber-200 p-3">
              <div className="flex-1 grid grid-cols-3 gap-3">
                <div className="col-span-3 sm:col-span-1">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Nome completo / Razão social</label>
                  <Input
                    value={p.nome}
                    onChange={(e) => update(idx, 'nome', e.target.value)}
                    placeholder="Nome do proprietário"
                    className="text-sm h-8"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">CPF / CNPJ</label>
                  <Input
                    value={p.cpf_cnpj}
                    onChange={(e) => update(idx, 'cpf_cnpj', e.target.value)}
                    placeholder="000.000.000-00"
                    className="text-sm h-8"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Fração / Percentual</label>
                  <Input
                    value={p.percentual}
                    onChange={(e) => update(idx, 'percentual', e.target.value)}
                    placeholder="50% ou 1/2"
                    className="text-sm h-8"
                  />
                </div>
              </div>
              {proprietarios.length > 1 && (
                <button
                  type="button"
                  onClick={() => remove(idx)}
                  className="mt-5 p-1.5 text-red-400 hover:bg-red-50 rounded flex-shrink-0"
                  title="Remover proprietário"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ── Helpers rurais ────────────────────────────────────────────────────────────

const RURAL_TYPES = new Set(['rural', 'fazenda', 'sitio', 'chacara', 'terreno_rural']);
const isRural = (tipo) => RURAL_TYPES.has((tipo || '').toLowerCase());

// Seção de documentação rural com borda diferenciada
const RuralDocSection = ({ form, setForm }) => {
  if (!isRural(form.property_type)) return null;
  return (
    <div className="col-span-2 mt-2">
      <div className="rounded-xl border-2 border-emerald-200 bg-emerald-50/50 p-5">
        <div className="text-sm font-semibold text-emerald-800 mb-4 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-600 inline-block" />
          Registros Rurais
          <span className="text-xs font-normal text-emerald-600 ml-1">— documentação específica de imóvel rural</span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Certificacao SIGEF (UUID)">
            <Input
              value={form.certificacao_sigef || ''}
              onChange={(e) => setForm({ ...form, certificacao_sigef: e.target.value })}
              placeholder="b533967e-f6b0-4b19-b4a1-fc834e1f9ebb"
            />
          </Field>
          <Field label="Codigo do Imovel Rural (INCRA)">
            <Input
              value={form.cadastro_incra || ''}
              onChange={(e) => setForm({ ...form, cadastro_incra: e.target.value })}
              placeholder="950.203.934.550-0"
            />
          </Field>
          <Field label="Numero do CCIR">
            <Input
              value={form.ccir || ''}
              onChange={(e) => setForm({ ...form, ccir: e.target.value })}
              placeholder="76280733267"
            />
          </Field>
          <Field label="CIB / NIRF">
            <Input
              value={form.nirf_cib || ''}
              onChange={(e) => setForm({ ...form, nirf_cib: e.target.value })}
              placeholder="5.690.070-8"
            />
          </Field>
          <Field label="Registro no CAR" full>
            <Input
              value={form.car || ''}
              onChange={(e) => setForm({ ...form, car: e.target.value })}
              placeholder="MA-2100055-F942.2E73.176D.42D5.B1C6.6A2F.01F5.B64F"
            />
          </Field>
          <Field label="Perímetro (m)">
            <Input
              type="number"
              step="0.01"
              value={form.perimetro_m ?? ''}
              onChange={(e) => setForm({ ...form, perimetro_m: e.target.value === '' ? null : Number(e.target.value) })}
              placeholder="Perímetro total em metros"
            />
          </Field>
        </div>

        {/* ── Documentos Rurais (uploads) ── */}
        <div className="mt-5 space-y-5">
          <div className="text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-1">Documentos Rurais — Upload</div>

          <ImageUploader
            label="Mapa Georreferenciado / Certificado SIGEF"
            images={form.doc_mapa_sigef || []}
            onImagesChange={(ids) => setForm({ ...form, doc_mapa_sigef: ids })}
            maxImages={3}
          />

          <ImageUploader
            label="Memorial Descritivo Topográfico / SIGEF"
            images={form.doc_memorial_descritivo || []}
            onImagesChange={(ids) => setForm({ ...form, doc_memorial_descritivo: ids })}
            maxImages={3}
          />

          <ImageUploader
            label="CCIR — Certificado de Cadastro de Imóvel Rural"
            images={form.doc_ccir || []}
            onImagesChange={(ids) => setForm({ ...form, doc_ccir: ids })}
            maxImages={3}
          />

          <div>
            <ImageUploader
              label="ITR — Imposto Territorial Rural"
              images={form.doc_itr || []}
              onImagesChange={(ids) => setForm({ ...form, doc_itr: ids })}
              maxImages={5}
            />
            <p className="text-xs text-emerald-700 mt-1">Envie os últimos 5 exercícios (máx. 5 arquivos)</p>
          </div>

          <ImageUploader
            label="CAR — Cadastro Ambiental Rural"
            images={form.doc_car || []}
            onImagesChange={(ids) => setForm({ ...form, doc_car: ids })}
            maxImages={3}
          />
        </div>
      </div>
    </div>
  );
};

// ── Step 3: Identificação do Imóvel ──────────────────────────────────────────
export const StepImovelId = ({ form, setForm }) => {
  const rural = isRural(form.property_type);
  return (
  <div>
    <SectionHeader
      title="3. Identificação do Imóvel"
      subtitle="Localização, registro e classificação do imóvel avaliando."
    />
    {rural && (
      <div className="mb-4 flex items-center gap-2 text-xs bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 text-emerald-800">
        <span className="font-semibold">Modo Rural ativo</span> — unidades de área em hectares (ha) e campos rurais habilitados
      </div>
    )}
    <div className="grid grid-cols-2 gap-4">
      <Field label="Tipo de imóvel" full>
        <Select value={form.property_type} onValueChange={(v) => setForm({ ...form, property_type: v })}>
          <SelectTrigger><SelectValue placeholder="Selecione o tipo..." /></SelectTrigger>
          <SelectContent>
            <SelectItem value="casa">Casa</SelectItem>
            <SelectItem value="apartamento">Apartamento</SelectItem>
            <SelectItem value="terreno">Terreno Urbano</SelectItem>
            <SelectItem value="rural">Imóvel Rural</SelectItem>
            <SelectItem value="fazenda">Fazenda</SelectItem>
            <SelectItem value="sitio">Sítio</SelectItem>
            <SelectItem value="chacara">Chácara</SelectItem>
            <SelectItem value="terreno_rural">Terreno Rural / Gleba</SelectItem>
            <SelectItem value="comercial">Sala / Loja Comercial</SelectItem>
            <SelectItem value="industrial">Galpão / Industrial</SelectItem>
            <SelectItem value="outros">Outros</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field label="Rótulo / Título do imóvel" full>
        <Input value={form.property_label} onChange={(e) => setForm({ ...form, property_label: e.target.value })} placeholder={rural ? 'Ex: Fazenda Santa Luzia, Gleba A' : 'Ex: Apartamento 302, Bloco A, Edifício Alfa'} />
      </Field>
      <Field label={rural ? 'Localidade / Logradouro' : 'Endereço completo'} full>
        <Input value={form.property_address} onChange={(e) => setForm({ ...form, property_address: e.target.value })} placeholder={rural ? 'Estrada, rodovia, km, zona rural...' : 'Rua, número, complemento'} />
      </Field>
      {!rural && (
        <Field label="Bairro">
          <Input value={form.property_neighborhood} onChange={(e) => setForm({ ...form, property_neighborhood: e.target.value })} />
        </Field>
      )}
      <Field label="Cidade">
        <Input value={form.property_city} onChange={(e) => setForm({ ...form, property_city: e.target.value })} />
      </Field>
      <Field label="Estado (UF)">
        <Input value={form.property_state} onChange={(e) => setForm({ ...form, property_state: e.target.value })} placeholder="MA" maxLength={2} />
      </Field>
      <Field label="CEP">
        <Input value={form.property_cep} onChange={(e) => setForm({ ...form, property_cep: e.target.value })} placeholder="00000-000" />
      </Field>
      <Field label="Matrícula">
        <Input value={form.property_matricula} onChange={(e) => setForm({ ...form, property_matricula: e.target.value })} />
      </Field>
      <Field label="Cartório / Ofício de Registro" full>
        <Input value={form.property_cartorio} onChange={(e) => setForm({ ...form, property_cartorio: e.target.value })} placeholder="Ex: 1º Ofício de Registro de Imóveis de ..." />
      </Field>
      <Field label="Latitude (GPS)">
        <Input value={form.property_gps_lat} onChange={(e) => setForm({ ...form, property_gps_lat: e.target.value })} placeholder="-4.9485" />
      </Field>
      <Field label="Longitude (GPS)">
        <Input value={form.property_gps_lng} onChange={(e) => setForm({ ...form, property_gps_lng: e.target.value })} placeholder="-47.4009" />
      </Field>
      <ProprietariosSection form={form} setForm={setForm} />
      {/* Área — condicional por tipo */}
      {rural ? (
        <>
          <Field label="Área total (ha — hectares)">
            <Input type="number" step="0.0001" value={form.property_area_ha} onChange={(e) => setForm({ ...form, property_area_ha: Number(e.target.value) })} placeholder="0,0000" />
          </Field>
          <Field label="Área construída / benfeitorias (m²)">
            <Input type="number" step="0.01" value={form.property_area_sqm} onChange={(e) => setForm({ ...form, property_area_sqm: Number(e.target.value) })} placeholder="Área das construções em m²" />
          </Field>
        </>
      ) : (
        <>
          <Field label="Área total (m²)">
            <Input type="number" step="0.01" value={form.property_area_sqm} onChange={(e) => setForm({ ...form, property_area_sqm: Number(e.target.value) })} />
          </Field>
          <Field label="Área (hectares)">
            <Input type="number" step="0.0001" value={form.property_area_ha} onChange={(e) => setForm({ ...form, property_area_ha: Number(e.target.value) })} />
          </Field>
        </>
      )}
      <Field label="Confrontações / Limites" full>
        <Textarea value={form.property_confrontations} onChange={(e) => setForm({ ...form, property_confrontations: e.target.value })} rows={3} placeholder="Norte: ..., Sul: ..., Leste: ..., Oeste: ..." />
      </Field>
      <Field label="Descrição geral do imóvel" full>
        <Textarea value={form.property_description} onChange={(e) => setForm({ ...form, property_description: e.target.value })} rows={4} />
      </Field>

      {/* Seção de Documentação Rural — aparece apenas para imóvel rural */}
      <RuralDocSection form={form} setForm={setForm} />
    </div>

    {/* ── Fotos e Documentos ─────────────────────────────────────────── */}
    <div className="mt-8 space-y-6 border-t border-gray-100 pt-6">
      <ImageUploader
        label="Fotos do Imóvel (máx 20)"
        images={form.fotos_imovel || []}
        onImagesChange={(ids) => setForm({ ...form, fotos_imovel: ids })}
        maxImages={20}
      />
      <ImageUploader
        label="Documentos do Imóvel — matrícula, IPTU, escritura (máx 10)"
        images={form.fotos_documentos || []}
        onImagesChange={(ids) => setForm({ ...form, fotos_documentos: ids })}
        maxImages={10}
        acceptPdf
      />
    </div>

    {/* ── Documentação Analisada (checklist NBR 14653 Seção 2) ──────── */}
    <div className="mt-8 border-t border-gray-100 pt-6">
      <div className="text-sm font-semibold text-gray-900 mb-3">Documentação Analisada <span className="text-xs font-normal text-gray-400">(NBR 14653 — Seção 2)</span></div>
      <div className="grid grid-cols-2 gap-2">
        {[
          { id: 'matricula', label: 'Matrícula do imóvel' },
          { id: 'IPTU', label: 'Carnê de IPTU' },
          { id: 'planta', label: 'Planta / Projeto aprovado' },
          { id: 'escritura', label: 'Escritura / Contrato' },
          { id: 'fotos', label: 'Fotografias do imóvel' },
          { id: 'habite_se', label: 'Habite-se / Auto de conclusão' },
          { id: 'geo_rural', label: 'Georreferenciamento (rural)' },
          { id: 'outros_docs', label: 'Outros documentos' },
        ].map(({ id, label }) => {
          const checked = (form.documentos_analisados || []).includes(id);
          return (
            <label key={id} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer select-none">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                checked={checked}
                onChange={(e) => {
                  const prev = form.documentos_analisados || [];
                  const next = e.target.checked ? [...prev, id] : prev.filter((d) => d !== id);
                  setForm({ ...form, documentos_analisados: next });
                }}
              />
              {label}
            </label>
          );
        })}
      </div>
    </div>
  </div>
  );
};

// ── Step 4: Caracterização da Região ─────────────────────────────────────────
export const StepRegiao = ({ form, setForm, onAi, aiLoading }) => {
  const fields = [
    { key: 'regiao_infraestrutura',    label: 'Infraestrutura Urbana', placeholder: 'Pavimentação, iluminação, calçadas, drenagem pluvial...' },
    { key: 'regiao_servicos_publicos', label: 'Serviços Públicos', placeholder: 'Água, esgoto, energia elétrica, coleta de lixo, transporte...' },
    { key: 'regiao_uso_predominante',  label: 'Uso Predominante do Solo', placeholder: 'Residencial unifamiliar, misto, comercial...' },
    { key: 'regiao_padrao_construtivo',label: 'Padrão Construtivo da Região', placeholder: 'Alto / médio / simples — características predominantes...' },
    { key: 'regiao_tendencia_mercado', label: 'Tendência de Mercado', placeholder: 'Valorização, estabilidade, desvalorização — fatores...' },
    { key: 'regiao_observacoes',       label: 'Observações Complementares', placeholder: 'Outros aspectos relevantes da região...' },
  ];
  return (
    <div>
      <SectionHeader
        title="4. Caracterização da Região"
        subtitle="Descreva as características do entorno e do mercado local."
      />

      {/* Zoneamento conforme Plano Diretor */}
      <div className="mb-5">
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          Zoneamento (Plano Diretor) <span className="text-xs text-gray-400">— NBR 14653-2</span>
        </label>
        <div className="flex gap-2 items-center">
          <Select value={form.zoneamento || ''} onValueChange={(v) => setForm({ ...form, zoneamento: v })}>
            <SelectTrigger className="max-w-xs"><SelectValue placeholder="Selecione o zoneamento..." /></SelectTrigger>
            <SelectContent>
              <SelectItem value="ZR1">ZR1 — Zona Residencial 1</SelectItem>
              <SelectItem value="ZR2">ZR2 — Zona Residencial 2</SelectItem>
              <SelectItem value="ZR3">ZR3 — Zona Residencial 3</SelectItem>
              <SelectItem value="ZC">ZC — Zona Comercial</SelectItem>
              <SelectItem value="ZCI">ZCI — Zona Comercial e Industrial</SelectItem>
              <SelectItem value="ZI">ZI — Zona Industrial</SelectItem>
              <SelectItem value="ZEI">ZEI — Zona de Expansão Industrial</SelectItem>
              <SelectItem value="ZRu">ZRu — Zona Rural</SelectItem>
              <SelectItem value="ZEIS">ZEIS — Zona Especial de Interesse Social</SelectItem>
              <SelectItem value="outro">Outro (especificar nas observações)</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-xs text-gray-400">ou informe nas observações</span>
        </div>
      </div>

      <div className="space-y-5">
        {fields.map((f) => (
          <div key={f.key}>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">{f.label}</label>
            <Textarea
              value={form[f.key] || ''}
              onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
              rows={3}
              placeholder={f.placeholder}
            />
            <div className="mt-1 flex justify-end">
              <AiButton onClick={() => onAi(f.key)} loading={aiLoading === f.key} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ── Step 5: Caracterização do Imóvel ─────────────────────────────────────────
export const StepCaracterizacao = ({ form, setForm, onAi, aiLoading }) => (
  <div>
    <SectionHeader
      title="5. Caracterização do Imóvel"
      subtitle="Características físicas e construtivas do imóvel avaliando."
    />
    <div className="grid grid-cols-2 gap-4">
      <Field label="Área do terreno (m²)">
        <Input type="number" step="0.01" value={form.imovel_area_terreno} onChange={(e) => setForm({ ...form, imovel_area_terreno: Number(e.target.value) })} />
      </Field>
      <Field label="Área construída (m²)">
        <Input type="number" step="0.01" value={form.imovel_area_construida} onChange={(e) => setForm({ ...form, imovel_area_construida: Number(e.target.value) })} />
      </Field>
      <Field label="Idade do imóvel (anos)">
        <Input type="number" min="0" value={form.imovel_idade} onChange={(e) => setForm({ ...form, imovel_idade: Number(e.target.value) })} />
      </Field>
      <Field label="Estado de conservação">
        <Select value={form.imovel_estado_conservacao} onValueChange={(v) => setForm({ ...form, imovel_estado_conservacao: v })}>
          <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
          <SelectContent>
            <SelectItem value="otimo">Ótimo</SelectItem>
            <SelectItem value="bom">Bom</SelectItem>
            <SelectItem value="regular">Regular</SelectItem>
            <SelectItem value="ruim">Ruim</SelectItem>
            <SelectItem value="pessimo">Péssimo</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field label="Padrão de acabamento">
        <Select value={form.imovel_padrao_acabamento} onValueChange={(v) => setForm({ ...form, imovel_padrao_acabamento: v })}>
          <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
          <SelectContent>
            <SelectItem value="alto">Alto</SelectItem>
            <SelectItem value="medio">Médio</SelectItem>
            <SelectItem value="simples">Simples</SelectItem>
            <SelectItem value="minimo">Mínimo</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field label="Número de quartos">
        <Input type="number" min="0" value={form.imovel_num_quartos} onChange={(e) => setForm({ ...form, imovel_num_quartos: Number(e.target.value) })} />
      </Field>
      <Field label="Número de banheiros">
        <Input type="number" min="0" value={form.imovel_num_banheiros} onChange={(e) => setForm({ ...form, imovel_num_banheiros: Number(e.target.value) })} />
      </Field>
      <Field label="Vagas de garagem">
        <Input type="number" min="0" value={form.imovel_num_vagas} onChange={(e) => setForm({ ...form, imovel_num_vagas: Number(e.target.value) })} />
      </Field>
      <Field label="Piscina">
        <Select value={form.imovel_piscina ? 'sim' : 'nao'} onValueChange={(v) => setForm({ ...form, imovel_piscina: v === 'sim' })}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="nao">Não</SelectItem>
            <SelectItem value="sim">Sim</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field label="Características adicionais / benfeitorias" full>
        <Textarea
          value={form.imovel_caracteristicas_adicionais || ''}
          onChange={(e) => setForm({ ...form, imovel_caracteristicas_adicionais: e.target.value })}
          rows={4}
          placeholder="Descreva acabamentos, instalações, reformas, itens diferenciados..."
        />
        <div className="mt-1 flex justify-end">
          <AiButton onClick={() => onAi('imovel_caracteristicas_adicionais')} loading={aiLoading === 'imovel_caracteristicas_adicionais'} />
        </div>
      </Field>
    </div>
  </div>
);

// ── Step 6: Amostras de Mercado ────────────────────────────────────────────────

const MarketSampleRow = ({ s, onChange, onRemove, idx }) => {
  const handleValue = (field, raw) => {
    const v = Number(raw);
    const area = field === 'area' ? v : Number(s.area || 0);
    const value = field === 'value' ? v : Number(s.value || 0);
    const vpm = area > 0 ? Math.round((value / area) * 100) / 100 : 0;
    onChange({ ...s, [field]: v, value_per_sqm: vpm });
  };

  const tipoLabel = s.tipo_amostra === 'consolidada' ? 'Consolidada' : 'Oferta';
  const tipoBadge = s.tipo_amostra === 'consolidada'
    ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
    : 'bg-amber-100 text-amber-800 border-amber-300';

  return (
    <tr className="border-t border-gray-100 text-sm">
      <td className="px-2 py-1.5 text-center text-gray-400 font-mono">{idx + 1}</td>
      <td className="px-2 py-1.5"><Input value={s.address || ''} onChange={(e) => onChange({ ...s, address: e.target.value })} placeholder="Endereço" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5"><Input value={s.neighborhood || ''} onChange={(e) => onChange({ ...s, neighborhood: e.target.value })} placeholder="Bairro" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-24"><Input type="number" value={s.area || ''} onChange={(e) => handleValue('area', e.target.value)} placeholder="m²" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-28"><Input type="number" value={s.value || ''} onChange={(e) => handleValue('value', e.target.value)} placeholder="R$" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-24 text-center font-semibold text-emerald-800">
        {s.value_per_sqm > 0 ? `R$ ${Number(s.value_per_sqm).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}` : '—'}
      </td>
      <td className="px-2 py-1.5 w-36">
        <div className="space-y-1">
          <select
            value={s.tipo_amostra || 'oferta'}
            onChange={(e) => onChange({ ...s, tipo_amostra: e.target.value })}
            className="w-full text-xs h-8 rounded border border-gray-200 px-1 focus:outline-none focus:border-emerald-400"
          >
            <option value="oferta">Oferta de Mercado</option>
            <option value="consolidada">Consolidada / Comercializada</option>
          </select>
          <span className={`inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded border ${tipoBadge}`}>
            {tipoLabel}
          </span>
        </div>
      </td>
      <td className="px-2 py-1.5"><Input value={s.source || ''} onChange={(e) => onChange({ ...s, source: e.target.value })} placeholder="Fonte" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-28"><Input type="date" value={s.collection_date || ''} onChange={(e) => onChange({ ...s, collection_date: e.target.value })} className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-28"><Input value={s.contact_phone || ''} onChange={(e) => onChange({ ...s, contact_phone: e.target.value })} placeholder="Telefone" className="text-xs h-8" /></td>
      <td className="px-2 py-1.5 w-24">
        <ImageUploader
          images={s.foto ? [s.foto] : []}
          onImagesChange={(ids) => onChange({ ...s, foto: ids[0] || null })}
          maxImages={1}
          single
          label=""
        />
      </td>
      <td className="px-2 py-1.5">
        <button type="button" onClick={onRemove} className="p-1.5 text-red-500 hover:bg-red-50 rounded">
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </td>
    </tr>
  );
};

export const StepAmostras = ({ form, setForm, onAi, aiLoading }) => {
  const samples = form.market_samples || [];
  const add = () => setForm({ ...form, market_samples: [...samples, emptyMarketSample()] });
  const update = (i, ns) => setForm({ ...form, market_samples: samples.map((s, idx) => idx === i ? ns : s) });
  const remove = (i) => setForm({ ...form, market_samples: samples.filter((_, idx) => idx !== i) });

  const validCount = samples.filter((s) => (s.value_per_sqm || 0) > 0).length;

  return (
    <div>
      <SectionHeader
        title="6. Amostras de Mercado"
        subtitle="Cadastre as amostras coletadas para a pesquisa de mercado (mínimo 3)."
      />

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">{samples.length} amostra(s) cadastrada(s)</span>
          {validCount < 3 && (
            <span className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-2 py-0.5">
              Adicione pelo menos 3 amostras com área e valor
            </span>
          )}
          {validCount >= 3 && (
            <span className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-2 py-0.5">
              {validCount} amostras com R$/m²
            </span>
          )}
        </div>
        <Button type="button" onClick={add} className="bg-emerald-900 hover:bg-emerald-800 text-white text-sm">
          <Plus className="w-4 h-4 mr-1" /> Nova amostra
        </Button>
      </div>

      {samples.length === 0 ? (
        <div className="text-center py-12 bg-emerald-50/40 rounded-xl border-2 border-dashed border-emerald-200 text-gray-500">
          Nenhuma amostra cadastrada. Clique em "Nova amostra" para começar.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="w-full text-sm min-w-[1050px]">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="px-2 py-2 text-center">#</th>
                <th className="px-2 py-2 text-left">Endereço</th>
                <th className="px-2 py-2 text-left">Bairro</th>
                <th className="px-2 py-2 text-left">Área (m²)</th>
                <th className="px-2 py-2 text-left">Valor (R$)</th>
                <th className="px-2 py-2 text-center">R$/m²</th>
                <th className="px-2 py-2 text-left">Tipo</th>
                <th className="px-2 py-2 text-left">Fonte</th>
                <th className="px-2 py-2 text-left">Data coleta</th>
                <th className="px-2 py-2 text-left">Telefone</th>
                <th className="px-2 py-2 text-left">Foto</th>
                <th className="px-2 py-2" />
              </tr>
            </thead>
            <tbody>
              {samples.map((s, i) => (
                <MarketSampleRow
                  key={s._key || `ms-${i}`}
                  s={s}
                  idx={i}
                  onChange={(ns) => update(i, ns)}
                  onRemove={() => remove(i)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2 mt-3">
        Amostras consolidadas (venda/locacao efetivada) tem maior peso na avaliacao conforme NBR 14653.
      </p>

      <div className="mt-6">
        <label className="block text-sm font-medium text-gray-700 mb-1.5">Análise de mercado (texto descritivo)</label>
        <Textarea
          value={form.market_analysis || ''}
          onChange={(e) => setForm({ ...form, market_analysis: e.target.value })}
          rows={4}
          placeholder="Descreva o comportamento do mercado imobiliário local, oferta, demanda, liquidez..."
        />
        <div className="mt-1 flex justify-end">
          <AiButton onClick={() => onAi('market_analysis')} loading={aiLoading === 'market_analysis'} />
        </div>
      </div>
    </div>
  );
};

// ── Step 7: Metodologia ────────────────────────────────────────────────────────
export const StepMetodologia = ({ form, setForm, onAi, aiLoading }) => (
  <div>
    <SectionHeader
      title="7. Metodologia"
      subtitle="Método avaliativo adotado conforme ABNT NBR 14.653."
    />
    <div className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">Método escolhido</label>
        <Select value={form.methodology} onValueChange={(v) => setForm({ ...form, methodology: v })}>
          <SelectTrigger className="max-w-md"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="Método Comparativo Direto de Dados de Mercado">Método Comparativo Direto de Dados de Mercado</SelectItem>
            <SelectItem value="Método Evolutivo">Método Evolutivo</SelectItem>
            <SelectItem value="Método Involutivo">Método Involutivo</SelectItem>
            <SelectItem value="Método da Renda">Método da Renda</SelectItem>
            <SelectItem value="Método do Custo de Reprodução">Método do Custo de Reprodução</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">Justificativa e fundamentação do método</label>
        <Textarea
          value={form.methodology_justification || ''}
          onChange={(e) => setForm({ ...form, methodology_justification: e.target.value })}
          rows={6}
          placeholder="Justifique tecnicamente a escolha do método conforme as características do imóvel e disponibilidade de dados..."
        />
        <div className="mt-1 flex justify-end">
          <AiButton onClick={() => onAi('methodology_justification')} loading={aiLoading === 'methodology_justification'} />
        </div>
      </div>
    </div>
  </div>
);

// ── Step 8: Cálculos e Tratamento Estatístico ─────────────────────────────────
export const StepCalculos = ({ form, setForm, onAi, aiLoading }) => {
  const samples = form.market_samples || [];
  const auto = computeStats(samples);

  useEffect(() => {
    if (samples.length > 0) {
      setForm((f) => ({
        ...f,
        calc_media: auto.media,
        calc_mediana: auto.mediana,
        calc_desvio_padrao: auto.desvio_padrao,
        calc_coef_variacao: auto.coef_variacao,
      }));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [samples.length]);

  const validSamples = samples.filter((s) => (s.value_per_sqm || 0) > 0);
  const cvClass = auto.coef_variacao <= 15 ? 'text-emerald-700' : auto.coef_variacao <= 30 ? 'text-amber-600' : 'text-red-600';

  return (
    <div>
      <SectionHeader
        title="8. Cálculos e Tratamento Estatístico"
        subtitle="Estatísticas calculadas automaticamente com base nas amostras coletadas."
      />

      {validSamples.length === 0 ? (
        <div className="p-6 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm mb-6">
          Nenhuma amostra com área e valor informados. Volte ao passo 6 e preencha as amostras.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <StatBox label="Média R$/m²" value={auto.media} unit={`${validSamples.length} amostras`} />
            <StatBox label="Mediana R$/m²" value={auto.mediana} />
            <StatBox label="Desvio Padrão" value={auto.desvio_padrao} />
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-center">
              <div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">CV (%)</div>
              <div className={`text-2xl font-bold ${cvClass}`}>
                {auto.coef_variacao.toFixed(2)}%
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                {auto.coef_variacao <= 15 ? 'Homogêneo' : auto.coef_variacao <= 30 ? 'Heterogêneo' : 'Muito heterogêneo'}
              </div>
            </div>
          </div>

          <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 mb-6">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-500 uppercase">
                <tr>
                  <th className="text-left py-1.5 px-2">#</th>
                  <th className="text-left py-1.5 px-2">Endereço / Bairro</th>
                  <th className="text-right py-1.5 px-2">Área (m²)</th>
                  <th className="text-right py-1.5 px-2">Valor (R$)</th>
                  <th className="text-right py-1.5 px-2">R$/m²</th>
                </tr>
              </thead>
              <tbody>
                {validSamples.map((s, i) => (
                  <tr key={s._key || i} className="border-t border-gray-100">
                    <td className="py-1.5 px-2 text-gray-400">{i + 1}</td>
                    <td className="py-1.5 px-2">{s.address || s.neighborhood || '—'}</td>
                    <td className="py-1.5 px-2 text-right">{Number(s.area || 0).toLocaleString('pt-BR')}</td>
                    <td className="py-1.5 px-2 text-right">{Number(s.value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</td>
                    <td className="py-1.5 px-2 text-right font-semibold text-emerald-800">
                      {Number(s.value_per_sqm || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Grau de Fundamentação (NBR 14.653-2)</label>
          <div className="flex gap-4 items-start">
            <div className="w-56 shrink-0">
              <Select value={form.calc_grau_fundamentacao} onValueChange={(v) => setForm({ ...form, calc_grau_fundamentacao: v })}>
                <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="I">Grau I</SelectItem>
                  <SelectItem value="II">Grau II</SelectItem>
                  <SelectItem value="III">Grau III</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {form.calc_grau_fundamentacao && (() => {
              const fundamentacaoTexts = {
                I: {
                  title: 'Grau I — Fundamentação Mínima',
                  text: 'Exige no mínimo 3 dados de mercado, com identificação dos fatores relevantes. Permite tratamento por fatores ou inferência estatística simplificada. Aplicável quando há limitação de dados disponíveis na região.',
                },
                II: {
                  title: 'Grau II — Fundamentação Intermediária',
                  text: 'Exige no mínimo 6 dados de mercado verificados, com apresentação de estatísticas descritivas. Requer tratamento por fatores com justificativa ou modelo de regressão com significância mínima de 80%. Indicado para avaliações de maior responsabilidade.',
                },
                III: {
                  title: 'Grau III — Fundamentação Máxima',
                  text: 'Exige no mínimo 10 dados de mercado verificados e visitados. Requer modelo de regressão com nível de significância de 90% ou superior, com análise de micronumerosidade. Obrigatório para desapropriações, perícias judiciais e financiamentos de grande porte.',
                },
              };
              const info = fundamentacaoTexts[form.calc_grau_fundamentacao];
              return info ? (
                <div className="flex-1 flex gap-2.5 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
                  <svg className="w-4 h-4 mt-0.5 text-amber-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <p className="text-xs font-semibold text-amber-800 mb-0.5">{info.title}</p>
                    <p className="text-xs text-amber-700 leading-relaxed">{info.text}</p>
                  </div>
                </div>
              ) : null;
            })()}
          </div>
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Fatores de Homogeneização aplicados</label>
          <Textarea
            value={form.calc_fatores_homogeneizacao || ''}
            onChange={(e) => setForm({ ...form, calc_fatores_homogeneizacao: e.target.value })}
            rows={3}
            placeholder="Descreva os fatores aplicados: localização, área, padrão construtivo, etc."
          />
          <div className="mt-1 flex justify-end">
            <AiButton onClick={() => onAi('calc_fatores_homogeneizacao')} loading={aiLoading === 'calc_fatores_homogeneizacao'} />
          </div>
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Observações sobre os cálculos</label>
          <Textarea
            value={form.calc_observacoes || ''}
            onChange={(e) => setForm({ ...form, calc_observacoes: e.target.value })}
            rows={3}
            placeholder="Outliers descartados, ajustes realizados, limitações dos dados..."
          />
          <div className="mt-1 flex justify-end">
            <AiButton onClick={() => onAi('calc_observacoes')} loading={aiLoading === 'calc_observacoes'} />
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Step 8b: Cálculo de Ponderância ──────────────────────────────────────────
export const StepPonderancia = ({ form, setForm }) => {
  const samples = (form.market_samples || []).filter((s) => Number(s.area || 0) > 0 && Number(s.value || 0) > 0);

  const fmtBrl = (v) =>
    Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

  const fmtBrlM2 = (v) =>
    `${Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/m²`;

  // Compute value_per_sqm for each sample on-the-fly (already stored, but recalc for reliability)
  const samplesWithVpm = samples.map((s) => ({
    ...s,
    _vpm: Number(s.area) > 0 ? Number(s.value) / Number(s.area) : 0,
  }));

  const eliminadas = form.ponderancia_eliminadas || [];

  const calcular = () => {
    if (samplesWithVpm.length === 0) return;
    const vpms = samplesWithVpm.map((s) => s._vpm);
    const mediaSimples = vpms.reduce((a, b) => a + b, 0) / vpms.length;
    const limInf = mediaSimples * 0.5;
    const limSup = mediaSimples * 1.5;

    const novasEliminadas = samplesWithVpm
      .map((s, idx) => ({ idx, vpm: s._vpm }))
      .filter(({ vpm }) => vpm < limInf || vpm > limSup)
      .map(({ idx }) => idx);

    const restantes = samplesWithVpm.filter((_, i) => !novasEliminadas.includes(i));
    const mediaFinal =
      restantes.length > 0
        ? restantes.reduce((a, s) => a + s._vpm, 0) / restantes.length
        : 0;

    // Area do imovel avaliando
    const area = Number(form.imovel_area_construida || form.imovel_area_terreno || form.property_area_sqm || 0);
    const valorFinal = mediaFinal * area;

    setForm((f) => ({
      ...f,
      ponderancia_media: Math.round(mediaFinal * 100) / 100,
      ponderancia_limite_inf: Math.round(limInf * 100) / 100,
      ponderancia_limite_sup: Math.round(limSup * 100) / 100,
      ponderancia_eliminadas: novasEliminadas,
      ponderancia_valor_final: Math.round(valorFinal * 100) / 100,
    }));
  };

  const usarNoLaudo = () => {
    if (!form.ponderancia_media) return;
    const area = Number(form.imovel_area_construida || form.imovel_area_terreno || form.property_area_sqm || 0);
    const valorFinal = form.ponderancia_valor_final || form.ponderancia_media * area;
    setForm((f) => ({
      ...f,
      resultado_valor_unitario: form.ponderancia_media,
      resultado_valor_total: Math.round(valorFinal * 100) / 100,
      total_indemnity: Math.round(valorFinal * 100) / 100,
    }));
  };

  const area = Number(form.imovel_area_construida || form.imovel_area_terreno || form.property_area_sqm || 0);
  const calculado = form.ponderancia_media != null && form.ponderancia_media > 0;
  const restantesCount = samplesWithVpm.length - (form.ponderancia_eliminadas || []).length;

  return (
    <div>
      <SectionHeader
        title="8b. Cálculo de Ponderância"
        subtitle="Filtra amostras fora da faixa de 50%–150% da média e calcula a média ponderada final."
      />

      {samples.length === 0 ? (
        <div className="p-6 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm">
          Nenhuma amostra com área e valor preenchidos. Volte ao passo 6 e cadastre as amostras.
        </div>
      ) : (
        <>
          {/* Tabela de amostras */}
          <div className="overflow-x-auto rounded-xl border border-gray-200 mb-5">
            <table className="w-full text-sm min-w-[640px]">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider">
                <tr>
                  <th className="px-3 py-2 text-center">Nº</th>
                  <th className="px-3 py-2 text-left">Bairro</th>
                  <th className="px-3 py-2 text-center">Quartos</th>
                  <th className="px-3 py-2 text-right">Área Total (m²)</th>
                  <th className="px-3 py-2 text-right">Valor Total (R$)</th>
                  <th className="px-3 py-2 text-right">Valor/m²</th>
                  <th className="px-3 py-2 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {samplesWithVpm.map((s, i) => {
                  const eliminada = eliminadas.includes(i);
                  const rowBg = calculado
                    ? eliminada
                      ? 'bg-red-50'
                      : 'bg-green-50'
                    : 'bg-white';
                  const textDecor = calculado && eliminada ? 'line-through text-red-400' : '';
                  return (
                    <tr key={s._key || i} className={`border-t border-gray-100 ${rowBg}`}>
                      <td className={`px-3 py-2 text-center font-mono text-gray-500 ${textDecor}`}>{i + 1}</td>
                      <td className={`px-3 py-2 ${textDecor}`}>{s.neighborhood || s.address || '—'}</td>
                      <td className={`px-3 py-2 text-center ${textDecor}`}>{s.quartos || '—'}</td>
                      <td className={`px-3 py-2 text-right ${textDecor}`}>
                        {Number(s.area || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className={`px-3 py-2 text-right ${textDecor}`}>
                        {fmtBrl(s.value)}
                      </td>
                      <td className={`px-3 py-2 text-right font-semibold ${calculado && !eliminada ? 'text-emerald-800' : textDecor || 'text-gray-700'}`}>
                        R$ {s._vpm.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {calculado ? (
                          eliminada ? (
                            <span className="text-xs font-semibold text-red-600 bg-red-100 px-2 py-0.5 rounded-full">Eliminada</span>
                          ) : (
                            <span className="text-xs font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">OK</span>
                          )
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Botão Calcular */}
          <div className="flex justify-center mb-6">
            <Button
              type="button"
              onClick={calcular}
              className="bg-emerald-900 hover:bg-emerald-800 text-white px-8 py-2 text-sm font-semibold"
            >
              Calcular Ponderância
            </Button>
          </div>

          {/* Card de resultado */}
          {calculado && (() => {
            const amostrasValidas = samplesWithVpm.filter((_, i) => !eliminadas.includes(i));
            const N = amostrasValidas.length;
            const peso = N > 0 ? 1 / N : 0;
            const somaVpm = amostrasValidas.reduce((acc, s) => acc + s._vpm, 0);
            const fmt2 = (v) => Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

            return (
              <div className="space-y-4">
                {/* Cards de métricas */}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center">
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Limite Inferior</div>
                    <div className="text-base font-bold text-gray-800">
                      R$ {fmt2(form.ponderancia_limite_inf)}/m²
                    </div>
                  </div>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center">
                    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Limite Superior</div>
                    <div className="text-base font-bold text-gray-800">
                      R$ {fmt2(form.ponderancia_limite_sup)}/m²
                    </div>
                  </div>
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center">
                    <div className="text-xs text-red-600 uppercase tracking-wider mb-1">Eliminadas</div>
                    <div className="text-base font-bold text-red-700">{eliminadas.length}</div>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center">
                    <div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">Restantes</div>
                    <div className="text-base font-bold text-emerald-800">{restantesCount}</div>
                  </div>
                </div>

                {/* Média ponderada final */}
                <div className="bg-emerald-50 border-2 border-emerald-300 rounded-xl p-5">
                  <div className="text-xs text-emerald-700 uppercase tracking-wider mb-2">
                    Fórmula: Σ Valores Restantes / {restantesCount} amostras restantes
                  </div>
                  <div className="text-3xl font-bold text-emerald-900 mb-1">
                    Média Ponderada Final: R$ {fmt2(form.ponderancia_media)}/m²
                  </div>
                </div>

                {/* ── Ponderação dos Valores ─────────────────────────────── */}
                {N > 0 && (
                  <div className="rounded-xl border border-emerald-200 bg-white overflow-hidden">
                    <div className="bg-emerald-800 text-white px-4 py-2.5">
                      <div className="text-sm font-semibold">Ponderação dos Valores</div>
                      <div className="text-xs text-emerald-200 mt-0.5">
                        Apenas amostras válidas (não eliminadas) — peso igualitário 1/N
                      </div>
                    </div>

                    {/* Tabela das amostras válidas */}
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm min-w-[540px]">
                        <thead className="bg-emerald-50 text-xs text-emerald-800 uppercase tracking-wider">
                          <tr>
                            <th className="px-3 py-2 text-center">Nº</th>
                            <th className="px-3 py-2 text-left">Bairro</th>
                            <th className="px-3 py-2 text-right">Valor/m²</th>
                            <th className="px-3 py-2 text-center">Peso (1/{N})</th>
                            <th className="px-3 py-2 text-right">Valor Ponderado</th>
                          </tr>
                        </thead>
                        <tbody>
                          {amostrasValidas.map((s, idx) => {
                            const valorPonderado = s._vpm * peso;
                            return (
                              <tr key={s._key || idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-emerald-50/40'}>
                                <td className="px-3 py-2 text-center font-mono text-gray-500">{idx + 1}</td>
                                <td className="px-3 py-2 text-gray-700">{s.neighborhood || s.address || '—'}</td>
                                <td className="px-3 py-2 text-right font-semibold text-emerald-800">
                                  R$ {fmt2(s._vpm)}
                                </td>
                                <td className="px-3 py-2 text-center text-gray-600">
                                  {(peso * 100).toFixed(4)}%
                                </td>
                                <td className="px-3 py-2 text-right font-semibold text-gray-800">
                                  R$ {fmt2(valorPonderado)}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                        <tfoot className="border-t-2 border-emerald-300 bg-emerald-100">
                          <tr>
                            <td colSpan={2} className="px-3 py-2.5 text-sm font-bold text-emerald-900">
                              SOMA ({N} amostras)
                            </td>
                            <td className="px-3 py-2.5 text-right font-bold text-emerald-900">
                              R$ {fmt2(somaVpm)}
                            </td>
                            <td className="px-3 py-2.5 text-center font-bold text-emerald-900">
                              100%
                            </td>
                            <td className="px-3 py-2.5 text-right font-bold text-emerald-900">
                              R$ {fmt2(form.ponderancia_media)}
                            </td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>

                    {/* Cálculo passo a passo */}
                    <div className="border-t border-emerald-100 bg-emerald-50/60 px-4 py-3 space-y-1.5">
                      <div className="text-xs font-semibold text-emerald-800 uppercase tracking-wider mb-2">
                        Cálculo Passo a Passo
                      </div>
                      <div className="text-sm text-gray-700">
                        <span className="font-medium">1.</span> Soma dos Valor/m² válidos:{' '}
                        <span className="font-bold text-emerald-800">
                          {amostrasValidas.map((s) => `R$ ${fmt2(s._vpm)}`).join(' + ')} = R$ {fmt2(somaVpm)}
                        </span>
                      </div>
                      <div className="text-sm text-gray-700">
                        <span className="font-medium">2.</span> Dividido por N (amostras válidas):{' '}
                        <span className="font-bold text-emerald-800">R$ {fmt2(somaVpm)} ÷ {N}</span>
                      </div>
                      <div className="text-sm text-gray-700 flex items-center gap-2">
                        <span className="font-medium">3.</span>
                        <span className="text-base font-bold text-emerald-900">
                          = Média Ponderada Final: R$ {fmt2(form.ponderancia_media)}/m²
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Valor final do imóvel */}
                <div className="border-t border-gray-100 pt-4">
                  <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-3">
                    <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
                      Área do imóvel avaliando (m²):
                    </label>
                    <span className="font-semibold text-gray-900">
                      {area > 0
                        ? area.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' m²'
                        : <span className="text-amber-600 text-sm">Preencha a área no step do imóvel (passo 5)</span>}
                    </span>
                  </div>

                  {area > 0 && (
                    <div className="bg-gradient-to-r from-amber-50 to-yellow-50 border-2 border-amber-400 rounded-xl p-5">
                      <div className="text-xs text-amber-700 uppercase tracking-wider mb-1">
                        Valor Final = {fmtBrlM2(form.ponderancia_media)} × {area.toLocaleString('pt-BR')} m²
                      </div>
                      <div className="text-3xl font-bold text-amber-800">
                        Valor do Imóvel: {fmtBrl(form.ponderancia_valor_final)}
                      </div>
                    </div>
                  )}
                </div>

                {/* Botão usar no laudo */}
                <div className="flex justify-end">
                  <Button
                    type="button"
                    onClick={usarNoLaudo}
                    className="bg-amber-600 hover:bg-amber-700 text-white px-6 py-2 text-sm font-semibold"
                  >
                    Usar este valor no laudo
                  </Button>
                </div>
              </div>
            );
          })()}
        </>
      )}
    </div>
  );
};

// ── Step 9: Resultado da Avaliação ────────────────────────────────────────────
export const StepResultado = ({ form, setForm }) => {
  const stats = computeStats(form.market_samples || []);
  const area = Number(form.imovel_area_construida || form.imovel_area_terreno || form.property_area_sqm || 0);
  const unitario = form.resultado_valor_unitario || stats.media || 0;
  const total = unitario * area;

  // confidence interval ±10% as default
  const inf = unitario * 0.9;
  const sup = unitario * 1.1;

  const fmtBrl = (v) => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

  return (
    <div>
      <SectionHeader
        title="9. Resultado da Avaliação"
        subtitle="Valor final do imóvel calculado com base nas amostras e método adotado."
      />

      <div className="bg-gradient-to-br from-emerald-900 to-emerald-950 text-white rounded-2xl p-7 mb-6">
        <div className="text-xs text-emerald-300 uppercase tracking-widest mb-1">Valor de Mercado Estimado</div>
        <div className="font-display text-5xl font-bold mb-2">
          {fmtBrl(form.resultado_valor_total || total)}
        </div>
        <div className="text-sm text-emerald-200">
          Valor unitário: {fmtBrl(unitario)}/m² &nbsp;·&nbsp; Área de referência: {area.toLocaleString('pt-BR')} m²
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Valor unitário R$/m² (base)</label>
          <Input
            type="number" step="0.01"
            value={form.resultado_valor_unitario || unitario}
            onChange={(e) => setForm({ ...form, resultado_valor_unitario: Number(e.target.value), resultado_valor_total: Number(e.target.value) * area })}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Valor total (R$)</label>
          <Input
            type="number" step="0.01"
            value={form.resultado_valor_total || total}
            onChange={(e) => setForm({ ...form, resultado_valor_total: Number(e.target.value), total_indemnity: Number(e.target.value) })}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Intervalo de confiança — Inf. R$/m²</label>
          <Input
            type="number" step="0.01"
            value={form.resultado_intervalo_inf || inf}
            onChange={(e) => setForm({ ...form, resultado_intervalo_inf: Number(e.target.value) })}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Intervalo de confiança — Sup. R$/m²</label>
          <Input
            type="number" step="0.01"
            value={form.resultado_intervalo_sup || sup}
            onChange={(e) => setForm({ ...form, resultado_intervalo_sup: Number(e.target.value) })}
          />
        </div>

        {/* Grau de Precisão — NBR 14653-1 item 9 */}
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Grau de Precisão <span className="text-xs text-gray-400">— NBR 14653-1 item 9</span>
          </label>
          <div className="flex gap-4 items-start">
            <div className="w-56 shrink-0">
              <Select value={form.grau_precisao || 'I'} onValueChange={(v) => setForm({ ...form, grau_precisao: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="I">Grau I — Amplitude ≤ 30%</SelectItem>
                  <SelectItem value="II">Grau II — Amplitude ≤ 20%</SelectItem>
                  <SelectItem value="III">Grau III — Amplitude ≤ 10%</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {(() => {
              const precisaoTexts = {
                I: {
                  title: 'Grau I — Precisão Mínima',
                  text: 'Amplitude do intervalo de confiança de até 30% em torno do valor central. Aceitável para avaliações expeditas e opinativas.',
                },
                II: {
                  title: 'Grau II — Precisão Intermediária',
                  text: 'Amplitude do intervalo de confiança de até 20%. Adequado para a maioria das avaliações de mercado e financiamentos.',
                },
                III: {
                  title: 'Grau III — Precisão Máxima',
                  text: 'Amplitude do intervalo de confiança de até 10%. Exigido em perícias judiciais e avaliações de alta complexidade.',
                },
              };
              const info = precisaoTexts[form.grau_precisao || 'I'];
              return info ? (
                <div className="flex-1 flex gap-2.5 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3">
                  <svg className="w-4 h-4 mt-0.5 text-emerald-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <p className="text-xs font-semibold text-emerald-800 mb-0.5">{info.title}</p>
                    <p className="text-xs text-emerald-700 leading-relaxed">{info.text}</p>
                  </div>
                </div>
              ) : null;
            })()}
          </div>
        </div>

        {/* Campo de Arbítrio — NBR 14653-1 item 9.2.4 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Campo de Arbítrio <span className="text-xs text-gray-400">— ±15% (NBR 14653-1 item 9.2.4)</span>
          </label>
          <div className="flex gap-2 items-center">
            <Input
              type="number" step="0.01" placeholder="-15% (mín)"
              value={form.campo_arbitrio_min || ''}
              onChange={(e) => setForm({ ...form, campo_arbitrio_min: Number(e.target.value) })}
              className="flex-1"
            />
            <span className="text-gray-400 text-sm">até</span>
            <Input
              type="number" step="0.01" placeholder="+15% (máx)"
              value={form.campo_arbitrio_max || ''}
              onChange={(e) => setForm({ ...form, campo_arbitrio_max: Number(e.target.value) })}
              className="flex-1"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Data de referência da avaliação</label>
          <Input type="date" value={form.resultado_data_referencia || ''} onChange={(e) => setForm({ ...form, resultado_data_referencia: e.target.value })} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Prazo de validade do laudo</label>
          <Input value={form.resultado_prazo_validade || ''} onChange={(e) => setForm({ ...form, resultado_prazo_validade: e.target.value })} placeholder="Ex: 6 meses" />
        </div>
        <div className="col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Valor por extenso</label>
          <Input
            value={form.total_indemnity_words || ''}
            onChange={(e) => setForm({ ...form, total_indemnity_words: e.target.value })}
            placeholder="Ex: cento e cinquenta mil reais"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Cidade de emissão</label>
          <Input value={form.conclusion_city || ''} onChange={(e) => setForm({ ...form, conclusion_city: e.target.value })} placeholder="São Luís/MA" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Data de emissão</label>
          <Input type="date" value={form.conclusion_date || ''} onChange={(e) => setForm({ ...form, conclusion_date: e.target.value })} />
        </div>
      </div>
    </div>
  );
};

// ── Step 10: Considerações Finais ─────────────────────────────────────────────
export const StepConclusao = ({ form, setForm, onAi, aiLoading }) => (
  <div>
    <SectionHeader
      title="10. Considerações Finais"
      subtitle="Ressalvas, pressupostos e assinatura do responsável técnico."
    />
    <div className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">Ressalvas</label>
        <Textarea
          value={form.consideracoes_ressalvas || ''}
          onChange={(e) => setForm({ ...form, consideracoes_ressalvas: e.target.value })}
          rows={3}
          placeholder="Registre ressalvas importantes sobre dados, documentação ou condições do imóvel..."
        />
        <div className="mt-1 flex justify-end">
          <AiButton onClick={() => onAi('consideracoes_ressalvas')} loading={aiLoading === 'consideracoes_ressalvas'} />
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">Pressupostos</label>
        <Textarea
          value={form.consideracoes_pressupostos || ''}
          onChange={(e) => setForm({ ...form, consideracoes_pressupostos: e.target.value })}
          rows={3}
          placeholder="Pressupostos adotados na avaliação..."
        />
        <div className="mt-1 flex justify-end">
          <AiButton onClick={() => onAi('consideracoes_pressupostos')} loading={aiLoading === 'consideracoes_pressupostos'} />
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">Limitações</label>
        <Textarea
          value={form.consideracoes_limitacoes || ''}
          onChange={(e) => setForm({ ...form, consideracoes_limitacoes: e.target.value })}
          rows={3}
          placeholder="Limitações da avaliação, dados indisponíveis, restrições de acesso ao imóvel..."
        />
        <div className="mt-1 flex justify-end">
          <AiButton onClick={() => onAi('consideracoes_limitacoes')} loading={aiLoading === 'consideracoes_limitacoes'} />
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">Texto de conclusão técnica</label>
        <Textarea
          value={form.conclusion_text || ''}
          onChange={(e) => setForm({ ...form, conclusion_text: e.target.value })}
          rows={5}
          placeholder="Texto final de conclusão do laudo..."
        />
        <div className="mt-1 flex justify-end">
          <AiButton onClick={() => onAi('conclusion_text')} loading={aiLoading === 'conclusion_text'} />
        </div>
      </div>

      <div className="border-t border-gray-100 pt-5">
        <div className="text-sm font-semibold text-gray-900 mb-3">Responsável Técnico</div>
        <div className="grid grid-cols-2 gap-4">
          {/* Tipo de profissional */}
          <div className="col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Tipo de profissional <span className="text-xs text-gray-400">— define habilitação legal</span>
            </label>
            <Select value={form.tipo_profissional || 'corretor'} onValueChange={(v) => setForm({ ...form, tipo_profissional: v })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="corretor">Corretor de Imóveis (CRECI) — Res. COFECI 957/06</SelectItem>
                <SelectItem value="engenheiro">Engenheiro / Arquiteto (CREA + ART) — Lei 5.194/66</SelectItem>
                <SelectItem value="arquiteto">Arquiteto (CAU + RRT) — Lei 12.378/10</SelectItem>
                <SelectItem value="perito_judicial">Perito Judicial (CREA/CAU + Cadastro Tribunal) — CPC art. 156</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Nome completo</label>
            <Input value={form.responsavel_nome || ''} onChange={(e) => setForm({ ...form, responsavel_nome: e.target.value })} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">CRECI</label>
            <Input value={form.responsavel_creci || ''} onChange={(e) => setForm({ ...form, responsavel_creci: e.target.value })} placeholder="CRECI/MA nº 000000" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">CNAI</label>
            <Input value={form.responsavel_cnai || ''} onChange={(e) => setForm({ ...form, responsavel_cnai: e.target.value })} placeholder="CNAI nº 000000" />
          </div>
          {/* Registro profissional unificado (CRECI/CREA/CAU) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Registro profissional (CREA / CAU)</label>
            <Input
              value={form.registro_profissional || ''}
              onChange={(e) => setForm({ ...form, registro_profissional: e.target.value })}
              placeholder="CREA/MA nº 000000 ou CAU/MA nº A000000"
            />
          </div>
          {/* ART / RRT */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Nº ART / RRT <span className="text-xs text-gray-400">— Res. CONFEA 345/90 (quando exigível)</span>
            </label>
            <Input
              value={form.art_rrt_numero || ''}
              onChange={(e) => setForm({ ...form, art_rrt_numero: e.target.value })}
              placeholder="Número da ART ou RRT"
            />
          </div>
          {/* Prazo de validade */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Prazo de validade do laudo <span className="text-xs text-gray-400">— padrão 6 meses</span>
            </label>
            <Select
              value={String(form.prazo_validade_meses || 6)}
              onValueChange={(v) => setForm({ ...form, prazo_validade_meses: Number(v) })}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="3">3 meses</SelectItem>
                <SelectItem value="6">6 meses (padrão NBR 14653)</SelectItem>
                <SelectItem value="12">12 meses</SelectItem>
                <SelectItem value="24">24 meses</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div />
        </div>
      </div>
    </div>
  </div>
);

// ── Step 8c: Método de Avaliação / Depreciação e Valorização ─────────────────

const fmtBRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const ESTADOS_RH = [
  { value: 'A', label: 'A — Novo',                ke: 1.00 },
  { value: 'B', label: 'B — Bom',                 ke: 0.85 },
  { value: 'C', label: 'C — Regular',             ke: 0.65 },
  { value: 'D', label: 'D — Precário',             ke: 0.50 },
  { value: 'E', label: 'E — Ruim',                ke: 0.35 },
  { value: 'F', label: 'F — Péssimo',             ke: 0.20 },
  { value: 'G', label: 'G — Sem Valor Comercial',  ke: 0.10 },
  { value: 'H', label: 'H — Demolição',            ke: 0.05 },
];

function calcRH(p) {
  const ke = (ESTADOS_RH.find((e) => e.value === (p.estado || 'C')) || ESTADOS_RH[2]).ke;
  const idRatio = Math.min(Number(p.idade_atual || 0) / Math.max(Number(p.vida_util || 60), 1), 1);
  const kd = idRatio * idRatio * (1 - ke) + idRatio * ke;
  return { kd, depPct: kd * 100, valDep: Number(p.valor_novo || 0) * kd, valResidual: Number(p.valor_novo || 0) * (1 - kd) };
}

const FormRossHeidecke = ({ params, setParams, onCalc }) => {
  const r = calcRH(params);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field label="Valor de Novo (R$)"><Input type="number" step="0.01" value={params.valor_novo || ''} onChange={(e) => setParams({ ...params, valor_novo: Number(e.target.value) })} placeholder="R$ 0,00" /></Field>
        <Field label="Idade Atual (anos)"><Input type="number" min="0" value={params.idade_atual || ''} onChange={(e) => setParams({ ...params, idade_atual: Number(e.target.value) })} placeholder="0" /></Field>
        <Field label="Vida Útil (padrão 60 anos)"><Input type="number" min="1" value={params.vida_util || 60} onChange={(e) => setParams({ ...params, vida_util: Number(e.target.value) })} /></Field>
        <Field label="Estado de Conservação (A–H)">
          <Select value={params.estado || 'C'} onValueChange={(v) => setParams({ ...params, estado: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{ESTADOS_RH.map((e) => <SelectItem key={e.value} value={e.value}>{e.label}</SelectItem>)}</SelectContent>
          </Select>
        </Field>
      </div>
      {Number(params.valor_novo) > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-center">
            <div className="text-xs text-amber-700 uppercase tracking-wider mb-1">Coeficiente Kd</div>
            <div className="text-xl font-bold text-amber-800">{r.kd.toFixed(4)}</div>
            <div className="text-xs text-gray-500">{r.depPct.toFixed(2)}% depreciado</div>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center">
            <div className="text-xs text-red-600 uppercase tracking-wider mb-1">Depreciação</div>
            <div className="text-xl font-bold text-red-700">{fmtBRL(r.valDep)}</div>
          </div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center">
            <div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">Valor Residual</div>
            <div className="text-xl font-bold text-emerald-800">{fmtBRL(r.valResidual)}</div>
          </div>
        </div>
      )}
      <button type="button" onClick={() => onCalc({ depPct: r.depPct, valDep: r.valDep, valBenfeitoria: r.valResidual, valTotal: r.valResidual })} className="w-full py-2 bg-emerald-900 hover:bg-emerald-800 text-white rounded-lg text-sm font-semibold">Aplicar Ross-Heidecke ao Laudo</button>
    </div>
  );
};

function calcLR(p) {
  const vn = Number(p.valor_novo || 0);
  const resid = vn * (Number(p.residual_pct ?? 20) / 100);
  const depAnual = (vn - resid) / Math.max(Number(p.vida_util ?? 40), 1);
  const depAcum = depAnual * Math.min(Number(p.idade_atual || 0), Number(p.vida_util ?? 40));
  return { depAnual, depAcum, valAtual: Math.max(vn - depAcum, resid) };
}

const FormLinhaReta = ({ params, setParams, onCalc }) => {
  const r = calcLR(params);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field label="Valor de Novo (R$)"><Input type="number" step="0.01" value={params.valor_novo || ''} onChange={(e) => setParams({ ...params, valor_novo: Number(e.target.value) })} placeholder="R$ 0,00" /></Field>
        <Field label="Valor Residual (%)"><Input type="number" min="0" max="100" step="0.1" value={params.residual_pct ?? 20} onChange={(e) => setParams({ ...params, residual_pct: Number(e.target.value) })} /></Field>
        <Field label="Vida Útil (padrão 40 anos)"><Input type="number" min="1" value={params.vida_util ?? 40} onChange={(e) => setParams({ ...params, vida_util: Number(e.target.value) })} /></Field>
        <Field label="Idade Atual (anos)"><Input type="number" min="0" value={params.idade_atual || ''} onChange={(e) => setParams({ ...params, idade_atual: Number(e.target.value) })} placeholder="0" /></Field>
      </div>
      {Number(params.valor_novo) > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center"><div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Dep. Anual</div><div className="text-lg font-bold text-gray-800">{fmtBRL(r.depAnual)}</div></div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center"><div className="text-xs text-red-600 uppercase tracking-wider mb-1">Dep. Acumulada</div><div className="text-lg font-bold text-red-700">{fmtBRL(r.depAcum)}</div></div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center"><div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">Valor Atual</div><div className="text-lg font-bold text-emerald-800">{fmtBRL(r.valAtual)}</div></div>
        </div>
      )}
      <button type="button" onClick={() => onCalc({ depPct: Number(params.valor_novo) > 0 ? (r.depAcum / Number(params.valor_novo)) * 100 : 0, valDep: r.depAcum, valBenfeitoria: r.valAtual, valTotal: r.valAtual })} className="w-full py-2 bg-emerald-900 hover:bg-emerald-800 text-white rounded-lg text-sm font-semibold">Aplicar Linha Reta ao Laudo</button>
    </div>
  );
};

const FATOR_LOC = [{ value: '1.10', label: 'Esquina (+10%)' }, { value: '1.00', label: 'Meio de Quadra (referência)' }, { value: '0.85', label: 'Fundos (-15%)' }];
const FATOR_TOPO = [{ value: '1.00', label: 'Plano' }, { value: '0.95', label: 'Aclive suave (-5%)' }, { value: '0.90', label: 'Declive suave (-10%)' }, { value: '0.80', label: 'Acentuado (-20%)' }, { value: '0.70', label: 'Irregular (-30%)' }];
const FATOR_INFRA = [{ value: '1.00', label: 'Infraestrutura completa' }, { value: '0.90', label: 'Parcial (-10%)' }, { value: '0.75', label: 'Básica apenas (-25%)' }];

function fatorTestada(m) { const v = Number(m || 0); if (v <= 0) return 1; if (v < 8) return 0.90; if (v <= 15) return 1.00; return 1.05; }

function calcFT(p) {
  const ft = fatorTestada(p.testada_m);
  const vuAdj = Number(p.valor_unitario || 0) * Number(p.f_loc || 1) * Number(p.f_topo || 1) * ft * Number(p.f_infra || 1);
  return { ft, vuAdj, valTotal: vuAdj * Number(p.area_terreno || 0) };
}

const FormFatoresTerreno = ({ params, setParams, onCalc }) => {
  const r = calcFT(params);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field label="Valor Unitário de Referência (R$/m²)"><Input type="number" step="0.01" value={params.valor_unitario || ''} onChange={(e) => setParams({ ...params, valor_unitario: Number(e.target.value) })} placeholder="R$/m² da ponderância" /></Field>
        <Field label="Área do Terreno (m²)"><Input type="number" step="0.01" value={params.area_terreno || ''} onChange={(e) => setParams({ ...params, area_terreno: Number(e.target.value) })} placeholder="m²" /></Field>
        <Field label="Fator Localização">
          <Select value={params.f_loc || '1.00'} onValueChange={(v) => setParams({ ...params, f_loc: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{FATOR_LOC.map((f) => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}</SelectContent></Select>
        </Field>
        <Field label="Fator Topografia">
          <Select value={params.f_topo || '1.00'} onValueChange={(v) => setParams({ ...params, f_topo: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{FATOR_TOPO.map((f) => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}</SelectContent></Select>
        </Field>
        <Field label="Testada (metros)"><Input type="number" step="0.1" value={params.testada_m || ''} onChange={(e) => setParams({ ...params, testada_m: Number(e.target.value) })} placeholder="metros" /></Field>
        <Field label="Fator Infraestrutura">
          <Select value={params.f_infra || '1.00'} onValueChange={(v) => setParams({ ...params, f_infra: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{FATOR_INFRA.map((f) => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}</SelectContent></Select>
        </Field>
      </div>
      {Number(params.valor_unitario) > 0 && Number(params.area_terreno) > 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
          <div className="grid grid-cols-4 gap-2 text-center text-sm mb-3">
            <div><div className="text-xs text-gray-400">Localização</div><div className="font-bold">{Number(params.f_loc || 1).toFixed(2)}</div></div>
            <div><div className="text-xs text-gray-400">Topografia</div><div className="font-bold">{Number(params.f_topo || 1).toFixed(2)}</div></div>
            <div><div className="text-xs text-gray-400">Testada</div><div className="font-bold">{r.ft.toFixed(2)}</div></div>
            <div><div className="text-xs text-gray-400">Infraestrutura</div><div className="font-bold">{Number(params.f_infra || 1).toFixed(2)}</div></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white border border-gray-200 rounded-lg p-3 text-center"><div className="text-xs text-gray-500 mb-1">VU Ajustado (R$/m²)</div><div className="text-lg font-bold text-gray-800">{fmtBRL(r.vuAdj)}</div></div>
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center"><div className="text-xs text-emerald-700 mb-1">Valor Total do Terreno</div><div className="text-lg font-bold text-emerald-800">{fmtBRL(r.valTotal)}</div></div>
          </div>
        </div>
      )}
      <button type="button" onClick={() => onCalc({ valTerreno: r.valTotal, valTotal: r.valTotal })} className="w-full py-2 bg-emerald-900 hover:bg-emerald-800 text-white rounded-lg text-sm font-semibold">Aplicar Fatores de Terreno ao Laudo</button>
    </div>
  );
};

const CLASSES_USO = [
  { value: '1.00', label: 'Classe I — Aptidão Boa (1,00)' },
  { value: '0.90', label: 'Classe II — Aptidão Regular (0,90)' },
  { value: '0.75', label: 'Classe III — Aptidão Restrita (0,75)' },
  { value: '0.60', label: 'Classe IV — Aptidão Marginal (0,60)' },
  { value: '0.40', label: 'Classe V–VII — Sem Aptidão Agrícola (0,40)' },
];

function calcRural(p) {
  const valTerra = Number(p.vtn_hectare || 0) * Number(p.area_ha || 0) * Number(p.classe_uso || 1);
  return { valTerra, valTotal: valTerra + Number(p.benfeitorias_rurais || 0) + Number(p.cultura_permanente || 0) + Number(p.cultura_temporaria || 0) };
}

const FormNbrRural = ({ params, setParams, onCalc }) => {
  const r = calcRural(params);
  return (
    <div className="space-y-4">
      <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-800">Conforme ABNT NBR 14653-3 e IN INCRA. VTN = valor de mercado do hectare sem benfeitorias.</div>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Área Total (ha)"><Input type="number" step="0.0001" value={params.area_ha || ''} onChange={(e) => setParams({ ...params, area_ha: Number(e.target.value) })} placeholder="0,0000" /></Field>
        <Field label="VTN — Valor por Hectare (R$/ha)"><Input type="number" step="0.01" value={params.vtn_hectare || ''} onChange={(e) => setParams({ ...params, vtn_hectare: Number(e.target.value) })} placeholder="R$/ha" /></Field>
        <Field label="Classe de Uso / CUF (NBR 14653-3)" full>
          <Select value={params.classe_uso || '1.00'} onValueChange={(v) => setParams({ ...params, classe_uso: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{CLASSES_USO.map((c) => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}</SelectContent></Select>
        </Field>
        <Field label="Benfeitorias Rurais (R$)"><Input type="number" step="0.01" value={params.benfeitorias_rurais || ''} onChange={(e) => setParams({ ...params, benfeitorias_rurais: Number(e.target.value) })} placeholder="R$ 0,00" /></Field>
        <Field label="Cultura Permanente (R$)"><Input type="number" step="0.01" value={params.cultura_permanente || ''} onChange={(e) => setParams({ ...params, cultura_permanente: Number(e.target.value) })} placeholder="R$ 0,00" /></Field>
        <Field label="Cultura Temporária (R$)"><Input type="number" step="0.01" value={params.cultura_temporaria || ''} onChange={(e) => setParams({ ...params, cultura_temporaria: Number(e.target.value) })} placeholder="R$ 0,00" /></Field>
      </div>
      {Number(params.area_ha) > 0 && Number(params.vtn_hectare) > 0 && (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center"><div className="text-xs text-green-700 uppercase tracking-wider mb-1">Valor da Terra Nua</div><div className="text-lg font-bold text-green-800">{fmtBRL(r.valTerra)}</div><div className="text-xs text-gray-500">VTN × {Number(params.area_ha)} ha × CUF {Number(params.classe_uso || 1).toFixed(2)}</div></div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center"><div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">Valor Total Rural</div><div className="text-lg font-bold text-emerald-800">{fmtBRL(r.valTotal)}</div><div className="text-xs text-gray-500">Terra + Benfeitorias + Culturas</div></div>
        </div>
      )}
      <button type="button" onClick={() => onCalc({ valTerreno: r.valTerra, valTotal: r.valTotal })} className="w-full py-2 bg-emerald-900 hover:bg-emerald-800 text-white rounded-lg text-sm font-semibold">Aplicar NBR Rural ao Laudo</button>
    </div>
  );
};

function calcRenda(p) {
  const rendaAnual = Number(p.renda_mensal || 0) * 12;
  const taxa = Number(p.taxa_cap || 8) / 100;
  let val = 0;
  if (p.tipo === 'prazo') {
    const n = Number(p.prazo_anos || 0) * 12;
    const tm = taxa / 12;
    val = tm > 0 && n > 0 ? Number(p.renda_mensal || 0) * ((1 - Math.pow(1 + tm, -n)) / tm) : Number(p.renda_mensal || 0) * n;
  } else {
    val = taxa > 0 ? rendaAnual / taxa : 0;
  }
  return { rendaAnual, valCapitalizado: val };
}

const FormRenda = ({ params, setParams, onCalc }) => {
  const r = calcRenda(params);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field label="Renda Mensal (R$)"><Input type="number" step="0.01" value={params.renda_mensal || ''} onChange={(e) => setParams({ ...params, renda_mensal: Number(e.target.value) })} placeholder="R$ 0,00" /></Field>
        <Field label="Taxa de Capitalização (%, padrão 8%)"><Input type="number" step="0.01" min="0.01" value={params.taxa_cap ?? 8} onChange={(e) => setParams({ ...params, taxa_cap: Number(e.target.value) })} /></Field>
        <Field label="Tipo de Cálculo">
          <Select value={params.tipo || 'perpetuidade'} onValueChange={(v) => setParams({ ...params, tipo: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="perpetuidade">Perpetuidade (Renda / Taxa)</SelectItem><SelectItem value="prazo">Prazo determinado (VPL)</SelectItem></SelectContent></Select>
        </Field>
        {params.tipo === 'prazo' && <Field label="Prazo (anos)"><Input type="number" min="1" value={params.prazo_anos || ''} onChange={(e) => setParams({ ...params, prazo_anos: Number(e.target.value) })} placeholder="anos" /></Field>}
      </div>
      {Number(params.renda_mensal) > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center"><div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Renda Anual</div><div className="text-lg font-bold text-gray-800">{fmtBRL(r.rendaAnual)}</div></div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center"><div className="text-xs text-blue-600 uppercase tracking-wider mb-1">Taxa a.a.</div><div className="text-lg font-bold text-blue-700">{Number(params.taxa_cap || 8).toFixed(2)}%</div></div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center"><div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">Valor Capitalizado</div><div className="text-lg font-bold text-emerald-800">{fmtBRL(r.valCapitalizado)}</div></div>
        </div>
      )}
      <button type="button" onClick={() => onCalc({ valTotal: r.valCapitalizado })} className="w-full py-2 bg-emerald-900 hover:bg-emerald-800 text-white rounded-lg text-sm font-semibold">Aplicar Método da Renda ao Laudo</button>
    </div>
  );
};

const METODOS_AVAL = [
  { value: 'ross_heidecke',   label: 'Ross-Heidecke',       desc: 'Casa/Apto com idade', icon: '🏠' },
  { value: 'linha_reta',      label: 'Linha Reta',           desc: 'Galpão/Construção',   icon: '🏭' },
  { value: 'fatores_terreno', label: 'Fatores Terreno',      desc: 'Terreno urbano',       icon: '🗺️' },
  { value: 'nbr_rural',       label: 'NBR Rural',            desc: 'Rural / INCRA',        icon: '🌾' },
  { value: 'renda',           label: 'Método da Renda',      desc: 'Comercial/Renda',      icon: '💰' },
];

export const StepMetodoAvaliacao = ({ form, setForm }) => {
  const metodo = form.metodo_avaliacao || null;
  const [params, setParams] = useState(form.metodo_params || {});

  const updateParams = (p) => { setParams(p); setForm((f) => ({ ...f, metodo_params: p })); };

  const handleCalc = ({ depPct, valDep, valBenfeitoria, valTerreno, valTotal }) => {
    setForm((f) => ({
      ...f,
      depreciacao_percentual: depPct !== undefined ? depPct : f.depreciacao_percentual,
      valor_depreciacao:      valDep !== undefined ? valDep : f.valor_depreciacao,
      valor_benfeitoria:      valBenfeitoria !== undefined ? valBenfeitoria : f.valor_benfeitoria,
      valor_terreno_calc:     valTerreno !== undefined ? valTerreno : f.valor_terreno_calc,
      valor_total_metodo:     valTotal !== undefined ? valTotal : f.valor_total_metodo,
    }));
  };

  const inserirNoLaudo = () => {
    if (!form.valor_total_metodo) return;
    setForm((f) => ({ ...f, resultado_valor_total: f.valor_total_metodo, total_indemnity: f.valor_total_metodo }));
  };

  const selectMetodo = (v) => {
    setParams({});
    setForm((f) => ({ ...f, metodo_avaliacao: v, metodo_params: {}, depreciacao_percentual: null, valor_depreciacao: null, valor_benfeitoria: null, valor_terreno_calc: null, valor_total_metodo: null }));
  };

  const hasResult = form.valor_total_metodo != null && form.valor_total_metodo > 0;

  return (
    <div>
      <SectionHeader
        title="8c. Método de Avaliação — Depreciação e Valorização"
        subtitle="Selecione o método conforme o tipo de imóvel. Cálculos automáticos no frontend."
      />

      <div className="grid grid-cols-5 gap-3 mb-6">
        {METODOS_AVAL.map((m) => (
          <button key={m.value} type="button" onClick={() => selectMetodo(m.value)}
            className={`flex flex-col items-center justify-center gap-1.5 rounded-xl border-2 px-2 py-3 text-center transition-all ${metodo === m.value ? 'border-emerald-600 bg-emerald-50 shadow-md' : 'border-gray-200 bg-white hover:border-emerald-300 hover:bg-emerald-50/50'}`}>
            <span className="text-xl">{m.icon}</span>
            <span className={`text-xs font-bold leading-tight ${metodo === m.value ? 'text-emerald-800' : 'text-gray-700'}`}>{m.label}</span>
            <span className="text-[10px] text-gray-400 leading-tight">{m.desc}</span>
          </button>
        ))}
      </div>

      {metodo && (
        <div className="rounded-xl border-2 border-emerald-200 bg-white p-5 mb-6">
          <div className="text-sm font-semibold text-emerald-800 mb-4">{METODOS_AVAL.find((m) => m.value === metodo)?.label}</div>
          {metodo === 'ross_heidecke'   && <FormRossHeidecke params={params} setParams={updateParams} onCalc={handleCalc} />}
          {metodo === 'linha_reta'      && <FormLinhaReta     params={params} setParams={updateParams} onCalc={handleCalc} />}
          {metodo === 'fatores_terreno' && <FormFatoresTerreno params={params} setParams={updateParams} onCalc={handleCalc} />}
          {metodo === 'nbr_rural'       && <FormNbrRural      params={params} setParams={updateParams} onCalc={handleCalc} />}
          {metodo === 'renda'           && <FormRenda         params={params} setParams={updateParams} onCalc={handleCalc} />}
        </div>
      )}

      {hasResult && (
        <div className="rounded-2xl border-2 border-amber-400 bg-gradient-to-br from-amber-50 to-yellow-50 p-6">
          <div className="text-xs font-bold text-amber-700 uppercase tracking-widest mb-3">Resultado Consolidado — {METODOS_AVAL.find((m) => m.value === metodo)?.label}</div>
          <div className="grid grid-cols-2 gap-3 mb-4">
            {form.valor_terreno_calc > 0 && (
              <div className="bg-white rounded-lg border border-amber-200 p-3"><div className="text-xs text-gray-500 mb-0.5">Valor do Terreno</div><div className="font-bold text-gray-800">{fmtBRL(form.valor_terreno_calc)}</div></div>
            )}
            {form.valor_benfeitoria > 0 && (
              <div className="bg-white rounded-lg border border-amber-200 p-3"><div className="text-xs text-gray-500 mb-0.5">Benfeitorias (depreciado)</div><div className="font-bold text-gray-800">{fmtBRL(form.valor_benfeitoria)}</div></div>
            )}
            {form.depreciacao_percentual > 0 && (
              <div className="bg-white rounded-lg border border-red-200 p-3"><div className="text-xs text-red-500 mb-0.5">Depreciação</div><div className="font-bold text-red-700">{Number(form.depreciacao_percentual).toFixed(2)}% — {fmtBRL(form.valor_depreciacao)}</div></div>
            )}
          </div>
          <div className="bg-amber-400/20 border border-amber-400 rounded-xl p-4 text-center">
            <div className="text-xs text-amber-700 uppercase tracking-wider mb-1">VALOR TOTAL (Terreno + Benfeitorias)</div>
            <div className="text-4xl font-bold text-amber-900">{fmtBRL(form.valor_total_metodo)}</div>
          </div>
          <div className="mt-4 flex justify-end">
            <button type="button" onClick={inserirNoLaudo} className="px-6 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-semibold shadow">Inserir no Laudo</button>
          </div>
        </div>
      )}

      {!metodo && (
        <div className="text-center py-10 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200 text-gray-400 text-sm">
          Selecione um método acima para iniciar o cálculo de depreciação ou valorização.
        </div>
      )}
    </div>
  );
};

// ── Legacy exports (kept so PtamWizard.jsx still compiles if needed) ──────────
export const StepIdentification = ({ form, setForm, onAi, aiLoading }) => <StepSolicitante form={form} setForm={setForm} />;
export const StepProperty = ({ form, setForm }) => <StepImovelId form={form} setForm={setForm} />;
export const StepVistoria = ({ form, setForm, onAi, aiLoading }) => <StepRegiao form={form} setForm={setForm} onAi={onAi} aiLoading={aiLoading} />;
export const StepMethodology = ({ form, setForm, onAi, aiLoading }) => <StepMetodologia form={form} setForm={setForm} onAi={onAi} aiLoading={aiLoading} />;
export const StepImpactAreas = ({ form, setForm, onAi, aiLoading }) => <StepAmostras form={form} setForm={setForm} onAi={onAi} aiLoading={aiLoading} />;
export const StepConclusion = ({ form, setForm, onAi, aiLoading }) => <StepConclusao form={form} setForm={setForm} onAi={onAi} aiLoading={aiLoading} />;
