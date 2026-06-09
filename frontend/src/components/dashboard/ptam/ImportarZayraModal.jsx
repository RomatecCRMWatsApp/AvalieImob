import React, { useEffect, useState } from 'react';
import { X, MapPin, Camera, Loader2, Check } from 'lucide-react';
import { useToast } from '../../../hooks/use-toast';
import { zayraAPI } from '../../../lib/api';

/**
 * Modal de importação de fotos do ZAYRA para um PTAM.
 * Props:
 *   ptamId      — id do PTAM destino (obrigatório para importar)
 *   onImportado — callback(qtd) após importar com sucesso
 *   onFechar    — fecha o modal
 */
export default function ImportarZayraModal({ ptamId, onImportado, onFechar }) {
  const { toast } = useToast();
  const [fotos, setFotos] = useState([]);
  const [selecionadas, setSelecionadas] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [importando, setImportando] = useState(false);

  useEffect(() => {
    let alive = true;
    zayraAPI.galeria({ limit: 100 })
      .then((d) => { if (alive) setFotos(d.fotos || []); })
      .catch((err) => {
        toast({
          title: 'Não foi possível carregar o ZAYRA',
          description: err.response?.data?.detail || 'Verifique a integração.',
          variant: 'destructive',
        });
      })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [toast]);

  const toggle = (id) => {
    setSelecionadas((s) => {
      const novo = new Set(s);
      novo.has(id) ? novo.delete(id) : novo.add(id);
      return novo;
    });
  };

  const importar = async () => {
    if (selecionadas.size === 0 || !ptamId) return;
    setImportando(true);
    try {
      const fotosParaImportar = fotos.filter((f) => selecionadas.has(f.id));
      const r = await zayraAPI.importar(ptamId, fotosParaImportar);
      toast({ title: `${r.importadas} foto(s) importada(s) do ZAYRA` });
      onImportado?.(r.importadas, r.fotos || []);
    } catch (err) {
      toast({
        title: 'Falha ao importar',
        description: err.response?.data?.detail || 'Tente novamente.',
        variant: 'destructive',
      });
    } finally {
      setImportando(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="bg-white rounded-t-2xl sm:rounded-2xl w-full max-w-2xl max-h-[88vh] flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Camera className="w-5 h-5 text-emerald-700" />
            <div>
              <h3 className="font-bold text-gray-800">Importar do ZAYRA</h3>
              <p className="text-xs text-gray-400 mt-0.5">
                {selecionadas.size > 0 ? `${selecionadas.size} selecionada(s)` : 'Toque para selecionar'}
              </p>
            </div>
          </div>
          <button onClick={onFechar} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Grid */}
        <div className="flex-1 overflow-y-auto p-3">
          {loading && (
            <div className="flex items-center justify-center h-40">
              <Loader2 className="w-8 h-8 text-emerald-700 animate-spin" />
            </div>
          )}

          {!loading && fotos.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <Camera className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p className="text-sm">Nenhuma foto sincronizada no ZAYRA</p>
            </div>
          )}

          {!loading && fotos.length > 0 && (
            <div className="grid grid-cols-3 gap-2">
              {fotos.map((foto) => {
                const sel = selecionadas.has(foto.id);
                return (
                  <button
                    key={foto.id}
                    type="button"
                    onClick={() => toggle(foto.id)}
                    className={`relative aspect-square rounded-xl overflow-hidden border-2 transition-all
                      ${sel ? 'border-emerald-500 ring-2 ring-emerald-300' : 'border-transparent'}`}
                  >
                    <img src={foto.url} alt={`Foto #${foto.numero}`} className="w-full h-full object-cover" />
                    {sel && (
                      <div className="absolute inset-0 bg-emerald-500/20 flex items-center justify-center">
                        <span className="bg-emerald-500 text-white rounded-full w-7 h-7 flex items-center justify-center">
                          <Check className="w-4 h-4" />
                        </span>
                      </div>
                    )}
                    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-1.5">
                      <p className="text-white text-[10px] font-semibold">#{foto.numero}</p>
                      {(foto.latitude || foto.endereco) && (
                        <p className="text-emerald-300 text-[9px] flex items-center gap-0.5">
                          <MapPin className="w-2.5 h-2.5" /> GPS
                        </p>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-100 flex gap-2">
          <button onClick={onFechar}
            className="flex-1 border border-gray-200 text-gray-500 py-2.5 rounded-xl text-sm">
            Cancelar
          </button>
          <button
            onClick={importar}
            disabled={selecionadas.size === 0 || importando}
            className="flex-1 bg-emerald-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2"
          >
            {importando && <Loader2 className="w-4 h-4 animate-spin" />}
            {importando ? 'Importando...' : `Importar ${selecionadas.size > 0 ? selecionadas.size : ''} foto(s)`}
          </button>
        </div>
      </div>
    </div>
  );
}
