import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Search, Loader2 } from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { tviAPI } from '../../../lib/api';
import { useModels } from './hooks/useTVI';
import ModelCard from './components/ModelCard';

const CATEGORIES = [
  'Todos', 'Geral', 'Locação', 'Rural', 'Regularização',
  'Obras', 'Judicial', 'Segurança', 'Comercial', 'Instalações', 'Complementares',
];

const TVINew = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const { models, loading, error } = useModels();
  const [activeTab, setActiveTab] = useState('Todos');
  const [search, setSearch] = useState('');
  const [creating, setCreating] = useState(false);

  const filtered = useMemo(() => {
    let list = models;
    if (activeTab !== 'Todos') {
      const tab = activeTab.toLowerCase();
      list = list.filter(m => (m.categoria || '').toLowerCase().startsWith(tab));
    }
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(m =>
        (m.nome || '').toLowerCase().includes(q) ||
        (m.descricao || '').toLowerCase().includes(q)
      );
    }
    return list;
  }, [models, activeTab, search]);

  const handleSelect = async (model) => {
    setCreating(true);
    try {
      const vistoria = await tviAPI.create({ model_id: model.id });
      nav(`/dashboard/tvi/${vistoria.id}`);
    } catch (e) {
      toast({ title: 'Erro ao criar vistoria', description: e?.response?.data?.detail, variant: 'destructive' });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center gap-3">
        <Button variant="ghost" onClick={() => nav('/dashboard/tvi')}>
          <ArrowLeft className="w-4 h-4 mr-1" /> Voltar
        </Button>
        <div>
          <h1 className="font-display text-2xl font-bold text-gray-900">Selecionar Modelo TVI</h1>
          <p className="text-gray-500 text-sm">Escolha um dos 45 modelos disponíveis para iniciar a vistoria</p>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar modelo..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 rounded-xl border border-gray-200 text-sm
                     focus:outline-none focus:border-emerald-400"
        />
      </div>

      {/* Category tabs */}
      <div className="flex gap-1.5 overflow-x-auto pb-1">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveTab(cat)}
            className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition
              ${activeTab === cat
                ? 'bg-emerald-900 text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'}`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Loading / error / grid */}
      {loading || creating ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-700" />
          <span className="ml-3 text-gray-500">{creating ? 'Criando vistoria...' : 'Carregando modelos...'}</span>
        </div>
      ) : error ? (
        <div className="text-center py-20 text-red-500">{error}</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-400">Nenhum modelo encontrado</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {filtered.map(m => (
            <ModelCard key={m.id} model={m} onSelect={handleSelect} />
          ))}
        </div>
      )}
    </div>
  );
};

export default TVINew;
