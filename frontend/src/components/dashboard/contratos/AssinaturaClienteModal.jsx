// Modal: corretor posiciona 1 caixa de assinatura por signatário, em CADA documento
// (contrato e, se houver, procuração), e dispara os links por WhatsApp.
import React, { useEffect, useRef, useState } from 'react';
import { X, Loader2, Send } from 'lucide-react';
import { assinaturaClienteAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';

const ROLE_LABEL = { contratante: 'Contratante', conjuge_anuente: 'Cônjuge anuente', outorgante: 'Outorgante', corretor: 'Você (corretor)' };
const CORES = ['#0B6E4F', '#B8860B', '#1d4ed8', '#9333ea', '#475569'];

export default function AssinaturaClienteModal({ contratoId, onClose }) {
  const { toast } = useToast();
  const [carregando, setCarregando] = useState(true);
  const [documentos, setDocumentos] = useState([]); // [{tipo,titulo,paginas}]
  const [docAtivo, setDocAtivo] = useState(0);
  const [signatarios, setSignatarios] = useState([]);
  const [ativo, setAtivo] = useState(0); // índice do signatário
  const [ancoras, setAncoras] = useState({}); // `${tipo}:${role}` -> {pagina,x_pt,y_pt,larg_pt,alt_pt,_px}
  const [enviando, setEnviando] = useState(false);
  const [sessao, setSessao] = useState(null);   // sessão já enviada (status + signatários)
  const [reenviando, setReenviando] = useState(false);
  const [reenvioFones, setReenvioFones] = useState({}); // role -> telefone editável (default cadastro)
  const [corretor, setCorretor] = useState(null);       // {nome, assinatura_b64} — opção A
  const [corretorTraco, setCorretorTraco] = useState(null); // dataURL PNG da SUA assinatura
  const corCanvas = useRef(null);
  const corDes = useRef(false);
  const arrasto = useRef(null);
  const [previa, setPrevia] = useState(null);

  const aplicarSessao = (s) => {
    setSessao(s || null);
    if (s) setReenvioFones(Object.fromEntries((s.signatarios || []).map((x) => [x.role, x.telefone || ''])));
  };

  useEffect(() => {
    assinaturaClienteAPI.sessao(contratoId).then((d) => aplicarSessao(d?.sessao)).catch(() => {});
    assinaturaClienteAPI.preparar(contratoId)
      .then((d) => {
        const docs = d.documentos || (d.paginas ? [{ tipo: 'contrato', titulo: 'Contrato', paginas: d.paginas }] : []);
        setDocumentos(docs);
        setSignatarios((d.signatarios || []).map((s) => ({ ...s })));
        setCorretor(d.corretor || null);
      })
      .catch((e) => toast({ title: 'Erro ao preparar', description: e?.response?.data?.detail || '', variant: 'destructive' }))
      .finally(() => setCarregando(false));
  }, [contratoId]); // eslint-disable-line

  const reenviar = async () => {
    setReenviando(true);
    try {
      const body = { signatarios: (sessao?.signatarios || []).map((s) => ({ role: s.role, telefone: reenvioFones[s.role] ?? s.telefone ?? '' })) };
      const r = await assinaturaClienteAPI.reenviar(contratoId, body);
      toast({ title: `Links reenviados (${r.reenviados})`, description: 'Pra quem ainda não assinou.' });
      const d = await assinaturaClienteAPI.sessao(contratoId);
      aplicarSessao(d?.sessao);
    } catch (e) {
      toast({ title: 'Falha ao reenviar', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally {
      setReenviando(false);
    }
  };

  // pré-carrega a assinatura salva do corretor no canvas
  useEffect(() => {
    if (!corretor?.assinatura_b64 || !corCanvas.current) return;
    const img = new Image();
    img.onload = () => {
      const c = corCanvas.current; if (!c) return; const ctx = c.getContext('2d');
      ctx.clearRect(0, 0, c.width, c.height); ctx.drawImage(img, 0, 0, c.width, c.height);
      setCorretorTraco(`data:image/png;base64,${corretor.assinatura_b64}`);
    };
    img.src = `data:image/png;base64,${corretor.assinatura_b64}`;
  }, [corretor]);

  const corPos = (e) => { const c = corCanvas.current; const r = c.getBoundingClientRect(); const t = e.touches?.[0] || e; return { x: (t.clientX - r.left) * (c.width / r.width), y: (t.clientY - r.top) * (c.height / r.height) }; };
  const corStart = (e) => { e.preventDefault(); e.stopPropagation(); corDes.current = true; const ctx = corCanvas.current.getContext('2d'); const p = corPos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y); };
  const corMove = (e) => { if (!corDes.current) return; e.stopPropagation(); const ctx = corCanvas.current.getContext('2d'); const p = corPos(e); ctx.lineWidth = 2.2; ctx.lineCap = 'round'; ctx.strokeStyle = '#14315c'; ctx.lineTo(p.x, p.y); ctx.stroke(); };
  const corEnd = () => { if (corDes.current) { corDes.current = false; setCorretorTraco(corCanvas.current.toDataURL('image/png')); } };
  const corLimpar = () => { const c = corCanvas.current; c.getContext('2d').clearRect(0, 0, c.width, c.height); setCorretorTraco(null); };

  // o corretor também é POSICIONÁVEL (assina visualmente PRIMEIRO, opção A)
  const posicionaveis = corretor ? [...signatarios, { role: 'corretor', nome: corretor.nome }] : signatarios;
  const sig = posicionaveis[ativo];
  const docTipo = documentos[docAtivo]?.tipo || 'contrato';
  const paginas = documentos[docAtivo]?.paginas || [];
  const k = (tipo, role) => `${tipo}:${role}`;

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
    setAncoras((a) => ({ ...a, [k(docTipo, sig.role)]: { pagina: previa.pagina, x_pt, y_pt, larg_pt, alt_pt, _px: { ...previa, doc: docTipo } } }));
    arrasto.current = null;
    setPrevia(null);
  };

  const enviar = async () => {
    if (corretor && !corretorTraco) { toast({ title: 'Desenhe a SUA assinatura (corretor) primeiro', description: 'Ela é carimbada antes de enviar ao cliente.', variant: 'destructive' }); return; }
    // cada posicionável (clientes + você) precisa de caixa em CADA documento
    for (const d of documentos) {
      const falta = posicionaveis.filter((s) => !ancoras[k(d.tipo, s.role)]);
      if (falta.length) {
        toast({ title: `Posicione no ${d.titulo}: ${falta.map((s) => s.nome.split(' ')[0]).join(', ')}`, variant: 'destructive' });
        return;
      }
    }
    const faltamFone = signatarios.filter((s) => !(s.telefone || '').replace(/\D/g, ''));
    if (faltamFone.length) { toast({ title: 'Informe o WhatsApp de: ' + faltamFone.map((s) => s.nome).join(', '), variant: 'destructive' }); return; }
    setEnviando(true);
    try {
      const body = {
        documentos: documentos.map((d) => ({
          tipo: d.tipo,
          ancoras: posicionaveis.map((s) => ({ role: s.role, ...stripPx(ancoras[k(d.tipo, s.role)]) })),
        })),
        signatarios: signatarios.map((s) => ({ role: s.role, nome: s.nome, cpf: s.cpf, telefone: s.telefone })),
        corretor_traco: corretorTraco,
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

  const setFone = (i, v) => setSignatarios((ss) => ss.map((s, kk) => (kk === i ? { ...s, telefone: v } : s)));

  return (
    <div style={ovl} onMouseMove={onMove} onMouseUp={onUp}>
      <div style={box}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <h3 style={{ fontWeight: 700, color: '#0B6E4F' }}>📲 Assinatura do cliente — posicionar</h3>
          <button onClick={onClose} style={{ border: 'none', background: 'none', cursor: 'pointer' }}><X size={20} /></button>
        </div>

        {sessao && sessao.status !== 'concluida' && (
          <div style={{ background: '#fffbeb', border: '1px solid #fcd34d', borderRadius: 10, padding: '10px 12px', marginBottom: 10 }}>
            <div style={{ fontSize: 13, color: '#92400e', fontWeight: 600 }}>
              Já enviado · {sessao.assinados}/{sessao.total} assinaram
            </div>
            <div style={{ fontSize: 12, color: '#9a6a00', margin: '2px 0 8px' }}>
              {sessao.signatarios?.map((s) => `${s.nome?.split(' ')[0]}: ${s.status === 'assinado' ? '✓ assinou' : 'pendente'}`).join(' · ')}
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
              {sessao.signatarios?.filter((s) => s.status !== 'assinado').map((s) => (
                <input key={s.role} value={reenvioFones[s.role] ?? ''}
                  onChange={(e) => setReenvioFones((f) => ({ ...f, [s.role]: e.target.value }))}
                  placeholder={`WhatsApp de ${s.nome?.split(' ')[0]} (DDD+número)`}
                  style={{ flex: '1 1 200px', border: '1px solid #fcd34d', borderRadius: 8, padding: '7px 10px', fontSize: 13, background: '#fff' }} />
              ))}
            </div>
            <button onClick={reenviar} disabled={reenviando}
              style={{ background: '#B8860B', color: '#fff', fontWeight: 700, border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontSize: 13 }}>
              {reenviando ? 'Reenviando…' : '🔁 Reenviar links (sem reposicionar)'}
            </button>
            <span style={{ fontSize: 11, color: '#9a6a00', marginLeft: 10 }}>ou reposicione abaixo para um novo envio</span>
          </div>
        )}
        {sessao && sessao.status === 'concluida' && (
          <div style={{ background: '#ecfdf5', border: '1px solid #6ee7b7', borderRadius: 10, padding: '10px 12px', marginBottom: 10, fontSize: 13, color: '#065f46', fontWeight: 600 }}>
            ✓ Todos os clientes já assinaram ({sessao.assinados}/{sessao.total}). {sessao.pdf_final_url ? 'PDF com assinaturas gerado.' : ''}
          </div>
        )}

        {carregando ? (
          <div style={{ padding: 40, textAlign: 'center' }}><Loader2 className="animate-spin" /> Preparando documentos…</div>
        ) : (
          <>
            {documentos.length > 1 && (
              <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                {documentos.map((d, i) => {
                  const okCount = posicionaveis.filter((s) => ancoras[k(d.tipo, s.role)]).length;
                  return (
                    <button key={d.tipo} onClick={() => { setDocAtivo(i); setPrevia(null); }}
                      style={{ flex: 1, padding: '8px 10px', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 700,
                        border: `2px solid #0B6E4F`, background: i === docAtivo ? '#0B6E4F' : '#fff', color: i === docAtivo ? '#fff' : '#0B6E4F' }}>
                      {d.titulo} ({okCount}/{posicionaveis.length})
                    </button>
                  );
                })}
              </div>
            )}

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
              {posicionaveis.map((s, i) => (
                <button key={s.role} onClick={() => setAtivo(i)}
                  style={{ padding: '6px 12px', borderRadius: 8, cursor: 'pointer', fontSize: 13,
                    border: `2px solid ${CORES[i % CORES.length]}`,
                    background: i === ativo ? CORES[i % CORES.length] : '#fff',
                    color: i === ativo ? '#fff' : '#333' }}>
                  {ROLE_LABEL[s.role] || s.role}: {s.nome.split(' ')[0]} {ancoras[k(docTipo, s.role)] ? '✓' : ''}
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
              {signatarios.map((s, i) => (
                <input key={s.role} value={s.telefone || ''} onChange={(e) => setFone(i, e.target.value)}
                  placeholder={`WhatsApp de ${s.nome.split(' ')[0]} (DDD+número)`}
                  style={{ flex: '1 1 200px', border: '1px solid #ccc', borderRadius: 8, padding: '7px 10px', fontSize: 13 }} />
              ))}
            </div>
            {corretor && (
              <div style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: 10, padding: 10, marginBottom: 10 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#334155', marginBottom: 6 }}>
                  ✍️ Sua assinatura ({corretor.nome?.split(' ')[0]}) — carimbada ANTES de enviar ao cliente
                </div>
                <canvas ref={corCanvas} width={500} height={120}
                  onMouseDown={corStart} onMouseMove={corMove} onMouseUp={corEnd} onMouseLeave={corEnd}
                  onTouchStart={corStart} onTouchMove={corMove} onTouchEnd={corEnd}
                  style={{ width: '100%', height: 120, background: '#fff', border: '1px dashed #94a3b8', borderRadius: 8, touchAction: 'none', cursor: 'crosshair', display: 'block' }} />
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 6 }}>
                  <button onClick={corLimpar} style={{ background: 'none', border: '1px solid #94a3b8', color: '#475569', borderRadius: 8, padding: '5px 12px', cursor: 'pointer', fontSize: 12 }}>Limpar</button>
                  <span style={{ fontSize: 11, color: corretorTraco ? '#0B6E4F' : '#b45309' }}>
                    {corretorTraco ? '✓ assinatura pronta (será salva p/ reutilizar)' : 'desenhe sua assinatura aqui'}
                  </span>
                </div>
                {corretor.assinatura_padrao && corretorTraco && (
                  <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                    ✨ Gerada automaticamente do seu nome. Desenhe por cima (ou Limpar) para usar a sua de próprio punho.
                  </div>
                )}
              </div>
            )}
            <p style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
              No <b>{documentos[docAtivo]?.titulo}</b>: selecione o signatário (inclusive <b>Você</b>) e <b>arraste um retângulo</b> sobre a linha de assinatura dele.
            </p>

            <div style={{ overflow: 'auto', maxHeight: '52vh', border: '1px solid #eee', borderRadius: 8 }}>
              {paginas.map((pg, idx) => (
                <div key={idx} style={{ position: 'relative', margin: '8px auto', width: 'fit-content' }}>
                  <img src={`data:image/png;base64,${pg.imagem_b64}`} alt={`Página ${idx + 1}`}
                    onMouseDown={(e) => onDown(e, idx)} draggable={false}
                    style={{ display: 'block', maxWidth: '100%', cursor: 'crosshair', userSelect: 'none' }} />
                  {posicionaveis.map((s, i) => {
                    const a = ancoras[k(docTipo, s.role)];
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
