// Modal: PDF(s) ASSINADO(s) — status, baixar e reenviar por WhatsApp com números
// editáveis (default = clientes do cadastro) + opção de adicionar outros destinos.
import React, { useEffect, useState } from 'react';
import { X, Loader2, Send, Download, Eye, Plus, Trash2, CheckCircle2 } from 'lucide-react';
import { assinaturaClienteAPI, contratosAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';

const downloadVia = async (apiFn, id, filename, toast) => {
  try {
    const blob = await apiFn(id);
    const b = blob instanceof Blob ? blob : new Blob([blob], { type: 'application/pdf' });
    const url = URL.createObjectURL(b);
    const a = document.createElement('a');
    a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  } catch {
    toast({ title: `Erro ao baixar ${filename}`, variant: 'destructive' });
  }
};

// Abre a aba JÁ no clique (gesto do usuário) p/ não ser bloqueado como popup.
const visualizarVia = async (apiFn, id, toast) => {
  const win = window.open('', '_blank');
  try {
    const blob = await apiFn(id);
    const b = blob instanceof Blob ? blob : new Blob([blob], { type: 'application/pdf' });
    const url = URL.createObjectURL(b);
    if (win) win.location.href = url; else window.location.href = url;
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch {
    if (win) win.close();
    toast({ title: 'Erro ao abrir o PDF assinado', variant: 'destructive' });
  }
};

export default function ReenviarAssinadoModal({ contratoId, onClose }) {
  const { toast } = useToast();
  const [carregando, setCarregando] = useState(true);
  const [info, setInfo] = useState(null);
  const [fones, setFones] = useState([]);
  const [incluirProc, setIncluirProc] = useState(true);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    assinaturaClienteAPI.statusAssinado(contratoId)
      .then((d) => {
        setInfo(d);
        const ds = (d.destinos || []).filter((x) => (x.telefone || '').replace(/\D/g, ''));
        setFones(ds.length ? ds.map((x) => ({ nome: x.nome, telefone: x.telefone || '' }))
                           : [{ nome: '', telefone: '' }]);
        setIncluirProc(!!d.procuracao_assinada);
      })
      .catch((e) => toast({ title: 'Erro ao carregar', description: e?.response?.data?.detail || '', variant: 'destructive' }))
      .finally(() => setCarregando(false));
  }, [contratoId]); // eslint-disable-line

  const setFone = (i, v) => setFones((f) => f.map((x, k) => (k === i ? { ...x, telefone: v } : x)));
  const addFone = () => setFones((f) => [...f, { nome: '', telefone: '' }]);
  const delFone = (i) => setFones((f) => f.filter((_, k) => k !== i));

  const reenviar = async () => {
    const telefones = fones.map((x) => x.telefone).filter((t) => (t || '').replace(/\D/g, ''));
    if (!telefones.length) { toast({ title: 'Informe ao menos um WhatsApp', variant: 'destructive' }); return; }
    setEnviando(true);
    try {
      const r = await assinaturaClienteAPI.reenviarAssinado(contratoId, { telefones, incluir_procuracao: incluirProc });
      toast({ title: `Reenviado (${r.enviados})`, description: (r.documentos || []).join(' · ') });
      setInfo((p) => ({ ...p, enviado_status: 'enviado', enviado_em: new Date().toISOString() }));
    } catch (e) {
      toast({ title: 'Falha ao reenviar', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div style={ovl}>
      <div style={box}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-bold text-emerald-800 flex items-center gap-2"><CheckCircle2 className="w-5 h-5" /> PDF assinado — ver / baixar / reenviar</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-gray-500" /></button>
        </div>

        {carregando ? (
          <div className="py-10 text-center"><Loader2 className="w-6 h-6 animate-spin text-emerald-700 mx-auto" /></div>
        ) : (
          <div className="space-y-3">
            {info?.enviado_status && (
              <div className="text-xs bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg px-3 py-2">
                ✓ Enviado{info.enviado_em ? ` em ${new Date(info.enviado_em).toLocaleString('pt-BR')}` : ''}
              </div>
            )}

            {/* Contrato assinado — ver / baixar */}
            <div>
              <div className="text-[11px] font-semibold text-emerald-700 mb-1">Contrato assinado</div>
              <div className="grid grid-cols-2 gap-2">
                <button disabled={!info?.contrato_assinado}
                  onClick={() => visualizarVia(contratosAPI.pdfAssinado, contratoId, toast)}
                  className="flex items-center justify-center gap-1.5 border rounded-lg py-2 text-sm disabled:opacity-40 border-emerald-300 text-emerald-700 hover:bg-emerald-50">
                  <Eye className="w-4 h-4" /> Visualizar
                </button>
                <button disabled={!info?.contrato_assinado}
                  onClick={() => downloadVia(contratosAPI.pdfAssinado, contratoId, `contrato-${contratoId}-assinado.pdf`, toast)}
                  className="flex items-center justify-center gap-1.5 border rounded-lg py-2 text-sm disabled:opacity-40 border-emerald-300 text-emerald-700 hover:bg-emerald-50">
                  <Download className="w-4 h-4" /> Baixar
                </button>
              </div>
            </div>

            {/* Procuração assinada — ver / baixar */}
            {info?.procuracao_assinada && (
              <div>
                <div className="text-[11px] font-semibold text-[#8a7320] mb-1">Procuração assinada</div>
                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => visualizarVia(assinaturaClienteAPI.pdfAssinadoProc, contratoId, toast)}
                    className="flex items-center justify-center gap-1.5 border rounded-lg py-2 text-sm border-[#C9A84C]/50 text-[#8a7320] hover:bg-[#C9A84C]/10">
                    <Eye className="w-4 h-4" /> Visualizar
                  </button>
                  <button onClick={() => downloadVia(assinaturaClienteAPI.pdfAssinadoProc, contratoId, `procuracao-${contratoId}-assinada.pdf`, toast)}
                    className="flex items-center justify-center gap-1.5 border rounded-lg py-2 text-sm border-[#C9A84C]/50 text-[#8a7320] hover:bg-[#C9A84C]/10">
                    <Download className="w-4 h-4" /> Baixar
                  </button>
                </div>
              </div>
            )}

            {info?.procuracao_assinada && (
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" checked={incluirProc} onChange={(e) => setIncluirProc(e.target.checked)} className="rounded" />
                Incluir a procuração no reenvio
              </label>
            )}

            {/* Destinos (default clientes) */}
            <div>
              <div className="text-xs font-semibold text-gray-600 mb-1">Reenviar para (WhatsApp) — clientes por padrão; adicione outros se quiser:</div>
              <div className="space-y-2">
                {fones.map((x, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input value={x.telefone} onChange={(e) => setFone(i, e.target.value)}
                      placeholder={`WhatsApp${x.nome ? ' de ' + x.nome.split(' ')[0] : ''} (DDD+número)`}
                      className="flex-1 border border-gray-300 rounded-lg px-2.5 py-1.5 text-sm" />
                    {fones.length > 1 && <button onClick={() => delFone(i)} className="text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>}
                  </div>
                ))}
              </div>
              <button onClick={addFone} className="mt-1.5 text-xs text-emerald-700 flex items-center gap-1"><Plus className="w-3.5 h-3.5" /> Adicionar outro destino</button>
            </div>

            <button onClick={reenviar} disabled={enviando}
              className="w-full bg-emerald-700 hover:bg-emerald-600 text-white font-bold rounded-xl py-3 text-sm flex items-center justify-center gap-2 disabled:opacity-60">
              {enviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Reenviar PDF assinado
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

const ovl = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', zIndex: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 };
const box = { background: '#fff', borderRadius: 14, padding: 18, width: '100%', maxWidth: 460, maxHeight: '92vh', overflow: 'auto' };
