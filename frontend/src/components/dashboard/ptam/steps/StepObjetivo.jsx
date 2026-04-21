// @module ptam/steps/StepObjetivo — Step 2: Objetivo da Avaliação com finalidades NBR/judicial
import React, { useState, useEffect, useRef } from 'react';
import { Input } from '../../../ui/input';
import { Textarea } from '../../../ui/textarea';
import { ChevronDown, Check } from 'lucide-react';
import { Field, SectionHeader, AiButton } from '../shared/primitives';

const FINALIDADES_JUDICIAIS = new Set([
  'judicial_partilha', 'judicial_desapropriacao', 'judicial_indenizacao',
  'judicial_execucao', 'judicial_usucapiao', 'judicial_pericia',
  'desap_utilidade', 'desap_interesse_social', 'desap_reforma_agraria',
]);

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

const FINALIDADE_MAP = Object.fromEntries(
  FINALIDADE_GRUPOS.flatMap((g) => g.items.map((it) => [it.value, it]))
);

function FinalidadeSelect({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const selected = FINALIDADE_MAP[value] || null;

  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div ref={ref} className="relative w-full">
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

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-white shadow-lg">
          <div className="max-h-80 overflow-y-auto py-1">
            {FINALIDADE_GRUPOS.map((grupo) => (
              <div key={grupo.label}>
                <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-gray-400 bg-gray-50 border-b border-gray-100 sticky top-0">
                  {grupo.label}
                </div>
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
