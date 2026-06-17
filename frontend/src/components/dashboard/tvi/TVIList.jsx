import React, { useState, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ClipboardCheck, Plus, Search, SearchX, Loader2, Trash2, Edit3 } from 'lucide-react';
import { BrandSpinner } from '../../brand/BrandSpinner';
import { Badge } from '../../ui/badge';
import { useToast } from '../../../hooks/use-toast';
import { tviAPI } from '../../../lib/api';
import { useVistorias, useModels } from './hooks/useTVI';
import ModelCard from './components/ModelCard';

const STATUS_COLOR = {
  'Emitido': 'bg-emerald-100 text-emerald-800',
  'Em revisão': 'bg-amber-100 text-amber-800',
  'Rascunho': 'bg-gray-100 text-gray-700',
};

const CATEGORIES = [
  'Todos', 'Geral', 'Locação', 'Rural', 'Regularização',
  'Obras', 'Judicial', 'Segurança', 'Comercial', 'Instalações', 'Complementares',
];

const TVIList = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const { vistorias, loading, remove } = useVistorias();
  const { models, loading: loadingModels } = useModels();
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState('Todos');
  const [modelSearch, setModelSearch] = useState('');
  const [creating, setCreating] = useState(false);
  const catalogRef = useRef(null);

  const filtered = vistorias.filter(v => {
    const q = search.toLowerCase();
    return !q
      || (v.titulo || '').toLowerCase().includes(q)
      || (v.endereco || v.imovel_endereco || '').toLowerCase().includes(q)
      || (v.modelo_nome || '').toLowerCase().includes(q);
  });

  const total = (models || []).length;
  const modelosFiltrados = useMemo(() => {
    let list = models || [];
    if (activeTab !== 'Todos') {
      const tab = activeTab.toLowerCase();
      list = list.filter(m => (m.categoria || '').toLowerCase().startsWith(tab));
    }
    if (modelSearch) {
      const q = modelSearch.toLowerCase();
      list = list.filter(m => (m.nome || '').toLowerCase().includes(q) || (m.descricao || '').toLowerCase().includes(q));
    }
    return list;
  }, [models, activeTab, modelSearch]);

  const countFor = (cat) => cat === 'Todos'
    ? total
    : (models || []).filter(m => (m.categoria || '').toLowerCase().startsWith(cat.toLowerCase())).length;

  const filtroAtivo = activeTab !== 'Todos' || !!modelSearch;
  const subtitulo = filtroAtivo
    ? `${modelosFiltrados.length} de ${total} modelos`
    : `${total || 45} modelos disponíveis`;

  const handleSelect = async (model) => {
    setCreating(true);
    try {
      const vistoria = await tviAPI.create({ model_id: model.id });
      nav(`/dashboard/tvi/${vistoria.id}`);
    } catch (e) {
      toast({ title: 'Erro ao criar vistoria', description: e?.response?.data?.detail, variant: 'destructive' });
      setCreating(false);
    }
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('Excluir esta vistoria?')) return;
    try {
      await remove(id);
      toast({ title: 'Vistoria excluída' });
    } catch {
      toast({ title: 'Erro ao excluir', variant: 'destructive' });
    }
  };

  const scrollCatalogo = () => catalogRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div>
        <h1 className="font-display text-[34px] font-bold leading-tight text-[#C9A84C]">Kit TVI</h1>
        <p className="text-sm mt-1 text-[#5B7466] dark:text-[#9FB5A6]">
          Termos de Vistoria de Imóvel — {subtitulo}
        </p>
      </div>

      {/* ── Minhas vistorias (só aparece se houver) ── */}
      {(loading || filtered.length > 0) && (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-[#F2EFE6]">Minhas vistorias</h2>
            <div className="relative max-w-xs flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="text" placeholder="Buscar..." value={search} onChange={e => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400" />
            </div>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-12"><BrandSpinner label="Carregando…" /></div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filtered.map(v => (
                <div key={v.id} onClick={() => nav(`/dashboard/tvi/${v.id}`)}
                  className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition cursor-pointer">
                  <div className="flex items-start justify-between mb-3">
                    <div className="w-10 h-10 rounded-lg bg-emerald-900/10 flex items-center justify-center">
                      <ClipboardCheck className="w-5 h-5 text-emerald-900" />
                    </div>
                    <Badge className={STATUS_COLOR[v.status] || STATUS_COLOR['Rascunho']}>{v.status || 'Rascunho'}</Badge>
                  </div>
                  <div className="text-xs font-semibold text-emerald-700 tracking-wide">{v.modelo_nome || 'TVI'}</div>
                  <div className="font-semibold text-gray-900 mt-1 line-clamp-1">{v.titulo || v.endereco || v.imovel_endereco || '(sem título)'}</div>
                  <div className="text-xs text-gray-500 mt-1 line-clamp-1">{v.categoria || v.modelo_categoria || '—'}</div>
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                    <span className="text-xs text-gray-400">{v.created_at ? new Date(v.created_at).toLocaleDateString('pt-BR') : '—'}</span>
                    <div className="flex gap-1">
                      <button title="Editar" onClick={e => { e.stopPropagation(); nav(`/dashboard/tvi/${v.id}`); }}
                        className="w-7 h-7 rounded-lg hover:bg-emerald-50 flex items-center justify-center text-emerald-700 transition"><Edit3 className="w-3.5 h-3.5" /></button>
                      <button title="Excluir" onClick={e => handleDelete(v.id, e)}
                        className="w-7 h-7 rounded-lg hover:bg-red-50 flex items-center justify-center text-red-500 transition"><Trash2 className="w-3.5 h-3.5" /></button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Catálogo de modelos ── */}
      <div ref={catalogRef} className="space-y-4 pt-2">
        {/* Linha de ação: CTA dourado + busca dark */}
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <button
            type="button" onClick={scrollCatalogo}
            className="inline-flex items-center gap-2 rounded-[10px] px-4 py-2.5 text-sm font-semibold
                       bg-[#C9A84C] text-[#0C3320] hover:brightness-95 transition
                       focus:outline-none focus-visible:ring-[3px] focus-visible:ring-[rgba(201,168,76,0.45)]"
          >
            <Plus className="w-4 h-4" /> Iniciar nova vistoria
          </button>
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9FB5A6]" />
            <input
              type="text" placeholder="Buscar modelo..." value={modelSearch}
              onChange={e => setModelSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 rounded-xl text-sm transition
                         bg-white border border-[rgba(12,51,32,0.12)] text-[#15301F] placeholder:text-[#5B7466]
                         focus:outline-none focus-visible:border-[#C9A84C] focus-visible:ring-[3px] focus-visible:ring-[rgba(201,168,76,0.16)]
                         dark:bg-white/[0.04] dark:border-[rgba(201,168,76,0.22)] dark:text-[#F2EFE6] dark:placeholder:text-[#9FB5A6]"
            />
          </div>
        </div>

        {/* Pills de categoria com contador */}
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
          {CATEGORIES.map(cat => {
            const ativo = activeTab === cat;
            const n = countFor(cat);
            return (
              <button
                key={cat} onClick={() => setActiveTab(cat)} aria-pressed={ativo}
                className={`flex-shrink-0 inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[13px] font-medium transition
                  focus:outline-none focus-visible:ring-[3px] focus-visible:ring-[rgba(201,168,76,0.45)]
                  ${ativo
                    ? 'bg-[#C9A84C] text-[#0C3320] font-semibold'
                    : 'bg-transparent border border-[rgba(201,168,76,0.25)] text-[#5B7466] hover:border-[#C9A84C] hover:text-[#15301F] dark:text-[#9FB5A6] dark:hover:text-[#F2EFE6]'}`}
              >
                {cat}<span className="opacity-65">· {n}</span>
              </button>
            );
          })}
        </div>

        {/* Grid / loading / empty */}
        {loadingModels || creating ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="rounded-2xl p-[18px] bg-white border border-[rgba(12,51,32,0.10)] dark:bg-[#103B26] dark:border-[rgba(201,168,76,0.10)]">
                <div className="flex items-start gap-3 animate-pulse">
                  <div className="w-[38px] h-[38px] rounded-xl bg-[rgba(201,168,76,0.12)]" />
                  <div className="flex-1 space-y-2">
                    <div className="h-2.5 w-16 rounded bg-black/5 dark:bg-white/5" />
                    <div className="h-3.5 w-full rounded bg-black/5 dark:bg-white/5" />
                    <div className="h-3.5 w-2/3 rounded bg-black/5 dark:bg-white/5" />
                  </div>
                </div>
              </div>
            ))}
            {creating && (
              <div className="col-span-full flex items-center justify-center gap-2 text-[#5B7466] py-2">
                <Loader2 className="w-5 h-5 animate-spin" /> Criando vistoria...
              </div>
            )}
          </div>
        ) : modelosFiltrados.length === 0 ? (
          <div className="text-center py-16">
            <SearchX className="w-8 h-8 mx-auto mb-3 text-[#9FB5A6]" />
            <p className="text-sm text-[#5B7466] dark:text-[#9FB5A6]">
              {modelSearch ? <>Nenhum modelo encontrado para “{modelSearch}”</> : 'Nenhum modelo nesta categoria'}
            </p>
            {(modelSearch || activeTab !== 'Todos') && (
              <button
                onClick={() => { setModelSearch(''); setActiveTab('Todos'); }}
                className="mt-3 inline-flex items-center rounded-lg px-3 py-1.5 text-xs font-semibold
                           border border-[rgba(201,168,76,0.45)] text-[#C9A84C] hover:bg-[rgba(201,168,76,0.08)]"
              >
                Limpar busca
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {modelosFiltrados.map(m => (
              <ModelCard key={m.id} model={m} onSelect={handleSelect} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default TVIList;
