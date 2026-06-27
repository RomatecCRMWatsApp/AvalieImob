// @module documentos-externos/ModalEnviarFinal — envia a VIA FINALIZADA (PDF assinado) ao
// WhatsApp de cada signatário, com números editáveis e resultado por destinatário.
import React, { useState, useEffect, useCallback } from 'react';
import { X, Send, Eye, Loader2, CheckCircle2, AlertTriangle, Plus, Trash2 } from 'lucide-react';
import { documentosExternosAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';

const soDig = (v) => String(v || '').replace(/\D/g, '');

export default function ModalEnviarFinal({ doc, onClose }) {
  const { toast } = useToast();
  const [sigs, setSigs] = useState([]);     // [{id, nome, papel, whatsapp, status}]
  const [fones, setFones] = useState({});   // id -> whatsapp editável
  const [carregando, setCarregando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null); // {enviados, falhas, total, via}
  const [extras, setExtras] = useState([]);          // outros números (fora dos signatários)
  const [sel, setSel] = useState(null);              // null até o 1º envio; depois {id:bool} p/ reenvio seletivo

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const d = await documentosExternosAPI.status(doc.id);
      const lista = d.signatarios || [];
      setSigs(lista);
      setFones(Object.fromEntries(lista.map((s) => [s.id, s.whatsapp || ''])));
      // se a via final JÁ foi distribuída antes, abre direto em modo reenvio (seleção visível, todos marcados)
      if (doc.via_final_enviada_em) setSel(Object.fromEntries(lista.map((s) => [s.id, true])));
    } catch (e) {
      toast({ title: 'Erro ao carregar signatários', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setCarregando(false); }
  }, [doc.id, doc.via_final_enviada_em, toast]);

  useEffect(() => { carregar(); }, [carregar]);

  const verFinal = async () => {
    const win = window.open('', '_blank');
    try {
      const blob = await documentosExternosAPI.pdfFinal(doc.id);
      const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob], { type: 'application/pdf' }));
      if (win) win.location.href = url; else window.location.href = url;
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch { if (win) win.close(); toast({ title: 'Via final indisponível', variant: 'destructive' }); }
  };

  const enviar = async () => {
    setEnviando(true); setResultado(null);
    try {
      const reenvio = sel !== null;
      const body = {
        signatarios: sigs.map((s) => ({ id: s.id, whatsapp: soDig(fones[s.id]) })),
        extras: extras.map(soDig).filter(Boolean),
      };
      if (reenvio) body.enviar_ids = sigs.filter((s) => sel[s.id]).map((s) => s.id);
      const r = await documentosExternosAPI.distribuirFinal(doc.id, body);
      setResultado(r);
      // após o envio, habilita a seleção p/ reenvio — marca por padrão quem FALHOU
      const falhou = new Set((r.falhas || []).map((f) => f.nome));
      setSel(Object.fromEntries(sigs.map((s) => [s.id, falhou.has(s.nome)])));
      if (r.falhas && r.falhas.length) {
        toast({ title: `Enviado a ${r.enviados} · falhou para ${r.falhas.length}`, variant: 'destructive' });
      } else {
        toast({ title: `Via final ${reenvio ? 'reenviada' : 'enviada'} a ${r.enviados} destinatário(s)` });
      }
    } catch (e) {
      toast({ title: 'Falha ao enviar a via final', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setEnviando(false); }
  };

  const erroDe = (nome) => (resultado?.falhas || []).find((f) => f.nome === nome)?.erro;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-1">
          <h3 className="text-lg font-bold text-emerald-950">Enviar via finalizada</h3>
          <button onClick={onClose}><X /></button>
        </div>
        <p className="text-xs text-gray-500 mb-4">{doc.codigo} · {doc.titulo} — o PDF assinado vai para o WhatsApp de cada signatário.</p>

        {carregando ? (
          <div className="py-10 flex justify-center text-emerald-700"><Loader2 className="w-6 h-6 animate-spin" /></div>
        ) : (
          <>
            <button onClick={verFinal} className="flex items-center gap-1.5 text-emerald-700 text-sm mb-3 border border-emerald-200 rounded-lg px-3 py-1.5 hover:bg-emerald-50">
              <Eye className="w-4 h-4" /> Ver via final
            </button>

            <div className="space-y-2 mb-4">
              {sigs.map((s) => {
                const err = erroDe(s.nome);
                const ok = resultado && !err;
                return (
                  <div key={s.id} className={`border rounded-lg px-3 py-2 ${sel !== null && !sel[s.id] ? 'opacity-50' : ''}`}>
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        {sel !== null && (
                          <input type="checkbox" checked={!!sel[s.id]} title="Reenviar para este"
                                 onChange={(e) => setSel((m) => ({ ...m, [s.id]: e.target.checked }))} />
                        )}
                        <div className="text-sm font-semibold text-gray-900 truncate">{s.nome}
                          <span className="ml-2 text-[11px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700">{s.papel}</span>
                        </div>
                      </div>
                      {resultado && (ok
                        ? <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                        : <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />)}
                    </div>
                    <input className="mt-1.5 w-full border rounded-lg px-2.5 py-1.5 text-[13px]"
                           placeholder="WhatsApp (55 DDD número)"
                           value={fones[s.id] || ''}
                           onChange={(e) => setFones((f) => ({ ...f, [s.id]: e.target.value }))} />
                    {err && <div className="text-[11px] text-red-600 mt-1">⚠ {err}</div>}
                  </div>
                );
              })}
              {sigs.length === 0 && <p className="text-sm text-gray-500">Nenhum signatário.</p>}
            </div>

            {/* Outros números (fora dos signatários) */}
            <div className="border-t pt-3 mb-3">
              <div className="text-[12px] font-medium text-gray-600 mb-1.5">Enviar também para outros números (opcional)</div>
              {extras.map((v, i) => (
                <div key={i} className="flex items-center gap-2 mb-1.5">
                  <input className="flex-1 border rounded-lg px-2.5 py-1.5 text-[13px]" placeholder="55 DDD número"
                         value={v} onChange={(e) => setExtras((xs) => xs.map((x, k) => (k === i ? e.target.value : x)))} />
                  <button onClick={() => setExtras((xs) => xs.filter((_, k) => k !== i))} className="text-red-500 p-1"><Trash2 className="w-4 h-4" /></button>
                </div>
              ))}
              <button onClick={() => setExtras((xs) => [...xs, ''])}
                      className="flex items-center gap-1.5 text-emerald-700 text-xs border border-emerald-300 rounded-lg px-2.5 py-1.5 hover:bg-emerald-50">
                <Plus className="w-3.5 h-3.5" /> Adicionar outro número
              </button>
            </div>

            {resultado && (
              <div className="text-[12px] text-gray-600 mb-1">
                Resultado: <b>{resultado.enviados}</b> enviado(s) · via: {resultado.via}
              </div>
            )}
            {sel !== null && (
              <div className="text-[11px] text-amber-700 mb-3">↻ Marque quem deve receber novamente e clique em <b>Reenviar selecionados</b>.</div>
            )}

            <div className="flex justify-end gap-2">
              <button onClick={onClose} className="px-4 py-2 border rounded-lg text-sm">Fechar</button>
              <button onClick={enviar}
                      disabled={enviando || sigs.length === 0 || (sel !== null && !sigs.some((s) => sel[s.id]) && !extras.map(soDig).filter(Boolean).length)}
                      className="flex items-center gap-1.5 px-4 py-2 bg-emerald-700 text-white rounded-lg text-sm disabled:opacity-50">
                {enviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                {enviando ? 'Enviando…' : (sel === null ? 'Enviar via final' : 'Reenviar selecionados')}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
