// @module dashboard/documentos/DocumentosList — Assinatura de Documentos (PDF avulso + ICP).
// Upload de PDF → posicionar/assinar com ICP-Brasil (reusa AssinaturaPosicionadaModal tipo="documento").
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { FileSignature, Upload, Eye, FileDown, MapPin, Trash2, Loader2, ShieldCheck, FileText } from 'lucide-react';
import { documentosAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { Button } from '../../ui/button';
import AssinaturaPosicionadaModal from '../assinatura/AssinaturaPosicionadaModal';

const fmtData = (d) => (d ? new Date(d).toLocaleDateString('pt-BR') : '');
const fmtTam = (b) => (b ? `${(b / 1024 / 1024).toFixed(1)} MB` : '');

const baixarBlob = (blob, nome) => {
  const b = blob instanceof Blob ? blob : new Blob([blob], { type: 'application/pdf' });
  const url = URL.createObjectURL(b);
  const a = document.createElement('a');
  a.href = url; a.download = nome; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
};

const visualizar = async (apiFn, id, toast) => {
  const win = window.open('', '_blank');
  try {
    const blob = await apiFn(id);
    const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob], { type: 'application/pdf' }));
    if (win) win.location.href = url; else window.location.href = url;
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch {
    if (win) win.close();
    toast({ title: 'Erro ao abrir o PDF', variant: 'destructive' });
  }
};

export default function DocumentosList() {
  const { toast } = useToast();
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [posicionar, setPosicionar] = useState(null);
  const inputRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { setDocs(await documentosAPI.listar()); }
    catch { toast({ title: 'Erro ao carregar documentos', variant: 'destructive' }); }
    finally { setLoading(false); }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  const onUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.type !== 'application/pdf') { toast({ title: 'Envie um arquivo PDF', variant: 'destructive' }); return; }
    setEnviando(true);
    try {
      await documentosAPI.upload(file);
      toast({ title: 'Documento enviado', description: file.name });
      load();
    } catch (err) {
      toast({ title: 'Falha no upload', description: err?.response?.data?.detail || '', variant: 'destructive' });
    } finally {
      setEnviando(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const excluir = async (d) => {
    if (!window.confirm(`Excluir "${d.nome}"? O PDF e a assinatura serão removidos.`)) return;
    try { await documentosAPI.excluir(d.id); toast({ title: 'Documento excluído' }); load(); }
    catch { toast({ title: 'Erro ao excluir', variant: 'destructive' }); }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FileSignature className="w-6 h-6 text-[#C9A84C]" />
            <h1 className="font-display text-[34px] font-bold leading-tight text-[#C9A84C]">Assinatura de Documentos</h1>
          </div>
          <p className="text-sm mt-1 text-[#5B7466] dark:text-[#9FB5A6]">
            Envie um PDF avulso (ART, TRT, ofício, declaração…) e assine com ICP-Brasil posicionando o carimbo na página.
          </p>
        </div>
        <div>
          <input ref={inputRef} type="file" accept="application/pdf" className="hidden" onChange={onUpload} />
          <Button onClick={() => inputRef.current?.click()} disabled={enviando} className="bg-emerald-900 hover:bg-emerald-800 text-white">
            {enviando ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Upload className="w-4 h-4 mr-2" />}
            {enviando ? 'Enviando…' : 'Enviar documento (PDF)'}
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="py-16 flex justify-center"><Loader2 className="w-7 h-7 animate-spin text-emerald-700" /></div>
      ) : docs.length === 0 ? (
        <div className="text-center py-16 bg-gray-50 rounded-xl border border-dashed border-gray-200">
          <FileText className="w-9 h-9 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Nenhum documento ainda. Clique em <b>Enviar documento (PDF)</b> para começar.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {docs.map((d) => {
            const assinado = d.icp_status === 'assinado';
            return (
              <div key={d.id} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 flex flex-col">
                <div className="flex items-start gap-2 mb-2">
                  <div className="w-9 h-9 rounded-lg bg-[rgba(201,168,76,0.16)] flex items-center justify-center flex-shrink-0">
                    <FileText className="w-4 h-4 text-[#C9A84C]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-sm text-gray-900 truncate" title={d.nome}>{d.nome}</div>
                    <div className="text-[11px] text-gray-400">{d.paginas ? `${d.paginas} pág.` : ''} {fmtTam(d.tamanho)} · {fmtData(d.created_at)}</div>
                  </div>
                </div>
                <div className={`text-[11px] font-medium mb-3 ${assinado ? 'text-emerald-700' : 'text-amber-700'}`}>
                  {assinado ? '✓ Assinado (ICP-Brasil)' : '⏳ Não assinado'}
                </div>

                <div className="grid grid-cols-2 gap-1.5 mt-auto">
                  {assinado ? (
                    <>
                      <Btn icon={Eye} label="Visualizar assinado" onClick={() => visualizar(documentosAPI.pdfAssinado, d.id, toast)} cls="border-emerald-300 text-emerald-700 hover:bg-emerald-50" />
                      <Btn icon={FileDown} label="Baixar assinado" onClick={async () => { try { baixarBlob(await documentosAPI.pdfAssinado(d.id), `${d.nome.replace(/\.pdf$/i, '')}-assinado.pdf`); } catch { toast({ title: 'Erro ao baixar', variant: 'destructive' }); } }} cls="border-emerald-300 bg-emerald-600 text-white hover:bg-emerald-700" />
                      <Btn icon={ShieldCheck} label="Reassinar" onClick={() => setPosicionar(d)} cls="border-emerald-200 text-emerald-700 hover:bg-emerald-50" />
                      <Btn icon={Trash2} label="Excluir" onClick={() => excluir(d)} cls="border-red-200 text-red-600 hover:bg-red-50" />
                    </>
                  ) : (
                    <>
                      <Btn icon={Eye} label="Visualizar" onClick={() => visualizar(documentosAPI.pdfOriginal, d.id, toast)} cls="border-gray-200 text-gray-700 hover:bg-gray-50" />
                      <Btn icon={MapPin} label="Posicionar / Assinar" onClick={() => setPosicionar(d)} cls="border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100" />
                      <Btn icon={Trash2} label="Excluir" onClick={() => excluir(d)} cls="border-red-200 text-red-600 hover:bg-red-50 col-span-2" />
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {posicionar && (
        <AssinaturaPosicionadaModal
          tipo="documento"
          documentId={posicionar.id}
          onAssinado={() => { setPosicionar(null); toast({ title: 'Documento assinado!' }); load(); }}
          onFechar={() => setPosicionar(null)}
        />
      )}
    </div>
  );
}

const Btn = ({ icon: Icon, label, onClick, cls }) => (
  <button onClick={onClick} className={`flex items-center justify-center gap-1.5 border rounded-lg py-2 text-xs font-medium ${cls}`}>
    <Icon className="w-3.5 h-3.5" /> {label}
  </button>
);
