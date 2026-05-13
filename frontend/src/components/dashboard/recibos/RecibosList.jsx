// @module recibos/RecibosList — Lista de recibos com cards e filtros
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Receipt, Loader2, Calendar, Trash2, FileDown, MessageCircle,
  CheckCircle2, Clock, Send, Search, Edit3,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { useToast } from '../../../hooks/use-toast';
import { recibosAPI } from '../../../lib/api';

const formatBRL = (v) => 'R$ ' + Number(v || 0).toLocaleString('pt-BR', {
  minimumFractionDigits: 2, maximumFractionDigits: 2,
});

const STATUS_CONFIG = {
  rascunho: { label: 'Rascunho', cls: 'bg-gray-100 text-gray-700', icon: Clock },
  emitido:  { label: 'Emitido',  cls: 'bg-amber-100 text-amber-800', icon: Receipt },
  enviado:  { label: 'Enviado',  cls: 'bg-emerald-100 text-emerald-800', icon: CheckCircle2 },
  cancelado:{ label: 'Cancelado',cls: 'bg-red-100 text-red-700', icon: Trash2 },
};

const RecibosList = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busca, setBusca] = useState('');
  const [filtroStatus, setFiltroStatus] = useState('');
  const [pdfLoading, setPdfLoading] = useState({});
  const [enviando, setEnviando] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await recibosAPI.listar(filtroStatus ? { status: filtroStatus } : {});
      setItems(data || []);
    } catch (e) {
      toast({ title: 'Erro ao carregar recibos', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [filtroStatus, toast]);

  useEffect(() => { load(); }, [load]);

  const filtered = items.filter(r => {
    if (!busca) return true;
    const q = busca.toLowerCase();
    return (r.numero || '').toLowerCase().includes(q)
        || (r.destinatario_nome || '').toLowerCase().includes(q)
        || (r.descricao || '').toLowerCase().includes(q);
  });

  const remove = async (r) => {
    if (!window.confirm(`Remover o recibo ${r.numero || '(rascunho)'}?`)) return;
    try {
      await recibosAPI.excluir(r.id);
      setItems(prev => prev.filter(x => x.id !== r.id));
      toast({ title: 'Recibo removido' });
    } catch (e) {
      toast({ title: 'Erro ao remover', variant: 'destructive' });
    }
  };

  const baixarPdf = async (r) => {
    setPdfLoading(prev => ({ ...prev, [r.id]: true }));
    try {
      const blob = await recibosAPI.pdf(r.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(r.numero || 'RECIBO_RASCUNHO').replace(/\//g, '-')}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast({ title: 'Erro ao baixar PDF', variant: 'destructive' });
    } finally {
      setPdfLoading(prev => ({ ...prev, [r.id]: false }));
    }
  };

  const enviarWA = async (r) => {
    if (!r.destinatario_whatsapp) {
      const phone = window.prompt('WhatsApp do destinatário (com DDI+DDD):', '55');
      if (!phone) return;
      r = { ...r, destinatario_whatsapp: phone };
    }
    setEnviando(prev => ({ ...prev, [r.id]: true }));
    try {
      await recibosAPI.enviarWhatsApp(r.id, r.destinatario_whatsapp);
      toast({ title: 'Recibo enviado via WhatsApp!' });
      load();
    } catch (e) {
      toast({ title: e.response?.data?.detail || 'Erro ao enviar', variant: 'destructive' });
    } finally {
      setEnviando(prev => ({ ...prev, [r.id]: false }));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Receipt className="w-7 h-7 text-amber-600" />
            Recibos
          </h1>
          <p className="text-gray-600 mt-1">
            Recibos de honorários, serviços e mão de obra. Gera PDF, envia por WhatsApp em 1 clique.
          </p>
        </div>
        <Button
          onClick={() => nav('/dashboard/recibos/novo')}
          className="bg-amber-500 hover:bg-amber-600 text-white shadow-md"
        >
          <Plus className="w-4 h-4 mr-2" />
          Novo Recibo
        </Button>
      </div>

      {/* Filtros */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={busca}
            onChange={e => setBusca(e.target.value)}
            placeholder="Buscar por número, destinatário ou descrição..."
            className="w-full pl-10 pr-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-amber-500"
          />
        </div>
        <select
          value={filtroStatus}
          onChange={e => setFiltroStatus(e.target.value)}
          className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-amber-500 bg-white"
        >
          <option value="">Todos os status</option>
          <option value="rascunho">Rascunho</option>
          <option value="emitido">Emitido</option>
          <option value="enviado">Enviado</option>
          <option value="cancelado">Cancelado</option>
        </select>
      </div>

      {/* Lista */}
      {loading ? (
        <div className="py-16 flex justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-amber-600" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-dashed border-gray-200">
          <Receipt className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <div className="font-semibold text-gray-900">Nenhum recibo {filtroStatus && 'com esse status'}</div>
          <p className="text-sm text-gray-500 mt-1">
            Clique em "Novo Recibo" para emitir o primeiro.
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(r => {
            const cfg = STATUS_CONFIG[r.status] || STATUS_CONFIG.rascunho;
            const StatusIcon = cfg.icon;
            return (
              <div
                key={r.id}
                className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition flex flex-col"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center">
                    <Receipt className="w-5 h-5 text-amber-700" />
                  </div>
                  <Badge className={`${cfg.cls} flex items-center gap-1`}>
                    <StatusIcon className="w-3 h-3" />
                    {cfg.label}
                  </Badge>
                </div>

                <div className="text-xs font-semibold text-amber-700 tracking-wider">
                  {r.numero || 'RASCUNHO'}
                </div>
                <div className="font-semibold text-gray-900 mt-1 line-clamp-1">
                  {r.destinatario_nome || '(sem destinatário)'}
                </div>
                {r.descricao && (
                  <div className="text-xs text-gray-500 mt-1 line-clamp-2">{r.descricao}</div>
                )}

                <div className="mt-4 pt-4 border-t border-gray-100 space-y-1.5">
                  <div className="text-xl font-bold text-emerald-900">{formatBRL(r.valor)}</div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <Calendar className="w-3 h-3" />
                    {r.created_at ? new Date(r.created_at).toLocaleDateString('pt-BR') : '—'}
                    {r.forma_pagamento && <> · {r.forma_pagamento}</>}
                  </div>
                </div>

                <div className="flex gap-2 mt-4 flex-wrap">
                  <Button
                    size="sm"
                    className="flex-1 bg-amber-400 hover:bg-amber-500 text-emerald-950 font-semibold gap-1"
                    onClick={() => nav(`/dashboard/recibos/${r.id}`)}
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    Abrir
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => baixarPdf(r)}
                    disabled={pdfLoading[r.id]}
                    title="Baixar PDF"
                    className="gap-1"
                  >
                    {pdfLoading[r.id] ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <FileDown className="w-3.5 h-3.5" />
                    )}
                    PDF
                  </Button>
                  <Button
                    size="sm"
                    className="bg-green-600 hover:bg-green-700 text-white gap-1"
                    onClick={() => enviarWA(r)}
                    disabled={enviando[r.id]}
                    title="Enviar via WhatsApp"
                  >
                    {enviando[r.id] ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <MessageCircle className="w-3.5 h-3.5" />
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-red-600 hover:bg-red-50"
                    onClick={() => remove(r)}
                    title="Excluir"
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

export default RecibosList;
