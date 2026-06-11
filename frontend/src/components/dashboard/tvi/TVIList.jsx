import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ClipboardCheck, Plus, Search, Loader2, Trash2, Edit3 } from 'lucide-react';
import { Button } from '../../ui/button';
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

  const filtered = vistorias.filter(v => {
    const q = search.toLowerCase();
    return !q
      || (v.titulo || '').toLowerCase().includes(q)
      || (v.endereco || v.imovel_endereco || '').toLowerCase().includes(q)
      || (v.modelo_nome || '').toLowerCase().includes(q);
  });

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

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-[#B8860B] dark:text-amber-400">Kit TVI</h1>
          <p className="text-gray-500 text-sm mt-1">Termos de Vistoria de Imóvel — 45 modelos disponíveis</p>
        </div>
      </div>

      {/* ── Minhas vistorias (só aparece se houver) ── */}
      {(loading || filtered.length > 0) && (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-gray-700">Minhas vistorias</h2>
            <div className="relative max-w-xs flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="text" placeholder="Buscar..." value={search} onChange={e => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400" />
            </div>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-12"><Loader2 className="w-7 h-7 animate-spin text-emerald-700" /></div>
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

      {/* ── Modelos disponíveis (catálogo direto na página) ── */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2"><Plus className="w-4 h-4 text-emerald-700" /> Iniciar nova vistoria — escolha um modelo</h2>
          <div className="relative max-w-xs flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input type="text" placeholder="Buscar modelo..." value={modelSearch} onChange={e => setModelSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400" />
          </div>
        </div>

        <div className="flex gap-1.5 overflow-x-auto pb-1">
          {CATEGORIES.map(cat => (
            <button key={cat} onClick={() => setActiveTab(cat)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition
                ${activeTab === cat ? 'bg-emerald-900 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
              {cat}
            </button>
          ))}
        </div>

        {loadingModels || creating ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-7 h-7 animate-spin text-emerald-700" />
            <span className="ml-3 text-gray-500">{creating ? 'Criando vistoria...' : 'Carregando modelos...'}</span>
          </div>
        ) : modelosFiltrados.length === 0 ? (
          <div className="text-center py-12 text-gray-400">Nenhum modelo encontrado</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
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
