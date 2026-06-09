import React, { useEffect, useRef, useState } from 'react';
import { X, Check, Loader2, Camera, MapPin } from 'lucide-react';
import { useToast } from '../../../hooks/use-toast';
import { galeriaAPI, API_BASE } from '../../../lib/api';

const fotoUrl = (id) => `${API_BASE}/upload/image/${id}`;

/**
 * Seleciona fotos da galeria própria do AvalieImob para anexar ao laudo.
 * Props:
 *   onSelecionar(fotos[])  — chamado com as fotos escolhidas ({id, numero, legenda...})
 *   onFechar()
 */
export default function GaleriaPickerModal({ onSelecionar, onFechar }) {
  const { toast } = useToast();
  const [fotos, setFotos] = useState([]);
  const [sel, setSel] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    galeriaAPI.listar({ limit: 300 })
      .then((d) => { if (alive.current) setFotos(d.fotos || []); })
      .catch((e) => toast({ title: 'Erro ao carregar galeria', description: e.response?.data?.detail, variant: 'destructive' }))
      .finally(() => { if (alive.current) setLoading(false); });
    return () => { alive.current = false; };
  }, [toast]);

  const toggle = (id) => setSel((s) => {
    const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n;
  });

  const confirmar = () => {
    const escolhidas = fotos.filter((f) => sel.has(f.id));
    if (!escolhidas.length) { toast({ title: 'Selecione ao menos uma foto' }); return; }
    onSelecionar?.(escolhidas);
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-[60] flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="bg-white rounded-t-2xl sm:rounded-2xl w-full max-w-2xl max-h-[88vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Camera className="w-5 h-5 text-emerald-700" />
            <div>
              <h3 className="font-bold text-gray-800">Galeria de Fotos</h3>
              <p className="text-xs text-gray-400">{sel.size > 0 ? `${sel.size} selecionada(s)` : 'Toque para selecionar'}</p>
            </div>
          </div>
          <button onClick={onFechar} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          {loading && <div className="flex justify-center py-10"><Loader2 className="w-8 h-8 text-emerald-700 animate-spin" /></div>}
          {!loading && fotos.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <Camera className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p className="text-sm">Sua galeria está vazia. Use a aba “Fotos” para capturar.</p>
            </div>
          )}
          {!loading && fotos.length > 0 && (
            <div className="grid grid-cols-3 gap-2">
              {fotos.map((f) => {
                const s = sel.has(f.id);
                return (
                  <button key={f.id} type="button" onClick={() => toggle(f.id)}
                    className={`relative aspect-square rounded-xl overflow-hidden border-2 transition-all ${s ? 'border-emerald-500 ring-2 ring-emerald-300' : 'border-transparent'}`}>
                    <img src={fotoUrl(f.id)} alt={`Foto ${f.numero}`} className="w-full h-full object-cover" loading="lazy" />
                    {s && (
                      <div className="absolute inset-0 bg-emerald-500/20 flex items-center justify-center">
                        <span className="bg-emerald-500 text-white rounded-full w-7 h-7 flex items-center justify-center"><Check className="w-4 h-4" /></span>
                      </div>
                    )}
                    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-1">
                      <p className="text-white text-[10px] font-semibold">#{f.numero}</p>
                      {(f.latitude || f.endereco) && <p className="text-emerald-300 text-[9px] flex items-center gap-0.5"><MapPin className="w-2.5 h-2.5" /> GPS</p>}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="p-4 border-t flex gap-2">
          <button onClick={onFechar} className="flex-1 border border-gray-200 text-gray-500 py-2.5 rounded-xl text-sm">Cancelar</button>
          <button onClick={confirmar} disabled={sel.size === 0}
            className="flex-1 bg-emerald-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl text-sm">
            Anexar {sel.size > 0 ? sel.size : ''} foto(s)
          </button>
        </div>
      </div>
    </div>
  );
}
