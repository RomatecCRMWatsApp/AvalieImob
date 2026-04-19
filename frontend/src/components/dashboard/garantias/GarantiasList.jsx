import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Loader2, Trash2, Calendar, DollarSign, Filter,
  Tractor, Wheat, Beef, Wrench, Car, Package, Shield, Building2
} from 'lucide-react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { useToast } from '../../../hooks/use-toast';
import { garantiasAPI } from '../../../lib/api';

const MODALIDADE_CONFIG = {
  sfh_fgts:             { label: 'SFH/FGTS',              color: 'bg-blue-100 text-blue-800' },
  sfi_bancario:         { label: 'SFI/Bancário',           color: 'bg-indigo-100 text-indigo-800' },
  alienacao_fiduciaria: { label: 'Alienação Fiduciária',   color: 'bg-violet-100 text-violet-800' },
  hipoteca:             { label: 'Hipoteca',               color: 'bg-cyan-100 text-cyan-800' },
  credito_rural:        { label: 'Crédito Rural',          color: 'bg-lime-100 text-lime-800' },
};

const TIPO_CONFIG = {
  imovel_rural:  { label: 'Imóvel Rural',     icon: Tractor,   color: 'bg-green-100 text-green-800' },
  imovel_urbano: { label: 'Imóvel Urbano',    icon: Building2, color: 'bg-teal-100 text-teal-800' },
  apartamento:   { label: 'Apartamento',      icon: Building2, color: 'bg-teal-100 text-teal-800' },
  casa:          { label: 'Casa',             icon: Building2, color: 'bg-teal-100 text-teal-800' },
  comercial:     { label: 'Comercial',        icon: Building2, color: 'bg-teal-100 text-teal-800' },
  terreno:       { label: 'Terreno',          icon: Building2, color: 'bg-teal-100 text-teal-800' },
  graos_safra:   { label: 'Grãos / Safra',    icon: Wheat,     color: 'bg-yellow-100 text-yellow-800' },
  bovinos:       { label: 'Bovinos',          icon: Beef,      color: 'bg-orange-100 text-orange-800' },
  equipamentos:  { label: 'Equipamentos',     icon: Wrench,    color: 'bg-blue-100 text-blue-800' },
  veiculos:      { label: 'Veículos',         icon: Car,       color: 'bg-purple-100 text-purple-800' },
  outros:        { label: 'Outros',           icon: Package,   color: 'bg-gray-100 text-gray-700' },
};

const STATUS_CONFIG = {
  rascunho:     { label: 'Rascunho',     color: 'bg-gray-100 text-gray-700' },
  em_andamento: { label: 'Em Andamento', color: 'bg-amber-100 text-amber-800' },
  concluido:    { label: 'Concluído',    color: 'bg-emerald-100 text-emerald-800' },
};

const TIPO_OPTIONS = [
  { value: '', label: 'Todos os tipos' },
  { value: 'imovel_rural', label: 'Imóvel Rural' },
  { value: 'imovel_urbano', label: 'Imóvel Urbano' },
  { value: 'apartamento', label: 'Apartamento' },
  { value: 'casa', label: 'Casa' },
  { value: 'terreno', label: 'Terreno' },
  { value: 'graos_safra', label: 'Grãos / Safra' },
  { value: 'bovinos', label: 'Bovinos' },
  { value: 'equipamentos', label: 'Equipamentos' },
  { value: 'veiculos', label: 'Veículos' },
  { value: 'outros', label: 'Outros' },
];

const MODALIDADE_OPTIONS = [
  { value: '', label: 'Todas as modalidades' },
  { value: 'sfh_fgts', label: 'SFH/FGTS' },
  { value: 'sfi_bancario', label: 'SFI/Bancário' },
  { value: 'alienacao_fiduciaria', label: 'Alienação Fiduciária' },
  { value: 'hipoteca', label: 'Hipoteca' },
  { value: 'credito_rural', label: 'Crédito Rural' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'Todos os status' },
  { value: 'rascunho', label: 'Rascunho' },
  { value: 'em_andamento', label: 'Em Andamento' },
  { value: 'concluido', label: 'Concluído' },
];

const GarantiasList = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterTipo, setFilterTipo] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterModalidade, setFilterModalidade] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterTipo) params.tipo = filterTipo;
      if (filterStatus) params.status = filterStatus;
      setItems(await garantiasAPI.list(params));
    } catch (err) {
      console.warn(err);
      toast({ title: 'Erro ao carregar garantias', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast, filterTipo, filterStatus]);

  useEffect(() => { load(); }, [load]);

  const remove = async (id) => {
    if (!window.confirm('Remover esta avaliação de garantia? Esta ação não pode ser desfeita.')) return;
    try {
      await garantiasAPI.remove(id);
      setItems(items.filter((g) => g.id !== id));
      toast({ title: 'Avaliação removida' });
    } catch {
      toast({ title: 'Erro ao remover', variant: 'destructive' });
    }
  };

  const fmtCurrency = (v) =>
    Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 2 });

  // Filtro client-side por modalidade (campo novo)
  const filtered = filterModalidade
    ? items.filter((g) => g.modalidade_financeira === filterModalidade)
    : items;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Shield className="w-6 h-6 text-emerald-800" />
            <h1 className="font-display text-3xl font-bold text-gray-900">Avaliação de Garantias</h1>
          </div>
          <p className="text-gray-600">
            Laudos conforme Res. CMN 4.676/2018 | NBR 14.653 — rurais, bancários, alienação fiduciária e mais.
          </p>
        </div>
        <Button
          onClick={() => nav('/dashboard/garantias/nova')}
          className="bg-emerald-900 hover:bg-emerald-800 text-white"
        >
          <Plus className="w-4 h-4 mr-2" />Nova Avaliação
        </Button>
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
          value={filterModalidade}
          onChange={(e) => setFilterModalidade(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          {MODALIDADE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        {(filterTipo || filterStatus || filterModalidade) && (
          <button
            onClick={() => { setFilterTipo(''); setFilterStatus(''); setFilterModalidade(''); }}
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
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-dashed border-gray-200">
          <Shield className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <div className="font-semibold text-gray-900">Nenhuma avaliação de garantia encontrada</div>
          <p className="text-sm text-gray-500 mt-1">
            {filterTipo || filterStatus || filterModalidade
              ? 'Tente outros filtros ou limpe a busca.'
              : 'Clique em "Nova Avaliação" para começar.'}
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((g) => {
            const tipo = TIPO_CONFIG[g.tipo_garantia] || TIPO_CONFIG.outros;
            const status = STATUS_CONFIG[g.status] || STATUS_CONFIG.rascunho;
            const modalidade = g.modalidade_financeira ? MODALIDADE_CONFIG[g.modalidade_financeira] : null;
            const Icon = tipo.icon;
            const valorDisplay = g.valor_mercado || g.valor_total;
            return (
              <div
                key={g.id}
                className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition cursor-pointer"
                onClick={() => nav(`/dashboard/garantias/${g.id}`)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-emerald-900/10 flex items-center justify-center">
                    <Icon className="w-5 h-5 text-emerald-900" />
                  </div>
                  <Badge className={status.color}>{status.label}</Badge>
                </div>

                <div className="text-xs font-semibold text-emerald-700 tracking-wider">
                  {g.numero || 'Sem número'}
                </div>
                <div className="flex flex-wrap gap-1 mt-1">
                  <Badge className={`${tipo.color} text-[10px]`}>{tipo.label}</Badge>
                  {modalidade && (
                    <Badge className={`${modalidade.color} text-[10px]`}>{modalidade.label}</Badge>
                  )}
                </div>

                <div className="font-semibold text-gray-900 mt-2 line-clamp-1">
                  {g.mutuario_nome || g.descricao_bem || g.municipio || '(sem descrição)'}
                </div>
                <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                  {g.instituicao_financeira || g.solicitante?.nome || '—'}{g.municipio ? ` · ${g.municipio}/${g.uf}` : ''}
                </div>

                <div className="mt-4 pt-4 border-t border-gray-100 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs text-gray-600">
                    <DollarSign className="w-3 h-3" />
                    {fmtCurrency(valorDisplay)}
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <Calendar className="w-3 h-3" />
                    {g.updated_at ? new Date(g.updated_at).toLocaleDateString('pt-BR') : '—'}
                  </div>
                </div>

                <div className="flex gap-2 mt-4" onClick={(e) => e.stopPropagation()}>
                  <Button
                    size="sm"
                    className="flex-1 bg-emerald-900 hover:bg-emerald-800 text-white"
                    onClick={() => nav(`/dashboard/garantias/${g.id}`)}
                  >
                    Editar
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-red-600 hover:bg-red-50"
                    onClick={() => remove(g.id)}
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

export default GarantiasList;
