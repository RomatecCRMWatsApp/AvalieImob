// Página pública de assinatura do doc-ext (link enviado por WhatsApp).
// Rota: /assinar-doc/:token (fora do guard). MOBILE-FIRST. O cliente lê o próprio
// documento no link (sem minuta separada) e assina em DUAS opções, como no Geo Urbano:
// DIGITAR (nome + CPF + fonte manuscrita) ou DESENHAR (traço no canvas). O backend
// renderiza a digitada em PNG e reusa o mesmo carimbo/posição da desenhada.
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { documentosExternosPublicoAPI } from '../lib/api';

const VERDE = '#0B6E4F';
const DOURADO = '#B8860B';
const FONTES_FALLBACK = [
  { id: 'DancingScript', label: 'Dancing Script' }, { id: 'GreatVibes', label: 'Great Vibes' },
  { id: 'Sacramento', label: 'Sacramento' }, { id: 'Allura', label: 'Allura' },
  { id: 'HomemadeApple', label: 'Homemade Apple' }, { id: 'Pacifico', label: 'Pacifico' },
];
// @font-face em runtime (TTF em /public/fonts/assinatura; não passa pelo css-loader do CRA).
const FONT_FACE_CSS = FONTES_FALLBACK.map((f) =>
  `@font-face{font-family:'${f.id}';src:url('/fonts/assinatura/${f.id}-Regular.ttf') format('truetype');font-display:swap;}`
).join('');

const limparCpf = (v) => (v || '').replace(/\D/g, '').slice(0, 11);
const mascaraCpf = (v) => limparCpf(v).replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
function validarCpf(cpf) {
  cpf = limparCpf(cpf);
  if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;
  const dig = (parc, pesoIni) => { let s = 0; for (let i = 0; i < parc.length; i++) s += +parc[i] * (pesoIni - i); const r = (s * 10) % 11; return r === 10 ? 0 : r; };
  return dig(cpf.slice(0, 9), 10) === +cpf[9] && dig(cpf.slice(0, 10), 11) === +cpf[10];
}

export default function AssinarDocExt() {
  const { token } = useParams();
  const [estado, setEstado] = useState('carregando'); // carregando|pronto|enviando|sucesso|jaassinado|erro
  const [info, setInfo] = useState(null);
  const [erro, setErro] = useState('');
  const [concordo, setConcordo] = useState(false);
  const [modo, setModo] = useState('digitada'); // 'digitada' | 'desenhada'
  const [nome, setNome] = useState('');
  const [cpf, setCpf] = useState('');
  const [fonte, setFonte] = useState('DancingScript');
  const [temTraco, setTemTraco] = useState(false);
  const [geo, setGeo] = useState({ lat: null, lng: null });
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const desenhando = useRef(false);

  useEffect(() => {
    documentosExternosPublicoAPI.obter(token)
      .then((d) => { setInfo(d); setNome(d?.nome || ''); setEstado(d.ja_assinado ? 'jaassinado' : 'pronto'); })
      .catch((e) => { setErro(e?.response?.data?.detail || 'Link inválido ou expirado'); setEstado('erro'); });
  }, [token]);

  // geolocalização uma vez, ao ficar pronto
  useEffect(() => {
    if (estado !== 'pronto' || !navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => setGeo({ lat: coords.latitude, lng: coords.longitude }),
      () => {}, { enableHighAccuracy: false, timeout: 6000 });
  }, [estado]);

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
    if (estado !== 'pronto' || modo !== 'desenhada') return;
    setTimeout(setupCanvas, 0);
    window.addEventListener('resize', setupCanvas);
    window.addEventListener('orientationchange', setupCanvas);
    return () => {
      window.removeEventListener('resize', setupCanvas);
      window.removeEventListener('orientationchange', setupCanvas);
    };
  }, [estado, modo, setupCanvas]);

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

  const cpfOk = validarCpf(cpf);
  const fontes = info?.fontes?.length ? info.fontes : FONTES_FALLBACK;

  const enviar = async () => {
    if (nome.trim().length < 3) { setErro('Informe seu nome completo.'); return; }
    if (!cpfOk) { setErro('CPF inválido.'); return; }
    if (!concordo) { setErro('Marque a concordância para assinar.'); return; }
    if (modo === 'desenhada' && !temTraco) { setErro('Desenhe sua assinatura antes de continuar.'); return; }
    if (modo === 'digitada' && !fonte) { setErro('Escolha um estilo de assinatura.'); return; }
    setErro(''); setEstado('enviando');
    try {
      const base = { concordo: true, geo_lat: geo.lat, geo_lng: geo.lng, nome_assinante: nome.trim(), cpf_assinante: limparCpf(cpf) };
      const payload = modo === 'digitada'
        ? { ...base, tipo_assinatura: 'digitada', fonte_assinatura: fonte }
        : { ...base, tipo_assinatura: 'desenhada', traco_base64: canvasRef.current.toDataURL('image/png') };
      const r = await documentosExternosPublicoAPI.assinar(token, payload);
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

  const inpSt = { width: '100%', padding: '11px 12px', border: '1px solid #cbd5e1', borderRadius: 10, fontSize: 15, boxSizing: 'border-box', background: '#fff', color: '#111' };
  const tabSt = (on) => ({ flex: 1, padding: '12px', fontSize: 14, fontWeight: 700, border: 'none', cursor: 'pointer', background: on ? DOURADO : '#122a20', color: on ? '#1a1a1a' : '#cfe3d8' });
  const podeAssinar = nome.trim().length >= 3 && cpfOk && concordo && (modo === 'digitada' ? !!fonte : temTraco) && estado !== 'enviando';

  return (
    <div style={page}>
      <style>{FONT_FACE_CSS}</style>
      <div style={inner}>
        <div style={{ fontFamily: 'Georgia, serif', fontSize: 21, color: '#fff', fontWeight: 700, lineHeight: 1.15 }}>
          Romatec <span style={{ color: DOURADO }}>Consultoria Total</span>
        </div>
        {info?.titulo && <p style={{ marginTop: 8, fontSize: 13, color: '#9bbfae' }}>📄 {info.titulo}</p>}
        <p style={{ marginTop: 10, fontSize: 15 }}>Olá, <b>{info?.nome}</b>.</p>
        <p style={{ margin: '2px 0', fontSize: 14 }}>Você assina como <b style={{ color: DOURADO }}>{info?.papel}</b>.</p>
        {(info?.documentos || []).length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 13, color: '#cfe3d8', marginBottom: 6 }}>
              Leia o documento abaixo. O <b style={{ color: DOURADO }}>quadro com a seta</b> mostra onde a sua assinatura será inserida.
            </div>
            {info.documentos.map((d) => (
              <div key={d.tipo} style={{ marginBottom: 12 }}>
                {(d.paginas || []).map((pg) => {
                  const boxes = (d.posicoes || []).filter((b) => b.pagina === pg.pagina && pg.largura_pt && pg.altura_pt);
                  const LBL = { assinatura: '➜ sua assinatura', rubrica: '➜ rubrica', data: '➜ data', nome_extenso: '➜ nome' };
                  return (
                    <div key={pg.pagina} style={{ position: 'relative', marginBottom: 6, borderRadius: 8, overflow: 'hidden', border: '1px solid #1c3a2c' }}>
                      <img src={`data:image/png;base64,${pg.imagem_b64}`} alt={`pág ${pg.pagina + 1}`} style={{ width: '100%', display: 'block' }} />
                      {boxes.map((b, i) => (
                        <div key={i} style={{
                          position: 'absolute',
                          left: `${(b.x_pt / pg.largura_pt) * 100}%`,
                          top: `${((pg.altura_pt - b.y_pt - b.alt_pt) / pg.altura_pt) * 100}%`,
                          width: `${(b.larg_pt / pg.largura_pt) * 100}%`,
                          height: `${(b.alt_pt / pg.altura_pt) * 100}%`,
                          border: `2px dashed ${DOURADO}`, borderRadius: 6, background: 'rgba(184,134,11,.18)',
                        }}>
                          <span style={{ position: 'absolute', top: -20, left: 0, background: DOURADO, color: '#1a1a1a', fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 5, whiteSpace: 'nowrap' }}>{LBL[b.tipo] || '➜ aqui'}</span>
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        )}

        {/* Dados do assinante — valem para as duas modalidades */}
        <div style={{ marginTop: 14 }}>
          <label style={{ fontSize: 13, color: '#cfe3d8', fontWeight: 600 }}>Nome completo</label>
          <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Seu nome completo" style={{ ...inpSt, marginTop: 4, marginBottom: 10 }} />
          <label style={{ fontSize: 13, color: '#cfe3d8', fontWeight: 600 }}>CPF</label>
          <input value={mascaraCpf(cpf)} onChange={(e) => setCpf(e.target.value)} inputMode="numeric" placeholder="000.000.000-00"
            style={{ ...inpSt, marginTop: 4, marginBottom: cpf && !cpfOk ? 2 : 12, borderColor: cpf && !cpfOk ? '#ef4444' : '#cbd5e1' }} />
          {cpf && !cpfOk && <p style={{ color: '#ff9b9b', fontSize: 12, margin: '0 0 10px' }}>CPF inválido</p>}
        </div>

        {/* Toggle de modalidade */}
        <div style={{ display: 'flex', border: `1px solid ${DOURADO}55`, borderRadius: 10, overflow: 'hidden', marginBottom: 12 }}>
          <button onClick={() => setModo('digitada')} style={tabSt(modo === 'digitada')}>Digitar</button>
          <button onClick={() => setModo('desenhada')} style={tabSt(modo === 'desenhada')}>Desenhar</button>
        </div>

        {modo === 'digitada' ? (
          <>
            <div style={{ fontSize: 12, color: '#9bbfae', marginBottom: 8 }}>Escolha o estilo da sua assinatura:</div>
            <div style={{ display: 'grid', gap: 8, marginBottom: 12 }}>
              {fontes.map((f) => (
                <button key={f.id} onClick={() => setFonte(f.id)}
                  style={{ textAlign: 'left', padding: '8px 14px', borderRadius: 10, cursor: 'pointer', background: '#fff',
                    border: fonte === f.id ? `2px solid ${DOURADO}` : '1px solid #e2e8f0', boxShadow: fonte === f.id ? `0 0 0 3px ${DOURADO}44` : 'none' }}>
                  <span style={{ fontFamily: f.id, fontSize: 30, color: '#0d1f17', lineHeight: 1.2 }}>{nome.trim() || 'Sua assinatura'}</span>
                </button>
              ))}
            </div>
            <div style={{ border: `2px dashed ${DOURADO}`, borderRadius: 12, padding: 18, textAlign: 'center', marginBottom: 4, background: '#fff' }}>
              <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>Pré-visualização</div>
              <span style={{ fontFamily: fonte, fontSize: 40, color: '#0d1f17' }}>{nome.trim() || 'Sua assinatura'}</span>
            </div>
          </>
        ) : (
          <>
            <p style={{ fontSize: 13, color: '#9bbfae', margin: '0 0 8px' }}>Desenhe sua assinatura no quadro com o dedo — assine grande, ocupando todo o quadro.</p>
            <div ref={wrapRef} style={{ background: '#fff', borderRadius: 12, border: `2px dashed ${DOURADO}`, position: 'relative', overflow: 'hidden' }}>
              {!temTraco && <span style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#bbb', fontSize: 14, pointerEvents: 'none' }}>assine aqui ✍️</span>}
              <canvas ref={canvasRef}
                style={{ display: 'block', width: '100%', touchAction: 'none' }}
                onMouseDown={start} onMouseMove={move} onMouseUp={end} onMouseLeave={end}
                onTouchStart={start} onTouchMove={move} onTouchEnd={end} />
            </div>
            <button onClick={limpar} style={{ marginTop: 10, background: 'none', border: `1px solid ${DOURADO}`, color: DOURADO,
              borderRadius: 10, padding: '10px 18px', cursor: 'pointer', fontSize: 14, minHeight: 44 }}>Limpar</button>
          </>
        )}

        <label style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginTop: 16, fontSize: 13.5, lineHeight: 1.4 }}>
          <input type="checkbox" checked={concordo} onChange={(e) => setConcordo(e.target.checked)}
            style={{ width: 22, height: 22, marginTop: 1, flexShrink: 0, accentColor: VERDE }} />
          <span>Declaro que li e concordo em assinar eletronicamente este documento (Lei nº 14.063/2020 · MP 2.200-2/2001). Autorizo o registro de nome, CPF, data/hora, IP e localização como evidência de autoria.</span>
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
