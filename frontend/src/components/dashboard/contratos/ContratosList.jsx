import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Loader2, Trash2, Calendar, DollarSign, Filter,
  FileSignature, FileText, Share2, PenSquare, Download, ChevronDown,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { useToast } from '../../../hooks/use-toast';
import { contratosAPI } from '../../../lib/api';

/* ── Status config ──────────────────────────────────────── */
const STATUS_CONFIG = {
  MINUTA:     { label: 'Minuta',     color: 'bg-gray-100 text-gray-700' },
  DEFINITIVO: { label: 'Definitivo', color: 'bg-blue-100 text-blue-800' },
  ASSINADO:   { label: 'Assinado',   color: 'bg-emerald-100 text-emerald-800' },
  DISTRATADO: { label: 'Distratado', color: 'bg-red-100 text-red-800' },
};

/* ── Tipo config ─────────────────────────────────────────── */
const TIPO_CONFIG = {
  compra_venda:          { label: 'Compra e Venda' },
  promessa_compra_venda: { label: 'Promessa C&V' },
  permuta:               { label: 'Permuta' },
  doacao:                { label: 'Doação' },
  locacao_residencial:   { label: 'Locação Residencial' },
  locacao_comercial:     { label: 'Locação Comercial' },
  comodato:              { label: 'Comodato' },
  arras:                 { label: 'Arras / Sinal' },
  intermediacao:         { label: 'Intermediação' },
  cessao_direitos:       { label: 'Cessão de Direitos' },
  usufruto:              { label: 'Usufruto' },
  parceria_rural:        { label: 'Parceria Rural' },
  arrendamento_rural:    { label: 'Arrendamento Rural' },
  compra_venda_veiculo:  { label: 'C&V Veículo' },
  distrato:              { label: 'Distrato' },
};

/* ── Filter options ─────────────────────────────────────── */
const TIPO_OPTIONS = [
  { value: '', label: 'Todos os tipos' },
  ...Object.entries(TIPO_CONFIG).map(([value, { label }]) => ({ value, label })),
];

const STATUS_OPTIONS = [
  { value: '', label: 'Todos os status' },
  { value: 'MINUTA', label: 'Minuta' },
  { value: 'DEFINITIVO', label: 'Definitivo' },
  { value: 'ASSINADO', label: 'Assinado' },
  { value: 'DISTRATADO', label: 'Distratado' },
];

const fmtCurrency = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const fmtDate = (s) => (s ? new Date(s).toLocaleDateString('pt-BR') : '—');

/* ── Download helper ─────────────────────────────────────── */
const downloadBlob = async (apiFn, id, filename, toast) => {
  try {
    const res = await apiFn(id);
    const url = URL.createObjectURL(new Blob([res.data]));
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  } catch {
    toast({ title: `Erro ao baixar ${filename}`, variant: 'destructive' });
  }
};

/* ── Action menu for each card ───────────────────────────── */
const CardActions = ({ contrato, onEdit, onDelete, toast }) => {
  const [open, setOpen] = useState(false);
  const id = contrato.id;

  return (
    <div className="relative" onClick={(e) => e.stopPropagation()}>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-800 border border-gray-200 rounded-lg px-2 py-1 hover:bg-gray-50 transition"
      >
        Ações <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          className="absolute right-0 bottom-full mb-1 w-44 bg-white border border-gray-200 rounded-xl shadow-xl py-1 z-50"
          onMouseLeave={() => setOpen(false)}
        >
          <button
            onClick={() => { setOpen(false); onEdit(); }}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left"
          >
            <PenSquare className="w-3.5 h-3.5 text-gray-400" /> Editar
          </button>
          <button
            onClick={() => { setOpen(false); downloadBlob(contratosAPI.docx, id, `contrato-${id}.docx`, toast); }}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left"
          >
            <Download className="w-3.5 h-3.5 text-blue-500" /> Baixar DOCX
          </button>
          <button
            onClick={() => { setOpen(false); downloadBlob(contratosAPI.pdf, id, `contrato-${id}.pdf`, toast); }}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left"
          >
            <FileText className="w-3.5 h-3.5 text-red-500" /> Baixar PDF
          </button>
          <button
            onClick={() => {
              setOpen(false);
              contratosAPI.compartilhar(id)
                .then(r => {
                  navigator.clipboard?.writeText(r.url || '');
                  toast({ title: 'Link copiado!', description: 'Compartilhamento ativado.' });
                })
                .catch(() => toast({ title: 'Erro ao compartilhar', variant: 'destructive' }));
            }}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left"
          >
            <Share2 className="w-3.5 h-3.5 text-emerald-600" /> Compartilhar
          </button>
          <button
            onClick={() => {
              setOpen(false);
              contratosAPI.assinarD4sign(id, {})
                .then(() => toast({ title: 'Enviado para assinatura D4Sign!' }))
                .catch(() => toast({ title: 'Erro ao enviar para D4Sign', variant: 'destructive' }));
            }}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left"
          >
            <FileSignature className="w-3.5 h-3.5 text-violet-600" /> D4Sign
          </button>
          <div className="border-t border-gray-100 mt-0.5 pt-0.5">
            <button
              onClick={() => { setOpen(false); onDelete(); }}
              className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 w-full text-left"
            >
              <Trash2 className="w-3.5 h-3.5" /> Excluir
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

/* ── Main component ──────────────────────────────────────── */
const ContratosList = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterTipo, setFilterTipo] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [search, setSearch] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterTipo) params.tipo = filterTipo;
      if (filterStatus) params.status = filterStatus;
      setItems(await contratosAPI.listar(params));
    } catch (err) {
      console.warn(err);
      toast({ title: 'Erro ao carregar contratos', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast, filterTipo, filterStatus]);

  useEffect(() => { load(); }, [load]);

  const remove = async (id) => {
    if (!window.confirm('Excluir este contrato? Esta ação não pode ser desfeita.')) return;
    try {
      await contratosAPI.excluir(id);
      setItems(items.filter((c) => c.id !== id));
      toast({ title: 'Contrato excluído' });
    } catch {
      toast({ title: 'Erro ao excluir', variant: 'destructive' });
    }
  };

  /* client-side search por partes */
  const filtered = search.trim()
    ? items.filter((c) => {
        const q = search.toLowerCase();
        const partes = [
          c.vendedores?.map(v => v.nome)?.join(' ') || '',
          c.compradores?.map(v => v.nome)?.join(' ') || '',
          c.numero || '',
          c.objeto?.endereco || '',
        ].join(' ').toLowerCase();
        return partes.includes(q);
      })
    : items;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FileSignature className="w-6 h-6 text-emerald-800" />
            <h1 className="font-display text-3xl font-bold text-gray-900">Contratos</h1>
          </div>
          <p className="text-gray-600">
            Compra e venda, locação, arras, permuta, intermediação e mais — com IA jurídica e D4Sign.
          </p>
        </div>
        <Button
          onClick={() => nav('/dashboard/contratos/novo')}
          className="bg-emerald-900 hover:bg-emerald-800 text-white"
        >
          <Plus className="w-4 h-4 mr-2" /> Novo Contrato
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center bg-white border border-gray-200 rounded-xl p-4">
        <Filter className="w-4 h-4 text-gray-400 flex-shrink-0" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nome das partes..."
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 min-w-[200px]"
        />
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
        {(filterTipo || filterStatus || search) && (
          <button
            onClick={() => { setFilterTipo(''); setFilterStatus(''); setSearch(''); }}
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
          <FileSignature className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <div className="font-semibold text-gray-900">Nenhum contrato encontrado</div>
          <p className="text-sm text-gray-500 mt-1">
            {filterTipo || filterStatus || search
              ? 'Tente outros filtros ou limpe a busca.'
              : 'Clique em "Novo Contrato" para começar.'}
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((c) => {
            const statusCfg = STATUS_CONFIG[c.status] || STATUS_CONFIG.MINUTA;
            const tipoCfg = TIPO_CONFIG[c.tipo] || { label: c.tipo || 'Contrato' };
            const partesPrinc = [
              ...(c.vendedores || []).map(v => v.nome).filter(Boolean),
              ...(c.compradores || []).map(v => v.nome).filter(Boolean),
            ].filter(Boolean);

            return (
              <div
                key={c.id}
                className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition cursor-pointer"
                onClick={() => nav(`/dashboard/contratos/${c.id}`)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-emerald-900/10 flex items-center justify-center">
                    <FileSignature className="w-5 h-5 text-emerald-900" />
                  </div>
                  <Badge className={statusCfg.color}>{statusCfg.label}</Badge>
                </div>

                <div className="text-xs font-semibold text-emerald-700 tracking-wider">
                  {c.numero || 'Sem número'}
                </div>
                <Badge className="bg-gray-100 text-gray-700 text-[10px] mt-1">{tipoCfg.label}</Badge>

                <div className="font-semibold text-gray-900 mt-2 line-clamp-1">
                  {partesPrinc.length > 0 ? partesPrinc.join(' / ') : '(partes não informadas)'}
                </div>
                <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                  {c.objeto?.endereco || c.objeto?.descricao || '—'}
                </div>

                <div className="mt-4 pt-4 border-t border-gray-100 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs text-gray-600">
                    <DollarSign className="w-3 h-3" />
                    {fmtCurrency(c.pagamento?.valor_total)}
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <Calendar className="w-3 h-3" />
                    {fmtDate(c.updated_at)}
                  </div>
                </div>

                <div className="flex gap-2 mt-4 items-center justify-between" onClick={(e) => e.stopPropagation()}>
                  <Button
                    size="sm"
                    className="flex-1 bg-emerald-900 hover:bg-emerald-800 text-white"
                    onClick={() => nav(`/dashboard/contratos/${c.id}`)}
                  >
                    Editar
                  </Button>
                  <CardActions
                    contrato={c}
                    onEdit={() => nav(`/dashboard/contratos/${c.id}`)}
                    onDelete={() => remove(c.id)}
                    toast={toast}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ContratosList;
