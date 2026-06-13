// Modal: corretor posiciona 1 caixa de assinatura por signatário no PDF renderizado
// e dispara os links por WhatsApp (assinatura DESENHada do cliente).
import React, { useEffect, useRef, useState } from 'react';
import { X, Loader2, Send } from 'lucide-react';
import { assinaturaClienteAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';

const ROLE_LABEL = { contratante: 'Contratante', conjuge_anuente: 'Cônjuge anuente', outorgante: 'Outorgante' };
const CORES = ['#0B6E4F', '#B8860B', '#1d4ed8', '#9333ea'];

export default function AssinaturaClienteModal({ contratoId, onClose }) {
  const { toast } = useToast();
  const [carregando, setCarregando] = useState(true);
  const [paginas, setPaginas] = useState([]);
  const [signatarios, setSignatarios] = useState([]);
  const [ativo, setAtivo] = useState(0); // índice do signatário sendo posicionado
  const [ancoras, setAncoras] = useState({}); // role -> {pagina,x_pt,y_pt,larg_pt,alt_pt}
  const [enviando, setEnviando] = useState(false);
  const arrasto = useRef(null);
  const [previa, setPrevia] = useState(null); // {pagina, x,y,w,h} em px (visual)

  useEffect(() => {
    assinaturaClienteAPI.preparar(contratoId)
      .then((d) => {
        setPaginas(d.paginas || []);
        setSignatarios((d.signatarios || []).map((s) => ({ ...s })));
      })
      .catch((e) => toast({ title: 'Erro ao preparar', description: e?.response?.data?.detail || '', variant: 'destructive' }))
      .finally(() => setCarregando(false));
  }, [contratoId]); // eslint-disable-line

  const sig = signatarios[ativo];

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
    if (!arrasto.current || !previa || previa.w < 8 || previa.h < 6 || !sig) { arrasto.current = null; return; }
    const pg = paginas[previa.pagina];
    const r = arrasto.current.el.getBoundingClientRect();
    const escX = pg.largura_pt / r.width;
    const escY = pg.altura_pt / r.height;
    const larg_pt = previa.w * escX;
    const alt_pt = previa.h * escY;
    const x_pt = previa.x * escX;
    const y_pt = pg.altura_pt - (previa.y * escY) - alt_pt; // inverte Y (origem inf-esq)
    setAncoras((a) => ({ ...a, [sig.role]: { pagina: previa.pagina, x_pt, y_pt, larg_pt, alt_pt, _px: previa } }));
    arrasto.current = null;
  };

  const enviar = async () => {
    const faltamCaixa = signatarios.filter((s) => !ancoras[s.role]);
    if (faltamCaixa.length) { toast({ title: 'Posicione a caixa de: ' + faltamCaixa.map((s) => s.nome).join(', '), variant: 'destructive' }); return; }
    const faltamFone = signatarios.filter((s) => !(s.telefone || '').replace(/\D/g, ''));
    if (faltamFone.length) { toast({ title: 'Informe o WhatsApp de: ' + faltamFone.map((s) => s.nome).join(', '), variant: 'destructive' }); return; }
    setEnviando(true);
    try {
      const body = {
        ancoras: signatarios.map((s) => ({ role: s.role, ...stripPx(ancoras[s.role]) })),
        signatarios: signatarios.map((s) => ({ role: s.role, nome: s.nome, cpf: s.cpf, telefone: s.telefone })),
      };
      const r = await assinaturaClienteAPI.posicionar(contratoId, body);
      toast({ title: 'Links enviados pelo WhatsApp', description: r.links?.map((l) => l.nome).join(' · ') });
      onClose?.();
    } catch (e) {
      toast({ title: 'Falha ao enviar', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally {
      setEnviando(false);
    }
  };

  const setFone = (i, v) => setSignatarios((ss) => ss.map((s, k) => (k === i ? { ...s, telefone: v } : s)));

  return (
    <div style={ovl} onMouseMove={onMove} onMouseUp={onUp}>
      <div style={box}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <h3 style={{ fontWeight: 700, color: '#0B6E4F' }}>📲 Assinatura do cliente — posicionar</h3>
          <button onClick={onClose} style={{ border: 'none', background: 'none', cursor: 'pointer' }}><X size={20} /></button>
        </div>

        {carregando ? (
          <div style={{ padding: 40, textAlign: 'center' }}><Loader2 className="animate-spin" /> Preparando documento…</div>
        ) : (
          <>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
              {signatarios.map((s, i) => (
                <button key={s.role} onClick={() => setAtivo(i)}
                  style={{ padding: '6px 12px', borderRadius: 8, cursor: 'pointer', fontSize: 13,
                    border: `2px solid ${CORES[i % CORES.length]}`,
                    background: i === ativo ? CORES[i % CORES.length] : '#fff',
                    color: i === ativo ? '#fff' : '#333' }}>
                  {ROLE_LABEL[s.role] || s.role}: {s.nome} {ancoras[s.role] ? '✓' : ''}
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
              {signatarios.map((s, i) => (
                <input key={s.role} value={s.telefone || ''} onChange={(e) => setFone(i, e.target.value)}
                  placeholder={`WhatsApp de ${s.nome} (DDD+número)`}
                  style={{ flex: '1 1 200px', border: '1px solid #ccc', borderRadius: 8, padding: '7px 10px', fontSize: 13 }} />
              ))}
            </div>
            <p style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
              Selecione o signatário acima e <b>arraste um retângulo</b> sobre a linha de assinatura dele no documento.
            </p>

            <div style={{ overflow: 'auto', maxHeight: '55vh', border: '1px solid #eee', borderRadius: 8 }}>
              {paginas.map((pg, idx) => (
                <div key={idx} style={{ position: 'relative', margin: '8px auto', width: 'fit-content' }}>
                  <img src={`data:image/png;base64,${pg.imagem_b64}`} alt={`Página ${idx + 1}`}
                    onMouseDown={(e) => onDown(e, idx)} draggable={false}
                    style={{ display: 'block', maxWidth: '100%', cursor: 'crosshair', userSelect: 'none' }} />
                  {signatarios.map((s, i) => {
                    const a = ancoras[s.role];
                    if (!a || a._px?.pagina !== idx) return null;
                    return <div key={s.role} style={{ position: 'absolute', border: `2px solid ${CORES[i % CORES.length]}`,
                      background: CORES[i % CORES.length] + '22', left: a._px.x, top: a._px.y, width: a._px.w, height: a._px.h,
                      pointerEvents: 'none', fontSize: 9, color: CORES[i % CORES.length] }}>{s.nome.split(' ')[0]}</div>;
                  })}
                  {previa && previa.pagina === idx && (
                    <div style={{ position: 'absolute', border: `2px dashed ${CORES[ativo % CORES.length]}`,
                      left: previa.x, top: previa.y, width: previa.w, height: previa.h, pointerEvents: 'none' }} />
                  )}
                </div>
              ))}
            </div>

            <button onClick={enviar} disabled={enviando}
              style={{ width: '100%', marginTop: 12, background: '#0B6E4F', color: '#fff', fontWeight: 700,
                border: 'none', borderRadius: 10, padding: '12px 0', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, opacity: enviando ? 0.6 : 1 }}>
              {enviando ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
              Enviar links por WhatsApp
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function stripPx(a) { if (!a) return {}; const { _px, ...rest } = a; return rest; }

const ovl = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', zIndex: 60,
  display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 };
const box = { background: '#fff', borderRadius: 14, padding: 20, width: '100%', maxWidth: 720, maxHeight: '92vh', overflow: 'auto' };
