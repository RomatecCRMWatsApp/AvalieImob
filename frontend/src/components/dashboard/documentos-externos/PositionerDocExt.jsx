// @module documentos-externos/PositionerDocExt — posicionador multi-signatário do doc-ext.
// Generaliza o AssinaturaClienteModal: N signatários (por id), VÁRIAS caixas por signatário,
// cada uma com um tipo (assinatura/rubrica/data/nome_extenso). O RT desenha + posiciona a sua.
import React, { useEffect, useRef, useState } from 'react';
import { X, Loader2, Send } from 'lucide-react';
import { documentosExternosAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';

const CORES = ['#0B6E4F', '#B8860B', '#1d4ed8', '#9333ea', '#db2777', '#0891b2', '#ca8a04', '#475569'];
const RT = '__rt__';
const TIPOS = [
  { v: 'assinatura', l: 'Assinatura' },
  { v: 'rubrica', l: 'Rubrica' },
  { v: 'data', l: 'Data' },
  { v: 'nome_extenso', l: 'Nome' },
];

export default function PositionerDocExt({ doc, onClose, onEnviado }) {
  const { toast } = useToast();
  const [carregando, setCarregando] = useState(true);
  const [paginas, setPaginas] = useState([]);
  const [signatarios, setSignatarios] = useState([]);
  const [rt, setRt] = useState(null);
  const [ativo, setAtivo] = useState(0);          // índice do alvo (signatários + RT)
  const [tipoCaixa, setTipoCaixa] = useState('assinatura');
  const [caixas, setCaixas] = useState([]);       // [{alvo, pagina, x_pt, y_pt, larg_pt, alt_pt, tipo, _px}]
  const [previa, setPrevia] = useState(null);
  const [rtTraco, setRtTraco] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const rtCanvas = useRef(null);
  const rtDes = useRef(false);
  const arrasto = useRef(null);

  useEffect(() => {
    documentosExternosAPI.preparar(doc.id)
      .then((d) => { setPaginas(d.paginas || []); setSignatarios(d.signatarios || []); setRt(d.rt || null); })
      .catch((e) => toast({ title: 'Erro ao preparar', description: e?.response?.data?.detail || '', variant: 'destructive' }))
      .finally(() => setCarregando(false));
  }, [doc.id]); // eslint-disable-line

  // pré-carrega a assinatura salva do RT no canvas
  useEffect(() => {
    if (!rt?.assinatura_b64 || !rtCanvas.current) return;
    const img = new Image();
    img.onload = () => {
      const c = rtCanvas.current; if (!c) return; const ctx = c.getContext('2d');
      ctx.clearRect(0, 0, c.width, c.height); ctx.drawImage(img, 0, 0, c.width, c.height);
      setRtTraco(`data:image/png;base64,${rt.assinatura_b64}`);
    };
    img.src = `data:image/png;base64,${rt.assinatura_b64}`;
  }, [rt]);

  const rtPos = (e) => { const c = rtCanvas.current; const r = c.getBoundingClientRect(); const t = e.touches?.[0] || e; return { x: (t.clientX - r.left) * (c.width / r.width), y: (t.clientY - r.top) * (c.height / r.height) }; };
  const rtStart = (e) => { e.preventDefault(); e.stopPropagation(); rtDes.current = true; const ctx = rtCanvas.current.getContext('2d'); const p = rtPos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y); };
  const rtMove = (e) => { if (!rtDes.current) return; e.stopPropagation(); const ctx = rtCanvas.current.getContext('2d'); const p = rtPos(e); ctx.lineWidth = 2.2; ctx.lineCap = 'round'; ctx.strokeStyle = '#14315c'; ctx.lineTo(p.x, p.y); ctx.stroke(); };
  const rtEnd = () => { if (rtDes.current) { rtDes.current = false; setRtTraco(rtCanvas.current.toDataURL('image/png')); } };
  const rtLimpar = () => { const c = rtCanvas.current; c.getContext('2d').clearRect(0, 0, c.width, c.height); setRtTraco(null); };

  const alvos = rt ? [...signatarios, { id: RT, nome: rt.nome, papel: 'Responsável Técnico' }] : signatarios;
  const alvo = alvos[ativo];
  const ehRT = alvo?.id === RT;

  const onDown = (e, pgIdx) => {
    const r = e.currentTarget.getBoundingClientRect();
    arrasto.current = { pgIdx, x0: e.clientX - r.left, y0: e.clientY - r.top, el: e.currentTarget };
  };
  const onMove = (e) => {
    if (!arrasto.current) return;
    const r = arrasto.current.el.getBoundingClientRect();
    const x = Math.min(arrasto.current.x0, e.clientX - r.left);
    const y = Math.min(arrasto.current.y0, e.clientY - r.top);
    const w = Math.abs(e.clientX - r.left - arrasto.current.x0);
    const h = Math.abs(e.clientY - r.top - arrasto.current.y0);
    setPrevia({ pagina: arrasto.current.pgIdx, x, y, w, h });
  };
  const onUp = () => {
    if (!arrasto.current || !previa || previa.w < 8 || previa.h < 6 || !alvo) { arrasto.current = null; setPrevia(null); return; }
    const pg = paginas[previa.pagina];
    const r = arrasto.current.el.getBoundingClientRect();
    const escX = pg.largura_pt / r.width;
    const escY = pg.altura_pt / r.height;
    const larg_pt = previa.w * escX;
    const alt_pt = previa.h * escY;
    const x_pt = previa.x * escX;
    const y_pt = pg.altura_pt - (previa.y * escY) - alt_pt; // origem inf-esq
    const tipo = ehRT ? 'assinatura' : tipoCaixa;
    setCaixas((cs) => [...cs, { alvo: alvo.id, pagina: previa.pagina, x_pt, y_pt, larg_pt, alt_pt, tipo,
      _px: { ...previa, alvo: alvo.id, tipo } }]);
    arrasto.current = null;
    setPrevia(null);
  };

  const removerCaixa = (idx) => setCaixas((cs) => cs.filter((_, i) => i !== idx));
  const nBoxes = (id) => caixas.filter((c) => c.alvo === id).length;
  const corDe = (id) => CORES[Math.max(0, alvos.findIndex((a) => a.id === id)) % CORES.length];

  const enviar = async () => {
    const faltam = signatarios.filter((s) => nBoxes(s.id) === 0);
    if (faltam.length) { toast({ title: 'Posicione a assinatura de: ' + faltam.map((s) => s.nome.split(' ')[0]).join(', '), variant: 'destructive' }); return; }
    const rtBox = caixas.find((c) => c.alvo === RT);
    if (rt && (!rtTraco || !rtBox)) { toast({ title: 'Desenhe a SUA assinatura (RT) e posicione a caixa do RT', variant: 'destructive' }); return; }
    setEnviando(true);
    try {
      const posicoes = {};
      signatarios.forEach((s) => {
        posicoes[s.id] = caixas.filter((c) => c.alvo === s.id)
          .map(({ pagina, x_pt, y_pt, larg_pt, alt_pt, tipo }) => ({ pagina, x_pt, y_pt, larg_pt, alt_pt, tipo }));
      });
      const body = {
        posicoes,
        rt_traco: rtTraco,
        rt_ancora: rtBox && { pagina: rtBox.pagina, x_pt: rtBox.x_pt, y_pt: rtBox.y_pt, larg_pt: rtBox.larg_pt, alt_pt: rtBox.alt_pt },
      };
      const r = await documentosExternosAPI.posicionar(doc.id, body);
      if (r.falhas && r.falhas.length) {
        toast({ title: `Enviado a ${r.enviados}/${r.total} · falhou para ${r.falhas.length}`,
          description: r.falhas.map((f) => `${f.nome}: ${f.erro}`).join(' · '), variant: 'destructive' });
      } else {
        toast({ title: 'Links enviados pelo WhatsApp', description: (r.links || []).map((l) => l.nome).join(' · ') });
      }
      onEnviado ? onEnviado() : onClose?.();
    } catch (e) {
      toast({ title: 'Falha ao enviar', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setEnviando(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-[60] flex flex-col" onMouseMove={onMove} onMouseUp={onUp}>
      <div className="bg-emerald-900 text-white px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Send className="w-5 h-5" />
          <div>
            <h2 className="font-bold text-sm">Posicionar assinaturas — {doc.codigo}</h2>
            <p className="text-xs text-emerald-300 mt-0.5">Selecione o signatário e o tipo, e arraste retângulos sobre as linhas de assinatura. Pode haver várias caixas por signatário.</p>
          </div>
        </div>
        <button onClick={onClose} className="text-emerald-300 hover:text-white"><X className="w-5 h-5" /></button>
      </div>

      {carregando ? (
        <div className="flex-1 flex items-center justify-center text-white"><Loader2 className="w-8 h-8 animate-spin mr-2" /> Preparando documento…</div>
      ) : (
        <>
          <div className="bg-white border-b border-gray-200 px-4 py-3 shrink-0 max-h-[42vh] overflow-auto space-y-3">
            {/* Alvos (signatários + RT) */}
            <div className="flex gap-2 flex-wrap">
              {alvos.map((s, i) => (
                <button key={s.id} onClick={() => setAtivo(i)}
                  className="px-3 py-1.5 rounded-lg text-[13px] border-2"
                  style={{ borderColor: CORES[i % CORES.length], background: i === ativo ? CORES[i % CORES.length] : '#fff', color: i === ativo ? '#fff' : '#333' }}>
                  {s.papel ? `${s.papel}: ` : ''}{s.nome?.split(' ')[0]} ({nBoxes(s.id)})
                </button>
              ))}
            </div>

            {/* Tipo de caixa (signatários; RT é sempre assinatura) */}
            {!ehRT && (
              <div className="flex gap-2 flex-wrap items-center">
                <span className="text-[12px] text-gray-500">Tipo da caixa:</span>
                {TIPOS.map((t) => (
                  <button key={t.v} onClick={() => setTipoCaixa(t.v)}
                    className="px-3 py-1 rounded-lg text-[12px] border"
                    style={{ background: tipoCaixa === t.v ? '#0B6E4F' : '#fff', color: tipoCaixa === t.v ? '#fff' : '#333', borderColor: '#0B6E4F' }}>
                    {t.l}
                  </button>
                ))}
              </div>
            )}

            {/* Canvas da assinatura do RT */}
            {rt && (
              <div className="bg-slate-50 border border-slate-300 rounded-xl p-2.5">
                <div className="text-[13px] font-bold text-slate-700 mb-1.5">
                  ✍️ Sua assinatura ({rt.nome?.split(' ')[0]}) — carimbada ANTES do envio; selecione "{rt.nome?.split(' ')[0]}" acima e posicione a caixa do RT.
                </div>
                <canvas ref={rtCanvas} width={500} height={120}
                  onMouseDown={rtStart} onMouseMove={rtMove} onMouseUp={rtEnd} onMouseLeave={rtEnd}
                  onTouchStart={rtStart} onTouchMove={rtMove} onTouchEnd={rtEnd}
                  style={{ width: '100%', height: 120, background: '#fff', border: '1px dashed #94a3b8', borderRadius: 8, touchAction: 'none', cursor: 'crosshair', display: 'block' }} />
                <div className="flex items-center gap-2.5 mt-1.5">
                  <button onClick={rtLimpar} className="border border-slate-400 text-slate-600 rounded-lg px-3 py-1 text-xs">Limpar</button>
                  <span className="text-[11px]" style={{ color: rtTraco ? '#0B6E4F' : '#b45309' }}>
                    {rtTraco ? '✓ assinatura pronta' : 'desenhe sua assinatura aqui'}
                  </span>
                </div>
              </div>
            )}

            <p className="text-xs text-gray-500">Selecione um alvo (e o tipo da caixa) e <b>arraste um retângulo</b> sobre a linha de assinatura. Clique numa caixa já desenhada para removê-la.</p>
          </div>

          {/* Visualizador */}
          <div className="flex-1 overflow-auto bg-gray-800 p-4">
            {paginas.map((pg, idx) => (
              <div key={idx} className="relative select-none mx-auto mb-4 shadow-2xl" style={{ width: 'fit-content', maxWidth: '100%' }}>
                <div className="absolute top-0 left-0 bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded-br z-10 pointer-events-none">Pág. {idx + 1}/{paginas.length}</div>
                <img src={`data:image/png;base64,${pg.imagem_b64}`} alt={`Página ${idx + 1}`}
                  onMouseDown={(e) => onDown(e, idx)} draggable={false}
                  style={{ display: 'block', width: 820, maxWidth: '100%', cursor: 'crosshair', userSelect: 'none' }} />
                {caixas.map((c, ci) => {
                  if (c._px?.pagina !== idx) return null;
                  const cor = corDe(c.alvo);
                  return (
                    <div key={ci} onClick={() => removerCaixa(ci)} title="Clique para remover"
                      style={{ position: 'absolute', border: `2px solid ${cor}`, background: cor + '22',
                        left: c._px.x, top: c._px.y, width: c._px.w, height: c._px.h,
                        cursor: 'pointer', fontSize: 9, color: cor, overflow: 'hidden' }}>
                      {c.tipo === 'assinatura' ? '' : c.tipo}
                    </div>
                  );
                })}
                {previa && previa.pagina === idx && (
                  <div style={{ position: 'absolute', border: `2px dashed ${corDe(alvo?.id)}`,
                    left: previa.x, top: previa.y, width: previa.w, height: previa.h, pointerEvents: 'none' }} />
                )}
              </div>
            ))}
          </div>

          <div className="bg-gray-900 px-4 py-3 shrink-0 flex gap-2">
            <button onClick={onClose} className="flex-1 border border-gray-600 text-gray-300 py-3 rounded-xl text-sm">Cancelar</button>
            <button onClick={enviar} disabled={enviando}
              className="flex-[2] bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-xl text-sm flex items-center justify-center gap-2 disabled:opacity-60">
              {enviando ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
              Enviar links por WhatsApp
            </button>
          </div>
        </>
      )}
    </div>
  );
}
