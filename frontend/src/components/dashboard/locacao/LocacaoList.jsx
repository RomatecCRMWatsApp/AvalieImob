import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, Plus, Search, FileDown, Loader2, Trash2, Edit3 } from 'lucide-react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { useToast } from '../../../hooks/use-toast';
import { locacaoAPI } from '../../../lib/api';
import { TIPO_LOCACAO_OPTIONS, fmtCurrency } from './locacaoHelpers';

const statusColor = (s) => {
  if (s === 'Emitido')   return 'bg-emerald-100 text-emerald-800';
  if (s === 'Em revisão') return 'bg-amber-100 text-amber-800';
  return 'bg-gray-100 text-gray-700';
};

const tipoLabel = (v) => TIPO_LOCACAO_OPTIONS.find(o => o.value === v)?.label || v || '—';

const LocacaoList = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [tipoFilter, setTipoFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (tipoFilter) params.tipo = tipoFilter;
      const data = await locacaoAPI.list(params);
      setItems(data.items || []);
    } catch {
      toast({ title: 'Erro ao carregar avaliações', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [tipoFilter, toast]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('Excluir esta avaliação de locação?')) return;
    try {
      await locacaoAPI.remove(id);
      setItems(prev => prev.filter(x => x.id !== id));
      toast({ title: 'Avaliação excluída' });
    } catch {
      toast({ title: 'Erro ao excluir', variant: 'destructive' });
    }
  };

  const handleDownloadPdf = async (id, numero, e) => {
    e.stopPropagation();
    try {
      const blob = await locacaoAPI.downloadPdf(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `avaliacao_locacao_${(numero || id).replace('/', '-')}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast({ title: 'Erro ao gerar PDF', variant: 'destructive' });
    }
  };

  const filtered = items.filter(p => {
    const q = search.toLowerCase();
    return !q || (p.solicitante_nome || '').toLowerCase().includes(q)
      || (p.imovel_endereco || '').toLowerCase().includes(q)
      || (p.numero_locacao || '').toLowerCase().includes(q);
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-gray-900">Avaliação de Locação</h1>
          <p className="text-gray-500 text-sm mt-1">Pareceres técnicos de valor de aluguel (Lei 8.245/91)</p>
        </div>
        <Button
          onClick={() => nav('/dashboard/locacao/nova')}
          className="bg-emerald-900 hover:bg-emerald-800 text-white gap-2"
        >
          <Plus className="w-4 h-4" /> Nova Avaliação
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por solicitante, endereço ou número..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400"
          />
        </div>
        <select
          value={tipoFilter}
          onChange={e => setTipoFilter(e.target.value)}
          className="px-3 py-2 rounded-xl border border-gray-200 text-sm text-gray-700 focus:outline-none focus:border-emerald-400"
        >
          <option value="">Todos os tipos</option>
          {TIPO_LOCACAO_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-700" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <Home className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="font-medium text-gray-600">Nenhuma avaliação encontrada</p>
          <p className="text-sm mt-1">Clique em "Nova Avaliação" para começar</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map(p => (
            <div
              key={p.id}
              onClick={() => nav(`/dashboard/locacao/${p.id}`)}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition cursor-pointer"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-blue-900/10 flex items-center justify-center">
                  <Home className="w-5 h-5 text-blue-900" />
                </div>
                <div className="flex gap-1.5 flex-wrap justify-end">
                  <Badge className={statusColor(p.status)}>{p.status}</Badge>
                </div>
              </div>
              <div className="text-xs font-semibold text-blue-700 tracking-wider">
                {p.numero_locacao || 'LOC-????/????'}
              </div>
              <div className="font-semibold text-gray-900 mt-1 line-clamp-1">
                {p.imovel_endereco || p.solicitante_nome || '(sem título)'}
              </div>
              <div className="text-xs text-gray-500 mt-1 line-clamp-1">
                {p.solicitante_nome || '—'}
              </div>
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                <div className="text-xs text-gray-400">
                  <span className="font-medium text-gray-600">{tipoLabel(p.tipo_locacao)}</span>
                  {p.valor_locacao_estimado
                    ? ` · ${fmtCurrency(p.valor_locacao_estimado)}/mês`
                    : ''}
                </div>
                <div className="flex gap-1">
                  <button
                    title="Editar"
                    onClick={e => { e.stopPropagation(); nav(`/dashboard/locacao/${p.id}`); }}
                    className="w-7 h-7 rounded-lg hover:bg-blue-50 flex items-center justify-center text-blue-600 transition"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    title="Baixar PDF"
                    onClick={e => handleDownloadPdf(p.id, p.numero_locacao, e)}
                    className="w-7 h-7 rounded-lg hover:bg-emerald-50 flex items-center justify-center text-emerald-700 transition"
                  >
                    <FileDown className="w-3.5 h-3.5" />
                  </button>
                  <button
                    title="Excluir"
                    onClick={e => handleDelete(p.id, e)}
                    className="w-7 h-7 rounded-lg hover:bg-red-50 flex items-center justify-center text-red-500 transition"
                  >
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

export default LocacaoList;
