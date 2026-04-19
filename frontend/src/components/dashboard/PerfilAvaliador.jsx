import React, { useState, useEffect, useCallback } from 'react';
import {
  User, Award, BookOpen, Briefcase, Star, Phone, Building2,
  MapPin, Plus, Trash2, Save, ChevronDown, ChevronUp, CheckSquare,
  Square, Tag, X, Loader2
} from 'lucide-react';
import ImageUploader from './ptam/ImageUploader';
import { useToast } from '../../hooks/use-toast';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8001';

const GOLD = '#D4A830';
const DARK_GREEN = '#1B4D1B';

const authHeaders = () => {
  const token = localStorage.getItem('token');
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
};

// ── Sub-components ──────────────────────────────────────────────────────────

const SectionCard = ({ title, icon: Icon, children, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: DARK_GREEN + '18' }}
          >
            <Icon className="w-4 h-4" style={{ color: DARK_GREEN }} />
          </div>
          <span className="text-sm font-semibold text-gray-800">{title}</span>
        </div>
        {open
          ? <ChevronUp className="w-4 h-4 text-gray-400" />
          : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </button>
      {open && (
        <div className="px-6 pb-6 pt-2 border-t border-gray-100">
          {children}
        </div>
      )}
    </div>
  );
};

const Field = ({ label, children, className = '' }) => (
  <div className={className}>
    <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
    {children}
  </div>
);

const Input = ({ ...props }) => (
  <input
    {...props}
    className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm text-gray-800
               focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-200 transition"
  />
);

const Select = ({ children, ...props }) => (
  <select
    {...props}
    className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm text-gray-800
               focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-200 transition bg-white"
  >
    {children}
  </select>
);

const Textarea = ({ ...props }) => (
  <textarea
    {...props}
    rows={4}
    className="w-full px-3 py-2 rounded-xl border border-gray-200 text-sm text-gray-800
               focus:outline-none focus:border-emerald-400 focus:ring-1 focus:ring-emerald-200 transition resize-none"
  />
);

const StatusBadge = ({ status }) => {
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

const TagInput = ({ tags, onChange, placeholder = 'Adicionar...' }) => {
  const [val, setVal] = useState('');
  const add = () => {
    const v = val.trim();
    if (v && !tags.includes(v)) onChange([...tags, v]);
    setVal('');
  };
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {tags.map(t => (
          <span key={t} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
            {t}
            <button type="button" onClick={() => onChange(tags.filter(x => x !== t))}>
              <X className="w-3 h-3" />
            </button>
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
        <button
          type="button"
          onClick={add}
          className="px-3 py-1.5 rounded-xl text-sm font-medium text-white transition"
          style={{ background: DARK_GREEN }}
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

const CheckList = ({ options, selected, onChange }) => (
  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
    {options.map(opt => {
      const active = selected.includes(opt);
      return (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(active ? selected.filter(x => x !== opt) : [...selected, opt])}
          className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-sm transition text-left
            ${active ? 'border-emerald-400 bg-emerald-50 text-emerald-800' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
        >
          {active
            ? <CheckSquare className="w-4 h-4 flex-shrink-0 text-emerald-600" />
            : <Square className="w-4 h-4 flex-shrink-0 text-gray-300" />}
          {opt}
        </button>
      );
    })}
  </div>
);

// ── Default / empty state ────────────────────────────────────────────────────

const EMPTY = {
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

const TIPOS_REGISTRO = ['CRECI', 'CREA', 'CAU', 'CRMV', 'CZO', 'CNAI', 'CFT', 'INCRA'];
const TIPOS_FORMACAO = ['graduacao', 'pos_graduacao', 'mestrado', 'doutorado', 'tecnico', 'curso_livre'];
const AREAS_ATUACAO = ['Avaliação Urbana', 'Avaliação Rural', 'Garantias Bancárias', 'Semoventes', 'Perícia Judicial', 'Topografia', 'Regularização Fundiária', 'Avaliação de Máquinas e Equipamentos'];
const TRIBUNAIS = ['TJ-MA', 'TJ-PI', 'TJ-CE', 'TJ-PA', 'TRF-1', 'TRT-16', 'TRT-22', 'STJ'];
const BANCOS = ['Caixa Econômica Federal', 'Banco do Brasil', 'Bradesco', 'Itaú', 'Santander', 'Sicoob', 'Sicredi', 'BRB'];
const UFS = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'];

// ── Main component ───────────────────────────────────────────────────────────

const PerfilAvaliador = () => {
  const { toast } = useToast();
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API}/api/perfil-avaliador`, { headers: authHeaders() });
        if (res.ok) {
          const data = await res.json();
          setForm({ ...EMPTY, ...data });
        }
      } catch {
        toast({ title: 'Erro ao carregar perfil', variant: 'destructive' });
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const set = useCallback((field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/perfil-avaliador`, {
        method: 'PUT',
        headers: authHeaders(),
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error();
      toast({ title: 'Perfil salvo com sucesso!' });
    } catch {
      toast({ title: 'Erro ao salvar perfil', variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  // ── Registros helpers ──
  const addRegistro = () => set('registros', [...form.registros, { tipo: 'CRECI', numero: '', uf: '', validade: '', status: 'ativo' }]);
  const updateRegistro = (i, field, val) => {
    const arr = [...form.registros];
    arr[i] = { ...arr[i], [field]: val };
    set('registros', arr);
  };
  const removeRegistro = (i) => set('registros', form.registros.filter((_, idx) => idx !== i));

  // ── Formacao helpers ──
  const addFormacao = () => set('formacoes', [...form.formacoes, { tipo: 'graduacao', curso: '', instituicao: '', ano_conclusao: new Date().getFullYear(), carga_horaria: null }]);
  const updateFormacao = (i, field, val) => {
    const arr = [...form.formacoes];
    arr[i] = { ...arr[i], [field]: val };
    set('formacoes', arr);
  };
  const removeFormacao = (i) => set('formacoes', form.formacoes.filter((_, idx) => idx !== i));

  // ── Experiencia helpers ──
  const addExperiencia = () => set('experiencias', [...form.experiencias, { cargo: '', empresa: '', periodo_inicio: '', periodo_fim: null, descricao: '' }]);
  const updateExperiencia = (i, field, val) => {
    const arr = [...form.experiencias];
    arr[i] = { ...arr[i], [field]: val };
    set('experiencias', arr);
  };
  const removeExperiencia = (i) => set('experiencias', form.experiencias.filter((_, idx) => idx !== i));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: DARK_GREEN }} />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-4 pb-10">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Meu Currículo Profissional</h1>
          <p className="text-sm text-gray-500 mt-0.5">Dados usados automaticamente nos laudos PTAM, Garantias e Semoventes</p>
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition disabled:opacity-60"
          style={{ background: DARK_GREEN }}
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? 'Salvando...' : 'Salvar Perfil'}
        </button>
      </div>

      {/* ── Secao 1: Dados Pessoais ── */}
      <SectionCard title="Dados Pessoais" icon={User} defaultOpen>
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-6">
            <div className="flex-shrink-0">
              <p className="text-xs font-medium text-gray-500 mb-2">Foto de Perfil</p>
              <ImageUploader
                images={form.foto_perfil ? [form.foto_perfil] : []}
                onImagesChange={ids => set('foto_perfil', ids[0] || null)}
                maxImages={1}
                single
                label=""
                accept="image/jpeg,image/jpg,image/png,image/webp"
              />
            </div>
            <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="Nome Completo" className="sm:col-span-2">
                <Input value={form.nome_completo} onChange={e => set('nome_completo', e.target.value)} placeholder="Jose Romario Pinto Bezerra" />
              </Field>
              <Field label="CPF">
                <Input value={form.cpf} onChange={e => set('cpf', e.target.value)} placeholder="000.000.000-00" />
              </Field>
              <Field label="RG">
                <Input value={form.rg} onChange={e => set('rg', e.target.value)} placeholder="0000000" />
              </Field>
              <Field label="Órgão Emissor RG">
                <Input value={form.rg_orgao} onChange={e => set('rg_orgao', e.target.value)} placeholder="SSP-MA" />
              </Field>
            </div>
          </div>
          <Field label="Bio / Resumo Profissional">
            <Textarea
              value={form.bio_resumo}
              onChange={e => set('bio_resumo', e.target.value)}
              placeholder="Descreva sua trajetória profissional, especialidades e diferenciais..."
            />
          </Field>
        </div>
      </SectionCard>

      {/* ── Secao 2: Registros Profissionais ── */}
      <SectionCard title="Registros Profissionais" icon={Award} defaultOpen>
        <div className="space-y-3">
          {form.registros.length === 0 && (
            <p className="text-sm text-gray-400 py-2">Nenhum registro adicionado.</p>
          )}
          {form.registros.map((r, i) => (
            <div key={i} className="grid grid-cols-2 sm:grid-cols-5 gap-2 p-3 rounded-xl bg-gray-50 border border-gray-100 items-end">
              <Field label="Tipo">
                <Select value={r.tipo} onChange={e => updateRegistro(i, 'tipo', e.target.value)}>
                  {TIPOS_REGISTRO.map(t => <option key={t}>{t}</option>)}
                </Select>
              </Field>
              <Field label="Número">
                <Input value={r.numero} onChange={e => updateRegistro(i, 'numero', e.target.value)} placeholder="031161" />
              </Field>
              <Field label="UF">
                <Select value={r.uf} onChange={e => updateRegistro(i, 'uf', e.target.value)}>
                  <option value="">—</option>
                  {UFS.map(u => <option key={u}>{u}</option>)}
                </Select>
              </Field>
              <Field label="Status">
                <Select value={r.status} onChange={e => updateRegistro(i, 'status', e.target.value)}>
                  <option value="ativo">Ativo</option>
                  <option value="inativo">Inativo</option>
                  <option value="suspenso">Suspenso</option>
                </Select>
              </Field>
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <StatusBadge status={r.status} />
                </div>
                <button type="button" onClick={() => removeRegistro(i)} className="p-2 rounded-lg text-red-400 hover:bg-red-50 transition">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
          <button
            type="button"
            onClick={addRegistro}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-dashed border-emerald-300 text-sm text-emerald-700 hover:bg-emerald-50 transition"
          >
            <Plus className="w-4 h-4" /> Adicionar Registro
          </button>
        </div>
      </SectionCard>

      {/* ── Secao 3: Formacao Academica ── */}
      <SectionCard title="Formação Acadêmica" icon={BookOpen}>
        <div className="space-y-3">
          {form.formacoes.length === 0 && (
            <p className="text-sm text-gray-400 py-2">Nenhuma formação adicionada.</p>
          )}
          {form.formacoes.map((f, i) => (
            <div key={i} className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-3 rounded-xl bg-gray-50 border border-gray-100">
              <Field label="Tipo">
                <Select value={f.tipo} onChange={e => updateFormacao(i, 'tipo', e.target.value)}>
                  {TIPOS_FORMACAO.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                </Select>
              </Field>
              <Field label="Curso" className="sm:col-span-2">
                <Input value={f.curso} onChange={e => updateFormacao(i, 'curso', e.target.value)} placeholder="Engenharia Civil" />
              </Field>
              <Field label="Ano de Conclusão">
                <Input
                  type="number"
                  value={f.ano_conclusao}
                  onChange={e => updateFormacao(i, 'ano_conclusao', parseInt(e.target.value) || 0)}
                  placeholder="2005"
                />
              </Field>
              <Field label="Instituição" className="sm:col-span-3">
                <Input value={f.instituicao} onChange={e => updateFormacao(i, 'instituicao', e.target.value)} placeholder="Universidade Federal do Maranhão" />
              </Field>
              <Field label="Carga Horária (h)">
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    value={f.carga_horaria || ''}
                    onChange={e => updateFormacao(i, 'carga_horaria', e.target.value ? parseInt(e.target.value) : null)}
                    placeholder="360"
                  />
                  <button type="button" onClick={() => removeFormacao(i)} className="p-2 rounded-lg text-red-400 hover:bg-red-50 transition flex-shrink-0">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </Field>
            </div>
          ))}
          <button
            type="button"
            onClick={addFormacao}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-dashed border-emerald-300 text-sm text-emerald-700 hover:bg-emerald-50 transition"
          >
            <Plus className="w-4 h-4" /> Adicionar Formação
          </button>
        </div>
      </SectionCard>

      {/* ── Secao 4: Experiencia Profissional ── */}
      <SectionCard title="Experiência Profissional" icon={Briefcase}>
        <div className="space-y-3">
          {form.experiencias.length === 0 && (
            <p className="text-sm text-gray-400 py-2">Nenhuma experiência adicionada.</p>
          )}
          {form.experiencias.map((exp, i) => (
            <div key={i} className="p-3 rounded-xl bg-gray-50 border border-gray-100 space-y-2">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                <Field label="Cargo">
                  <Input value={exp.cargo} onChange={e => updateExperiencia(i, 'cargo', e.target.value)} placeholder="Engenheiro Avaliador" />
                </Field>
                <Field label="Empresa">
                  <Input value={exp.empresa} onChange={e => updateExperiencia(i, 'empresa', e.target.value)} placeholder="Romatec Consultoria" />
                </Field>
                <Field label="Início">
                  <Input value={exp.periodo_inicio} onChange={e => updateExperiencia(i, 'periodo_inicio', e.target.value)} placeholder="2010" />
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-2 items-end">
                <Field label="Fim (deixe vazio = atual)">
                  <Input
                    value={exp.periodo_fim || ''}
                    onChange={e => updateExperiencia(i, 'periodo_fim', e.target.value || null)}
                    placeholder="Atual"
                  />
                </Field>
                {exp.periodo_fim === null && (
                  <span className="pb-2 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-1 rounded-lg self-end">Emprego Atual</span>
                )}
              </div>
              <Field label="Descrição">
                <div className="flex gap-2">
                  <Textarea
                    value={exp.descricao}
                    onChange={e => updateExperiencia(i, 'descricao', e.target.value)}
                    placeholder="Descreva as principais atividades e responsabilidades..."
                  />
                  <button type="button" onClick={() => removeExperiencia(i)} className="p-2 rounded-lg text-red-400 hover:bg-red-50 transition self-start">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </Field>
            </div>
          ))}
          <button
            type="button"
            onClick={addExperiencia}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-dashed border-emerald-300 text-sm text-emerald-700 hover:bg-emerald-50 transition"
          >
            <Plus className="w-4 h-4" /> Adicionar Experiência
          </button>
        </div>
      </SectionCard>

      {/* ── Secao 5: Especializacoes e Habilitacoes ── */}
      <SectionCard title="Especializações e Habilitações" icon={Star}>
        <div className="space-y-5">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Especializações</p>
            <TagInput
              tags={form.especializacoes}
              onChange={v => set('especializacoes', v)}
              placeholder="Ex: Avaliação Imobiliária, Perícia Judicial..."
            />
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Habilitações</p>
            <TagInput
              tags={form.habilitacoes}
              onChange={v => set('habilitacoes', v)}
              placeholder="Ex: Perito Judicial, Avaliador Caixa..."
            />
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Tribunais Cadastrado</p>
            <CheckList options={TRIBUNAIS} selected={form.tribunais_cadastrado} onChange={v => set('tribunais_cadastrado', v)} />
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Bancos Habilitado</p>
            <CheckList options={BANCOS} selected={form.bancos_habilitado} onChange={v => set('bancos_habilitado', v)} />
          </div>
        </div>
      </SectionCard>

      {/* ── Secao 6: Contato e Empresa ── */}
      <SectionCard title="Contato e Empresa" icon={Phone}>
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Field label="Telefone">
              <Input value={form.telefone} onChange={e => set('telefone', e.target.value)} placeholder="(99) 99181-1246" />
            </Field>
            <Field label="E-mail Profissional">
              <Input value={form.email_profissional} onChange={e => set('email_profissional', e.target.value)} placeholder="contato@consultoriaromatec.com.br" />
            </Field>
            <Field label="Site">
              <Input value={form.site} onChange={e => set('site', e.target.value)} placeholder="www.consultoriaromatec.com.br" />
            </Field>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Field label="Endereço do Escritório" className="sm:col-span-2">
              <Input value={form.endereco_escritorio} onChange={e => set('endereco_escritorio', e.target.value)} placeholder="Rua Exemplo, 123, Bairro" />
            </Field>
            <Field label="CEP">
              <Input value={form.cep} onChange={e => set('cep', e.target.value)} placeholder="65000-000" />
            </Field>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Field label="Cidade" className="sm:col-span-3">
              <Input value={form.cidade} onChange={e => set('cidade', e.target.value)} placeholder="Imperatriz" />
            </Field>
            <Field label="UF">
              <Select value={form.uf} onChange={e => set('uf', e.target.value)}>
                <option value="">—</option>
                {UFS.map(u => <option key={u}>{u}</option>)}
              </Select>
            </Field>
          </div>

          <div className="pt-2 border-t border-gray-100">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5" /> Dados da Empresa
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Field label="Nome da Empresa" className="sm:col-span-2">
                <Input value={form.empresa_nome} onChange={e => set('empresa_nome', e.target.value)} placeholder="Romatec Consultoria Total" />
              </Field>
              <Field label="CNPJ">
                <Input value={form.empresa_cnpj} onChange={e => set('empresa_cnpj', e.target.value)} placeholder="00.000.000/0001-00" />
              </Field>
              <Field label="Razão Social" className="sm:col-span-3">
                <Input value={form.empresa_razao_social} onChange={e => set('empresa_razao_social', e.target.value)} placeholder="Romatec Consultoria Total Eireli" />
              </Field>
            </div>
          </div>
        </div>
      </SectionCard>

      {/* ── Secao 7: Areas de Atuacao ── */}
      <SectionCard title="Áreas de Atuação e Associações" icon={MapPin}>
        <div className="space-y-5">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Áreas de Atuação</p>
            <CheckList options={AREAS_ATUACAO} selected={form.areas_atuacao} onChange={v => set('areas_atuacao', v)} />
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Associações Profissionais</p>
            <TagInput
              tags={form.membro_associacoes}
              onChange={v => set('membro_associacoes', v)}
              placeholder="Ex: IBAPE, SOBRAE, IBEF..."
            />
          </div>
          <Field label="Número de Laudos Emitidos">
            <div className="flex items-center gap-3">
              <Input
                type="number"
                value={form.numero_laudos_emitidos}
                onChange={e => set('numero_laudos_emitidos', parseInt(e.target.value) || 0)}
                placeholder="0"
                className="max-w-[160px]"
              />
              <span className="text-xs text-gray-400">laudos emitidos ao longo da carreira</span>
            </div>
          </Field>
        </div>
      </SectionCard>

      {/* ── Botao salvar final ── */}
      <div className="flex justify-end pt-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white transition disabled:opacity-60 shadow-md"
          style={{ background: DARK_GREEN }}
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? 'Salvando...' : 'Salvar Perfil'}
        </button>
      </div>
    </div>
  );
};

export default PerfilAvaliador;
