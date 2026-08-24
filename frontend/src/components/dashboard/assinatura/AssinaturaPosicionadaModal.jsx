import React, { useEffect, useRef, useState } from 'react';
import { X, Loader2, PenLine, Copy, CheckCircle2 } from 'lucide-react';
import { useToast } from '../../../hooks/use-toast';
import { assinaturaPosAPI, perfilAPI } from '../../../lib/api';

// Qualidades em que o USUÁRIO LOGADO assina — o carimbo do ICP mostra a escolhida.
// "" = padrão do perfil (registros cadastrados).
//
// ATENÇÃO: NUNCA fixar aqui número de CRECI/CNAI/CFT de ninguém. Este modal é
// usado por todos os assinantes e o valor escolhido é ESTAMPADO num PDF com
// valor jurídico — presets fixos faziam um usuário assinar com o registro
// profissional de outra pessoa. As opções vêm do perfil de quem está logado.
const PRESETS_CARIMBO_DEFAULT = [
  { label: 'Padrão do perfil (registros cadastrados)', value: '' },
];

/** Sugestão montada a partir dos registros do próprio usuário. */
const presetsDosRegistros = (perfil) => {
  const regs = Array.isArray(perfil?.registros) ? perfil.registros : [];
  const linha = regs
    .filter((r) => r && r.numero)
    .map((r) => `${r.tipo || ''}${r.uf ? `/${r.uf}` : ''} ${r.numero}`.trim())
    .join(' · ');
  return linha ? [{ label: 'Meus registros profissionais', value: linha }] : [];
};

/**
 * Assinatura ICP-Brasil posicionada — MULTI-PÁGINA. O usuário desenha o retângulo
 * da assinatura em cada página que quiser; o sistema carimba o visual em todas e
 * aplica UM selo ICP-Brasil (PAdES) que sela o documento inteiro. Props:
 *   tipo        — 'ptam' | 'tvi' | 'garantia' | 'recibo' | 'contrato' | 'documento' | 'georef' ...
 *   documentId  — id do documento
 *   onAssinado  — callback({ download_url, hash, verificacao_url })
 *   onFechar    — fecha o modal
 */
export default function AssinaturaPosicionadaModal({ tipo, documentId, onAssinado, onFechar }) {
  const { toast } = useToast();
  const [paginas, setPaginas] = useState([]);
  const [paginaAtual, setPaginaAtual] = useState(0);
  const [boxes, setBoxes] = useState({});          // { [pageIdx]: {fx,fy,fw,fh} } frações 0..1
  const [desenhando, setDesenhando] = useState(false);
  const [inicio, setInicio] = useState({ x: 0, y: 0 });
  const [loading, setLoading] = useState(true);
  const [assinando, setAssinando] = useState(false);
  const [erro, setErro] = useState('');
  const [certId, setCertId] = useState(null);
  const [certs, setCerts] = useState([]);
  const [carimboQualif, setCarimboQualif] = useState('');   // qualificação a exibir no carimbo
  const [presets, setPresets] = useState(PRESETS_CARIMBO_DEFAULT);
  const imgRef = useRef(null);

  const certSel = certs.find((c) => c.id === certId) || null;
  const certTipo = (c) => (c?.perfil === 'PJ' ? 'e-CNPJ' : 'e-CPF');
  const certLabel = certSel ? `${certTipo(certSel)} — ${certSel.titular || certSel.label || 'ICP-Brasil'}` : '';

  const boxValido = (b) => b && b.fw > 0.03 && b.fh > 0.015;
  const box = boxes[paginaAtual] && boxValido(boxes[paginaAtual]) ? boxes[paginaAtual] : null;
  const paginasMarcadas = Object.keys(boxes).filter((k) => boxValido(boxes[k])).length;

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [prep, cs, perfil] = await Promise.all([
          assinaturaPosAPI.preparar(tipo, documentId),
          assinaturaPosAPI.certificados().catch(() => []),
          perfilAPI.get().catch(() => null),
        ]);
        if (!alive) return;
        // Opções = padrão + qualidades que o PRÓPRIO usuário cadastrou + sugestão
        // montada dos registros dele. Nunca dados de outra pessoa.
        const qs = (perfil?.carimbo_qualidades || []).filter((q) => q && q.label);
        setPresets([...PRESETS_CARIMBO_DEFAULT, ...presetsDosRegistros(perfil), ...qs]);
        setPaginas(prep.paginas || []);
        const lista = (Array.isArray(cs) ? cs : (cs?.certificados || [])).filter((c) => c.ativo !== false);
        setCerts(lista);
        // Peças do Topografia & Geo (inclusive o Dossiê do ONR) são assinadas pelo
        // RT — pessoa física — então prefere o e-CPF ao e-CNPJ.
        const ehGeoref = tipo === 'georef' || tipo === 'onr';
        const escolhido = ehGeoref ? (lista.find((c) => c.perfil !== 'PJ') || lista[0]) : lista[0];
        if (escolhido) setCertId(escolhido.id);
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
    return { x: clientX - r.left, y: clientY - r.top, w: r.width, h: r.height };
  };

  const start = (cx, cy) => {
    const p = posFrom(cx, cy);
    setInicio(p);
    setDesenhando(true);
    setBoxes((prev) => ({ ...prev, [paginaAtual]: null }));
  };
  const move = (cx, cy) => {
    if (!desenhando || !imgRef.current) return;
    const p = posFrom(cx, cy);
    const x = Math.min(inicio.x, p.x), y = Math.min(inicio.y, p.y);
    const w = Math.abs(p.x - inicio.x), h = Math.abs(p.y - inicio.y);
    setBoxes((prev) => ({ ...prev, [paginaAtual]: { fx: x / p.w, fy: y / p.h, fw: w / p.w, fh: h / p.h } }));
  };
  const end = () => setDesenhando(false);

  const repetirEmTodas = () => {
    const b = boxes[paginaAtual];
    if (!boxValido(b)) { toast({ title: 'Desenhe a assinatura nesta página primeiro', variant: 'destructive' }); return; }
    const novo = {};
    paginas.forEach((_, i) => { novo[i] = b; });
    setBoxes(novo);
    toast({ title: `Assinatura aplicada em ${paginas.length} páginas` });
  };

  const limparPagina = () => setBoxes((prev) => { const n = { ...prev }; delete n[paginaAtual]; return n; });

  const construirPosicoes = () => {
    const out = [];
    Object.entries(boxes).forEach(([idx, b]) => {
      if (!boxValido(b)) return;
      const pg = paginas[Number(idx)];
      if (!pg) return;
      const largura_pt = b.fw * pg.largura_pt;
      const altura_pt = b.fh * pg.altura_pt;
      const x_pt = b.fx * pg.largura_pt;
      const y_pt = pg.altura_pt - (b.fy * pg.altura_pt) - altura_pt;  // inverte eixo Y (PDF)
      out.push({ pagina: Number(idx), x_pt, y_pt, largura_pt, altura_pt });
    });
    return out.sort((a, b) => a.pagina - b.pagina);
  };

  const assinar = async () => {
    const posicoes = construirPosicoes();
    if (!posicoes.length) {
      toast({ title: 'Desenhe o campo de assinatura', description: 'Arraste um retângulo em pelo menos uma página.', variant: 'destructive' });
      return;
    }
    if (!certId) { toast({ title: 'Sem certificado ICP-Brasil', variant: 'destructive' }); return; }
    setAssinando(true);
    setErro('');
    try {
      const r = await assinaturaPosAPI.assinar(tipo, documentId, { cert_id: certId, posicoes, carimbo_qualificacao: carimboQualif.trim() || undefined });
      toast({ title: 'Documento assinado', description: `ICP-Brasil aplicada em ${posicoes.length} página(s).` });
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
              {certLabel ? `Certificado: ${certLabel}` : 'Desenhe a assinatura nas páginas que quiser'}
            </p>
          </div>
        </div>
        <button onClick={onFechar} className="text-emerald-300 hover:text-white"><X className="w-5 h-5" /></button>
      </div>

      {/* Páginas (com indicador de marcada) */}
      {paginas.length > 1 && (
        <div className="bg-gray-900 px-4 py-2 flex items-center gap-2 overflow-x-auto shrink-0">
          <span className="text-xs text-gray-400 shrink-0">Página:</span>
          {paginas.map((_, i) => {
            const marcada = boxValido(boxes[i]);
            return (
              <button key={i} onClick={() => setPaginaAtual(i)}
                className={`relative shrink-0 w-8 h-8 rounded text-xs font-bold ${paginaAtual === i ? 'bg-emerald-600 text-white' : 'bg-gray-700 text-gray-300'}`}>
                {i + 1}
                {marcada && <CheckCircle2 className="w-3 h-3 text-emerald-300 absolute -top-1 -right-1 bg-gray-900 rounded-full" />}
              </button>
            );
          })}
          <span className="text-xs text-emerald-400 shrink-0 ml-auto">{paginasMarcadas} marcada(s)</span>
        </div>
      )}

      {/* Visualização */}
      <div className="flex-1 overflow-auto bg-gray-800 flex justify-center p-4">
        {loading && <div className="flex items-center justify-center w-full"><Loader2 className="w-10 h-10 text-emerald-400 animate-spin" /></div>}
        {!loading && pg && (
          <div className="relative select-none self-start">
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
            {box && (
              <div className="absolute border-2 border-emerald-400 bg-emerald-400/20 pointer-events-none flex items-center justify-center"
                style={{ left: `${box.fx * 100}%`, top: `${box.fy * 100}%`, width: `${box.fw * 100}%`, height: `${box.fh * 100}%` }}>
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
        {certs.length > 0 && (
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 shrink-0">Assinar com:</label>
            <select value={certId || ''} onChange={(e) => setCertId(e.target.value)}
              className="flex-1 bg-gray-800 border border-gray-600 text-gray-100 text-xs rounded-lg px-2 py-2 focus:outline-none focus:border-emerald-500">
              {certs.map((c) => (
                <option key={c.id} value={c.id}>
                  {certTipo(c)} — {c.titular || c.label || 'ICP-Brasil'}{c.documento ? ` · ${c.documento}` : ''}
                </option>
              ))}
            </select>
          </div>
        )}
        {paginas.length > 1 && (
          <div className="flex items-center justify-center gap-3">
            <button onClick={repetirEmTodas} disabled={!box}
              className={`inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border ${box ? 'border-emerald-600 text-emerald-300 hover:bg-emerald-900/30' : 'border-gray-700 text-gray-600 cursor-not-allowed'}`}>
              <Copy className="w-3.5 h-3.5" /> Repetir em todas as páginas
            </button>
            {box && <button onClick={limparPagina} className="text-xs text-gray-400 underline">Limpar esta página</button>}
          </div>
        )}
        <div>
          <label className="block text-[11px] text-gray-400 mb-1">Assinar nesta qualidade (escolha conforme o documento)</label>
          <select
            value={presets.some((p) => p.value === carimboQualif) ? carimboQualif : '__custom__'}
            onChange={(e) => { if (e.target.value !== '__custom__') setCarimboQualif(e.target.value); }}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-2 text-xs text-gray-100 mb-1.5">
            {presets.map((p) => <option key={p.label} value={p.value}>{p.label}</option>)}
            <option value="__custom__">Personalizado (editar abaixo)…</option>
          </select>
          <input value={carimboQualif} onChange={(e) => setCarimboQualif(e.target.value)}
            placeholder="Padrão do perfil (CRECI/registros). Ou digite a qualificação para o carimbo."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-2 text-xs text-gray-100 placeholder-gray-500" />
        </div>
        <div className="text-center text-xs text-gray-400">
          {paginasMarcadas > 0
            ? `${paginasMarcadas} página(s) marcada(s). Navegue e desenhe em outras, ou assine.`
            : 'Toque e arraste na página onde a assinatura deve aparecer.'}
        </div>
        <div className="flex gap-2">
          <button onClick={onFechar} className="flex-1 border border-gray-600 text-gray-300 py-3 rounded-xl text-sm">Cancelar</button>
          <button onClick={assinar} disabled={paginasMarcadas === 0 || assinando || !certId}
            className={`flex-1 font-bold py-3 rounded-xl text-sm flex items-center justify-center gap-2 ${paginasMarcadas > 0 && certId && !assinando ? 'bg-emerald-600 hover:bg-emerald-500 text-white' : 'bg-gray-700 text-gray-500 cursor-not-allowed'}`}>
            {assinando && <Loader2 className="w-4 h-4 animate-spin" />}
            {assinando ? 'Assinando...' : `Assinar ${paginasMarcadas > 1 ? `(${paginasMarcadas} págs)` : ''} com ${certSel ? certTipo(certSel) : 'ICP-Brasil'}`}
          </button>
        </div>
      </div>
    </div>
  );
}
