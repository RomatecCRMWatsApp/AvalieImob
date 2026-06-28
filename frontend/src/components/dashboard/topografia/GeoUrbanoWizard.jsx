// @module topografia/GeoUrbanoWizard — Wizard 7 passos do Geo Urbano (Remembramento).
// Espelha o GeorefWizard: autosave PATCH (debounce), uploads→R2, conferência com
// reconciliação matrícula↔BCI, preview SVG da poligonal, geração e entrega.
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft, Upload, Trash2, Plus, FileText, AlertTriangle, CheckCircle2,
  Download, Eye, RefreshCw,
} from 'lucide-react';
import { geoUrbanoAPI, assinaturaPosAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';
import AssinaturaPosicionadaModal from '../assinatura/AssinaturaPosicionadaModal';
import AssinaturaProprietarioModal from './AssinaturaProprietarioModal';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';

const PASSOS = ['Projeto', 'Uploads', 'Matrículas & BCI', 'Vértices & Mapa', 'Partes', 'Geração', 'Aprovação', 'Entrega'];
const STATUS_GERAL = {
  rascunho: 'Rascunho', assinatura_partes: 'Assinatura das partes', assinatura_tecnico: 'Assinatura do técnico',
  enviado_superintendencia: 'Enviado à Superintendência', aprovado: 'Aprovado', oficio_emitido: 'Ofício emitido', protocolado: 'Protocolado',
};
const ST_CELULA = {
  pendente: { t: 'Pendente', c: 'bg-gray-100 text-gray-500' },
  parcial: { t: 'Parcial', c: 'bg-amber-100 text-amber-700' },
  assinado: { t: 'Assinado', c: 'bg-emerald-100 text-emerald-700' },
  aprovado: { t: 'Aprovado', c: 'bg-emerald-100 text-emerald-700' },
};

const UPLOADS = [
  { tipo: 'imagem_imovel', label: 'Imagem do imóvel (aérea/satélite com perímetro)', req: true, multi: false },
  { tipo: 'mapa_atual', label: 'Mapa atual', req: true, multi: false },
  { tipo: 'mapa_remembramento', label: 'Mapa de remembramento', req: true, multi: false },
  { tipo: 'mapa_desdobro', label: 'Mapa(s) de desdobro (por lote resultante)', req: true, multi: true },
  { tipo: 'mapa_retificado', label: 'Mapa retificado (como está)', req: true, multi: false },
  { tipo: 'bci', label: 'BCI de cada lote', req: true, multi: true },
  { tipo: 'certidao_inteiro_teor', label: 'Certidão de inteiro teor (por matrícula)', req: true, multi: true },
  { tipo: 'cnd_iptu', label: 'CND de IPTU (negativa)', req: false, multi: true },
  { tipo: 'guia_iptu', label: 'Guia de IPTU (DAM)', req: false, multi: true },
  { tipo: 'comprovante_pagamento_iptu', label: 'Comprovante de pagamento do IPTU', req: false, multi: true },
  { tipo: 'art_trt', label: 'ART / TRT / RRT', req: true, multi: false },
  { tipo: 'art_trt_boleto', label: 'Boleto da TRT', req: true, multi: false },
  { tipo: 'comprovante_pagamento_trt', label: 'Comprovante de pagamento da TRT', req: true, multi: false },
  { tipo: 'contrato_social', label: 'Contrato social (PJ)', req: false, multi: true },
  { tipo: 'doc_socio', label: 'Documento do sócio (PJ)', req: false, multi: true },
  { tipo: 'doc_proprietario', label: 'Documento do proprietário (PF)', req: false, multi: true },
  { tipo: 'cnh', label: 'CNH / RG', req: false, multi: true },
  { tipo: 'certidao_casamento', label: 'Certidão de casamento (PF, se casado)', req: false, multi: true },
];

const DOCS_GERAVEIS = [
  ['requerimento_cartorio', 'Requerimento — Via 1 (Cartório de RI)'],
  ['requerimento_superintendencia', 'Requerimento — Via 2 (Superintendência)'],
  ['memorial_descritivo', 'Memorial Descritivo'],
  ['cadeia_dominical', 'Cadeia Dominical'],
  ['dossie', 'Dossiê consolidado (capa + sumário + tudo)'],
];

const inp = 'w-full border rounded-lg px-2.5 py-1.5 text-sm';
const lbl = 'block text-[11px] font-medium text-gray-500 mb-0.5';

function Field({ label, value, onChange, full, ...rest }) {
  return (
    <div className={full ? 'sm:col-span-2' : ''}>
      <label className={lbl}>{label}</label>
      <input className={inp} value={value ?? ''} onChange={(e) => onChange(e.target.value)} {...rest} />
    </div>
  );
}

// Preview SVG da poligonal (UTM coord_e/coord_n)
function Poligonal({ vertices = [] }) {
  const pts = (vertices || []).filter((v) => v.coord_e != null && v.coord_n != null)
    .map((v) => ({ x: Number(v.coord_e), y: Number(v.coord_n), de: v.de }));
  if (pts.length < 3) return <div className="text-sm text-gray-400 py-10 text-center">Sem vértices suficientes para o desenho.</div>;
  const W = 460, H = 300, pad = 30;
  const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const sx = (W - 2 * pad) / (maxX - minX || 1), sy = (H - 2 * pad) / (maxY - minY || 1);
  const s = Math.min(sx, sy);
  const xy = pts.map((p) => ({ x: pad + (p.x - minX) * s, y: H - pad - (p.y - minY) * s, de: p.de }));
  const poly = xy.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full border rounded-lg bg-white">
      <polygon points={poly} fill="rgba(12,51,32,0.08)" stroke={GREEN} strokeWidth="1.6" />
      {xy.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="3.2" fill={GOLD} stroke={GREEN} strokeWidth="0.8" />
          <text x={p.x + 5} y={p.y - 4} fontSize="8" fill={GREEN}>{(p.de || '').split('-').pop()}</text>
        </g>
      ))}
    </svg>
  );
}

export default function GeoUrbanoWizard() {
  const { id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();
  const [proj, setProj] = useState(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(0);
  const [rec, setRec] = useState(null);
  const [recLoad, setRecLoad] = useState(false);
  const [extraindo, setExtraindo] = useState(false);
  const [retAnalise, setRetAnalise] = useState(null);
  const [retBusy, setRetBusy] = useState(false);
  const [docsSel, setDocsSel] = useState(DOCS_GERAVEIS.map((d) => d[0]));
  const [gerando, setGerando] = useState(false);
  const [aprov, setAprov] = useState(null);
  const [aprovBusy, setAprovBusy] = useState(false);
  const [capaUrl, setCapaUrl] = useState(null);
  const [capaBusy, setCapaBusy] = useState(false);
  const [assinId, setAssinId] = useState(null);
  const [assinaturas, setAssinaturas] = useState({});
  const [preparandoAssin, setPreparandoAssin] = useState(null);
  const [propModal, setPropModal] = useState(false);
  const [propSessao, setPropSessao] = useState(null);
  const [propBusy, setPropBusy] = useState(false);

  const projRef = useRef(proj);
  const dirtyRef = useRef(false);
  const debounceRef = useRef(null);
  useEffect(() => { projRef.current = proj; }, [proj]);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const d = await geoUrbanoAPI.obter(id);
      setProj(d);
    } catch (e) {
      toast({ title: 'Projeto não encontrado', variant: 'destructive' });
      nav('/dashboard/topografia/geo-urbano');
    } finally {
      setLoading(false);
    }
  }, [id, nav, toast]);
  useEffect(() => { carregar(); }, [carregar]);

  const salvar = useCallback(async (silent = true) => {
    const p = projRef.current;
    if (!p || !dirtyRef.current) return;
    try {
      const payload = {
        denominacao_imovel: p.denominacao_imovel, tipo_servico: p.tipo_servico, tema: p.tema,
        municipio: p.municipio, uf: p.uf, bairro: p.bairro, loteamento: p.loteamento,
        quadra: p.quadra, lote_resultante: p.lote_resultante, endereco: p.endereco,
        cmi_resultante: p.cmi_resultante, cadastro_novo: p.cadastro_novo, cadastro_antigo: p.cadastro_antigo,
        area_declarada_m2: p.area_declarada_m2 === '' ? null : Number(p.area_declarada_m2),
        perimetro_m: p.perimetro_m === '' ? null : Number(p.perimetro_m),
        trt_numero: p.trt_numero, cartorio: p.cartorio, superintendencia: p.superintendencia,
        matriculas: p.matriculas, bci: p.bci, vertices: p.vertices, partes: p.partes, iptu: p.iptu,
      };
      const upd = await geoUrbanoAPI.atualizar(p.id, payload);
      dirtyRef.current = false;
      if (upd?.completude != null) setProj((x) => ({ ...x, completude: upd.completude }));
      if (!silent) toast({ title: 'Salvo' });
    } catch (e) {
      toast({ title: 'Erro ao salvar', variant: 'destructive' });
    }
  }, [toast]);

  const mark = () => {
    dirtyRef.current = true;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => salvar(true), 1200);
  };
  const upd = (patch) => { setProj((p) => ({ ...p, ...patch })); mark(); };
  const updArr = (campo, i, patch) => {
    setProj((p) => {
      const arr = [...(p[campo] || [])];
      arr[i] = { ...arr[i], ...patch };
      return { ...p, [campo]: arr };
    });
    mark();
  };
  // Lotes resultantes (desdobro)
  const addLote = () => {
    const n = (proj.lotes_resultantes || []).length + 1;
    upd({ lotes_resultantes: [...(proj.lotes_resultantes || []), { id: `tmp-${Date.now()}`, ordem: n, denominacao: '', confrontacoes: [] }] });
  };
  const rmLote = (i) => upd({ lotes_resultantes: (proj.lotes_resultantes || []).filter((_, k) => k !== i) });
  const setLoteConf = (i, lado, valor, campo) => {
    setProj((p) => {
      const lotes = [...(p.lotes_resultantes || [])];
      const l = { ...lotes[i] };
      const confs = [...(l.confrontacoes || [])];
      const idx = confs.findIndex((c) => c.lado === lado);
      const novo = idx < 0 ? { lado } : { ...confs[idx] };
      novo[campo] = campo === 'medida_m' ? (valor === '' ? null : Number(valor)) : valor;
      if (idx < 0) confs.push(novo); else confs[idx] = novo;
      l.confrontacoes = confs; lotes[i] = l;
      return { ...p, lotes_resultantes: lotes };
    });
    mark();
  };
  const confDe = (l, lado, campo) => {
    const c = (l.confrontacoes || []).find((x) => x.lado === lado);
    return c ? (c[campo] ?? '') : '';
  };

  // troca de passo → flush + carrega reconciliação/aprovação ao entrar
  const irPasso = async (n) => {
    if (dirtyRef.current) await salvar(true);
    setStep(n);
    if (n === 2) carregarRec();
    if (n === 6) carregarAprov();
  };

  const carregarRec = async () => {
    setRecLoad(true);
    try { setRec(await geoUrbanoAPI.reconciliacao(id)); }
    catch (e) { /* silencioso */ }
    finally { setRecLoad(false); }
    if (proj?.tipo_servico === 'retificacao') {
      try { setRetAnalise(await geoUrbanoAPI.retificacaoAnalise(id)); } catch (e) { /* silencioso */ }
    }
  };
  const confirmarRet = async () => {
    setRetBusy(true);
    try { setRetAnalise(await geoUrbanoAPI.retificacaoConfirmar(id)); toast({ title: 'Quadro de retificação confirmado' }); }
    catch (e) { toast({ title: 'Erro ao confirmar', variant: 'destructive' }); }
    finally { setRetBusy(false); }
  };

  const carregarAprov = async () => {
    try { setAprov(await geoUrbanoAPI.aprovacaoStatus(id)); }
    catch (e) { /* silencioso */ }
    recarregarAssinaturas();
  };
  const recarregarAssinaturas = async () => {
    try {
      const lst = await geoUrbanoAPI.listarAssinaturas(id);
      const map = {};
      (lst || []).forEach((a) => { map[a.doc] = a; });
      setAssinaturas(map);
    } catch (e) { /* silencioso */ }
    try { setPropSessao(await geoUrbanoAPI.propSessao(id)); } catch (e) { /* silencioso */ }
  };
  const reenviarProp = async () => {
    setPropBusy(true);
    try { const r = await geoUrbanoAPI.propReenviar(id); toast({ title: `Reenviado: ${r.enviados || 0}` }); recarregarAssinaturas(); }
    catch (e) { toast({ title: 'Erro ao reenviar', variant: 'destructive' }); }
    finally { setPropBusy(false); }
  };
  const abrirAssinaturaTecnico = async (peca) => {
    setPreparandoAssin(peca);
    try {
      const r = await geoUrbanoAPI.prepararAssinatura(id, { doc: peca, tema: proj.tema });
      setAssinId(r.id);
    } catch (e) {
      toast({ title: 'Erro ao preparar assinatura', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setPreparandoAssin(null); }
  };
  const verAssinado = async (assId) => {
    try { await verBlob(assinaturaPosAPI.downloadIcp('geo_urbano', assId)); }
    catch (e) { toast({ title: 'Não foi possível abrir o assinado', variant: 'destructive' }); }
  };
  const aprovarPeca = async (campo, valor) => {
    setAprovBusy(true);
    try { setAprov(await geoUrbanoAPI.aprovacaoSuperintendencia(id, { [campo]: valor })); }
    catch (e) { toast({ title: 'Erro ao registrar aprovação', variant: 'destructive' }); }
    finally { setAprovBusy(false); }
  };
  const enviarSuper = async () => {
    setAprovBusy(true);
    try { setAprov(await geoUrbanoAPI.aprovacaoEnviar(id)); toast({ title: 'Enviado à Superintendência' }); }
    catch (e) { toast({ title: 'Erro ao enviar', variant: 'destructive' }); }
    finally { setAprovBusy(false); }
  };
  const emitirOficio = async () => {
    setAprovBusy(true);
    try {
      const r = await geoUrbanoAPI.gerarOficio(id);
      setAprov(r.status);
      toast({ title: `Ofício ${r.oficio_numero} emitido` });
    } catch (e) {
      toast({ title: 'Erro ao emitir ofício', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setAprovBusy(false); }
  };

  const extrairDocs = async () => {
    setExtraindo(true);
    try {
      const r = await geoUrbanoAPI.extrair(id);
      await carregar();
      await carregarRec();
      const e = r.extraido || {};
      toast({ title: 'Extração concluída', description: `${e.matriculas || 0} matrículas · ${e.bci || 0} BCI · ${e.vertices || 0} vértices · ${e.iptu || 0} IPTU/CND` });
      (r.avisos || []).forEach((a) => toast({ title: 'Aviso', description: a }));
    } catch (e) {
      toast({ title: 'Erro na extração', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setExtraindo(false); }
  };

  const enviar = async (tipo, files) => {
    const lista = Array.from(files || []);
    if (!lista.length) return;
    try {
      for (const f of lista) await geoUrbanoAPI.upload(id, tipo, f);
      await carregar();
      toast({ title: `${lista.length} arquivo(s) enviado(s)` });
    } catch (e) {
      toast({ title: 'Falha no upload', description: e?.response?.data?.detail || '', variant: 'destructive' });
    }
  };
  const removerUp = async (tipo, itemId) => {
    try { await geoUrbanoAPI.removerUpload(id, tipo, itemId); await carregar(); }
    catch (e) { toast({ title: 'Erro ao remover', variant: 'destructive' }); }
  };

  const carregarCapa = async () => {
    setCapaBusy(true);
    try {
      const blob = await geoUrbanoAPI.capaPreview(id);
      setCapaUrl((old) => { if (old) URL.revokeObjectURL(old); return URL.createObjectURL(blob); });
    } catch (e) {
      toast({ title: 'Envie a imagem do imóvel para gerar a capa', variant: 'destructive' });
    } finally { setCapaBusy(false); }
  };

  const salvarBlob = (blob, nome) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = nome; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  };
  const verBlob = async (promise) => {
    const win = window.open('', '_blank');
    try {
      const blob = await promise;
      const url = URL.createObjectURL(blob);
      if (win) win.location.href = url; else window.open(url, '_blank');
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) { if (win) win.close(); toast({ title: 'Erro ao abrir documento', variant: 'destructive' }); }
  };

  const gerar = async () => {
    setGerando(true);
    try {
      await salvar(true);
      const r = await geoUrbanoAPI.gerar(id, { documentos: docsSel, tema: proj.tema });
      setProj((p) => ({ ...p, status: 'assinatura' }));
      const blo = r?.reconciliacao?.bloqueantes || 0;
      toast({ title: 'Documentos prontos', description: blo ? `${blo} alerta(s) bloqueante(s) na reconciliação` : 'Reconciliação OK' });
      setStep(6);
    } catch (e) {
      toast({ title: 'Erro ao gerar', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setGerando(false); }
  };

  if (loading || !proj) return <div className="py-24"><BrandSpinner label="Carregando…" /></div>;

  const nb = proj.numero || 'geo-urbano';
  const uploads = proj.uploads || {};
  const isDesdobro = proj.tipo_servico === 'desdobro';
  const isRetificacao = proj.tipo_servico === 'retificacao';
  const lotes = proj.lotes_resultantes || [];

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <header className="flex items-center gap-3 mb-5">
        <button onClick={() => nav('/dashboard/topografia/geo-urbano')} className="p-2 rounded-lg hover:bg-gray-100">
          <ArrowLeft className="w-5 h-5" style={{ color: GREEN }} />
        </button>
        <div className="flex-1">
          <h1 className="text-lg font-bold leading-tight" style={{ color: GREEN }}>{proj.denominacao_imovel || 'Projeto'}</h1>
          <p className="text-xs text-gray-500">{nb} · Remembramento · Etapa {step + 1} de {PASSOS.length} · {proj.completude || 0}% preenchido</p>
        </div>
      </header>

      {/* chips de etapa */}
      <div className="flex flex-wrap gap-1.5 mb-5">
        {PASSOS.map((p, i) => (
          <button key={p} onClick={() => irPasso(i)}
            className={`text-[11px] px-2.5 py-1 rounded-full border ${i === step ? 'text-white' : 'text-gray-600 bg-white'}`}
            style={i === step ? { background: GREEN, borderColor: GREEN } : {}}>
            {i + 1}. {p}
          </button>
        ))}
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden mb-6">
        <div className="h-full rounded-full" style={{ width: `${((step + 1) / PASSOS.length) * 100}%`, background: GOLD }} />
      </div>

      {/* ─────────────────────────── Passo 1: Projeto ─────────────────────────── */}
      {step === 0 && (
        <div className="space-y-6">
          <section className="rounded-xl border bg-white p-5">
            <h2 className="font-semibold mb-3" style={{ color: GREEN }}>Identificação do imóvel resultante</h2>
            <div className="grid sm:grid-cols-2 gap-3">
              <Field label="Denominação do imóvel" full value={proj.denominacao_imovel} onChange={(v) => upd({ denominacao_imovel: v })} />
              <Field label="Município" value={proj.municipio} onChange={(v) => upd({ municipio: v })} />
              <Field label="UF" value={proj.uf} onChange={(v) => upd({ uf: v })} />
              <Field label="Bairro" value={proj.bairro} onChange={(v) => upd({ bairro: v })} />
              <Field label="Loteamento" value={proj.loteamento} onChange={(v) => upd({ loteamento: v })} />
              <Field label="Quadra" value={proj.quadra} onChange={(v) => upd({ quadra: v })} />
              <Field label="Lote resultante" value={proj.lote_resultante} onChange={(v) => upd({ lote_resultante: v })} />
              <Field label="Endereço" full value={proj.endereco} onChange={(v) => upd({ endereco: v })} />
              <Field label="CMI resultante" value={proj.cmi_resultante} onChange={(v) => upd({ cmi_resultante: v })} />
              <Field label="Nº da TRT" value={proj.trt_numero} onChange={(v) => upd({ trt_numero: v })} />
              <Field label="Cadastro novo" value={proj.cadastro_novo} onChange={(v) => upd({ cadastro_novo: v })} />
              <Field label="Cadastro antigo" value={proj.cadastro_antigo} onChange={(v) => upd({ cadastro_antigo: v })} />
              <Field label="Área declarada (m²)" type="number" value={proj.area_declarada_m2} onChange={(v) => upd({ area_declarada_m2: v })} />
              <Field label="Perímetro (m)" type="number" value={proj.perimetro_m} onChange={(v) => upd({ perimetro_m: v })} />
            </div>
          </section>
          {isDesdobro && (
            <section className="rounded-xl border border-amber-200 bg-amber-50/40 p-5">
              <h2 className="font-semibold mb-3" style={{ color: GREEN }}>Desdobro — lote-mãe → N lotes</h2>
              <div className="grid sm:grid-cols-2 gap-3">
                <Field label="Área da matrícula-mãe (m²)" type="number" value={proj.area_mae_m2} onChange={(v) => upd({ area_mae_m2: v === '' ? null : Number(v) })} />
                <Field label="Área de via/doação (m²) — se houver" type="number" value={proj.area_via_doacao_m2} onChange={(v) => upd({ area_via_doacao_m2: v === '' ? 0 : Number(v) })} />
                <Field label="Lote mínimo municipal (m²)" type="number" value={proj.lote_minimo_municipal_m2} onChange={(v) => upd({ lote_minimo_municipal_m2: v === '' ? null : Number(v) })} />
                <Field label="Testada mínima (m)" type="number" value={proj.testada_minima_m} onChange={(v) => upd({ testada_minima_m: v === '' ? null : Number(v) })} />
              </div>
              <p className="text-[11px] text-gray-500 mt-2">Com área de via/doação &gt; 0 o ato é classificado como desmembramento. Cadastre os lotes resultantes na etapa Matrículas &amp; BCI.</p>
            </section>
          )}
          {isRetificacao && (
            <section className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-5">
              <h2 className="font-semibold mb-3" style={{ color: GREEN }}>Retificação — tipo de análise</h2>
              <select className={inp + ' max-w-xs'} value={proj.retificacao_tipo || 'mista'} onChange={(e) => upd({ retificacao_tipo: e.target.value })}>
                <option value="cadastral">Cadastral (matrícula × BCI)</option>
                <option value="area_perimetro">Área/Perímetro (mapa atual × retificado)</option>
                <option value="mista">Mista (ambos os eixos)</option>
              </select>
              <p className="text-[11px] text-gray-500 mt-2">A análise compara registro × cadastro e/ou a geometria antes × depois (art. 213, Lei 6.015/73). O quadro "de → para" é conferido na etapa Matrículas &amp; BCI.</p>
            </section>
          )}
          <section className="rounded-xl border bg-white p-5">
            <h2 className="font-semibold mb-3" style={{ color: GREEN }}>Destinatários do Requerimento (2 vias)</h2>
            <div className="grid sm:grid-cols-2 gap-3">
              <Field label="Cartório de RI" full value={proj.cartorio?.nome} onChange={(v) => upd({ cartorio: { ...proj.cartorio, nome: v } })} />
              <Field label="Endereço do cartório" value={proj.cartorio?.endereco} onChange={(v) => upd({ cartorio: { ...proj.cartorio, endereco: v } })} />
              <Field label="Titular do cartório" value={proj.cartorio?.titular} onChange={(v) => upd({ cartorio: { ...proj.cartorio, titular: v } })} />
              <Field label="Superintendência" full value={proj.superintendencia?.nome} onChange={(v) => upd({ superintendencia: { ...proj.superintendencia, nome: v } })} />
              <Field label="Responsável" value={proj.superintendencia?.responsavel} onChange={(v) => upd({ superintendencia: { ...proj.superintendencia, responsavel: v } })} />
              <Field label="Portaria" value={proj.superintendencia?.portaria} onChange={(v) => upd({ superintendencia: { ...proj.superintendencia, portaria: v } })} />
            </div>
          </section>
        </div>
      )}

      {/* ─────────────────────────── Passo 2: Uploads ─────────────────────────── */}
      {step === 1 && (
        <>
        <div className="flex items-center justify-between mb-3 rounded-xl border border-emerald-200 bg-emerald-50/50 p-3">
          <span className="text-sm text-gray-600">Depois de enviar o Mapa de Remembramento e os BCIs/IPTU, extraia os dados automaticamente.</span>
          <button onClick={extrairDocs} disabled={extraindo}
            className="text-xs inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-white shrink-0" style={{ background: GREEN }}>
            <RefreshCw className={`w-3.5 h-3.5 ${extraindo ? 'animate-spin' : ''}`} /> {extraindo ? 'Extraindo…' : 'Extrair dos documentos'}
          </button>
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          {UPLOADS.filter((u) => {
            if (u.tipo === 'mapa_remembramento') return !isDesdobro && !isRetificacao;
            if (u.tipo === 'mapa_desdobro') return isDesdobro;
            if (u.tipo === 'mapa_retificado') return isRetificacao;
            return true;
          }).map((u) => {
            const itens = uploads[u.tipo] || [];
            return (
              <div key={u.tipo} className="rounded-xl border bg-white p-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700">{u.label}</span>
                  {u.req && <span className="text-[10px] text-amber-600 font-semibold">obrigatório</span>}
                </div>
                <label className="flex items-center gap-2 text-xs cursor-pointer text-emerald-700 hover:underline">
                  <Upload className="w-4 h-4" />
                  {itens.length ? 'Enviar mais' : 'Enviar arquivo'}
                  <input type="file" className="hidden" multiple={u.multi}
                    accept=".pdf,image/*"
                    onChange={(e) => enviar(u.tipo, e.target.files)} />
                </label>
                {itens.map((it) => (
                  <div key={it.id} className="flex items-center justify-between text-xs text-gray-500 mt-1.5">
                    <span className="truncate flex items-center gap-1"><FileText className="w-3 h-3" />{it.nome}</span>
                    <Trash2 className="w-3.5 h-3.5 text-gray-300 hover:text-red-500 cursor-pointer shrink-0"
                      onClick={() => removerUp(u.tipo, it.id)} />
                  </div>
                ))}
              </div>
            );
          })}
        </div>
        </>
      )}

      {/* ───────────────────── Passo 3: Matrículas & BCI + reconcile ───────────── */}
      {step === 2 && (
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold" style={{ color: GREEN }}>Conferência — Matrículas, BCI e reconciliação</h2>
            <div className="flex items-center gap-3">
              <button onClick={extrairDocs} disabled={extraindo} className="text-xs inline-flex items-center gap-1 text-emerald-700 hover:underline">
                <RefreshCw className={`w-3.5 h-3.5 ${extraindo ? 'animate-spin' : ''}`} /> {extraindo ? 'Extraindo…' : 'Extrair dos documentos'}
              </button>
              <button onClick={carregarRec} className="text-xs inline-flex items-center gap-1 text-emerald-700 hover:underline">
                <RefreshCw className="w-3.5 h-3.5" /> Reavaliar
              </button>
            </div>
          </div>

          {/* painel de reconciliação */}
          <div className="rounded-xl border bg-white p-4">
            {recLoad ? <p className="text-sm text-gray-400">Avaliando…</p> : rec ? (
              <>
                <div className="flex items-center gap-2 text-sm mb-2">
                  {rec.resumo?.pode_protocolar
                    ? <span className="inline-flex items-center gap-1 text-emerald-700"><CheckCircle2 className="w-4 h-4" /> Reconciliação OK — pode protocolar</span>
                    : <span className="inline-flex items-center gap-1 text-amber-700"><AlertTriangle className="w-4 h-4" /> {rec.resumo?.bloqueantes || 0} alerta(s) bloqueante(s)</span>}
                </div>
                {(rec.alertas || []).map((a, i) => (
                  <div key={i} className={`text-xs rounded px-2 py-1 mb-1 ${a.severidade === 'bloqueante' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'}`}>
                    <strong>{a.tipo}</strong> — {a.mensagem}{a.acao_sugerida ? ` · Ação: ${a.acao_sugerida}` : ''}
                  </div>
                ))}
                {rec.areas?.aviso && <div className="text-xs text-amber-700 mt-1">{rec.areas.aviso}</div>}
                {rec.areas && !rec.areas.aviso && (
                  <div className="text-xs text-gray-500 mt-1">Área calculada {Number(rec.areas.area_calculada_m2).toLocaleString('pt-BR')} m² · perímetro {rec.areas.perimetro_m} m (confere).</div>
                )}
              </>
            ) : <p className="text-sm text-gray-400">Clique em “Reavaliar” para conferir.</p>}
          </div>

          {/* lotes resultantes (desdobro) */}
          {isDesdobro && (
            <div className="rounded-xl border bg-white p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold" style={{ color: GREEN }}>Lotes resultantes</h3>
                <button onClick={addLote} className="text-xs inline-flex items-center gap-1 text-emerald-700 hover:underline"><Plus className="w-3.5 h-3.5" /> Adicionar lote</button>
              </div>
              {rec?.conservacao && (
                <div className={`text-xs rounded px-2 py-1 ${rec.conservacao.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                  Σ lotes {rec.conservacao.soma_resultantes_m2} + via {rec.conservacao.via_doacao_m2} = {rec.conservacao.total_m2} m² · mãe {rec.conservacao.area_mae_m2} m² · {rec.conservacao.modalidade}
                  {rec.conservacao.aviso ? ` — ${rec.conservacao.aviso}` : ' ✓ fecha'}
                </div>
              )}
              {(rec?.urbanisticas || []).map((a, i) => (
                <div key={i} className="text-xs bg-amber-50 text-amber-700 rounded px-2 py-1">{a.mensagem}</div>
              ))}
              {lotes.map((l, i) => (
                <div key={l.id || i} className="rounded-lg border p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium" style={{ color: GREEN }}>Lote {i + 1}</span>
                    <Trash2 className="w-4 h-4 text-gray-300 hover:text-red-500 cursor-pointer" onClick={() => rmLote(i)} />
                  </div>
                  <div className="grid sm:grid-cols-3 gap-2">
                    <Field label="Denominação" value={l.denominacao} onChange={(v) => updArr('lotes_resultantes', i, { denominacao: v })} />
                    <Field label="Área (m²)" type="number" value={l.area_declarada_m2} onChange={(v) => updArr('lotes_resultantes', i, { area_declarada_m2: v === '' ? null : Number(v) })} />
                    <Field label="Perímetro (m)" type="number" value={l.perimetro_m} onChange={(v) => updArr('lotes_resultantes', i, { perimetro_m: v === '' ? null : Number(v) })} />
                  </div>
                  <div className="grid sm:grid-cols-2 gap-2 mt-2">
                    {['frente', 'lateral_direita', 'lateral_esquerda', 'fundo'].map((lado) => (
                      <div key={lado}>
                        <label className={lbl}>{lado.replace('_', ' ')} (m · confrontante)</label>
                        <div className="flex gap-1">
                          <input className={inp + ' w-20'} type="number" placeholder="m" value={confDe(l, lado, 'medida_m')} onChange={(e) => setLoteConf(i, lado, e.target.value, 'medida_m')} />
                          <input className={inp} placeholder="confrontante" value={confDe(l, lado, 'confrontante')} onChange={(e) => setLoteConf(i, lado, e.target.value, 'confrontante')} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {!lotes.length && <p className="text-sm text-gray-400">Adicione os lotes resultantes — a soma das áreas deve fechar com a matrícula-mãe.</p>}
            </div>
          )}

          {/* análise comparativa (retificação) */}
          {isRetificacao && (
            <div className="rounded-xl border bg-white p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold" style={{ color: GREEN }}>Análise comparativa (de → para)</h3>
                <button onClick={confirmarRet} disabled={retBusy} className="text-xs px-3 py-1.5 rounded-lg border hover:bg-gray-50">{retBusy ? 'Confirmando…' : 'Confirmar quadro'}</button>
              </div>
              {(retAnalise?.cadastral_diffs || []).length > 0 && (
                <div className="overflow-x-auto">
                  <div className="text-xs font-semibold text-gray-600 mb-1">Cadastral — Matrícula × BCI</div>
                  <table className="w-full text-xs">
                    <thead><tr className="text-gray-400 text-left"><th className="py-1">Campo</th><th>Registro</th><th>BCI</th><th>Correto</th><th>Status</th></tr></thead>
                    <tbody>
                      {retAnalise.cadastral_diffs.map((d, i) => (
                        <tr key={i} className={`border-t ${d.divergente ? 'bg-red-50' : ''}`}>
                          <td className="py-1">{d.campo}</td><td>{String(d.valor_registro)}</td><td>{String(d.valor_bci)}</td><td>{String(d.valor_correto)}</td>
                          <td>{d.divergente ? <span className="text-red-700 font-semibold">divergente</span> : <span className="text-emerald-700">ok</span>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {retAnalise?.geometrico && Object.keys(retAnalise.geometrico).length > 0 && (
                <div className="text-xs text-gray-600">
                  <div className="font-semibold mb-1">Geométrico — antes × depois</div>
                  Área {retAnalise.geometrico.area_antes_m2} → {retAnalise.geometrico.area_depois_m2} m² (Δ {retAnalise.geometrico.area_delta_m2}) · Perímetro {retAnalise.geometrico.perimetro_antes_m} → {retAnalise.geometrico.perimetro_depois_m} m
                  {(retAnalise.geometrico.confrontantes_diff || []).filter((c) => c.alterado).map((c, i) => (
                    <div key={i} className="text-amber-700">Confrontação {c.lado}: “{c.de}” → “{c.para}”</div>
                  ))}
                </div>
              )}
              {!retAnalise && <p className="text-sm text-gray-400">Clique em “Reavaliar” para rodar a análise.</p>}
            </div>
          )}

          {/* matrículas */}
          {(proj.matriculas || []).map((m, i) => {
            const bci = (proj.bci || [])[i] || {};
            return (
              <div key={m.id || i} className="rounded-xl border bg-white p-4">
                <div className="text-sm font-semibold mb-2" style={{ color: GREEN }}>
                  {i + 1}- Matrícula {m.matricula || '—'} · Lote {m.lote_origem || '—'}
                </div>
                <div className="grid sm:grid-cols-4 gap-2">
                  <Field label="Matrícula" value={m.matricula} onChange={(v) => updArr('matriculas', i, { matricula: v })} />
                  <Field label="Livro" value={m.livro} onChange={(v) => updArr('matriculas', i, { livro: v })} />
                  <Field label="Folhas" value={m.folhas} onChange={(v) => updArr('matriculas', i, { folhas: v })} />
                  <Field label="Lote" value={m.lote_origem} onChange={(v) => updArr('matriculas', i, { lote_origem: v })} />
                  <Field label="Cód. imóvel" value={m.cod_imovel} onChange={(v) => updArr('matriculas', i, { cod_imovel: v })} />
                  <Field label="Loc. cartográfica" value={m.loc_cartografica} onChange={(v) => updArr('matriculas', i, { loc_cartografica: v })} />
                  <Field label="Área (m²)" type="number" value={m.area_m2} onChange={(v) => updArr('matriculas', i, { area_m2: Number(v) })} />
                  <Field label="Proprietário (registro)" value={m.proprietario_registral?.nome}
                    onChange={(v) => updArr('matriculas', i, { proprietario_registral: { ...m.proprietario_registral, nome: v } })} />
                </div>
                <div className="mt-2 text-[11px] text-gray-500">
                  Confrontações: {(m.confrontacoes || []).map((c) => `${c.lado} ${c.medida_m}m (${c.confrontante})`).join(' · ') || '—'}
                </div>
                <div className="mt-2 pt-2 border-t grid sm:grid-cols-3 gap-2">
                  <Field label="BCI — proprietário cadastral" value={bci.proprietario_cadastral?.nome}
                    onChange={(v) => updArr('bci', i, { proprietario_cadastral: { ...bci.proprietario_cadastral, nome: v } })} />
                  <Field label="BCI — CPF/CNPJ" value={bci.proprietario_cadastral?.doc}
                    onChange={(v) => updArr('bci', i, { proprietario_cadastral: { ...bci.proprietario_cadastral, doc: v } })} />
                  <Field label="BCI — inscrição contribuinte" value={bci.inscricao_contribuinte}
                    onChange={(v) => updArr('bci', i, { inscricao_contribuinte: v })} />
                </div>
              </div>
            );
          })}
          {!(proj.matriculas || []).length && (
            <p className="text-sm text-gray-400">Nenhuma matrícula. A extração automática das certidões entra em uma próxima etapa; por ora use o projeto-teste J&G ou edite manualmente.</p>
          )}
        </div>
      )}

      {/* ───────────────────────── Passo 4: Vértices & Mapa ─────────────────────── */}
      {step === 3 && (
        <div className="grid md:grid-cols-2 gap-5">
          <div className="rounded-xl border bg-white p-4">
            <h2 className="font-semibold mb-2" style={{ color: GREEN }}>Poligonal resultante</h2>
            <Poligonal vertices={proj.vertices} />
            <p className="text-xs text-gray-500 mt-2">
              Área declarada {proj.area_declarada_m2 ? Number(proj.area_declarada_m2).toLocaleString('pt-BR') : '—'} m² · Perímetro {proj.perimetro_m || '—'} m
            </p>
          </div>
          <div className="rounded-xl border bg-white p-4 overflow-x-auto">
            <h2 className="font-semibold mb-2" style={{ color: GREEN }}>Quadro de vértices</h2>
            <table className="w-full text-xs">
              <thead><tr className="text-gray-400 text-left">
                <th className="py-1">De</th><th>Para</th><th>Coord. N</th><th>Coord. E</th><th>Azimute</th><th>Dist.</th><th>Confrontante</th>
              </tr></thead>
              <tbody>
                {(proj.vertices || []).map((v, i) => (
                  <tr key={v.id || i} className="border-t">
                    <td className="py-1">{v.de}</td><td>{v.para}</td>
                    <td>{v.coord_n}</td><td>{v.coord_e}</td><td>{v.azimute}</td><td>{v.distancia_m}</td><td>{v.confrontante_lado}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!(proj.vertices || []).length && <p className="text-sm text-gray-400 mt-2">Sem vértices. Virão da planilha do mapa de remembramento (extração).</p>}
          </div>
        </div>
      )}

      {/* ─────────────────────────── Passo 5: Partes ─────────────────────────── */}
      {step === 4 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold" style={{ color: GREEN }}>Requerentes e representantes</h2>
            <button onClick={() => { upd({ partes: [...(proj.partes || []), { id: `tmp-${Date.now()}`, papel: 'requerente', tipo_pessoa: 'fisica' }] }); }}
              className="text-xs inline-flex items-center gap-1 text-emerald-700 hover:underline"><Plus className="w-3.5 h-3.5" /> Adicionar parte</button>
          </div>
          {(proj.partes || []).map((p, i) => (
            <div key={p.id || i} className="rounded-xl border bg-white p-4">
              <div className="flex items-center gap-2 mb-2">
                <select className={inp + ' max-w-[150px]'} value={p.papel} onChange={(e) => updArr('partes', i, { papel: e.target.value })}>
                  <option value="requerente">Requerente</option>
                  <option value="representante">Representante</option>
                  <option value="socio">Sócio</option>
                  <option value="conjuge">Cônjuge</option>
                </select>
                <select className={inp + ' max-w-[140px]'} value={p.tipo_pessoa} onChange={(e) => updArr('partes', i, { tipo_pessoa: e.target.value })}>
                  <option value="juridica">Pessoa Jurídica</option>
                  <option value="fisica">Pessoa Física</option>
                </select>
                <Trash2 className="w-4 h-4 text-gray-300 hover:text-red-500 cursor-pointer ml-auto"
                  onClick={() => upd({ partes: proj.partes.filter((_, k) => k !== i) })} />
              </div>
              {p.tipo_pessoa === 'juridica' ? (
                <div className="grid sm:grid-cols-2 gap-2">
                  <Field label="Razão social" value={p.razao_social} onChange={(v) => updArr('partes', i, { razao_social: v })} />
                  <Field label="CNPJ" value={p.cnpj} onChange={(v) => updArr('partes', i, { cnpj: v })} />
                  <Field label="NIRE" value={p.nire} onChange={(v) => updArr('partes', i, { nire: v })} />
                  <Field label="Junta/registro" value={p.junta} onChange={(v) => updArr('partes', i, { junta: v })} />
                  <Field label="Sede" full value={p.sede} onChange={(v) => updArr('partes', i, { sede: v })} />
                </div>
              ) : (
                <div className="grid sm:grid-cols-2 gap-2">
                  <Field label="Nome" value={p.nome} onChange={(v) => updArr('partes', i, { nome: v })} />
                  <Field label="CPF" value={p.cpf} onChange={(v) => updArr('partes', i, { cpf: v })} />
                  <Field label="RG" value={p.rg} onChange={(v) => updArr('partes', i, { rg: v })} />
                  <Field label="Profissão" value={p.profissao} onChange={(v) => updArr('partes', i, { profissao: v })} />
                  <Field label="Estado civil" value={p.estado_civil} onChange={(v) => updArr('partes', i, { estado_civil: v })} />
                  <Field label="Endereço" full value={p.endereco} onChange={(v) => updArr('partes', i, { endereco: v })} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ─────────────────────────── Passo 6: Geração ─────────────────────────── */}
      {step === 5 && (
        <div className="space-y-5">
        <div className="rounded-xl border bg-white p-5">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-semibold" style={{ color: GREEN }}>Capa do processo — "Lupa Geo"</h2>
            <button onClick={carregarCapa} disabled={capaBusy}
              className="text-xs inline-flex items-center gap-1 text-emerald-700 hover:underline">
              <RefreshCw className="w-3.5 h-3.5" /> {capaBusy ? 'Gerando…' : 'Atualizar prévia'}
            </button>
          </div>
          {capaUrl ? (
            <img src={capaUrl} alt="Prévia da capa" className="mx-auto max-h-[460px] rounded-lg border shadow-sm" />
          ) : (
            <p className="text-sm text-gray-400">Envie a “Imagem do imóvel” na etapa Uploads e clique em “Atualizar prévia”.</p>
          )}
        </div>
        <div className="rounded-xl border bg-white p-5 space-y-3">
          <h2 className="font-semibold" style={{ color: GREEN }}>Gerar documentos</h2>
          <div className="grid sm:grid-cols-2 gap-2">
            {DOCS_GERAVEIS.map(([k, lab]) => (
              <label key={k} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={docsSel.includes(k)}
                  onChange={(e) => setDocsSel((s) => e.target.checked ? [...s, k] : s.filter((x) => x !== k))} />
                {lab}
              </label>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-600">Tema:</label>
            <select className={inp + ' max-w-[260px]'} value={proj.tema} onChange={(e) => upd({ tema: e.target.value })}>
              <option value="prime_i">Prime I — Elegante</option>
              <option value="prime_ii">Prime II — Editorial</option>
              <option value="tradicional">Tradicional — Sóbrio</option>
            </select>
          </div>
          <button onClick={gerar} disabled={gerando}
            className="px-4 py-2 rounded-lg text-sm font-semibold text-white" style={{ background: GREEN }}>
            {gerando ? 'Gerando…' : 'Gerar e ir para Aprovação'}
          </button>
        </div>
        </div>
      )}

      {/* ─────────────────────── Passo 7: Aprovação & Assinaturas ──────────────── */}
      {step === 6 && (
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold" style={{ color: GREEN }}>Aprovação & Assinaturas</h2>
            {aprov && (
              <span className="text-xs px-2.5 py-1 rounded-full font-semibold" style={{ background: GOLD, color: GREEN }}>
                {STATUS_GERAL[aprov.status_geral] || aprov.status_geral}
              </span>
            )}
          </div>

          {/* matriz §1 */}
          <div className="rounded-xl border bg-white p-4 overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-gray-400 text-left">
                <th className="py-1">Documento</th><th>Proprietário</th><th>Técnico</th><th>Superintendência</th>
              </tr></thead>
              <tbody>
                {(aprov?.matriz || []).map((row) => (
                  <tr key={row.documento} className="border-t">
                    <td className="py-1.5 font-medium text-gray-700">{row.label}</td>
                    {['proprietario', 'tecnico', 'superintendente'].map((papel) => {
                      const c = row.celulas[papel];
                      const s = c && (ST_CELULA[c.status] || ST_CELULA.pendente);
                      return (
                        <td key={papel} className="py-1.5">
                          {c ? (
                            <span className={`px-1.5 py-0.5 rounded ${s.c}`}>{s.t}{c.carimbo ? ' + carimbo' : ''}</span>
                          ) : <span className="text-gray-300">—</span>}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[11px] text-gray-400 mt-2">
              O proprietário assina Requerimento + ART/TRT por WhatsApp (próximo increment).
              O técnico assina abaixo via ICP; a Superintendência aprova e emite o Ofício.
            </p>
          </div>

          {/* bloco Técnico — assinatura ICP */}
          <div className="rounded-xl border bg-white p-4 space-y-3">
            <h3 className="text-sm font-semibold" style={{ color: GREEN }}>Técnico — assinatura ICP (Memorial + Mapa)</h3>
            <div className="flex flex-wrap gap-3">
              {[['memorial_descritivo', 'Memorial'], ['mapa', 'Mapa']].map(([peca, lab]) => {
                const a = assinaturas[peca];
                return (
                  <div key={peca} className="flex items-center gap-1.5">
                    <button onClick={() => abrirAssinaturaTecnico(peca)} disabled={preparandoAssin === peca}
                      className={`text-xs px-3 py-1.5 rounded-lg border ${a?.assinado ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'hover:bg-gray-50'}`}>
                      {preparandoAssin === peca ? 'Preparando…' : a?.assinado ? `✓ ${lab} assinado` : `Assinar ${lab} (ICP)`}
                    </button>
                    {a?.assinado && (
                      <button onClick={() => verAssinado(a.id)} className="text-xs text-emerald-700 hover:underline">ver</button>
                    )}
                  </div>
                );
              })}
            </div>
            <p className="text-[11px] text-gray-400">Assina-se sobre a peça gerada; o selo ICP-Brasil (PAdES) é aplicado posicionando o carimbo.</p>
          </div>

          {/* bloco Proprietário — WhatsApp */}
          <div className="rounded-xl border bg-white p-4 space-y-3">
            <h3 className="text-sm font-semibold" style={{ color: GREEN }}>Proprietário — assinatura por WhatsApp (Requerimento + ART/TRT)</h3>
            {propSessao?.existe ? (
              <>
                <div className="text-xs text-gray-600">Enviado · {propSessao.assinados}/{propSessao.total} assinaram · {propSessao.status}</div>
                {(propSessao.signatarios || []).map((s, i) => (
                  <div key={i} className="text-xs flex items-center gap-2">
                    <span className={`px-1.5 py-0.5 rounded ${s.status === 'assinado' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{s.status}</span>
                    <span>{s.nome} · {s.papel}</span>
                  </div>
                ))}
                <div className="flex flex-wrap gap-2">
                  <button onClick={() => setPropModal(true)} className="text-xs px-3 py-1.5 rounded-lg border hover:bg-gray-50">Reposicionar e reenviar</button>
                  <button onClick={reenviarProp} disabled={propBusy} className="text-xs px-3 py-1.5 rounded-lg border hover:bg-gray-50">{propBusy ? 'Reenviando…' : 'Reenviar pendentes'}</button>
                </div>
              </>
            ) : (
              <button onClick={() => setPropModal(true)} className="text-xs px-3 py-1.5 rounded-lg text-white" style={{ background: GREEN }}>
                Enviar ao proprietário (posicionar e disparar links)
              </button>
            )}
          </div>

          {/* bloco Superintendência */}
          <div className="rounded-xl border bg-white p-4 space-y-3">
            <h3 className="text-sm font-semibold" style={{ color: GREEN }}>Superintendência de Habitação e Regularização Fundiária</h3>
            <p className="text-xs text-gray-500">
              {aprov?.superintendencia?.responsavel || proj.superintendencia?.responsavel}
              {(aprov?.superintendencia?.portaria || proj.superintendencia?.portaria) ? ` · Portaria ${aprov?.superintendencia?.portaria || proj.superintendencia?.portaria}` : ''}
            </p>
            <div className="flex flex-wrap gap-2">
              <button onClick={enviarSuper} disabled={aprovBusy}
                className={`text-xs px-3 py-1.5 rounded-lg border ${aprov?.superintendencia?.enviado ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'hover:bg-gray-50'}`}>
                {aprov?.superintendencia?.enviado ? '✓ Enviado à Superintendência' : 'Enviar à Superintendência'}
              </button>
              <button onClick={() => aprovarPeca('memorial_aprovado', !aprov?.superintendencia?.memorial_aprovado)} disabled={aprovBusy}
                className={`text-xs px-3 py-1.5 rounded-lg border ${aprov?.superintendencia?.memorial_aprovado ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'hover:bg-gray-50'}`}>
                {aprov?.superintendencia?.memorial_aprovado ? '✓ Memorial aprovado' : 'Aprovar Memorial'}
              </button>
              <button onClick={() => aprovarPeca('mapa_aprovado', !aprov?.superintendencia?.mapa_aprovado)} disabled={aprovBusy}
                className={`text-xs px-3 py-1.5 rounded-lg border ${aprov?.superintendencia?.mapa_aprovado ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'hover:bg-gray-50'}`}>
                {aprov?.superintendencia?.mapa_aprovado ? '✓ Mapa aprovado' : 'Aprovar Mapa'}
              </button>
            </div>
            <div className="pt-2 border-t flex flex-wrap items-center gap-2">
              <button onClick={emitirOficio} disabled={aprovBusy || !aprov?.pode_emitir_oficio}
                className="text-xs px-3 py-1.5 rounded-lg text-white disabled:opacity-40" style={{ background: GREEN }}>
                {aprov?.superintendencia?.oficio_emitido ? `✓ Ofício ${aprov.superintendencia.oficio_numero} emitido` : 'Emitir Ofício ao Cartório'}
              </button>
              {aprov?.superintendencia?.oficio_emitido && (
                <>
                  <button onClick={() => verBlob(geoUrbanoAPI.documento(id, 'oficio_aprovacao', proj.tema))}
                    className="text-xs inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border hover:bg-gray-50"><Eye className="w-3.5 h-3.5" /> Ver ofício</button>
                  <button onClick={() => geoUrbanoAPI.documento(id, 'oficio_aprovacao', proj.tema).then((b) => salvarBlob(b, `oficio_${nb}.pdf`))}
                    className="text-xs inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border hover:bg-gray-50"><Download className="w-3.5 h-3.5" /> PDF</button>
                </>
              )}
              {!aprov?.pode_emitir_oficio && <span className="text-[11px] text-gray-400">Aprove o Memorial e o Mapa para liberar o Ofício.</span>}
            </div>
          </div>
        </div>
      )}

      {/* ─────────────────────────── Passo 8: Entrega ─────────────────────────── */}
      {step === 7 && (
        <div className="space-y-3">
          <h2 className="font-semibold" style={{ color: GREEN }}>Entrega — documentos gerados</h2>
          {[
            ...((uploads.imagem_imovel || []).length ? [['capa', 'Capa do processo (Lupa Geo)']] : []),
            ...DOCS_GERAVEIS,
            ...(isRetificacao ? [['quadro_retificacao', 'Quadro de Retificação (de → para)']] : []),
            ...(aprov?.superintendencia?.oficio_emitido ? [['oficio_aprovacao', 'Ofício de Aprovação ao Cartório']] : []),
          ].map(([k, lab]) => (
            <div key={k} className="rounded-xl border bg-white p-4 flex items-center justify-between">
              <span className="text-sm text-gray-700">{lab}</span>
              <div className="flex gap-2">
                <button onClick={() => verBlob(geoUrbanoAPI.documento(id, k, proj.tema))}
                  className="text-xs inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border hover:bg-gray-50">
                  <Eye className="w-3.5 h-3.5" /> Ver
                </button>
                <button onClick={() => geoUrbanoAPI.documento(id, k, proj.tema).then((b) => salvarBlob(b, `${k}_${nb}.pdf`)).catch(() => toast({ title: 'Erro ao baixar', variant: 'destructive' }))}
                  className="text-xs inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-white" style={{ background: GREEN }}>
                  <Download className="w-3.5 h-3.5" /> PDF
                </button>
              </div>
            </div>
          ))}
          {isDesdobro && lotes.length > 0 && (
            <div className="rounded-xl border bg-white p-4">
              <div className="text-sm font-semibold mb-2" style={{ color: GREEN }}>Memoriais por lote resultante</div>
              {lotes.map((l) => (
                <div key={l.id} className="flex items-center justify-between py-1.5 border-t first:border-t-0">
                  <span className="text-sm text-gray-700">Memorial — Lote {l.denominacao || l.ordem}</span>
                  <div className="flex gap-2">
                    <button onClick={() => verBlob(geoUrbanoAPI.documento(id, 'memorial_descritivo', proj.tema, l.id))}
                      className="text-xs inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border hover:bg-gray-50"><Eye className="w-3.5 h-3.5" /> Ver</button>
                    <button onClick={() => geoUrbanoAPI.documento(id, 'memorial_descritivo', proj.tema, l.id).then((b) => salvarBlob(b, `memorial_${l.denominacao || l.ordem}.pdf`)).catch(() => toast({ title: 'Erro ao baixar', variant: 'destructive' }))}
                      className="text-xs inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-white" style={{ background: GREEN }}><Download className="w-3.5 h-3.5" /> PDF</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {propModal && (
        <AssinaturaProprietarioModal
          projetoId={id}
          onFechar={() => setPropModal(false)}
          onEnviado={() => carregarAprov()}
        />
      )}

      {assinId && (
        <AssinaturaPosicionadaModal
          tipo="geo_urbano"
          documentId={assinId}
          onAssinado={() => {
            const aId = assinId;
            setAssinId(null);
            toast({ title: 'Assinado com ICP-Brasil ✓' });
            carregarAprov();
            verAssinado(aId);
          }}
          onFechar={() => setAssinId(null)}
        />
      )}

      {/* navegação */}
      <div className="flex justify-between mt-8">
        <button onClick={() => irPasso(Math.max(0, step - 1))} disabled={step === 0}
          className="px-4 py-2 rounded-lg text-sm border disabled:opacity-40">Voltar</button>
        {step < PASSOS.length - 1 && (
          <button onClick={() => irPasso(step + 1)}
            className="px-4 py-2 rounded-lg text-sm font-semibold text-white" style={{ background: GREEN }}>Avançar</button>
        )}
      </div>
    </div>
  );
}
