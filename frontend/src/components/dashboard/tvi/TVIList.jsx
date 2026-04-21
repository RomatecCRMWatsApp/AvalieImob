import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ClipboardCheck, Plus, Search, Loader2, Trash2, Edit3, FileDown } from 'lucide-react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { useToast } from '../../../hooks/use-toast';
import { useVistorias } from './hooks/useTVI';

const STATUS_COLOR = {
  'Emitido': 'bg-emerald-100 text-emerald-800',
  'Em revisão': 'bg-amber-100 text-amber-800',
  'Rascunho': 'bg-gray-100 text-gray-700',
};

const TVIList = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const { vistorias, loading, remove } = useVistorias();
  const [search, setSearch] = useState('');

  const filtered = vistorias.filter(v => {
    const q = search.toLowerCase();
    return !q
      || (v.titulo || '').toLowerCase().includes(q)
      || (v.endereco || '').toLowerCase().includes(q)
      || (v.modelo_nome || '').toLowerCase().includes(q);
  });

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
          <h1 className="font-display text-3xl font-bold text-gray-900">Kit TVI</h1>
          <p className="text-gray-500 text-sm mt-1">Termos de Vistoria de Imóvel — 45 modelos disponíveis</p>
        </div>
        <Button
          onClick={() => nav('/dashboard/tvi/nova')}
          className="bg-emerald-900 hover:bg-emerald-800 text-white gap-2"
        >
          <Plus className="w-4 h-4" /> Nova Vistoria
        </Button>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar por título, endereço ou modelo..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 rounded-xl border border-gray-200 text-sm
                     focus:outline-none focus:border-emerald-400"
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-700" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-xl border border-dashed border-gray-200">
          <ClipboardCheck className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <div className="font-semibold text-gray-900">Nenhuma vistoria encontrada</div>
          <p className="text-sm text-gray-500 mt-1">Clique em "Nova Vistoria" para começar</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map(v => (
            <div
              key={v.id}
              onClick={() => nav(`/dashboard/tvi/${v.id}`)}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition cursor-pointer"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-emerald-900/10 flex items-center justify-center">
                  <ClipboardCheck className="w-5 h-5 text-emerald-900" />
                </div>
                <Badge className={STATUS_COLOR[v.status] || STATUS_COLOR['Rascunho']}>
                  {v.status || 'Rascunho'}
                </Badge>
              </div>
              <div className="text-xs font-semibold text-emerald-700 tracking-wide">
                {v.modelo_nome || 'TVI'}
              </div>
              <div className="font-semibold text-gray-900 mt-1 line-clamp-1">
                {v.titulo || v.endereco || '(sem título)'}
              </div>
              <div className="text-xs text-gray-500 mt-1 line-clamp-1">
                {v.categoria || v.modelo_categoria || '—'}
              </div>
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                <span className="text-xs text-gray-400">
                  {v.created_at ? new Date(v.created_at).toLocaleDateString('pt-BR') : '—'}
                </span>
                <div className="flex gap-1">
                  <button title="Editar" onClick={e => { e.stopPropagation(); nav(`/dashboard/tvi/${v.id}`); }}
                    className="w-7 h-7 rounded-lg hover:bg-emerald-50 flex items-center justify-center text-emerald-700 transition">
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                  <button title="Excluir" onClick={e => handleDelete(v.id, e)}
                    className="w-7 h-7 rounded-lg hover:bg-red-50 flex items-center justify-center text-red-500 transition">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TVIList;
