// Pré-visualização do DANFSe (espelho da NFS-e) nos 3 temas Prime I / II / Tradicional.
// Rota: /dashboard/admin/danfse (admin). Usa o caso real NFS-e 59 (endpoint exemplo).
// Quando o módulo de EMISSÃO existir, o mesmo seletor vai p/ o modal de emissão.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { FileText, Download, Loader2 } from 'lucide-react';
import { adminAPI } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';

const VERDE = '#0C3320';
const DOURADO = '#C9A84C';

const TEMAS = [
  { id: 'prime1', nome: 'Prime I', desc: 'Cabeçalho split-diagonal preto × verde, numeral dourado.', sw: ['#0E0E0E', '#0C3320', '#C9A84C'] },
  { id: 'prime2', nome: 'Prime II', desc: 'Cabeçalho verde gradiente + numeral-fantasma dourado.', sw: ['#0C3320', '#15724A', '#C9A84C'] },
  { id: 'tradicional', nome: 'Tradicional', desc: 'Branco, serifa Times, faixas cinza — uso cartorial.', sw: ['#FFFFFF', '#EAEAEA', '#8A6D1F'] },
];

export default function DanfseTemas() {
  const { toast } = useToast();
  const [tema, setTema] = useState('prime1');
  const [pdfUrl, setPdfUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const urlRef = useRef(null);

  useEffect(() => () => { if (urlRef.current) URL.revokeObjectURL(urlRef.current); }, []);

  const carregar = useCallback(async (t) => {
    setLoading(true);
    try {
      const blob = await adminAPI.danfseExemplo(t);
      const u = URL.createObjectURL(blob);
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
      urlRef.current = u;
      setPdfUrl(u);
    } catch (e) {
      toast({ title: 'Erro ao gerar DANFSe', description: e.response?.data?.detail, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { carregar(tema); }, [tema, carregar]);

  const baixar = () => {
    if (!pdfUrl) return;
    const a = document.createElement('a');
    a.href = pdfUrl; a.download = `danfse-exemplo-${tema}.pdf`;
    document.body.appendChild(a); a.click(); a.remove();
  };

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-1 font-display" style={{ color: VERDE }}>DANFSe — Temas</h1>
      <p className="text-sm text-gray-500 mb-5">
        Espelho da NFS-e nos 3 acabamentos do AvalieImob. Pré-visualização com o caso real (NFS-e 59 · Açailândia).
        A emissão fiscal (DPS → NFS-e) é um módulo à parte; aqui você escolhe e confere o layout.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
        {TEMAS.map((t) => {
          const ativo = tema === t.id;
          return (
            <button key={t.id} type="button" onClick={() => setTema(t.id)}
              className={`text-left rounded-xl border-2 p-4 transition ${ativo ? 'shadow-md' : 'border-gray-200 hover:border-emerald-300'}`}
              style={ativo ? { borderColor: DOURADO, backgroundColor: '#FBF8F0' } : {}}>
              <div className="flex items-center gap-2 mb-2">
                {t.sw.map((cor, i) => (
                  <span key={i} className="w-5 h-5 rounded border border-gray-300" style={{ backgroundColor: cor }} />
                ))}
                {ativo && <span className="ml-auto text-[11px] font-bold uppercase" style={{ color: DOURADO }}>Selecionado</span>}
              </div>
              <div className="font-bold text-gray-800">{t.nome}</div>
              <div className="text-xs text-gray-500 mt-0.5">{t.desc}</div>
            </button>
          );
        })}
      </div>

      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: VERDE }}>
          <FileText className="w-4 h-4" /> Pré-visualização ({TEMAS.find((t) => t.id === tema)?.nome})
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
        </div>
        <button onClick={baixar} disabled={!pdfUrl || loading}
          className="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          style={{ backgroundColor: VERDE }}>
          <Download className="w-4 h-4" /> Baixar DANFSe
        </button>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
        {pdfUrl ? (
          <iframe title="DANFSe" src={`${pdfUrl}#toolbar=1&navpanes=0`} style={{ width: '100%', height: '78vh', border: 0 }} />
        ) : (
          <div className="h-[78vh] flex items-center justify-center text-gray-400 text-sm">
            <Loader2 className="w-4 h-4 animate-spin mr-2" /> Gerando DANFSe…
          </div>
        )}
      </div>
    </div>
  );
}
