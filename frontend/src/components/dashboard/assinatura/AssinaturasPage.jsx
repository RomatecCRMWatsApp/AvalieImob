// @module dashboard/assinatura/AssinaturasPage — Acompanhamento dos envios para assinatura.
import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Download, XCircle, FileSignature, ChevronDown } from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';
import { assinaturaExternaAPI as API } from '../../../lib/api';

const STATUS_CLS = {
  enviado: 'bg-sky-50 text-sky-700 border-sky-200', parcialmente_assinado: 'bg-amber-50 text-amber-700 border-amber-200',
  assinado: 'bg-emerald-50 text-emerald-700 border-emerald-200', recusado: 'bg-red-50 text-red-600 border-red-200',
  cancelado: 'bg-gray-100 text-gray-500 border-gray-200', expirado: 'bg-gray-100 text-gray-500 border-gray-200',
  erro: 'bg-red-50 text-red-600 border-red-200', rascunho: 'bg-gray-100 text-gray-500 border-gray-200',
};
const STATUS_LBL = {
  enviado: 'Enviado', parcialmente_assinado: 'Parcial', assinado: 'Assinado', recusado: 'Recusado',
  cancelado: 'Cancelado', expirado: 'Expirado', erro: 'Erro', rascunho: 'Rascunho',
};
const PROV_LBL = { d4sign: 'D4Sign', clicksign: 'Clicksign', autentique: 'Autentique' };
const FILTROS = ['', 'enviado', 'parcialmente_assinado', 'assinado', 'cancelado'];
const fmt = (iso) => { try { return iso ? new Date(iso).toLocaleString('pt-BR') : ''; } catch { return ''; } };

const AssinaturasPage = () => {
  const { toast } = useToast();
  const [envios, setEnvios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fStatus, setFStatus] = useState('');
  const [aberto, setAberto] = useState(null);
  const [busy, setBusy] = useState(null);

  const carregar = useCallback(async () => {
    setLoading(true);
    try { setEnvios(await API.listarEnvios(fStatus ? { status: fStatus } : {})); }
    catch { toast({ title: 'Falha ao carregar', variant: 'destructive' }); }
    finally { setLoading(false); }
  }, [fStatus, toast]);
  useEffect(() => { carregar(); }, [carregar]);

  const sincronizar = async (e) => {
    setBusy(e.id);
    try { await API.sincronizarEnvio(e.id); await carregar(); toast({ title: 'Sincronizado' }); }
    catch { toast({ title: 'Falha ao sincronizar', variant: 'destructive' }); } finally { setBusy(null); }
  };
  const cancelar = async (e) => {
    if (!window.confirm('Cancelar este envio?')) return;
    setBusy(e.id);
    try { await API.cancelarEnvio(e.id); await carregar(); toast({ title: 'Envio cancelado' }); }
    catch { toast({ title: 'Falha ao cancelar', variant: 'destructive' }); } finally { setBusy(null); }
  };
  const baixar = async (e) => {
    setBusy(e.id);
    try {
      const blob = await API.arquivoAssinado(e.id);
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch { toast({ title: 'Arquivo assinado indisponível ainda', variant: 'destructive' }); }
    finally { setBusy(null); }
  };

  const prog = (e) => {
    const t = (e.signatarios || []).length;
    const a = (e.signatarios || []).filter((s) => s.status === 'assinado').length;
    return t ? `${a}/${t}` : '—';
  };

  if (loading) return <div className="py-20 flex justify-center"><BrandSpinner label="Carregando…" /></div>;

  return (
    <div className="max-w-4xl mx-auto pb-24 space-y-4">
      <div className="flex items-center justify-between">
        <div className="font-display text-2xl font-bold text-gray-900">Assinaturas</div>
        <Button variant="outline" onClick={carregar} className="gap-1"><RefreshCw className="w-4 h-4" /> Atualizar</Button>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {FILTROS.map((f) => (
          <button key={f || 'todos'} type="button" onClick={() => setFStatus(f)}
            className={`px-3 py-1 rounded-full text-xs font-semibold border ${fStatus === f ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white text-gray-600 border-gray-200'}`}>
            {f ? (STATUS_LBL[f] || f) : 'Todos'}
          </button>
        ))}
      </div>

      {envios.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 p-10 text-center text-sm text-gray-400">
          <FileSignature className="w-8 h-8 mx-auto mb-2 text-gray-300" />
          Nenhum envio ainda. Use “Enviar para assinatura” em um documento.
        </div>
      ) : envios.map((e) => {
        const open = aberto === e.id;
        return (
          <div key={e.id} className="rounded-xl border border-gray-200 bg-white">
            <button type="button" onClick={() => setAberto(open ? null : e.id)} className="w-full text-left p-4 flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-gray-800 truncate">{e.nome_documento || e.origem_tipo}</div>
                <div className="text-[11px] text-gray-400">{PROV_LBL[e.provider] || e.provider} · {fmt(e.created_at)}</div>
              </div>
              <span className="text-[11px] font-semibold text-gray-500 tabular-nums">{prog(e)}</span>
              <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${STATUS_CLS[e.status] || ''}`}>{STATUS_LBL[e.status] || e.status}</span>
              <ChevronDown className={`w-4 h-4 text-gray-400 transition ${open ? 'rotate-180' : ''}`} />
            </button>
            {open && (
              <div className="border-t border-gray-100 p-4 space-y-3">
                <div>
                  <div className="text-[11px] font-bold uppercase text-gray-500 mb-1">Signatários</div>
                  {(e.signatarios || []).map((s, i) => (
                    <div key={i} className="flex items-center justify-between text-xs py-0.5">
                      <span className="text-gray-700">{s.nome} <span className="text-gray-400">· {s.papel}</span></span>
                      <span className={s.status === 'assinado' ? 'text-emerald-600 font-semibold' : s.status === 'recusado' ? 'text-red-600' : 'text-gray-400'}>
                        {s.status === 'assinado' ? '✓ assinou' : s.status === 'recusado' ? '✕ recusou' : 'aguardando'}
                      </span>
                    </div>
                  ))}
                  {(e.signatarios || []).length === 0 && <div className="text-xs text-gray-400">—</div>}
                </div>
                {(e.eventos || []).length > 0 && (
                  <div>
                    <div className="text-[11px] font-bold uppercase text-gray-500 mb-1">Histórico</div>
                    <ul className="text-[11px] text-gray-500 space-y-0.5">
                      {(e.eventos || []).slice(-8).map((ev, i) => (
                        <li key={i}>• {ev.tipo}{ev.status ? ` (${ev.status})` : ''} — {fmt(ev.em)}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="flex flex-wrap gap-2 pt-1">
                  <Button variant="outline" disabled={busy === e.id} onClick={() => sincronizar(e)} className="gap-1 h-8 text-xs">
                    <RefreshCw className={`w-3.5 h-3.5 ${busy === e.id ? 'animate-spin' : ''}`} /> Sincronizar
                  </Button>
                  {e.status === 'assinado' && (
                    <Button variant="outline" disabled={busy === e.id} onClick={() => baixar(e)} className="gap-1 h-8 text-xs">
                      <Download className="w-3.5 h-3.5" /> Baixar assinado
                    </Button>
                  )}
                  {!['assinado', 'cancelado', 'recusado'].includes(e.status) && (
                    <Button variant="outline" disabled={busy === e.id} onClick={() => cancelar(e)}
                      className="gap-1 h-8 text-xs text-red-500 border-red-200 hover:bg-red-50">
                      <XCircle className="w-3.5 h-3.5" /> Cancelar
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default AssinaturasPage;
