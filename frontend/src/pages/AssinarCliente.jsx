// Página pública de assinatura DESENHADA do cliente (link enviado por WhatsApp).
// Rota: /assinar-cliente/:token (fora do guard de auth). Tema verde/dourado.
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { assinaturaClienteAPI } from '../lib/api';

const VERDE = '#0B6E4F';
const DOURADO = '#B8860B';

const ROLE_LABEL = { contratante: 'Contratante', conjuge_anuente: 'Cônjuge anuente', outorgante: 'Outorgante' };

export default function AssinarCliente() {
  const { token } = useParams();
  const [estado, setEstado] = useState('carregando'); // carregando|pronto|enviando|sucesso|jaassinado|erro
  const [info, setInfo] = useState(null);
  const [erro, setErro] = useState('');
  const [concordo, setConcordo] = useState(false);
  const [temTraco, setTemTraco] = useState(false);
  const [geo, setGeo] = useState({ lat: null, lng: null });
  const canvasRef = useRef(null);
  const desenhando = useRef(false);

  useEffect(() => {
    assinaturaClienteAPI.obter(token)
      .then((d) => {
        setInfo(d);
        if (d.ja_assinado) setEstado('jaassinado');
        else setEstado('pronto');
      })
      .catch((e) => {
        setErro(e?.response?.data?.detail || 'Link inválido ou expirado');
        setEstado('erro');
      });
  }, [token]);

  useEffect(() => {
    if (estado !== 'pronto') return;
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        ({ coords }) => setGeo({ lat: coords.latitude, lng: coords.longitude }),
        () => {}, { enableHighAccuracy: false, timeout: 6000 },
      );
    }
  }, [estado]);

  const pos = (e) => {
    const c = canvasRef.current;
    const r = c.getBoundingClientRect();
    const t = e.touches ? e.touches[0] : e;
    return { x: (t.clientX - r.left) * (c.width / r.width), y: (t.clientY - r.top) * (c.height / r.height) };
  };

  const start = (e) => {
    e.preventDefault();
    desenhando.current = true;
    const ctx = canvasRef.current.getContext('2d');
    const p = pos(e);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
  };
  const move = (e) => {
    if (!desenhando.current) return;
    e.preventDefault();
    const ctx = canvasRef.current.getContext('2d');
    const p = pos(e);
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#14315c';
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    setTemTraco(true);
  };
  const end = () => { desenhando.current = false; };

  const limpar = useCallback(() => {
    const c = canvasRef.current;
    c.getContext('2d').clearRect(0, 0, c.width, c.height);
    setTemTraco(false);
  }, []);

  const enviar = async () => {
    if (!temTraco) { setErro('Desenhe sua assinatura antes de continuar.'); return; }
    if (!concordo) { setErro('Marque a concordância para assinar.'); return; }
    setErro('');
    setEstado('enviando');
    try {
      const traco_base64 = canvasRef.current.toDataURL('image/png');
      const r = await assinaturaClienteAPI.assinar(token, {
        traco_base64, concordo: true, geo_lat: geo.lat, geo_lng: geo.lng,
      });
      setEstado(r.ja_assinado ? 'jaassinado' : 'sucesso');
    } catch (e) {
      setErro(e?.response?.data?.detail || 'Falha ao registrar a assinatura.');
      setEstado('pronto');
    }
  };

  const wrap = { minHeight: '100vh', background: '#0d1f17', color: '#eee', fontFamily: 'system-ui, sans-serif',
    display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 };
  const card = { width: '100%', maxWidth: 540, background: '#13261d', border: `1px solid ${VERDE}`,
    borderRadius: 16, padding: 24, boxShadow: '0 10px 40px rgba(0,0,0,.4)' };

  if (estado === 'carregando') return <div style={wrap}><div style={card}>Carregando…</div></div>;
  if (estado === 'erro') return <div style={wrap}><div style={{ ...card, textAlign: 'center' }}>
    <h2 style={{ color: DOURADO }}>Link indisponível</h2><p>{erro}</p></div></div>;
  if (estado === 'jaassinado') return <div style={wrap}><div style={{ ...card, textAlign: 'center' }}>
    <div style={{ fontSize: 44 }}>✔</div><h2 style={{ color: DOURADO }}>Assinatura já registrada</h2>
    <p>Obrigado, {info?.nome}. Sua assinatura já consta neste documento.</p></div></div>;
  if (estado === 'sucesso') return <div style={wrap}><div style={{ ...card, textAlign: 'center' }}>
    <div style={{ fontSize: 44 }}>✔</div><h2 style={{ color: DOURADO }}>Assinado com sucesso!</h2>
    <p>Obrigado, {info?.nome}. O documento final será enviado a você pelo WhatsApp assim que todas as partes assinarem.</p>
    <p style={{ fontSize: 12, color: '#9bbfae', marginTop: 12 }}>Assinatura eletrônica · Lei nº 14.063/2020</p></div></div>;

  return (
    <div style={wrap}>
      <div style={card}>
        <div style={{ fontFamily: 'Georgia, serif', fontSize: 22, color: '#fff', fontWeight: 700 }}>
          Romatec <span style={{ color: DOURADO }}>Consultoria Total</span>
        </div>
        <p style={{ marginTop: 8 }}>Olá, <b>{info?.nome}</b> — assinatura como <b style={{ color: DOURADO }}>{ROLE_LABEL[info?.role] || info?.role}</b>.</p>
        <p style={{ fontSize: 13, color: '#9bbfae' }}>Desenhe sua assinatura no quadro abaixo (dedo ou mouse).</p>

        <div style={{ background: '#fff', borderRadius: 10, marginTop: 12, border: `1px dashed ${DOURADO}` }}>
          <canvas
            ref={canvasRef} width={500} height={200}
            style={{ width: '100%', height: 200, touchAction: 'none', borderRadius: 10 }}
            onMouseDown={start} onMouseMove={move} onMouseUp={end} onMouseLeave={end}
            onTouchStart={start} onTouchMove={move} onTouchEnd={end}
          />
        </div>
        <button onClick={limpar} style={{ marginTop: 8, background: 'none', border: `1px solid ${DOURADO}`,
          color: DOURADO, borderRadius: 8, padding: '6px 14px', cursor: 'pointer' }}>Limpar</button>

        <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginTop: 16, fontSize: 13 }}>
          <input type="checkbox" checked={concordo} onChange={(e) => setConcordo(e.target.checked)} style={{ marginTop: 3 }} />
          <span>Declaro que li e concordo em assinar eletronicamente este documento (Lei nº 14.063/2020). Autorizo o registro de data/hora, IP e localização como evidência de autoria.</span>
        </label>

        {erro && <p style={{ color: '#ff9b9b', fontSize: 13, marginTop: 10 }}>{erro}</p>}

        <button onClick={enviar} disabled={estado === 'enviando'}
          style={{ width: '100%', marginTop: 16, background: DOURADO, color: '#1a1a1a', fontWeight: 700,
            border: 'none', borderRadius: 10, padding: '13px 0', cursor: 'pointer', fontSize: 15,
            opacity: estado === 'enviando' ? 0.6 : 1 }}>
          {estado === 'enviando' ? 'Registrando…' : 'ASSINAR'}
        </button>
        <p style={{ fontSize: 11, color: '#7fa593', textAlign: 'center', marginTop: 12 }}>
          Link pessoal e intransferível · {geo.lat ? 'localização capturada' : 'sem localização'}
        </p>
      </div>
    </div>
  );
}
