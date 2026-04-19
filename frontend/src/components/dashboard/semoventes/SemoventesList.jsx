import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Loader2, Trash2, Calendar, DollarSign, Filter,
  Beef, PawPrint, Bird, Layers
} from 'lucide-react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { useToast } from '../../../hooks/use-toast';
import { semoventesAPI } from '../../../lib/api';

const TIPO_CONFIG = {
  bovino:       { label: 'Bovino',        icon: Beef,     color: 'bg-orange-100 text-orange-800' },
  equino:       { label: 'Equino',        icon: PawPrint, color: 'bg-amber-100 text-amber-800' },
  suino:        { label: 'Suíno',         icon: PawPrint, color: 'bg-pink-100 text-pink-800' },
  ovino_caprino:{ label: 'Ovino/Caprino', icon: PawPrint, color: 'bg-violet-100 text-violet-800' },
  aves:         { label: 'Aves',          icon: Bird,     color: 'bg-sky-100 text-sky-800' },
};

const STATUS_CONFIG = {
  rascunho:     { label: 'Rascunho',     color: 'bg-gray-100 text-gray-700' },
  em_andamento: { label: 'Em Andamento', color: 'bg-amber-100 text-amber-800' },
  concluido:    { label: 'Concluído',    color: 'bg-emerald-100 text-emerald-800' },
};

const TIPO_OPTIONS = [
  { value: '', label: 'Todos os tipos' },
  { value: 'bovino', label: 'Bovino' },
  { value: 'equino', label: 'Equino' },
  { value: 'suino', label: 'Suíno' },
  { value: 'ovino_caprino', label: 'Ovino/Caprino' },
  { value: 'aves', label: 'Aves' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'Todos os status' },
  { value: 'rascunho', label: 'Rascunho' },
  { value: 'em_andamento', label: 'Em Andamento' },
  { value: 'concluido', label: 'Concluído' },
];

const fmtCurrency = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 2 });

const SemoventesList = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterTipo, setFilterTipo] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterTipo) params.tipo = filterTipo;
      if (filterStatus) params.status = filterStatus;
      setItems(await semoventesAPI.list(params));
    } catch (err) {
      console.warn(err);
      toast({ title: 'Erro ao carregar laudos de semoventes', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast, filterTipo, filterStatus]);

  useEffect(() => { load(); }, [load]);

  const remove = async (id) => {
    if (!window.confirm('Remover este laudo de semoventes? Esta ação não pode ser desfeita.')) return;
    try {
      await semoventesAPI.remove(id);
      setItems(items.filter((s) => s.id !== id));
      toast({ title: 'Laudo removido' });
    } catch {
      toast({ title: 'Erro ao remover', variant: 'destructive' });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Beef className="w-6 h-6 text-emerald-800" />
            <h1 className="font-display text-3xl font-bold text-gray-900">Avaliação de Semoventes</h1>
          </div>
          <p className="text-gray-600">
            Laudos para penhor rural bancário — Res. CMN 4.676/2018, Dec.-Lei 167/1967, CFMV Res. 722/2002.
          </p>
        </div>
        <Button
          onClick={() => nav('/dashboard/semoventes/nova')}
          className="bg-emerald-900 hover:bg-emerald-800 text-white"
        >
          <Plus className="w-4 h-4 mr-2" />Nova Avaliação
        </Button>
      </div>

      {/* Alert CRMV */}
      <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
        <div className="mt-0.5 w-5 h-5 rounded-full bg-red-500 flex items-center justify-center flex-shrink-0">
          <span className="text-white text-xs font-bold">!</span>
        </div>
        <p className="text-sm text-red-800">
          <strong>ATENÇÃO:</strong> Avaliação de semoventes para fins bancários exige obrigatoriamente
          Médico Veterinário com CRMV ativo. Laudo sem CRMV/CZO é <strong>nulo</strong> para fins de penhor rural.
          (CFMV Res. 722/2002 · MCR BACEN Cap. 6)
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center bg-white border border-gray-200 rounded-xl p-4">
        <Filter className="w-4 h-4 text-gray-400" />
        <select
          value={filterTipo}
          onChange={(e) => setFilterTipo(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          {TIPO_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        {(filterTipo || filterStatus) && (
          <button
            onClick={() => { setFilterTipo(''); setFilterStatus(''); }}
            className="text-xs text-red-500 hover:text-red-700 underline"
          >
            Limpar filtros
          </button>
        )}
      </div>

      {/* List */}
      {loading ? (
        <div className="py-16 flex justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-emerald-800" />
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-dashed border-gray-200">
          <Beef className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <div className="font-semibold text-gray-900">Nenhum laudo de semoventes encontrado</div>
          <p className="text-sm text-gray-500 mt-1">
            {filterTipo || filterStatus
              ? 'Tente outros filtros ou limpe a busca.'
              : 'Clique em "Nova Avaliação" para começar.'}
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((s) => {
            const tipo = TIPO_CONFIG[s.tipo_semovente] || TIPO_CONFIG.bovino;
            const status = STATUS_CONFIG[s.status] || STATUS_CONFIG.rascunho;
            const Icon = tipo.icon;
            return (
              <div
                key={s.id}
                className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition cursor-pointer"
                onClick={() => nav(`/dashboard/semoventes/${s.id}`)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-emerald-900/10 flex items-center justify-center">
                    <Icon className="w-5 h-5 text-emerald-900" />
                  </div>
                  <Badge className={status.color}>{status.label}</Badge>
                </div>

                <div className="text-xs font-semibold text-emerald-700 tracking-wider">
                  {s.numero_laudo || 'Sem número'}
                </div>
                <Badge className={`${tipo.color} mt-1 text-[10px]`}>{tipo.label}</Badge>

                <div className="font-semibold text-gray-900 mt-2 line-clamp-1">
                  {s.propriedade_nome || s.devedor_nome || '(sem identificação)'}
                </div>
                <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                  {s.propriedade_municipio
                    ? `${s.propriedade_municipio}/${s.propriedade_uf}`
                    : s.instituicao_financeira || '—'}
                </div>

                <div className="mt-4 pt-4 border-t border-gray-100 space-y-1.5">
                  {(s.total_cabecas > 0) && (
                    <div className="flex items-center gap-1.5 text-xs text-gray-600">
                      <Layers className="w-3 h-3" />
                      {s.total_cabecas} cabeças · {(s.total_ua || 0).toFixed(1)} UA
                    </div>
                  )}
                  <div className="flex items-center gap-1.5 text-xs text-gray-600">
                    <DollarSign className="w-3 h-3" />
                    {fmtCurrency(s.valor_mercado_total)}
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <Calendar className="w-3 h-3" />
                    {s.updated_at ? new Date(s.updated_at).toLocaleDateString('pt-BR') : '—'}
                  </div>
                </div>

                <div className="flex gap-2 mt-4" onClick={(e) => e.stopPropagation()}>
                  <Button
                    size="sm"
                    className="flex-1 bg-emerald-900 hover:bg-emerald-800 text-white"
                    onClick={() => nav(`/dashboard/semoventes/${s.id}`)}
                  >
                    Editar
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-red-600 hover:bg-red-50"
                    onClick={() => remove(s.id)}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default SemoventesList;
