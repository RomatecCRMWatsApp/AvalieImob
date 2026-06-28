// @page AssinarGeoUrbano — assinatura desenhada do proprietário (mobile, sem auth).
// Rota pública /assinar-geo/:token. Mostra as peças (Requerimento 2 vias + ART/TRT),
// o proprietário desenha a assinatura no celular e envia.
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { geoUrbanoPublicoAPI } from '../lib/api';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';

export default function AssinarGeoUrbano() {
  const { token } = useParams();
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState('');
  const [loading, setLoading] = useState(true);
  const [concordo, setConcordo] = useState(false);
  const [geo, setGeo] = useState({ lat: null, lng: null });
  const [enviando, setEnviando] = useState(false);
  const [okFinal, setOkFinal] = useState(null);
  const canvasRef = useRef(null);
  const desenhou = useRef(false);

  useEffect(() => {
    geoUrbanoPublicoAPI.obter(token)
      .then((d) => setDados(d))
      .catch((e) => setErro(e?.response?.data?.detail || 'Link inválido ou expirado.'))
      .finally(() => setLoading(false));
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        ({ coords }) => setGeo({ lat: coords.latitude, lng: coords.longitude }),
        () => {}, { enableHighAccuracy: false, timeout: 6000 });
    }
  }, [token]);

  const setupCanvas = useCallback(() => {
    const c = canvasRef.current;
    if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    const w = c.clientWidth, h = c.clientHeight;
    c.width = Math.round(w * dpr);
    c.height = Math.round(h * dpr);
    const ctx = c.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.lineWidth = 2.4; ctx.lineCap = 'round'; ctx.strokeStyle = '#14315c';
  }, []);
  useEffect(() => { if (dados && !dados.ja_assinado) setupCanvas(); }, [dados, setupCanvas]);

  const pos = (e) => {
    const c = canvasRef.current; const r = c.getBoundingClientRect();
    const t = e.touches ? e.touches[0] : e;
    return { x: t.clientX - r.left, y: t.clientY - r.top };
  };
  const drawing = useRef(false);
  const start = (e) => { e.preventDefault(); drawing.current = true; const ctx = canvasRef.current.getContext('2d'); const p = pos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y); };
  const move = (e) => { if (!drawing.current) return; e.preventDefault(); const ctx = canvasRef.current.getContext('2d'); const p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke(); desenhou.current = true; };
  const end = () => { drawing.current = false; };
  const limpar = () => { const c = canvasRef.current; c.getContext('2d').clearRect(0, 0, c.width, c.height); desenhou.current = false; };

  const assinar = async () => {
    if (!desenhou.current) { setErro('Desenhe sua assinatura.'); return; }
    if (!concordo) { setErro('Marque o aceite para assinar.'); return; }
    setEnviando(true); setErro('');
    try {
      const traco_base64 = canvasRef.current.toDataURL('image/png');
      const r = await geoUrbanoPublicoAPI.assinar(token, { traco_base64, concordo: true, geo_lat: geo.lat, geo_lng: geo.lng });
      setOkFinal(r.concluido ? 'todos' : 'voce');
    } catch (e) {
      setErro(e?.response?.data?.detail || 'Não foi possível registrar a assinatura.');
    } finally { setEnviando(false); }
  };

  if (loading) return <Centro><p>Carregando…</p></Centro>;
  if (erro && !dados) return <Centro><p style={{ color: '#b91c1c' }}>{erro}</p></Centro>;
  if (okFinal) return (
    <Centro>
      <div style={{ fontSize: 44 }}>✓</div>
      <h2 style={{ color: GREEN, margin: '8px 0' }}>Assinatura registrada!</h2>
      <p style={{ color: '#475569' }}>
        {okFinal === 'todos' ? 'Todos assinaram — os documentos finais serão enviados em instantes.' : 'Obrigado. Aguardando os demais signatários.'}
      </p>
    </Centro>
  );
  if (dados?.ja_assinado || dados?.concluido) return (
    <Centro><div style={{ fontSize: 40 }}>✓</div><p style={{ color: GREEN }}>Este documento já foi assinado por você.</p></Centro>
  );

  return (
    <div style={{ minHeight: '100dvh', background: '#f1f5f9', padding: 'env(safe-area-inset-top) 0 0' }}>
      <header style={{ background: GREEN, color: 'white', padding: '16px', textAlign: 'center' }}>
        <div style={{ fontWeight: 700, fontSize: 18 }}>Assinatura eletrônica</div>
        <div style={{ fontSize: 13, opacity: 0.85 }}>{dados?.nome} · {dados?.papel}</div>
      </header>
      <div style={{ padding: 14, maxWidth: 620, margin: '0 auto' }}>
        <div style={{ background: '#fffbeb', border: `1px solid ${GOLD}`, borderRadius: 10, padding: '8px 12px', fontSize: 12.5, color: '#92400e', marginBottom: 12 }}>
          Confira o documento abaixo. O <b>quadro pontilhado com a seta</b> indica onde a sua assinatura será inserida em cada peça.
        </div>
        {(dados?.documentos || []).map((d) => (
          <div key={d.doc} style={{ marginBottom: 14 }}>
            <div style={{ fontWeight: 600, color: GREEN, marginBottom: 6 }}>{d.titulo}</div>
            {(d.paginas || []).map((pg) => {
              const boxes = (d.posicoes || []).filter((b) => b.pagina === pg.pagina && pg.largura_pt && pg.altura_pt);
              return (
                <div key={pg.pagina} style={{ position: 'relative', marginBottom: 6 }}>
                  <img src={`data:image/png;base64,${pg.imagem_b64}`} alt={`pág ${pg.pagina + 1}`}
                    style={{ width: '100%', display: 'block', border: '1px solid #e2e8f0', borderRadius: 8 }} />
                  {boxes.map((b, i) => {
                    const st = {
                      position: 'absolute',
                      left: `${(b.x_pt / pg.largura_pt) * 100}%`,
                      top: `${((pg.altura_pt - b.y_pt - b.alt_pt) / pg.altura_pt) * 100}%`,
                      width: `${(b.larg_pt / pg.largura_pt) * 100}%`,
                      height: `${(b.alt_pt / pg.altura_pt) * 100}%`,
                      border: `2px dashed ${GOLD}`, borderRadius: 6, background: 'rgba(201,168,76,.12)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    };
                    return (
                      <div key={i} style={st}>
                        <span style={{ position: 'absolute', top: -22, left: 0, background: GOLD, color: '#3a2e00', fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 5, whiteSpace: 'nowrap' }}>
                          ➜ sua assinatura aqui
                        </span>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        ))}

        <div style={{ background: 'white', borderRadius: 12, padding: 14, boxShadow: '0 1px 3px rgba(0,0,0,.08)' }}>
          <div style={{ fontWeight: 600, color: GREEN, marginBottom: 6 }}>Desenhe sua assinatura ✍️</div>
          <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6 }}>Assine grande, ocupando todo o quadro — sua firma será aplicada nas peças no tamanho da caixa indicada.</div>
          <canvas ref={canvasRef}
            style={{ width: '100%', height: 260, border: `2px dashed ${GOLD}`, borderRadius: 10, touchAction: 'none', background: '#fff' }}
            onMouseDown={start} onMouseMove={move} onMouseUp={end} onMouseLeave={end}
            onTouchStart={start} onTouchMove={move} onTouchEnd={end} />
          <button onClick={limpar} style={{ marginTop: 6, fontSize: 13, color: '#64748b', background: 'none', border: 'none' }}>Limpar</button>

          <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', margin: '10px 0', fontSize: 13, color: '#334155' }}>
            <input type="checkbox" checked={concordo} onChange={(e) => setConcordo(e.target.checked)} style={{ width: 20, height: 20, accentColor: GREEN }} />
            <span>Li e concordo em assinar eletronicamente os documentos acima (MP 2.200-2/2001 · Lei 14.063/2020).</span>
          </label>
          {erro && <p style={{ color: '#b91c1c', fontSize: 13 }}>{erro}</p>}
          <button onClick={assinar} disabled={enviando}
            style={{ width: '100%', minHeight: 50, background: GREEN, color: 'white', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: 16 }}>
            {enviando ? 'Enviando…' : 'ASSINAR'}
          </button>
        </div>
      </div>
    </div>
  );
}

function Centro({ children }) {
  return <div style={{ minHeight: '100dvh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: 24 }}>{children}</div>;
}
