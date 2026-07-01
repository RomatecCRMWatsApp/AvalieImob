// @page AssinarGeoUrbano — assinatura do proprietário/advogado (mobile, sem auth).
// Rota pública /assinar-geo/:token. Duas modalidades: DIGITAR (nome + CPF + fonte
// manuscrita) ou DESENHAR (traço no canvas). O backend renderiza a digitada em PNG e
// reusa o mesmo carimbo/posição da desenhada.
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { geoUrbanoPublicoAPI } from '../lib/api';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';
const FONTES_FALLBACK = [
  { id: 'DancingScript', label: 'Dancing Script' }, { id: 'GreatVibes', label: 'Great Vibes' },
  { id: 'Sacramento', label: 'Sacramento' }, { id: 'Allura', label: 'Allura' },
  { id: 'HomemadeApple', label: 'Homemade Apple' }, { id: 'Pacifico', label: 'Pacifico' },
];
// @font-face injetado em runtime (as fontes ficam em /public/fonts/assinatura; não passa
// pelo css-loader do CRA, que tentaria resolver o caminho absoluto e quebraria o build).
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

export default function AssinarGeoUrbano() {
  const { token } = useParams();
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState('');
  const [loading, setLoading] = useState(true);
  const [modo, setModo] = useState('digitada');   // 'digitada' | 'desenhada'
  const [nome, setNome] = useState('');
  const [cpf, setCpf] = useState('');
  const [fonte, setFonte] = useState('DancingScript');
  const [concordo, setConcordo] = useState(false);
  const [geo, setGeo] = useState({ lat: null, lng: null });
  const [enviando, setEnviando] = useState(false);
  const [okFinal, setOkFinal] = useState(null);
  const canvasRef = useRef(null);
  const desenhou = useRef(false);

  useEffect(() => {
    geoUrbanoPublicoAPI.obter(token)
      .then((d) => { setDados(d); setNome(d?.nome || ''); })
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
    c.width = Math.round(c.clientWidth * dpr);
    c.height = Math.round(c.clientHeight * dpr);
    const ctx = c.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.lineWidth = 2.4; ctx.lineCap = 'round'; ctx.strokeStyle = '#14315c';
    desenhou.current = false;
  }, []);
  useEffect(() => { if (dados && !dados.ja_assinado && modo === 'desenhada') setTimeout(setupCanvas, 0); }, [dados, modo, setupCanvas]);

  const pos = (e) => { const r = canvasRef.current.getBoundingClientRect(); const t = e.touches ? e.touches[0] : e; return { x: t.clientX - r.left, y: t.clientY - r.top }; };
  const drawing = useRef(false);
  const start = (e) => { e.preventDefault(); drawing.current = true; const ctx = canvasRef.current.getContext('2d'); const p = pos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y); };
  const move = (e) => { if (!drawing.current) return; e.preventDefault(); const ctx = canvasRef.current.getContext('2d'); const p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke(); desenhou.current = true; };
  const end = () => { drawing.current = false; };
  const limpar = () => { const c = canvasRef.current; c.getContext('2d').clearRect(0, 0, c.width, c.height); desenhou.current = false; };

  const cpfOk = validarCpf(cpf);
  const fontes = dados?.fontes?.length ? dados.fontes : FONTES_FALLBACK;

  const assinar = async () => {
    if (nome.trim().length < 3) { setErro('Informe seu nome completo.'); return; }
    if (!cpfOk) { setErro('CPF inválido.'); return; }
    if (!concordo) { setErro('Marque o aceite para assinar.'); return; }
    if (modo === 'desenhada' && !desenhou.current) { setErro('Desenhe sua assinatura.'); return; }
    if (modo === 'digitada' && !fonte) { setErro('Escolha um estilo de assinatura.'); return; }
    setEnviando(true); setErro('');
    try {
      const base = { concordo: true, geo_lat: geo.lat, geo_lng: geo.lng, nome_assinante: nome.trim(), cpf_assinante: limparCpf(cpf) };
      const payload = modo === 'digitada'
        ? { ...base, tipo_assinatura: 'digitada', fonte_assinatura: fonte }
        : { ...base, tipo_assinatura: 'desenhada', traco_base64: canvasRef.current.toDataURL('image/png') };
      const r = await geoUrbanoPublicoAPI.assinar(token, payload);
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

  const inpSt = { width: '100%', padding: '10px 12px', border: '1px solid #cbd5e1', borderRadius: 10, fontSize: 15, boxSizing: 'border-box' };
  const tabSt = (on) => ({ flex: 1, padding: '12px', fontSize: 14, fontWeight: 600, border: 'none', cursor: 'pointer', background: on ? GREEN : '#fff', color: on ? '#fff' : GREEN });

  return (
    <div style={{ minHeight: '100dvh', background: '#f1f5f9', padding: 'env(safe-area-inset-top) 0 0' }}>
      <style>{FONT_FACE_CSS}</style>
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
                  {boxes.map((b, i) => (
                    <div key={i} style={{
                      position: 'absolute',
                      left: `${(b.x_pt / pg.largura_pt) * 100}%`,
                      top: `${((pg.altura_pt - b.y_pt - b.alt_pt) / pg.altura_pt) * 100}%`,
                      width: `${(b.larg_pt / pg.largura_pt) * 100}%`,
                      height: `${(b.alt_pt / pg.altura_pt) * 100}%`,
                      border: `2px dashed ${GOLD}`, borderRadius: 6, background: 'rgba(201,168,76,.12)',
                    }}>
                      <span style={{ position: 'absolute', top: -22, left: 0, background: GOLD, color: '#3a2e00', fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 5, whiteSpace: 'nowrap' }}>➜ sua assinatura aqui</span>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        ))}

        <div style={{ background: 'white', borderRadius: 12, padding: 14, boxShadow: '0 1px 3px rgba(0,0,0,.08)' }}>
          {/* dados do assinante (as duas modalidades) */}
          <label style={{ fontSize: 13, color: '#334155', fontWeight: 600 }}>Nome completo</label>
          <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Seu nome completo" style={{ ...inpSt, marginTop: 4, marginBottom: 10 }} />
          <label style={{ fontSize: 13, color: '#334155', fontWeight: 600 }}>CPF</label>
          <input value={mascaraCpf(cpf)} onChange={(e) => setCpf(e.target.value)} inputMode="numeric" placeholder="000.000.000-00"
            style={{ ...inpSt, marginTop: 4, marginBottom: cpf && !cpfOk ? 2 : 12, borderColor: cpf && !cpfOk ? '#ef4444' : '#cbd5e1' }} />
          {cpf && !cpfOk && <p style={{ color: '#ef4444', fontSize: 12, margin: '0 0 10px' }}>CPF inválido</p>}

          {/* toggle de modalidade */}
          <div style={{ display: 'flex', border: `1px solid ${GREEN}33`, borderRadius: 10, overflow: 'hidden', marginBottom: 12 }}>
            <button onClick={() => setModo('digitada')} style={tabSt(modo === 'digitada')}>Digitar</button>
            <button onClick={() => setModo('desenhada')} style={tabSt(modo === 'desenhada')}>Desenhar</button>
          </div>

          {modo === 'digitada' ? (
            <>
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>Escolha o estilo da sua assinatura:</div>
              <div style={{ display: 'grid', gap: 8, marginBottom: 12 }}>
                {fontes.map((f) => (
                  <button key={f.id} onClick={() => setFonte(f.id)}
                    style={{ textAlign: 'left', padding: '8px 14px', borderRadius: 10, cursor: 'pointer', background: '#fff',
                      border: fonte === f.id ? `2px solid ${GOLD}` : '1px solid #e2e8f0', boxShadow: fonte === f.id ? `0 0 0 3px ${GOLD}33` : 'none' }}>
                    <span style={{ fontFamily: f.id, fontSize: 30, color: GREEN, lineHeight: 1.2 }}>{nome.trim() || 'Sua assinatura'}</span>
                  </button>
                ))}
              </div>
              <div style={{ border: '2px dashed #cbd5e1', borderRadius: 12, padding: 18, textAlign: 'center', marginBottom: 8 }}>
                <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>Pré-visualização</div>
                <span style={{ fontFamily: fonte, fontSize: 40, color: GREEN }}>{nome.trim() || 'Sua assinatura'}</span>
              </div>
            </>
          ) : (
            <>
              <div style={{ fontWeight: 600, color: GREEN, marginBottom: 4 }}>Desenhe sua assinatura ✍️</div>
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6 }}>Assine grande, ocupando todo o quadro.</div>
              <canvas ref={canvasRef}
                style={{ width: '100%', height: 240, border: `2px dashed ${GOLD}`, borderRadius: 10, touchAction: 'none', background: '#fff' }}
                onMouseDown={start} onMouseMove={move} onMouseUp={end} onMouseLeave={end}
                onTouchStart={start} onTouchMove={move} onTouchEnd={end} />
              <button onClick={limpar} style={{ marginTop: 6, fontSize: 13, color: '#64748b', background: 'none', border: 'none' }}>Limpar</button>
            </>
          )}

          <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', margin: '12px 0', fontSize: 13, color: '#334155' }}>
            <input type="checkbox" checked={concordo} onChange={(e) => setConcordo(e.target.checked)} style={{ width: 20, height: 20, accentColor: GREEN }} />
            <span>Li e concordo em assinar eletronicamente os documentos acima (MP 2.200-2/2001 · Lei 14.063/2020).</span>
          </label>
          {erro && <p style={{ color: '#b91c1c', fontSize: 13 }}>{erro}</p>}
          <button onClick={assinar} disabled={enviando}
            style={{ width: '100%', minHeight: 50, background: GREEN, color: 'white', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: 16, opacity: enviando ? 0.6 : 1 }}>
            {enviando ? 'Enviando…' : 'ASSINAR'}
          </button>
          <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 10, lineHeight: 1.4 }}>
            Assinatura eletrônica avançada (Lei 14.063/2020 e MP 2.200-2/2001). Registramos nome, CPF, data/hora, IP e um código de integridade (hash).
          </p>
        </div>
      </div>
    </div>
  );
}

function Centro({ children }) {
  return <div style={{ minHeight: '100dvh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: 24 }}>{children}</div>;
}
