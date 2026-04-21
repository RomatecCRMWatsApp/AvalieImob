// @module perfil/primitives — Primitivos, constantes e estado vazio do PerfilAvaliador
import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Plus, CheckSquare, Square, X } from 'lucide-react';

export const GOLD = '#D4A830';
export const DARK_GREEN = '#1B4D1B';

/* ── Lista de opções ──────────────────────────────────────── */
export const UFS = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'];
export const TIPOS_REGISTRO = ['CRECI', 'CREA', 'CAU', 'CRMV', 'CZO', 'CNAI', 'CFT', 'INCRA'];
export const TIPOS_FORMACAO = ['graduacao', 'pos_graduacao', 'mestrado', 'doutorado', 'tecnico', 'curso_livre'];
export const AREAS_ATUACAO = ['Avaliação Urbana', 'Avaliação Rural', 'Garantias Bancárias', 'Semoventes', 'Perícia Judicial', 'Topografia', 'Regularização Fundiária', 'Avaliação de Máquinas e Equipamentos'];
export const TRIBUNAIS = ['TJ-MA', 'TJ-PI', 'TJ-CE', 'TJ-PA', 'TRF-1', 'TRT-16', 'TRT-22', 'STJ'];
export const BANCOS = ['Caixa Econômica Federal', 'Banco do Brasil', 'Bradesco', 'Itaú', 'Santander', 'Sicoob', 'Sicredi', 'BRB'];

/* ── Estado inicial vazio ─────────────────────────────────── */
export const EMPTY_PERFIL = {
  nome_completo: '',
  foto_perfil: null,
  cpf: '',
  rg: '',
  rg_orgao: '',
  bio_resumo: '',
  registros: [],
  formacoes: [],
  experiencias: [],
  especializacoes: [],
  habilitacoes: [],
  tribunais_cadastrado: [],
  bancos_habilitado: [],
  telefone: '',
  email_profissional: '',
  site: '',
  endereco_escritorio: '',
  cidade: '',
  uf: '',
  cep: '',
  empresa_nome: '',
  empresa_cnpj: '',
  empresa_razao_social: '',
  areas_atuacao: [],
  membro_associacoes: [],
  numero_laudos_emitidos: 0,
};

/* ── Primitivos de UI ─────────────────────────────────────── */
export const SectionCard = ({ title, icon: Icon, children, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: DARK_GREEN + '18' }}>
            <Icon className="w-4 h-4" style={{ color: DARK_GREEN }} />
          </div>
          <span className="text-sm font-semibold text-gray-800">{title}</span>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </button>
      {open && (
        <div className="px-6 pb-6 pt-2 border-t border-gray-100">{children}</div>
      )}
    </div>
  );
};

export const Field = ({ label, children, className = '' }) => (
  <div className={className}>
    <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
    {children}
  </div>
);

export const Input = ({ ...props }) => (
  <input
    {...props}
    className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm text-gray-800 focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-200 transition"
  />
);

export const Select = ({ children, ...props }) => (
  <select
    {...props}
    className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm text-gray-800 focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-200 transition bg-white"
  >
    {children}
  </select>
);

export const Textarea = ({ ...props }) => (
  <textarea
    {...props}
    rows={4}
    className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm text-gray-800 focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-200 transition resize-none"
  />
);

export const StatusBadge = ({ status }) => {
  const map = {
    ativo: 'bg-emerald-100 text-emerald-700',
    inativo: 'bg-gray-100 text-gray-500',
    suspenso: 'bg-red-100 text-red-600',
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize ${map[status] || map.inativo}`}>
      {status}
    </span>
  );
};

export const TagInput = ({ tags, onChange, placeholder = 'Adicionar...' }) => {
  const [val, setVal] = useState('');
  const add = () => {
    const v = val.trim();
    if (v && !tags.includes(v)) onChange([...tags, v]);
    setVal('');
  };
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {tags.map(t => (
          <span key={t} className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
            {t}
            <button type="button" onClick={() => onChange(tags.filter(x => x !== t))} className="hover:text-red-500 transition"><X className="w-3 h-3" /></button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={val}
          onChange={e => setVal(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add(); } }}
          placeholder={placeholder}
          className="flex-1 px-3 py-1.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400 transition"
        />
        <button type="button" onClick={add} className="px-3 py-1.5 rounded-xl text-sm font-medium text-white transition" style={{ background: DARK_GREEN }}>
          <Plus className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export const CheckList = ({ options, selected, onChange }) => (
  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
    {options.map(opt => {
      const active = selected.includes(opt);
      return (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(active ? selected.filter(x => x !== opt) : [...selected, opt])}
          className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-sm transition text-left ${active ? 'border-emerald-400 bg-emerald-50 text-emerald-800' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
        >
          {active ? <CheckSquare className="w-4 h-4 flex-shrink-0 text-emerald-600" /> : <Square className="w-4 h-4 flex-shrink-0 text-gray-300" />}
          {opt}
        </button>
      );
    })}
  </div>
);
