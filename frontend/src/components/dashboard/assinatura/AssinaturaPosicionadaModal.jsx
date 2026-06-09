import React, { useEffect, useRef, useState } from 'react';
import { X, Loader2, PenLine } from 'lucide-react';
import { useToast } from '../../../hooks/use-toast';
import { assinaturaPosAPI } from '../../../lib/api';

/**
 * Assinatura ICP-Brasil posicionada — usuário arrasta o retângulo onde quer o
 * carimbo. Props:
 *   tipo        — 'ptam' | 'tvi' | 'garantia' | 'recibo'
 *   documentId  — id do documento
 *   onAssinado  — callback({ download_url, hash, verificacao_url })
 *   onFechar    — fecha o modal
 */
export default function AssinaturaPosicionadaModal({ tipo, documentId, onAssinado, onFechar }) {
  const { toast } = useToast();
  const [paginas, setPaginas] = useState([]);
  const [paginaAtual, setPaginaAtual] = useState(0);
  const [ret, setRet] = useState(null);           // {x,y,w,h} em px da imagem
  const [desenhando, setDesenhando] = useState(false);
  const [inicio, setInicio] = useState({ x: 0, y: 0 });
  const [loading, setLoading] = useState(true);
  const [assinando, setAssinando] = useState(false);
  const [erro, setErro] = useState('');
  const [certId, setCertId] = useState(null);
  const [certLabel, setCertLabel] = useState('');
  const imgRef = useRef(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [prep, certs] = await Promise.all([
          assinaturaPosAPI.preparar(tipo, documentId),
          assinaturaPosAPI.certificados().catch(() => []),
        ]);
        if (!alive) return;
        setPaginas(prep.paginas || []);
        const lista = Array.isArray(certs) ? certs : (certs?.certificados || []);
        const ativo = lista.find((c) => c.ativo !== false) || lista[0];
        if (ativo) { setCertId(ativo.id); setCertLabel(ativo.titular || ativo.label || 'e-CPF ICP-Brasil'); }
        else setErro('Nenhum certificado ICP-Brasil cadastrado. Cadastre seu e-CPF/e-CNPJ.');
      } catch (e) {
        if (alive) setErro(e.response?.data?.detail || 'Erro ao preparar o documento para assinatura.');
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [tipo, documentId]);

  const posFrom = (clientX, clientY) => {
    const r = imgRef.current.getBoundingClientRect();
    return { x: clientX - r.left, y: clientY - r.top };
  };

  const start = (cx, cy) => { setInicio(posFrom(cx, cy)); setDesenhando(true); setRet(null); };
  const move = (cx, cy) => {
    if (!desenhando || !imgRef.current) return;
    const p = posFrom(cx, cy);
    setRet({
      x: Math.min(inicio.x, p.x), y: Math.min(inicio.y, p.y),
      w: Math.abs(p.x - inicio.x), h: Math.abs(p.y - inicio.y),
    });
  };
  const end = () => setDesenhando(false);

  const converter = () => {
    const pg = paginas[paginaAtual];
    const el = imgRef.current;
    const escalaX = pg.largura_pt / el.clientWidth;
    const escalaY = pg.altura_pt / el.clientHeight;
    const largura_pt = ret.w * escalaX;
    const altura_pt = ret.h * escalaY;
    const x_pt = ret.x * escalaX;
    const y_pt = pg.altura_pt - (ret.y * escalaY) - altura_pt;   // inverte eixo Y
    return { x_pt, y_pt, largura_pt, altura_pt };
  };

  const assinar = async () => {
    if (!ret || ret.w < 30 || ret.h < 15) {
      toast({ title: 'Desenhe o campo de assinatura', description: 'Arraste um retângulo na página.', variant: 'destructive' });
      return;
    }
    if (!certId) { toast({ title: 'Sem certificado ICP-Brasil', variant: 'destructive' }); return; }
    setAssinando(true);
    setErro('');
    try {
      const coords = converter();
      const r = await assinaturaPosAPI.assinar(tipo, documentId, {
        cert_id: certId, pagina: paginaAtual, ...coords,
      });
      toast({ title: 'Documento assinado', description: 'ICP-Brasil aplicada com sucesso.' });
      onAssinado?.(r);
    } catch (e) {
      setErro(e.response?.data?.detail || 'Falha ao assinar.');
    } finally {
      setAssinando(false);
    }
  };

  const pg = paginas[paginaAtual];

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex flex-col">
      {/* Header */}
      <div className="bg-emerald-900 text-white px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <PenLine className="w-5 h-5" />
          <div>
            <h2 className="font-bold text-sm">Assinar documento — ICP-Brasil</h2>
            <p className="text-xs text-emerald-300 mt-0.5">
              {certLabel ? `Certificado: ${certLabel}` : 'Arraste para definir o campo da assinatura'}
            </p>
          </div>
        </div>
        <button onClick={onFechar} className="text-emerald-300 hover:text-white"><X className="w-5 h-5" /></button>
      </div>

      {/* Páginas */}
      {paginas.length > 1 && (
        <div className="bg-gray-900 px-4 py-2 flex items-center gap-2 overflow-x-auto shrink-0">
          <span className="text-xs text-gray-400 shrink-0">Página:</span>
          {paginas.map((_, i) => (
            <button key={i} onClick={() => { setPaginaAtual(i); setRet(null); }}
              className={`shrink-0 w-8 h-8 rounded text-xs font-bold ${paginaAtual === i ? 'bg-emerald-600 text-white' : 'bg-gray-700 text-gray-300'}`}>
              {i + 1}
            </button>
          ))}
        </div>
      )}

      {/* Visualização */}
      <div className="flex-1 overflow-auto bg-gray-800 flex justify-center p-4">
        {loading && <div className="flex items-center justify-center w-full"><Loader2 className="w-10 h-10 text-emerald-400 animate-spin" /></div>}
        {!loading && pg && (
          <div className="relative select-none" style={{ display: 'inline-block' }}>
            <img
              ref={imgRef}
              src={`data:image/png;base64,${pg.imagem_b64}`}
              alt={`Página ${paginaAtual + 1}`}
              className="block shadow-2xl cursor-crosshair max-w-full"
              draggable={false}
              onMouseDown={(e) => start(e.clientX, e.clientY)}
              onMouseMove={(e) => move(e.clientX, e.clientY)}
              onMouseUp={end}
              onMouseLeave={end}
              onTouchStart={(e) => start(e.touches[0].clientX, e.touches[0].clientY)}
              onTouchMove={(e) => { e.preventDefault(); move(e.touches[0].clientX, e.touches[0].clientY); }}
              onTouchEnd={end}
            />
            {ret && ret.w > 4 && ret.h > 4 && (
              <div className="absolute border-2 border-emerald-400 bg-emerald-400/20 pointer-events-none flex items-center justify-center"
                style={{ left: ret.x, top: ret.y, width: ret.w, height: ret.h }}>
                <span className="text-emerald-800 text-[10px] font-bold bg-white/85 px-1 rounded whitespace-nowrap">
                  Assinatura ICP-Brasil
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="bg-gray-900 px-4 py-4 shrink-0 space-y-3">
        {erro && <div className="bg-red-900/50 border border-red-500 text-red-300 text-xs px-3 py-2 rounded-lg">{erro}</div>}
        <div className="text-center text-xs text-gray-400">
          {ret ? 'Reposicione arrastando de novo, se quiser.' : 'Toque e arraste na página onde a assinatura deve aparecer.'}
        </div>
        <div className="flex gap-2">
          <button onClick={onFechar} className="flex-1 border border-gray-600 text-gray-300 py-3 rounded-xl text-sm">Cancelar</button>
          <button onClick={assinar} disabled={!ret || assinando || !certId}
            className={`flex-1 font-bold py-3 rounded-xl text-sm flex items-center justify-center gap-2 ${ret && certId && !assinando ? 'bg-emerald-600 hover:bg-emerald-500 text-white' : 'bg-gray-700 text-gray-500 cursor-not-allowed'}`}>
            {assinando && <Loader2 className="w-4 h-4 animate-spin" />}
            {assinando ? 'Assinando...' : 'Assinar com e-CPF ICP-Brasil'}
          </button>
        </div>
      </div>
    </div>
  );
}
