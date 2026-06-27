// Página pública de assinatura DESENHADA do doc-ext (link enviado por WhatsApp).
// Rota: /assinar-doc/:token (fora do guard). MOBILE-FIRST (canvas responsivo com dpr).
// Clona AssinarCliente.jsx, apontando para documentosExternosPublicoAPI (papel/título livres).
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { documentosExternosPublicoAPI } from '../lib/api';

const VERDE = '#0B6E4F';
const DOURADO = '#B8860B';

export default function AssinarDocExt() {
  const { token } = useParams();
  const [estado, setEstado] = useState('carregando'); // carregando|pronto|enviando|sucesso|jaassinado|erro
  const [info, setInfo] = useState(null);
  const [erro, setErro] = useState('');
  const [concordo, setConcordo] = useState(false);
  const [temTraco, setTemTraco] = useState(false);
  const [geo, setGeo] = useState({ lat: null, lng: null });
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const desenhando = useRef(false);

  useEffect(() => {
    documentosExternosPublicoAPI.obter(token)
      .then((d) => { setInfo(d); setEstado(d.ja_assinado ? 'jaassinado' : 'pronto'); })
      .catch((e) => { setErro(e?.response?.data?.detail || 'Link inválido ou expirado'); setEstado('erro'); });
  }, [token]);

  const setupCanvas = useCallback(() => {
    const c = canvasRef.current, wrap = wrapRef.current;
    if (!c || !wrap) return;
    const dpr = window.devicePixelRatio || 1;
    const w = wrap.clientWidth;
    const h = Math.max(190, Math.min(300, Math.round(window.innerHeight * 0.34)));
    c.style.width = w + 'px';
    c.style.height = h + 'px';
    c.width = Math.round(w * dpr);
    c.height = Math.round(h * dpr);
    const ctx = c.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.lineWidth = 2.8; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = '#14315c';
    setTemTraco(false);
  }, []);

  useEffect(() => {
    if (estado !== 'pronto') return;
    setupCanvas();
    window.addEventListener('resize', setupCanvas);
    window.addEventListener('orientationchange', setupCanvas);
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        ({ coords }) => setGeo({ lat: coords.latitude, lng: coords.longitude }),
        () => {}, { enableHighAccuracy: false, timeout: 6000 });
    }
    return () => {
      window.removeEventListener('resize', setupCanvas);
      window.removeEventListener('orientationchange', setupCanvas);
    };
  }, [estado, setupCanvas]);

  const pos = (e) => {
    const c = canvasRef.current; const r = c.getBoundingClientRect();
    const t = e.touches && e.touches[0] ? e.touches[0] : e;
    return { x: t.clientX - r.left, y: t.clientY - r.top };
  };
  const start = (e) => { e.preventDefault(); desenhando.current = true; const ctx = canvasRef.current.getContext('2d'); const p = pos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y); };
  const move = (e) => {
    if (!desenhando.current) return; e.preventDefault();
    const ctx = canvasRef.current.getContext('2d'); const p = pos(e);
    ctx.lineTo(p.x, p.y); ctx.stroke(); setTemTraco(true);
  };
  const end = () => { desenhando.current = false; };

  const limpar = useCallback(() => {
    const c = canvasRef.current; const ctx = c.getContext('2d');
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, c.width, c.height); ctx.restore();
    setTemTraco(false);
  }, []);

  const enviar = async () => {
    if (!temTraco) { setErro('Desenhe sua assinatura antes de continuar.'); return; }
    if (!concordo) { setErro('Marque a concordância para assinar.'); return; }
    setErro(''); setEstado('enviando');
    try {
      const traco_base64 = canvasRef.current.toDataURL('image/png');
      const r = await documentosExternosPublicoAPI.assinar(token, { traco_base64, concordo: true, geo_lat: geo.lat, geo_lng: geo.lng });
      setEstado(r.ja_assinado ? 'jaassinado' : 'sucesso');
    } catch (e) {
      setErro(e?.response?.data?.detail || 'Falha ao registrar a assinatura.'); setEstado('pronto');
    }
  };

  const page = { minHeight: '100dvh', background: '#0d1f17', color: '#eee',
    fontFamily: 'system-ui, -apple-system, sans-serif', display: 'flex', flexDirection: 'column' };
  const inner = { flex: 1, width: '100%', maxWidth: 560, margin: '0 auto', padding: '18px 16px calc(18px + env(safe-area-inset-bottom))', boxSizing: 'border-box' };
  const msgCard = { ...inner, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', gap: 8 };

  if (estado === 'carregando') return <div style={page}><div style={msgCard}>Carregando…</div></div>;
  if (estado === 'erro') return <div style={page}><div style={msgCard}>
    <div style={{ fontSize: 40 }}>⚠️</div><h2 style={{ color: DOURADO, margin: 0 }}>Link indisponível</h2><p>{erro}</p></div></div>;
  if (estado === 'jaassinado') return <div style={page}><div style={msgCard}>
    <div style={{ fontSize: 52 }}>✔</div><h2 style={{ color: DOURADO, margin: 0 }}>Assinatura já registrada</h2>
    <p>Obrigado, {info?.nome}. Sua assinatura já consta neste documento.</p></div></div>;
  if (estado === 'sucesso') return <div style={page}><div style={msgCard}>
    <div style={{ fontSize: 52 }}>✔</div><h2 style={{ color: DOURADO, margin: 0 }}>Assinado com sucesso!</h2>
    <p>Obrigado, {info?.nome}. O documento final será enviado a você pelo WhatsApp assim que todas as partes assinarem.</p>
    <p style={{ fontSize: 12, color: '#9bbfae' }}>Assinatura eletrônica · Lei nº 14.063/2020</p></div></div>;

  const podeAssinar = temTraco && concordo && estado !== 'enviando';
  return (
    <div style={page}>
      <div style={inner}>
        <div style={{ fontFamily: 'Georgia, serif', fontSize: 21, color: '#fff', fontWeight: 700, lineHeight: 1.15 }}>
          Romatec <span style={{ color: DOURADO }}>Consultoria Total</span>
        </div>
        {info?.titulo && <p style={{ marginTop: 8, fontSize: 13, color: '#9bbfae' }}>📄 {info.titulo}</p>}
        <p style={{ marginTop: 10, fontSize: 15 }}>Olá, <b>{info?.nome}</b>.</p>
        <p style={{ margin: '2px 0', fontSize: 14 }}>Você assina como <b style={{ color: DOURADO }}>{info?.papel}</b>.</p>
        <p style={{ fontSize: 13, color: '#9bbfae', marginTop: 6 }}>Desenhe sua assinatura no quadro abaixo com o dedo.</p>

        <div ref={wrapRef} style={{ background: '#fff', borderRadius: 12, marginTop: 12, border: `2px dashed ${DOURADO}`, position: 'relative', overflow: 'hidden' }}>
          {!temTraco && <span style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#bbb', fontSize: 14, pointerEvents: 'none' }}>assine aqui ✍️</span>}
          <canvas ref={canvasRef}
            style={{ display: 'block', width: '100%', touchAction: 'none' }}
            onMouseDown={start} onMouseMove={move} onMouseUp={end} onMouseLeave={end}
            onTouchStart={start} onTouchMove={move} onTouchEnd={end} />
        </div>
        <button onClick={limpar} style={{ marginTop: 10, background: 'none', border: `1px solid ${DOURADO}`, color: DOURADO,
          borderRadius: 10, padding: '10px 18px', cursor: 'pointer', fontSize: 14, minHeight: 44 }}>Limpar</button>

        <label style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginTop: 16, fontSize: 13.5, lineHeight: 1.4 }}>
          <input type="checkbox" checked={concordo} onChange={(e) => setConcordo(e.target.checked)}
            style={{ width: 22, height: 22, marginTop: 1, flexShrink: 0, accentColor: VERDE }} />
          <span>Declaro que li e concordo em assinar eletronicamente este documento (Lei nº 14.063/2020). Autorizo o registro de data/hora, IP e localização como evidência de autoria.</span>
        </label>

        {erro && <p style={{ color: '#ff9b9b', fontSize: 13.5, marginTop: 12 }}>{erro}</p>}

        <button onClick={enviar} disabled={!podeAssinar}
          style={{ width: '100%', marginTop: 18, background: podeAssinar ? DOURADO : '#3a4a42', color: podeAssinar ? '#1a1a1a' : '#8aa195',
            fontWeight: 800, border: 'none', borderRadius: 12, padding: '16px 0', cursor: podeAssinar ? 'pointer' : 'not-allowed',
            fontSize: 16, minHeight: 54, letterSpacing: 0.3 }}>
          {estado === 'enviando' ? 'Registrando…' : 'ASSINAR'}
        </button>
        <p style={{ fontSize: 11, color: '#7fa593', textAlign: 'center', marginTop: 12 }}>
          Link pessoal e intransferível · {geo.lat ? 'localização capturada' : 'sem localização'}
        </p>
      </div>
    </div>
  );
}
