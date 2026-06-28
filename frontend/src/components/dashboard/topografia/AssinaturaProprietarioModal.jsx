// @module topografia/AssinaturaProprietarioModal — posiciona a assinatura do
// proprietário (Requerimento 2 vias + ART/TRT) e dispara os links por WhatsApp.
import React, { useEffect, useState } from 'react';
import { X, Send } from 'lucide-react';
import { geoUrbanoAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';
const BOX_W = 230, BOX_H = 84;          // tamanho da caixa de assinatura (pt) — amplo p/ a firma

export default function AssinaturaProprietarioModal({ projetoId, onFechar, onEnviado }) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [documentos, setDocumentos] = useState([]);
  const [sigs, setSigs] = useState([]);
  const [ativo, setAtivo] = useState(null);          // parte_id ativo ('__tecnico__' = firma do RT)
  const [pos, setPos] = useState({});                // {parte_id: {doc: [{pagina,x_pt,y_pt,larg_pt,alt_pt,tipo}]}}
  const [tecnico, setTecnico] = useState({ tem_assinatura: false, nome: '' });
  const [tecnicoPos, setTecnicoPos] = useState({});  // {doc: [rects]} — opção A
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    geoUrbanoAPI.propPreparar(projetoId)
      .then((d) => {
        setDocumentos(d.documentos || []);
        const ss = (d.signatarios || []).map((s) => ({ ...s }));
        setSigs(ss);
        setTecnico(d.tecnico || { tem_assinatura: false, nome: '' });
        setAtivo(ss[0]?.parte_id || null);
      })
      .catch((e) => toast({ title: 'Erro ao preparar', description: e?.response?.data?.detail || '', variant: 'destructive' }))
      .finally(() => setLoading(false));
  }, [projetoId, toast]);

  const setFone = (pid, fone) => setSigs((ss) => ss.map((s) => (s.parte_id === pid ? { ...s, telefone: fone } : s)));

  const clicar = (e, docNome, pg) => {
    if (!ativo) { toast({ title: 'Selecione um signatário' }); return; }
    const r = e.currentTarget.getBoundingClientRect();
    const cx = e.clientX - r.left, cy = e.clientY - r.top;
    const escX = pg.largura_pt / r.width, escY = pg.altura_pt / r.height;
    const x_pt = Math.max(0, Math.min(pg.largura_pt - BOX_W, cx * escX));
    const y_pt = Math.max(0, pg.altura_pt - cy * escY - BOX_H);
    const box = { pagina: pg.pagina, x_pt, y_pt, larg_pt: BOX_W, alt_pt: BOX_H, tipo: 'assinatura' };
    if (ativo === '__tecnico__') {
      setTecnicoPos((p) => ({ ...p, [docNome]: [box] }));
      return;
    }
    setPos((p) => {
      const porSig = { ...(p[ativo] || {}) };
      porSig[docNome] = [box];
      return { ...p, [ativo]: porSig };
    });
  };

  const caixaNaTela = (box, pg, rectW, rectH) => ({
    left: (box.x_pt / pg.largura_pt) * rectW,
    top: ((pg.altura_pt - box.y_pt - box.alt_pt) / pg.altura_pt) * rectH,
    width: (box.larg_pt / pg.largura_pt) * rectW,
    height: (box.alt_pt / pg.altura_pt) * rectH,
  });

  const corSig = (pid) => {
    const i = sigs.findIndex((s) => s.parte_id === pid);
    return ['#0C3320', '#0B6E4F', '#8A2BE2', '#B8860B'][i % 4];
  };

  const enviar = async () => {
    if (sigs.some((s) => !s.telefone)) { toast({ title: 'Informe o WhatsApp de todos os signatários', variant: 'destructive' }); return; }
    const algum = Object.values(pos).some((m) => Object.values(m).some((a) => a.length))
      || Object.values(tecnicoPos).some((a) => a.length);
    if (!algum) { toast({ title: 'Posicione ao menos uma assinatura', variant: 'destructive' }); return; }
    setEnviando(true);
    try {
      const r = await geoUrbanoAPI.propPosicionar(projetoId, {
        signatarios: sigs.map((s) => ({ parte_id: s.parte_id, nome: s.nome, papel: s.papel, cpf_cnpj: s.cpf_cnpj, telefone: s.telefone })),
        posicoes: pos,
        tecnico_pos: tecnicoPos,
      });
      toast({ title: `Links enviados: ${r.enviados || 0}`, description: r.falhas ? `${r.falhas} falha(s)` : '' });
      onEnviado && onEnviado();
      onFechar();
    } catch (e) {
      toast({ title: 'Erro ao enviar', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setEnviando(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex flex-col z-[1000]">
      <div className="flex items-center justify-between px-4 py-3" style={{ background: GREEN }}>
        <h2 className="text-white font-semibold text-sm">Assinatura do proprietário — posicionar e enviar</h2>
        <button onClick={onFechar} className="text-white"><X className="w-5 h-5" /></button>
      </div>

      {loading ? <div className="flex-1 grid place-items-center"><BrandSpinner label="Preparando…" /></div> : (
        <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
          {/* controles */}
          <div className="md:w-72 shrink-0 bg-white p-3 overflow-y-auto space-y-3">
            <div className="text-xs text-gray-500">Selecione o signatário e clique na peça onde ele assina.</div>
            {sigs.map((s) => (
              <div key={s.parte_id} className={`rounded-lg border p-2 ${ativo === s.parte_id ? 'ring-2' : ''}`}
                style={{ borderColor: corSig(s.parte_id), ...(ativo === s.parte_id ? { boxShadow: `0 0 0 2px ${corSig(s.parte_id)}` } : {}) }}>
                <button onClick={() => setAtivo(s.parte_id)} className="text-left w-full">
                  <div className="text-sm font-medium" style={{ color: corSig(s.parte_id) }}>{s.nome}</div>
                  <div className="text-[11px] text-gray-500">{s.papel}</div>
                </button>
                <input className="mt-1 w-full border rounded px-2 py-1 text-xs" placeholder="WhatsApp (55DDDNUMERO)"
                  value={s.telefone || ''} onChange={(e) => setFone(s.parte_id, e.target.value)} />
              </div>
            ))}
            {tecnico.tem_assinatura && (
              <div className={`rounded-lg border p-2 ${ativo === '__tecnico__' ? 'ring-2' : ''}`}
                style={{ borderColor: GOLD, ...(ativo === '__tecnico__' ? { boxShadow: `0 0 0 2px ${GOLD}` } : {}) }}>
                <button onClick={() => setAtivo('__tecnico__')} className="text-left w-full">
                  <div className="text-sm font-medium" style={{ color: '#9a7d2e' }}>✍️ Minha assinatura (técnico)</div>
                  <div className="text-[11px] text-gray-500">{tecnico.nome} — já vai CARIMBADA na peça antes do envio</div>
                </button>
                {Object.values(tecnicoPos).some((a) => a.length) && (
                  <button onClick={() => setTecnicoPos({})} className="mt-1 text-[11px] text-red-600 hover:underline">limpar posições</button>
                )}
              </div>
            )}
          </div>

          {/* documentos */}
          <div className="flex-1 overflow-y-auto bg-gray-800 p-3 space-y-4">
            {documentos.map((d) => (
              <div key={d.doc}>
                <div className="text-white text-sm font-semibold mb-1">{d.titulo}</div>
                {(d.paginas || []).map((pg) => (
                  <Pagina key={pg.pagina} pg={pg} doc={d.doc} pos={pos} sigs={sigs}
                    corSig={corSig} caixaNaTela={caixaNaTela} tecnicoBoxes={tecnicoPos[d.doc] || []}
                    onClick={(e) => clicar(e, d.doc, pg)} />
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center justify-end gap-2 px-4 py-3 bg-white">
        <button onClick={onFechar} className="px-4 py-2 rounded-lg text-sm border">Cancelar</button>
        <button onClick={enviar} disabled={enviando}
          className="px-4 py-2 rounded-lg text-sm font-semibold text-white inline-flex items-center gap-2" style={{ background: GREEN }}>
          <Send className="w-4 h-4" /> {enviando ? 'Enviando…' : 'Enviar links'}
        </button>
      </div>
    </div>
  );
}

function Pagina({ pg, doc, pos, sigs, corSig, caixaNaTela, onClick, tecnicoBoxes = [] }) {
  const ref = React.useRef(null);
  const [rect, setRect] = React.useState({ w: 0, h: 0 });
  React.useEffect(() => {
    const upd = () => { if (ref.current) setRect({ w: ref.current.clientWidth, h: ref.current.clientHeight }); };
    upd(); window.addEventListener('resize', upd); return () => window.removeEventListener('resize', upd);
  }, []);
  return (
    <div className="relative inline-block w-full max-w-[820px] mb-2" style={{ cursor: 'crosshair' }}>
      <img ref={ref} src={`data:image/png;base64,${pg.imagem_b64}`} alt={`pág ${pg.pagina + 1}`}
        className="w-full rounded border border-gray-600" onClick={onClick} draggable={false} />
      {sigs.map((s) => {
        const boxes = (pos[s.parte_id] || {})[doc] || [];
        return boxes.filter((b) => b.pagina === pg.pagina).map((b, i) => {
          const c = caixaNaTela(b, pg, rect.w, rect.h);
          return <div key={s.parte_id + i} className="absolute pointer-events-none rounded"
            style={{ left: c.left, top: c.top, width: c.width, height: c.height, border: `2px solid ${corSig(s.parte_id)}`, background: `${corSig(s.parte_id)}22` }}>
            <span className="text-[9px] px-1" style={{ color: corSig(s.parte_id) }}>{s.nome?.split(' ')[0]}</span>
          </div>;
        });
      })}
      {tecnicoBoxes.filter((b) => b.pagina === pg.pagina).map((b, i) => {
        const c = caixaNaTela(b, pg, rect.w, rect.h);
        return <div key={'tec' + i} className="absolute pointer-events-none rounded"
          style={{ left: c.left, top: c.top, width: c.width, height: c.height, border: `2px dashed ${GOLD}`, background: `${GOLD}22` }}>
          <span className="text-[9px] px-1" style={{ color: '#9a7d2e' }}>RT (firma)</span>
        </div>;
      })}
    </div>
  );
}
