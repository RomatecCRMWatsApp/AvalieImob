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

  const [marcaMinuta, setMarcaMinuta] = useState('MINUTA');
  const [enviandoMinuta, setEnviandoMinuta] = useState(false);
  const enviarMinutaAvulsa = async () => {
    const telefones = signatarios.map((s) => s.telefone).filter((t) => (t || '').replace(/\D/g, ''));
    setEnviandoMinuta(true);
    try {
      const r = await assinaturaClienteAPI.enviarMinuta(contratoId, { marca: marcaMinuta, telefones });
      toast({ title: `Minuta enviada (${r.enviados})`, description: `${marcaMinuta} • ${(r.documentos || []).join(' · ')}` });
    } catch (e) {
      toast({ title: 'Falha ao enviar minuta', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally {
      setEnviandoMinuta(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-[60] flex flex-col" onMouseMove={onMove} onMouseUp={onUp}>
      {/* Header */}
      <div className="bg-emerald-900 text-white px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Send className="w-5 h-5" />
          <div>
            <h2 className="font-bold text-sm">Assinatura do cliente — posicionar</h2>
            <p className="text-xs text-emerald-300 mt-0.5">Arraste um retângulo sobre a linha de assinatura de cada signatário, em cada documento.</p>
          </div>
        </div>
        <button onClick={onClose} className="text-emerald-300 hover:text-white"><X className="w-5 h-5" /></button>
      </div>

      {carregando ? (
        <div className="flex-1 flex items-center justify-center text-white"><Loader2 className="w-8 h-8 animate-spin mr-2" /> Preparando documentos…</div>
      ) : (
        <>
          {/* Controles (rolável, não engole o visualizador) */}
          <div className="bg-white border-b border-gray-200 px-4 py-3 shrink-0 max-h-[42vh] overflow-auto space-y-3">
            {sessao && sessao.status !== 'concluida' && (
              <div className="bg-amber-50 border border-amber-300 rounded-xl px-3 py-2.5">
                <div className="text-[13px] font-semibold text-amber-800">Já enviado · {sessao.assinados}/{sessao.total} assinaram</div>
                <div className="text-xs text-amber-700 mt-0.5 mb-2">
                  {sessao.signatarios?.map((s) => `${s.nome?.split(' ')[0]}: ${s.status === 'assinado' ? '✓ assinou' : 'pendente'}`).join(' · ')}
                </div>
                <div className="flex gap-2 flex-wrap mb-2">
                  {sessao.signatarios?.filter((s) => s.status !== 'assinado').map((s) => (
                    <input key={s.role} value={reenvioFones[s.role] ?? ''}
                      onChange={(e) => setReenvioFones((f) => ({ ...f, [s.role]: e.target.value }))}
                      placeholder={`WhatsApp de ${s.nome?.split(' ')[0]} (DDD+número)`}
                      className="flex-1 min-w-[200px] border border-amber-300 rounded-lg px-2.5 py-1.5 text-[13px] bg-white" />
                  ))}
                </div>
                <button onClick={reenviar} disabled={reenviando}
                  className="bg-[#B8860B] text-white font-bold rounded-lg px-4 py-2 text-[13px]">
                  {reenviando ? 'Reenviando…' : '🔁 Reenviar links (sem reposicionar)'}
                </button>
                <span className="text-[11px] text-amber-700 ml-2.5">ou reposicione abaixo para um novo envio</span>
              </div>
            )}
            {sessao && sessao.status === 'concluida' && (
              <div className="bg-emerald-50 border border-emerald-300 rounded-xl px-3 py-2.5 text-[13px] text-emerald-800 font-semibold">
                ✓ Todos os clientes já assinaram ({sessao.assinados}/{sessao.total}). {sessao.pdf_final_url ? 'PDF com assinaturas gerado.' : ''}
              </div>
            )}

            {documentos.length > 1 && (
              <div className="flex gap-2">
                {documentos.map((d, i) => {
                  const okCount = posicionaveis.filter((s) => ancoras[k(d.tipo, s.role)]).length;
                  return (
                    <button key={d.tipo} onClick={() => { setDocAtivo(i); setPrevia(null); }}
                      className="flex-1 px-3 py-2 rounded-lg text-[13px] font-bold border-2 border-emerald-700"
                      style={{ background: i === docAtivo ? '#0B6E4F' : '#fff', color: i === docAtivo ? '#fff' : '#0B6E4F' }}>
                      {d.titulo} ({okCount}/{posicionaveis.length})
                    </button>
                  );
                })}
              </div>
            )}

            <div className="flex gap-2 flex-wrap">
              {posicionaveis.map((s, i) => (
                <button key={s.role} onClick={() => setAtivo(i)}
                  className="px-3 py-1.5 rounded-lg text-[13px] border-2"
                  style={{ borderColor: CORES[i % CORES.length], background: i === ativo ? CORES[i % CORES.length] : '#fff', color: i === ativo ? '#fff' : '#333' }}>
                  {ROLE_LABEL[s.role] || s.role}: {s.nome.split(' ')[0]} {ancoras[k(docTipo, s.role)] ? '✓' : ''}
                </button>
              ))}
            </div>

            <div className="flex gap-2 flex-wrap">
              {signatarios.map((s, i) => (
                <input key={s.role} value={s.telefone || ''} onChange={(e) => setFone(i, e.target.value)}
                  placeholder={`WhatsApp de ${s.nome.split(' ')[0]} (DDD+número)`}
                  className="flex-1 min-w-[200px] border border-gray-300 rounded-lg px-2.5 py-1.5 text-[13px]" />
              ))}
            </div>

            <div className="flex items-center gap-2 flex-wrap bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">
              <span className="text-[12px] text-amber-800">📄 A <b>minuta (rascunho)</b> já vai junto com o link. Pode enviar avulsa para leitura antecipada:</span>
              <select value={marcaMinuta} onChange={(e) => setMarcaMinuta(e.target.value)}
                className="border border-amber-300 rounded-lg px-2 py-1 text-[12px] bg-white">
                <option value="MINUTA">MINUTA</option>
                <option value="RASCUNHO">RASCUNHO</option>
              </select>
              <button onClick={enviarMinutaAvulsa} disabled={enviandoMinuta}
                className="bg-amber-600 hover:bg-amber-500 text-white font-bold rounded-lg px-3 py-1.5 text-[12px] disabled:opacity-60">
                {enviandoMinuta ? 'Enviando…' : 'Enviar minuta avulsa'}
              </button>
            </div>

            {corretor && (
              <div className="bg-slate-50 border border-slate-300 rounded-xl p-2.5">
                <div className="text-[13px] font-bold text-slate-700 mb-1.5">
                  ✍️ Sua assinatura ({corretor.nome?.split(' ')[0]}) — carimbada ANTES de enviar ao cliente
                </div>
                <canvas ref={corCanvas} width={500} height={120}
                  onMouseDown={corStart} onMouseMove={corMove} onMouseUp={corEnd} onMouseLeave={corEnd}
                  onTouchStart={corStart} onTouchMove={corMove} onTouchEnd={corEnd}
                  style={{ width: '100%', height: 120, background: '#fff', border: '1px dashed #94a3b8', borderRadius: 8, touchAction: 'none', cursor: 'crosshair', display: 'block' }} />
                <div className="flex items-center gap-2.5 mt-1.5">
                  <button onClick={corLimpar} className="border border-slate-400 text-slate-600 rounded-lg px-3 py-1 text-xs">Limpar</button>
                  <span className="text-[11px]" style={{ color: corretorTraco ? '#0B6E4F' : '#b45309' }}>
                    {corretorTraco ? '✓ assinatura pronta (será salva p/ reutilizar)' : 'desenhe sua assinatura aqui'}
                  </span>
                </div>
                {corretor.assinatura_padrao && corretorTraco && (
                  <div className="text-[11px] text-slate-500 mt-1">
                    ✨ Gerada automaticamente do seu nome. Desenhe por cima (ou Limpar) para usar a sua de próprio punho.
                  </div>
                )}
              </div>
            )}

            <p className="text-xs text-gray-500">
              No <b>{documentos[docAtivo]?.titulo}</b>: selecione o signatário (inclusive <b>Você</b>) e <b>arraste um retângulo</b> sobre a linha de assinatura dele. Role o documento abaixo para navegar entre as páginas.
            </p>
          </div>

          {/* Visualizador grande (todas as páginas do documento ativo) */}
          <div className="flex-1 overflow-auto bg-gray-800 p-4">
            {paginas.map((pg, idx) => (
              <div key={idx} className="relative select-none mx-auto mb-4 shadow-2xl" style={{ width: 'fit-content', maxWidth: '100%' }}>
                <div className="absolute -top-0 left-0 bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded-br z-10 pointer-events-none">Pág. {idx + 1}/{paginas.length}</div>
                <img src={`data:image/png;base64,${pg.imagem_b64}`} alt={`Página ${idx + 1}`}
                  onMouseDown={(e) => onDown(e, idx)} draggable={false}
                  style={{ display: 'block', width: 820, maxWidth: '100%', cursor: 'crosshair', userSelect: 'none' }} />
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

          {/* Footer */}
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

function stripPx(a) { if (!a) return {}; const { _px, ...rest } = a; return rest; }
