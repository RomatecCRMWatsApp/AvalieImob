// @page AssinarTestemunha — assinatura DESENHADA da testemunha (mobile, sem auth).
// Rota pública /assinar/testemunha/:token. Mostra o documento FINAL (já assinado pelas
// partes) + o quadro/seta na posição, a testemunha lê e desenha a assinatura no celular.
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { testemunhaPublicoAPI } from '../lib/api';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';

export default function AssinarTestemunha() {
  const { token } = useParams();
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState('');
  const [loading, setLoading] = useState(true);
  const [concordo, setConcordo] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [ok, setOk] = useState(false);
  const canvasRef = useRef(null);
  const desenhou = useRef(false);
  const drawing = useRef(false);
  const [docTipo, setDocTipo] = useState('CNH');
  const [frente, setFrente] = useState('');
  const [verso, setVerso] = useState('');

  useEffect(() => {
    testemunhaPublicoAPI.obter(token)
      .then((d) => setDados(d))
      .catch((e) => setErro(e?.response?.data?.detail || 'Link inválido ou expirado.'))
      .finally(() => setLoading(false));
  }, [token]);

  const setupCanvas = useCallback(() => {
    const c = canvasRef.current;
    if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    c.width = Math.round(c.clientWidth * dpr);
    c.height = Math.round(c.clientHeight * dpr);
    const ctx = c.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.lineWidth = 2.6; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = '#14315c';
  }, []);
  useEffect(() => { if (dados && !dados.ja_assinado) setupCanvas(); }, [dados, setupCanvas]);

  const pos = (e) => {
    const c = canvasRef.current; const r = c.getBoundingClientRect();
    const t = e.touches ? e.touches[0] : e;
    return { x: t.clientX - r.left, y: t.clientY - r.top };
  };
  const start = (e) => { e.preventDefault(); drawing.current = true; const ctx = canvasRef.current.getContext('2d'); const p = pos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y); };
  const move = (e) => { if (!drawing.current) return; e.preventDefault(); const ctx = canvasRef.current.getContext('2d'); const p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke(); desenhou.current = true; };
  const end = () => { drawing.current = false; };
  const limpar = () => { const c = canvasRef.current; c.getContext('2d').clearRect(0, 0, c.width, c.height); desenhou.current = false; };

  const lerImagem = (file) => new Promise((res, rej) => {
    const fr = new FileReader();
    fr.onload = () => {
      const img = new Image();
      img.onload = () => {
        const max = 1600; let w = img.width, h = img.height;
        if (w > max || h > max) { const s = Math.min(max / w, max / h); w = Math.round(w * s); h = Math.round(h * s); }
        const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
        cv.getContext('2d').drawImage(img, 0, 0, w, h);
        res(cv.toDataURL('image/jpeg', 0.82));
      };
      img.onerror = rej; img.src = fr.result;
    };
    fr.onerror = rej; fr.readAsDataURL(file);
  });
  const pick = (set) => async (e) => { const f = e.target.files?.[0]; if (f) { try { set(await lerImagem(f)); } catch { set(''); } } };

  const docEnviado = dados?.documento_enviado;
  const assinar = async () => {
    if (!docEnviado && !frente) { setErro('Envie a frente do seu documento (CNH ou RG).'); return; }
    if (!desenhou.current) { setErro('Desenhe sua assinatura.'); return; }
    if (!concordo) { setErro('Marque o aceite para assinar.'); return; }
    setEnviando(true); setErro('');
    try {
      if (!docEnviado && frente) {
        await testemunhaPublicoAPI.enviarDocumento(token, { tipo: docTipo, frente_base64: frente, verso_base64: verso });
      }
      const assinatura_base64 = canvasRef.current.toDataURL('image/png');
      await testemunhaPublicoAPI.assinar(token, { assinatura_base64, concordo: true });
      setOk(true);
    } catch (e) {
      setErro(e?.response?.data?.detail || 'Não foi possível registrar a assinatura.');
    } finally { setEnviando(false); }
  };

  if (loading) return <Centro><p>Carregando…</p></Centro>;
  if (erro && !dados) return <Centro><p style={{ color: '#b91c1c' }}>{erro}</p></Centro>;
  if (ok) return (
    <Centro>
      <div style={{ fontSize: 44 }}>✓</div>
      <h2 style={{ color: GREEN, margin: '8px 0' }}>Assinatura registrada!</h2>
      <p style={{ color: '#475569' }}>Obrigado. Sua assinatura como testemunha foi registrada e autenticada via WhatsApp.</p>
    </Centro>
  );
  if (dados?.ja_assinado) return (
    <Centro><div style={{ fontSize: 40 }}>✓</div><p style={{ color: GREEN }}>Você já assinou este documento.</p></Centro>
  );

  const tw = dados?.testemunha || {};
  const vinc = tw.parte_vinculada_nome ? `${tw.vinculo || ''} (${tw.parte_vinculada_nome})` : (tw.vinculo || '');
  return (
    <div style={{ minHeight: '100dvh', background: '#f1f5f9', padding: 'env(safe-area-inset-top) 0 0' }}>
      <header style={{ background: GREEN, color: 'white', padding: '16px', textAlign: 'center' }}>
        <div style={{ fontWeight: 700, fontSize: 18 }}>Assinatura de Testemunha</div>
        <div style={{ fontSize: 13, opacity: 0.9 }}>{tw.nome}{vinc ? ` · Testemunha de ${vinc}` : ''}</div>
      </header>
      <div style={{ padding: 14, maxWidth: 620, margin: '0 auto' }}>
        <div style={{ background: '#fffbeb', border: `1px solid ${GOLD}`, borderRadius: 10, padding: '8px 12px', fontSize: 12.5, color: '#92400e', marginBottom: 12 }}>
          Documento "{dados?.documento?.titulo}". Confira abaixo — o <b>quadro com a seta</b> indica onde a sua assinatura entra.
        </div>
        {(dados?.paginas || []).map((pg) => {
          const boxes = (dados.posicoes || []).filter((b) => b.pagina === pg.pagina && pg.largura_pt && pg.altura_pt);
          return (
            <div key={pg.pagina} style={{ position: 'relative', marginBottom: 6 }}>
              <img src={`data:image/png;base64,${pg.imagem_b64}`} alt={`pág ${pg.pagina + 1}`}
                style={{ width: '100%', display: 'block', border: '1px solid #e2e8f0', borderRadius: 8 }} />
              {boxes.map((b, i) => (
                <div key={i} style={{
                  position: 'absolute',
                  left: `${(b.x_pt / pg.largura_pt) * 100}%`,
                  top: `${((pg.altura_pt - b.y_pt - b.alt_pt) / pg.altura_pt) * 100}%`,
                  width: `${(b.larg_pt / pg.largura_pt) * 100}%`,
                  height: `${(b.alt_pt / pg.altura_pt) * 100}%`,
                  border: `2px dashed ${GOLD}`, borderRadius: 6, background: 'rgba(201,168,76,.12)',
                }}>
                  <span style={{ position: 'absolute', top: -20, left: 0, background: GOLD, color: '#3a2e00', fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 5, whiteSpace: 'nowrap' }}>➜ sua assinatura aqui</span>
                </div>
              ))}
            </div>
          );
        })}

        <div style={{ background: 'white', borderRadius: 12, padding: 14, boxShadow: '0 1px 3px rgba(0,0,0,.08)', marginTop: 8 }}>
          <div style={{ fontWeight: 600, color: GREEN, marginBottom: 6 }}>Documento de identidade (CNH ou RG)</div>
          {docEnviado ? (
            <p style={{ color: '#15803d', fontSize: 13, margin: 0 }}>✓ Documento já enviado — seguirá anexado.</p>
          ) : (
            <>
              <p style={{ fontSize: 12.5, color: '#64748b', margin: '0 0 8px' }}>Anexe a foto do seu documento. Ela vai junto ao contrato para identificação.</p>
              <select value={docTipo} onChange={(e) => setDocTipo(e.target.value)}
                style={{ width: '100%', padding: '9px', borderRadius: 8, border: '1px solid #cbd5e1', marginBottom: 8 }}>
                <option value="CNH">CNH</option><option value="RG">RG</option><option value="OUTRO">Outro documento</option>
              </select>
              <div style={{ display: 'flex', gap: 8 }}>
                {[['Frente', frente, pick(setFrente)], ['Verso (opcional)', verso, pick(setVerso)]].map(([lbl, val, on]) => (
                  <label key={lbl} style={{ flex: 1, border: `2px dashed ${val ? '#15803d' : GOLD}`, borderRadius: 10, padding: 8, textAlign: 'center', cursor: 'pointer', background: '#fafafa' }}>
                    {val ? <img src={val} alt={lbl} style={{ width: '100%', borderRadius: 6, maxHeight: 110, objectFit: 'cover' }} />
                      : <span style={{ fontSize: 12.5, color: '#64748b' }}>📷 {lbl}</span>}
                    <input type="file" accept="image/*" capture="environment" onChange={on} style={{ display: 'none' }} />
                  </label>
                ))}
              </div>
            </>
          )}
        </div>

        <div style={{ background: 'white', borderRadius: 12, padding: 14, boxShadow: '0 1px 3px rgba(0,0,0,.08)', marginTop: 8 }}>
          <div style={{ fontWeight: 600, color: GREEN, marginBottom: 6 }}>Desenhe sua assinatura ✍️</div>
          <canvas ref={canvasRef}
            style={{ width: '100%', height: 240, border: `2px dashed ${GOLD}`, borderRadius: 10, touchAction: 'none', background: '#fff' }}
            onMouseDown={start} onMouseMove={move} onMouseUp={end} onMouseLeave={end}
            onTouchStart={start} onTouchMove={move} onTouchEnd={end} />
          <button onClick={limpar} style={{ marginTop: 6, fontSize: 13, color: '#64748b', background: 'none', border: 'none' }}>Limpar</button>

          <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', margin: '10px 0', fontSize: 13, color: '#334155' }}>
            <input type="checkbox" checked={concordo} onChange={(e) => setConcordo(e.target.checked)} style={{ width: 20, height: 20, accentColor: GREEN }} />
            <span>Declaro, como testemunha, que li e concordo em assinar eletronicamente este documento (MP 2.200-2/2001 · Lei 14.063/2020).</span>
          </label>
          {erro && <p style={{ color: '#b91c1c', fontSize: 13 }}>{erro}</p>}
          <button onClick={assinar} disabled={enviando}
            style={{ width: '100%', minHeight: 50, background: GREEN, color: 'white', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: 16 }}>
            {enviando ? 'Enviando…' : 'ASSINAR COMO TESTEMUNHA'}
          </button>
        </div>
      </div>
    </div>
  );
}

function Centro({ children }) {
  return <div style={{ minHeight: '100dvh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: 24 }}>{children}</div>;
}
