// @module ptam/ImportarVistoriaModal — Importa memorial + fotos de uma Vistoria (TVI) para o PTAM
import React, { useState, useEffect } from 'react';
import { X, Loader2, FileText, Camera, Check, ArrowLeft, ClipboardCheck, MapPin } from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { ptamExtrasAPI, tviAPI } from '../../../lib/api';

export default function ImportarVistoriaModal({ ptamId, onClose, onImported }) {
  const { toast } = useToast();
  const [step, setStep] = useState('select');     // select | options
  const [loading, setLoading] = useState(true);
  const [vistorias, setVistorias] = useState([]);
  const [sel, setSel] = useState(null);            // vistoria selecionada
  const [fotos, setFotos] = useState([]);
  const [fotosSel, setFotosSel] = useState({});    // id -> bool
  const [importMemorial, setImportMemorial] = useState(true);
  const [modoMemorial, setModoMemorial] = useState('substituir');
  const [importFotos, setImportFotos] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    ptamExtrasAPI.vistoriasCompativeis(ptamId)
      .then((r) => setVistorias(r.vistorias || []))
      .catch((e) => toast({ title: 'Erro ao listar vistorias', description: e.response?.data?.detail, variant: 'destructive' }))
      .finally(() => setLoading(false));
  }, [ptamId, toast]);

  const escolher = async (v) => {
    setSel(v);
    setStep('options');
    try {
      const ps = await tviAPI.listPhotos(v.id);
      const arr = Array.isArray(ps) ? ps : [];
      setFotos(arr);
      const init = {};
      arr.forEach((p) => { init[p.id] = true; });
      setFotosSel(init);
    } catch {
      setFotos([]);
    }
  };

  const toggleFoto = (id) => setFotosSel((s) => ({ ...s, [id]: !s[id] }));
  const todasMarcadas = fotos.length > 0 && fotos.every((p) => fotosSel[p.id]);
  const selecionarTodas = () => {
    const next = {};
    fotos.forEach((p) => { next[p.id] = !todasMarcadas; });
    setFotosSel(next);
  };
  const nSelecionadas = fotos.filter((p) => fotosSel[p.id]).length;

  const confirmar = async () => {
    if (!sel) return;
    setBusy(true);
    try {
      const fotos_ids = fotos.filter((p) => fotosSel[p.id]).map((p) => p.id);
      const r = await ptamExtrasAPI.importarVistoria(ptamId, sel.id, {
        importar_memorial: importMemorial,
        modo_memorial: modoMemorial,
        importar_fotos: importFotos,
        fotos_ids: importFotos ? fotos_ids : [],
      });
      toast({ title: `Importado ✓`, description: `${r.fotos_importadas || 0} foto(s)${r.memorial_aplicado ? ' + memorial' : ''}` });
      onImported && onImported(r);
      onClose && onClose();
    } catch (e) {
      const st = e.response?.status;
      toast({
        title: st === 409 ? 'PTAM assinado' : 'Erro ao importar',
        description: e.response?.data?.detail, variant: 'destructive',
      });
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <div className="flex items-center gap-2">
            {step === 'options' && (
              <button onClick={() => setStep('select')} className="text-gray-400 hover:text-gray-700"><ArrowLeft className="w-5 h-5" /></button>
            )}
            <ClipboardCheck className="w-5 h-5 text-emerald-800" />
            <h2 className="font-semibold text-gray-900">Importar de Vistoria</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700"><X className="w-5 h-5" /></button>
        </div>

        <div className="p-5 overflow-y-auto">
          {/* Passo 1: seleção */}
          {step === 'select' && (
            loading ? (
              <div className="py-16 flex justify-center"><Loader2 className="w-7 h-7 animate-spin text-emerald-700" /></div>
            ) : vistorias.length === 0 ? (
              <p className="text-center text-gray-400 py-12">Nenhuma vistoria encontrada.</p>
            ) : (
              <div className="space-y-2">
                {vistorias.map((v) => (
                  <button key={v.id} onClick={() => escolher(v)}
                    className="w-full text-left border border-gray-200 rounded-xl p-3 hover:border-emerald-300 hover:bg-emerald-50/40 transition">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-gray-900 truncate">{v.imovel_endereco || v.modelo_nome || 'Vistoria'}</div>
                        <div className="text-xs text-gray-500 truncate">
                          {v.numero_tvi || ''}{v.imovel_matricula ? ` · Matrícula ${v.imovel_matricula}` : ''}{v.data_vistoria ? ` · ${v.data_vistoria}` : ''}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {v.mesma_matricula && <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">mesma matrícula</span>}
                        {!v.mesma_matricula && v.mesmo_endereco && <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">mesmo endereço</span>}
                        <span className="text-[11px] text-gray-400 flex items-center gap-1"><Camera className="w-3 h-3" />{v.n_fotos}</span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )
          )}

          {/* Passo 2: opções */}
          {step === 'options' && sel && (
            <div className="space-y-5">
              <div className="text-sm text-gray-600">
                Vistoria: <b>{sel.imovel_endereco || sel.numero_tvi}</b>
              </div>

              {/* Memorial */}
              <div className="border border-gray-200 rounded-xl p-4 space-y-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={importMemorial} onChange={(e) => setImportMemorial(e.target.checked)} />
                  <FileText className="w-4 h-4 text-emerald-700" />
                  <span className="text-sm font-medium text-gray-800">Importar memorial (caracterização)</span>
                </label>
                {importMemorial && (
                  <div className="flex gap-2 pl-6">
                    {[['substituir', 'Substituir'], ['anexar', 'Anexar ao final']].map(([v, l]) => (
                      <button key={v} onClick={() => setModoMemorial(v)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold border ${modoMemorial === v ? 'bg-emerald-900 text-white border-emerald-900' : 'bg-white text-gray-600 border-gray-200'}`}>{l}</button>
                    ))}
                  </div>
                )}
              </div>

              {/* Fotos */}
              <div className="border border-gray-200 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={importFotos} onChange={(e) => setImportFotos(e.target.checked)} />
                    <Camera className="w-4 h-4 text-emerald-700" />
                    <span className="text-sm font-medium text-gray-800">Importar fotos ({nSelecionadas}/{fotos.length})</span>
                  </label>
                  {importFotos && fotos.length > 0 && (
                    <button onClick={selecionarTodas} className="text-xs font-semibold text-emerald-700">{todasMarcadas ? 'Desmarcar todas' : 'Selecionar todas'}</button>
                  )}
                </div>
                {importFotos && (
                  fotos.length === 0 ? (
                    <p className="text-xs text-gray-400">Esta vistoria não tem fotos.</p>
                  ) : (
                    <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                      {fotos.map((p) => (
                        <button key={p.id} type="button" onClick={() => toggleFoto(p.id)}
                          className={`relative aspect-square rounded-lg overflow-hidden border-2 ${fotosSel[p.id] ? 'border-emerald-500' : 'border-transparent'}`}>
                          {p.url ? <img src={p.url} alt={p.legenda || ''} className="w-full h-full object-cover" /> : <div className="w-full h-full bg-gray-100" />}
                          {fotosSel[p.id] && <span className="absolute top-1 right-1 w-5 h-5 rounded-full bg-emerald-500 text-white flex items-center justify-center"><Check className="w-3 h-3" /></span>}
                          {p.gps && <span className="absolute bottom-1 left-1 text-white"><MapPin className="w-3 h-3" /></span>}
                        </button>
                      ))}
                    </div>
                  )
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        {step === 'options' && (
          <div className="p-5 border-t border-gray-100 flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>Cancelar</Button>
            <Button onClick={confirmar} disabled={busy || (!importMemorial && !importFotos)} className="bg-emerald-900 hover:bg-emerald-800 text-white gap-1">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />} Importar
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
