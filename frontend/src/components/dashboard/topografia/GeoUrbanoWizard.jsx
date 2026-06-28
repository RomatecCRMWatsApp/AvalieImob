// @module topografia/GeoUrbanoWizard — Wizard 7 passos do Geo Urbano (Remembramento).
// Espelha o GeorefWizard: autosave PATCH (debounce), uploads→R2, conferência com
// reconciliação matrícula↔BCI, preview SVG da poligonal, geração e entrega.
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft, Upload, Trash2, Plus, FileText, AlertTriangle, CheckCircle2,
  Download, Eye, RefreshCw,
} from 'lucide-react';
import { geoUrbanoAPI, assinaturaPosAPI, brandingAPI, perfilAPI, georefAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';
import AssinaturaPosicionadaModal from '../assinatura/AssinaturaPosicionadaModal';
import AssinaturaProprietarioModal from './AssinaturaProprietarioModal';
import EtapaConcluidaBox from '../ptam/EtapaConcluidaBox';
import { fmtDataHora } from '../../../utils/datasServidor';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';

const PASSOS = ['Projeto', 'Uploads', 'Matrículas & BCI', 'Vértices & Mapa', 'Partes', 'Geração', 'Aprovação', 'Entrega'];
const STATUS_GERAL = {
  rascunho: 'Rascunho', assinatura_partes: 'Assinatura das partes', assinatura_tecnico: 'Assinatura do técnico',
  enviado_superintendencia: 'Enviado à Superintendência', aprovado: 'Aprovado', oficio_emitido: 'Ofício anexado', protocolado: 'Protocolado',
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
  { tipo: 'comprovante_pagamento_trt', label: 'Comprovante de pagamento da TRT (opcional — o boleto já sai com carimbo de pago)', req: false, multi: false },
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

// Preview SVG da poligonal (UTM coord_e/coord_n) — com cotas e confrontantes por
// aresta (rótulos perpendiculares à aresta, p/ aferir os dados igual ao croqui do PDF)
function Poligonal({ vertices = [] }) {
  const pts = (vertices || []).filter((v) => v.coord_e != null && v.coord_n != null)
    .slice().sort((a, b) => (a.ordem || 0) - (b.ordem || 0))
    .map((v) => ({ x: Number(v.coord_e), y: Number(v.coord_n), de: v.de, dist: v.distancia_m, conf: v.confrontante_lado }));
  if (pts.length < 3) return <div className="text-sm text-gray-400 py-10 text-center">Sem vértices suficientes para o desenho.</div>;
  const W = 520, H = 360, pad = 56;
  const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const s = Math.min((W - 2 * pad) / (maxX - minX || 1), (H - 2 * pad) / (maxY - minY || 1));
  const ox = (W - (maxX - minX) * s) / 2, oy = (H - (maxY - minY) * s) / 2;
  const xy = pts.map((p) => ({ x: ox + (p.x - minX) * s, y: H - oy - (p.y - minY) * s, de: p.de, dist: p.dist, conf: p.conf }));
  const cx = xy.reduce((a, p) => a + p.x, 0) / xy.length, cy = xy.reduce((a, p) => a + p.y, 0) / xy.length;
  const poly = xy.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const fmt = (n) => (n == null ? '' : Number(n).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full border rounded-lg bg-white">
      <polygon points={poly} fill="rgba(12,51,32,0.08)" stroke={GREEN} strokeWidth="1.6" />
      {/* cotas + confrontante por aresta: offset pela normal E rotacionados ao longo do segmento (azimute) */}
      {xy.map((p, i) => {
        const b = xy[(i + 1) % xy.length];
        const mx = (p.x + b.x) / 2, my = (p.y + b.y) / 2;
        const ex = b.x - p.x, ey = b.y - p.y, eln = Math.hypot(ex, ey) || 1;
        let nx = -ey / eln, ny = ex / eln;
        if (nx * (mx - cx) + ny * (my - cy) < 0) { nx = -nx; ny = -ny; }
        const lx = mx + nx * 15, ly = my + ny * 15;
        let ang = Math.atan2(ey, ex) * 180 / Math.PI;
        if (ang > 90 || ang < -90) ang += 180;       // mantém o texto "para cima"
        return (
          <g key={`e${i}`} transform={`translate(${lx.toFixed(1)},${ly.toFixed(1)}) rotate(${ang.toFixed(1)})`}>
            {p.dist != null && <text x="0" y="-2" fontSize="8.5" fontWeight="600" fill="#111" textAnchor="middle">{fmt(p.dist)} m</text>}
            {p.conf && <text x="0" y="7" fontSize="7" fill="#666" textAnchor="middle">{String(p.conf).slice(0, 22)}</text>}
          </g>
        );
      })}
      {xy.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="3.2" fill={GOLD} stroke={GREEN} strokeWidth="0.8" />
          <text x={p.x + 5} y={p.y - 4} fontSize="8.5" fontWeight="600" fill={GREEN}>{(p.de || '').split('-').pop()}</text>
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
  const [previewUrl, setPreviewUrl] = useState('');
  const [previewTipo, setPreviewTipo] = useState('requerimento_cartorio');
  const [previewBusy, setPreviewBusy] = useState(false);
  const previewUrlRef = useRef('');
  const [firmaTecnico, setFirmaTecnico] = useState('');   // b64 da assinatura gráfica do RT
  const [firmaBusy, setFirmaBusy] = useState(false);
  const [cnsBusy, setCnsBusy] = useState(false);
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
  useEffect(() => {
    perfilAPI.get().then((p) => setFirmaTecnico(p?.assinatura_tecnico_b64 || p?.assinatura_visual_b64 || '')).catch(() => {});
  }, []);
  const onUploadFirma = (file) => {
    if (!file) return;
    if (file.type !== 'image/png') { toast({ title: 'Envie um PNG com fundo transparente', variant: 'destructive' }); return; }
    setFirmaBusy(true);
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const b64 = String(reader.result).split(',')[1];
        await perfilAPI.setAssinaturaTecnico(b64);
        setFirmaTecnico(b64);
        toast({ title: 'Assinatura do técnico salva', description: 'Será carimbada no Memorial ao gerar/enviar.' });
      } catch (e) { toast({ title: 'Erro ao salvar a assinatura', variant: 'destructive' }); }
      finally { setFirmaBusy(false); }
    };
    reader.readAsDataURL(file);
  };
  const removerFirma = async () => {
    setFirmaBusy(true);
    try { await perfilAPI.setAssinaturaTecnico(''); setFirmaTecnico(''); }
    catch (e) { toast({ title: 'Erro ao remover', variant: 'destructive' }); }
    finally { setFirmaBusy(false); }
  };
  // Cartório pelo CNS — reusa a tabela oficial de serventias (mesma do Georref)
  const buscarCartorioCns = async () => {
    const cns = (proj.cartorio?.cns || '').replace(/\D/g, '');
    if (!cns) { toast({ title: 'Informe o CNS da serventia', variant: 'destructive' }); return; }
    setCnsBusy(true);
    try {
      const s = await georefAPI.buscarServentia(cns);
      const nova = { ...proj.cartorio, cns };
      if (s.denominacao) nova.nome = s.denominacao;
      if (s.cidade && s.uf && (!nova.endereco || !nova.endereco.trim())) nova.endereco = `${s.cidade}/${s.uf}`;
      upd({ cartorio: nova });
      toast({ title: 'Cartório encontrado', description: `${s.denominacao} — ${s.cidade}/${s.uf}` });
    } catch (e) {
      toast({ title: 'CNS não encontrado', description: e?.response?.data?.detail || 'Confira o número.', variant: 'destructive' });
    } finally { setCnsBusy(false); }
  };

  const salvar = useCallback(async (silent = true) => {
    const p = projRef.current;
    if (!p || !dirtyRef.current) return;
    try {
      const payload = {
        denominacao_imovel: p.denominacao_imovel, tipo_servico: p.tipo_servico, tema: p.tema,
        municipio: p.municipio, uf: p.uf, bairro: p.bairro, loteamento: p.loteamento,
        quadra: p.quadra, lote_resultante: p.lote_resultante, endereco: p.endereco,
        cmi_resultante: p.cmi_resultante, cmi_controle: p.cmi_controle, cadastro_novo: p.cadastro_novo, cadastro_antigo: p.cadastro_antigo,
        area_declarada_m2: p.area_declarada_m2 === '' ? null : Number(p.area_declarada_m2),
        perimetro_m: p.perimetro_m === '' ? null : Number(p.perimetro_m),
        trt_numero: p.trt_numero, cartorio: p.cartorio, superintendencia: p.superintendencia,
        matriculas: p.matriculas, bci: p.bci, vertices: p.vertices, partes: p.partes, iptu: p.iptu,
        etapas_concluidas: p.etapas_concluidas, etapas_concluidas_em: p.etapas_concluidas_em,
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
  // auditoria: marca/desmarca a etapa concluída e SALVA na hora (carimba data/hora)
  const toggleEtapa = (idx, checked) => {
    setProj((p) => {
      const ec = { ...(p.etapas_concluidas || {}) };
      const em = { ...(p.etapas_concluidas_em || {}) };
      if (checked) { ec[idx] = true; em[idx] = new Date().toISOString(); }
      else { delete ec[idx]; delete em[idx]; }
      const np = { ...p, etapas_concluidas: ec, etapas_concluidas_em: em };
      geoUrbanoAPI.atualizar(p.id, { etapas_concluidas: ec, etapas_concluidas_em: em }).catch(() => {});
      return np;
    });
  };
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
  // Vértices (editáveis — confrontante não vem da planilha do mapa)
  const addVert = () => upd({ vertices: [...(proj.vertices || []), { id: `tmp-${Date.now()}`, ordem: (proj.vertices || []).length + 1 }] });
  const rmVert = (i) => upd({ vertices: (proj.vertices || []).filter((_, k) => k !== i) });
  // Confrontantes + DRL (retificação, eixo geométrico)
  const addConfr = () => upd({ confrontantes: [...(proj.confrontantes || []), { id: `tmp-${Date.now()}`, tipo: 'particular', anuencia: { status: 'pendente' } }] });
  const rmConfr = (i) => upd({ confrontantes: (proj.confrontantes || []).filter((_, k) => k !== i) });
  const verDrl = (cid) => verBlob(geoUrbanoAPI.baixarDrl(id, cid, proj.tema));
  const setAnuencia = async (cid, status) => {
    try { await geoUrbanoAPI.drlAnuencia(id, cid, status); await carregar(); toast({ title: `Anuência: ${status}` }); }
    catch (e) { toast({ title: 'Erro ao registrar anuência', variant: 'destructive' }); }
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

  // PRÉVIA REAL embutida (aferição): renderiza o PDF da peça no próprio sistema
  const carregarPreview = useCallback(async (tipo) => {
    const t = tipo || previewTipo;
    setPreviewBusy(true);
    try {
      const data = await geoUrbanoAPI.documento(id, t, proj.tema);
      const blob = new Blob([data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = url;
      setPreviewUrl(url); setPreviewTipo(t);
    } catch (e) {
      toast({ title: 'Erro ao gerar a prévia', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setPreviewBusy(false); }
  }, [id, previewTipo, proj?.tema, toast]);
  useEffect(() => () => { if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current); }, []);

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
              <div>
                <label className={lbl}>CMI resultante (base — controle)</label>
                <div className="flex items-center gap-1">
                  <input className={inp} value={proj.cmi_resultante || ''} placeholder="01.10.041.0001.00001"
                    onChange={(e) => upd({ cmi_resultante: e.target.value })} />
                  <span className="text-gray-400 font-semibold">—</span>
                  <input className="w-16 border rounded-lg px-2 py-1.5 text-sm text-center font-mono" maxLength={3}
                    value={proj.cmi_controle || ''} placeholder="111"
                    onChange={(e) => upd({ cmi_controle: e.target.value.replace(/\D/g, '').slice(0, 3) })} />
                </div>
                <p className="text-[10px] text-gray-400 mt-0.5">Controle de 3 dígitos (informado pela prefeitura/BCI). Sai como {proj.cmi_resultante || '—'}{proj.cmi_controle ? `-${proj.cmi_controle}` : ''}.</p>
              </div>
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
            <div className="sm:col-span-2 flex items-end gap-2 mb-3 bg-emerald-50/60 border border-emerald-100 rounded-lg p-3">
              <div className="flex-1">
                <Field label="CNS da serventia (Código Nacional) — preenche o cartório automaticamente"
                  value={proj.cartorio?.cns} onChange={(v) => upd({ cartorio: { ...proj.cartorio, cns: v } })} />
              </div>
              <button onClick={buscarCartorioCns} disabled={cnsBusy}
                className="px-3 py-2 rounded-lg text-sm font-semibold text-white whitespace-nowrap inline-flex items-center gap-1" style={{ background: GREEN }}>
                <RefreshCw className={`w-3.5 h-3.5 ${cnsBusy ? 'animate-spin' : ''}`} /> {cnsBusy ? 'Buscando…' : 'Buscar pelo CNS'}
              </button>
            </div>
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

          {/* auditoria: carimbo da última extração dos documentos */}
          <div className="text-[11px] text-gray-500 -mt-3">
            {proj.extracao_em
              ? <span className="inline-flex items-center gap-1"><CheckCircle2 className="w-3 h-3 text-emerald-600" /> Dados extraídos dos documentos em <b className="text-gray-700">{fmtDataHora(proj.extracao_em)}</b> — reextrair atualiza o carimbo.</span>
              : <span className="inline-flex items-center gap-1"><AlertTriangle className="w-3 h-3 text-amber-500" /> Ainda não extraído — clique em “Extrair dos documentos” para auditar com data/hora.</span>}
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
              {/* confrontantes & DRL (anuência art. 213) */}
              {proj.retificacao_tipo !== 'cadastral' && (
                <div className="pt-2 border-t">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-gray-600">Confrontantes &amp; DRL (anuência — art. 213)</span>
                    <button onClick={addConfr} className="text-xs text-emerald-700 hover:underline"><Plus className="w-3 h-3 inline" /> Confrontante</button>
                  </div>
                  {(proj.confrontantes || []).map((c, i) => (
                    <div key={c.id || i} className="rounded-lg border p-2 mb-2">
                      <div className="grid sm:grid-cols-4 gap-2">
                        <input className={inp} placeholder="lado" value={c.lado || ''} onChange={(e) => updArr('confrontantes', i, { lado: e.target.value })} />
                        <input className={inp} placeholder="confrontante" value={c.confrontante || ''} onChange={(e) => updArr('confrontantes', i, { confrontante: e.target.value })} />
                        <select className={inp} value={c.tipo || 'particular'} onChange={(e) => updArr('confrontantes', i, { tipo: e.target.value })}>
                          <option value="particular">Particular</option>
                          <option value="via_publica">Via pública</option>
                          <option value="area_publica">Área pública</option>
                        </select>
                        <input className={inp} type="number" placeholder="medida (m)" value={c.medida_m ?? ''} onChange={(e) => updArr('confrontantes', i, { medida_m: e.target.value === '' ? null : Number(e.target.value) })} />
                      </div>
                      {(c.tipo || 'particular') === 'particular' && (
                        <div className="grid sm:grid-cols-2 gap-2 mt-1">
                          <input className={inp} placeholder="CPF/CNPJ" value={c.doc || ''} onChange={(e) => updArr('confrontantes', i, { doc: e.target.value })} />
                          <input className={inp} placeholder="endereço" value={c.endereco || ''} onChange={(e) => updArr('confrontantes', i, { endereco: e.target.value })} />
                        </div>
                      )}
                      <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                        {(c.tipo || 'particular') === 'particular' ? (
                          <>
                            <span className={`text-[11px] px-1.5 py-0.5 rounded ${c.anuencia?.status === 'assinada' ? 'bg-emerald-100 text-emerald-700' : c.anuencia?.status === 'recusada' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>{c.anuencia?.status || 'pendente'}</span>
                            <button onClick={() => verDrl(c.id)} className="text-xs text-emerald-700 hover:underline">Ver DRL</button>
                            <button onClick={() => setAnuencia(c.id, 'assinada')} className="text-xs text-emerald-700 hover:underline">marcar assinada</button>
                            <button onClick={() => setAnuencia(c.id, 'recusada')} className="text-xs text-red-600 hover:underline">recusada</button>
                            <button onClick={() => setAnuencia(c.id, 'notificado')} className="text-xs text-amber-700 hover:underline">notificado</button>
                          </>
                        ) : <span className="text-[11px] text-gray-400">DRL dispensada (via/área pública)</span>}
                        <Trash2 className="w-3.5 h-3.5 text-gray-300 hover:text-red-500 cursor-pointer ml-auto" onClick={() => rmConfr(i)} />
                      </div>
                    </div>
                  ))}
                  {!(proj.confrontantes || []).length && <p className="text-xs text-gray-400">Cadastre os confrontantes — cada particular gera uma DRL para anuência.</p>}
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
          <div className="rounded-xl border bg-white p-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-semibold" style={{ color: GREEN }}>Quadro de vértices <span className="text-[11px] font-normal text-gray-400">(editável)</span></h2>
              <div className="flex items-center gap-3">
                <span className="text-[10px] text-gray-400">arraste ↔</span>
                <button onClick={addVert} className="text-xs inline-flex items-center gap-1 text-emerald-700 hover:underline"><Plus className="w-3.5 h-3.5" /> Vértice</button>
              </div>
            </div>
            <p className="text-[11px] text-amber-600 mb-2">O <b>Confrontante</b> não vem da planilha do mapa — preencha/corrija por aqui (1 por segmento) para o Memorial sair completo.</p>
            <div className="overflow-x-auto -mx-1 px-1">
              <table className="text-xs border-collapse" style={{ minWidth: 820 }}>
                <thead>
                  <tr className="text-left" style={{ color: GREEN }}>
                    {['De', 'Para', 'Coord. N (Y)', 'Coord. E (X)', 'Azimute', 'Dist. (m)', 'Fator K', 'Confrontante', ''].map((h) => (
                      <th key={h} className="px-1.5 py-1.5 whitespace-nowrap border-b font-semibold bg-gray-50">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(proj.vertices || []).map((v, i) => {
                    const vci = 'w-full bg-transparent px-1.5 py-1 text-xs outline-none focus:bg-emerald-50 rounded';
                    const set = (campo, val) => updArr('vertices', i, { [campo]: val });
                    const setN = (campo, val) => updArr('vertices', i, { [campo]: val === '' ? null : Number(val) });
                    return (
                      <tr key={v.id || i} className="border-b">
                        <td className="border-r"><input className={vci + ' font-medium'} style={{ minWidth: 92 }} value={v.de || ''} onChange={(e) => set('de', e.target.value)} /></td>
                        <td className="border-r"><input className={vci} style={{ minWidth: 92 }} value={v.para || ''} onChange={(e) => set('para', e.target.value)} /></td>
                        <td className="border-r"><input className={vci + ' font-mono'} style={{ minWidth: 104 }} type="number" value={v.coord_n ?? ''} onChange={(e) => setN('coord_n', e.target.value)} /></td>
                        <td className="border-r"><input className={vci + ' font-mono'} style={{ minWidth: 104 }} type="number" value={v.coord_e ?? ''} onChange={(e) => setN('coord_e', e.target.value)} /></td>
                        <td className="border-r"><input className={vci} style={{ minWidth: 84 }} value={v.azimute || ''} onChange={(e) => set('azimute', e.target.value)} /></td>
                        <td className="border-r"><input className={vci + ' text-right'} style={{ minWidth: 60 }} type="number" value={v.distancia_m ?? ''} onChange={(e) => setN('distancia_m', e.target.value)} /></td>
                        <td className="border-r"><input className={vci + ' font-mono'} style={{ minWidth: 88 }} type="number" value={v.fator_k ?? ''} onChange={(e) => setN('fator_k', e.target.value)} /></td>
                        <td className="border-r bg-amber-50/40"><input className={vci} style={{ minWidth: 150 }} placeholder="ex.: Rua Suriname" value={v.confrontante_lado || ''} onChange={(e) => set('confrontante_lado', e.target.value)} /></td>
                        <td className="px-1"><Trash2 className="w-3.5 h-3.5 text-gray-300 hover:text-red-500 cursor-pointer" onClick={() => rmVert(i)} /></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {!(proj.vertices || []).length && <p className="text-sm text-gray-400 mt-2">Sem vértices ainda — extraia do mapa (passo Uploads) ou adicione manualmente.</p>}
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
        <div className="rounded-xl border bg-white p-5">
          <LogoBranding toast={toast} />
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

        {/* PRÉVIA REAL — aferição antes de gerar/protocolar (evita erros) */}
        <div className="rounded-xl border bg-white p-5 space-y-3">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <h2 className="font-semibold" style={{ color: GREEN }}>Pré-visualização (aferição)</h2>
            <div className="flex items-center gap-2">
              <select className={inp + ' max-w-[280px]'} value={previewTipo}
                onChange={(e) => carregarPreview(e.target.value)}>
                {DOCS_GERAVEIS.map(([k, lab]) => <option key={k} value={k}>{lab}</option>)}
              </select>
              <button onClick={() => carregarPreview()} disabled={previewBusy}
                className="text-xs inline-flex items-center gap-1 px-2.5 py-2 rounded-lg text-white" style={{ background: GREEN }}>
                <RefreshCw className={`w-3.5 h-3.5 ${previewBusy ? 'animate-spin' : ''}`} /> {previewBusy ? 'Gerando…' : (previewUrl ? 'Atualizar' : 'Ver prévia')}
              </button>
            </div>
          </div>
          <p className="text-[11px] text-gray-500">Confira a peça exatamente como sairá no PDF (tema {proj.tema}) antes de gerar/protocolar.</p>
          {previewUrl
            ? <iframe title="Prévia do documento" src={`${previewUrl}#toolbar=1`} className="w-full rounded-lg border" style={{ height: 560 }} />
            : <div className="text-sm text-gray-400 border border-dashed rounded-lg p-8 text-center">Escolha a peça e clique em “Ver prévia” para aferir o PDF aqui mesmo.</div>}
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

          {/* bloco Assinatura GRÁFICA do técnico — carimbada no Memorial */}
          <div className="rounded-xl border bg-white p-4 space-y-3">
            <h3 className="text-sm font-semibold" style={{ color: GREEN }}>Assinatura gráfica do técnico (carimbada no Memorial)</h3>
            <p className="text-[11px] text-gray-500">PNG com fundo transparente. Vai <b>carimbada automaticamente</b> no Memorial ao gerar/enviar às partes — o selo ICP-Brasil é aplicado depois como etapa final.</p>
            <div className="flex items-center gap-4 flex-wrap">
              {firmaTecnico
                ? <img src={`data:image/png;base64,${firmaTecnico}`} alt="Assinatura do técnico" className="h-16 max-w-[280px] object-contain border rounded-lg bg-white p-1" />
                : <div className="h-16 w-[280px] border border-dashed rounded-lg flex items-center justify-center text-xs text-gray-400">Sem assinatura cadastrada</div>}
              <div className="flex flex-col gap-2">
                <label className="text-xs px-3 py-1.5 rounded-lg text-white cursor-pointer inline-flex items-center gap-1" style={{ background: GREEN }}>
                  <Upload className="w-3.5 h-3.5" /> {firmaBusy ? 'Salvando…' : (firmaTecnico ? 'Trocar' : 'Enviar PNG')}
                  <input type="file" accept="image/png" className="hidden" disabled={firmaBusy}
                    onChange={(e) => { onUploadFirma(e.target.files?.[0]); e.target.value = ''; }} />
                </label>
                {firmaTecnico && <button onClick={removerFirma} disabled={firmaBusy} className="text-xs text-red-600 hover:underline">Remover</button>}
              </div>
            </div>
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
            <div className="pt-2 border-t space-y-2">
              <p className="text-[11px] text-gray-500">
                O <b>Ofício de Aprovação é expedido e assinado pela própria Superintendência</b> (o sistema não o emite).
                Ao recebê-lo, faça o upload aqui — junto com o Memorial e o Mapa aprovados/assinados — e o sistema monta
                o processo final para envio ao Cartório (etapa de encerramento).
              </p>
              {[
                ['oficio_assinado', 'Ofício de Aprovação (assinado pela Superintendência)'],
                ['memorial_aprovado', 'Memorial aprovado/assinado (devolvido)'],
                ['mapa_aprovado', 'Mapa aprovado/assinado (devolvido)'],
              ].map(([tp, lab]) => {
                const itens = uploads[tp] || [];
                return (
                  <div key={tp} className={`rounded-lg border p-2 ${itens.length ? 'bg-emerald-50/40 border-emerald-200' : ''}`}>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-gray-700">{lab}{itens.length ? ' ✓' : ''}</span>
                      <label className="text-xs cursor-pointer text-emerald-700 hover:underline inline-flex items-center gap-1 shrink-0">
                        <Upload className="w-3.5 h-3.5" />{itens.length ? 'Trocar/enviar' : 'Enviar arquivo'}
                        <input type="file" className="hidden" accept=".pdf,image/*"
                          onChange={async (e) => { await enviar(tp, e.target.files); carregarAprov(); }} />
                      </label>
                    </div>
                    {itens.map((it) => (
                      <div key={it.id} className="flex items-center justify-between text-[11px] text-gray-500 mt-1">
                        <span className="truncate flex items-center gap-1"><FileText className="w-3 h-3" />{it.nome}</span>
                        <Trash2 className="w-3.5 h-3.5 text-gray-300 hover:text-red-500 cursor-pointer shrink-0"
                          onClick={async () => { await removerUp(tp, it.id); carregarAprov(); }} />
                      </div>
                    ))}
                  </div>
                );
              })}
              {aprov?.superintendencia?.oficio_anexado && (
                <p className="text-[11px] text-emerald-700">✓ Ofício anexado — o Dossiê final (Entrega) já inclui o Ofício e as peças aprovadas.</p>
              )}
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
          <div className="rounded-xl border bg-white p-4">
            <div className="text-sm font-semibold mb-1" style={{ color: GREEN }}>Arquivos geoespaciais — SIG-RI (Prov. CNJ 195/2025)</div>
            <p className="text-[11px] text-gray-500 mb-2">Obrigatório para alimentar a malha fundiária do Registro de Imóveis (SIRGAS 2000 / EPSG:4674). Exige Latitude/Longitude dos vértices.</p>
            <div className="flex gap-2 flex-wrap">
              <button onClick={() => geoUrbanoAPI.shapefile(id).then((b) => salvarBlob(b, `SIGRI_${nb}.zip`)).catch(() => toast({ title: 'Erro ao gerar o Shapefile', description: 'Confira se os vértices têm Latitude/Longitude.', variant: 'destructive' }))}
                className="text-xs inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-white" style={{ background: GREEN }}>
                <Download className="w-3.5 h-3.5" /> Shapefile SIG-RI (.zip)
              </button>
              <button onClick={() => geoUrbanoAPI.kml(id).then((b) => salvarBlob(b, `${nb}.kml`)).catch(() => toast({ title: 'Erro ao gerar o KML', variant: 'destructive' }))}
                className="text-xs inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border hover:bg-gray-50">
                <Download className="w-3.5 h-3.5" /> KML (Google Earth)
              </button>
            </div>
          </div>
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

      {/* auditoria: etapa concluída (carimba data/hora) — em todas as etapas */}
      <EtapaConcluidaBox stepIndex={step} label={PASSOS[step]} form={proj}
        onToggle={toggleEtapa} entidade="projeto" />

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

// Logo white-label do usuário — aparece no cabeçalho de TODAS as peças geradas.
// Exige PNG com fundo TRANSPARENTE (senão ganharia caixa branca sobre o tema).
function LogoBranding({ toast }) {
  const [info, setInfo] = useState(null);
  const [busy, setBusy] = useState(false);
  const ref = useRef(null);
  const carregar = useCallback(async () => {
    try { setInfo(await brandingAPI.get()); } catch { /* */ }
  }, []);
  useEffect(() => { carregar(); }, [carregar]);

  const validarPng = (file) => new Promise((resolve) => {
    if (!/png/i.test(file.type) && !/\.png$/i.test(file.name)) { resolve('O logo precisa ser um arquivo PNG.'); return; }
    const img = new Image();
    img.onload = () => {
      try {
        const cv = document.createElement('canvas');
        cv.width = img.naturalWidth; cv.height = img.naturalHeight;
        const ctx = cv.getContext('2d'); ctx.drawImage(img, 0, 0);
        const d = ctx.getImageData(0, 0, cv.width, cv.height).data;
        let transp = false;
        for (let i = 3; i < d.length; i += 4) { if (d[i] < 245) { transp = true; break; } }
        resolve(transp ? null : 'O PNG precisa ter FUNDO TRANSPARENTE (sem fundo branco/colorido).');
      } catch { resolve(null); }
    };
    img.onerror = () => resolve('Não foi possível ler a imagem.');
    img.src = URL.createObjectURL(file);
  });

  const onPick = async (file) => {
    if (!file) return;
    const erro = await validarPng(file);
    if (erro) { toast({ title: 'Logo inválido', description: erro, variant: 'destructive' }); return; }
    setBusy(true);
    try {
      await brandingAPI.uploadLogo(file);
      await carregar();
      toast({ title: 'Logo aplicado ✓', description: 'Vai sair no cabeçalho das peças geradas.' });
    } catch (e) {
      toast({ title: 'Falha ao enviar o logo', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setBusy(false); }
  };

  const remover = async () => {
    setBusy(true);
    try { await brandingAPI.deleteLogo(); await carregar(); toast({ title: 'Logo removido (volta ao padrão)' }); }
    catch { toast({ title: 'Erro ao remover', variant: 'destructive' }); }
    finally { setBusy(false); }
  };

  const temCustom = !!(info && info.logo_url);
  return (
    <div>
      <div className="text-sm font-medium text-gray-700">Logo da empresa (white-label)</div>
      <div className="text-xs text-gray-500 mb-1">
        PNG com fundo <strong>transparente</strong> — aparece no cabeçalho das peças geradas (Requerimento, Memorial, DRL, Dossiê).
      </div>
      <div className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 mb-2">
        ⚠️ Envie o logo <strong>antes de assinar</strong>. Peça já assinada mantém o cabeçalho do momento da assinatura — use <strong>Reassinar</strong> para aplicar o novo logo.
      </div>
      <div className="flex items-center gap-3 flex-wrap">
        {temCustom ? (
          <img src={info.logo_url} alt="logo" className="h-10 max-w-[170px] object-contain bg-white border rounded px-1"
            onError={(e) => { e.currentTarget.style.display = 'none'; }} />
        ) : (
          <span className="inline-flex items-center gap-2 text-xs text-gray-500">
            <img src="/icon-192.png" alt="AvalieImob" className="h-9 w-9 object-contain rounded bg-white border" />
            Padrão do sistema (AvalieImob) — enviar o seu é opcional
          </span>
        )}
        <input ref={ref} type="file" accept=".png,image/png" className="hidden"
          onChange={(e) => { onPick(e.target.files?.[0]); e.target.value = ''; }} />
        <button onClick={() => ref.current?.click()} disabled={busy}
          className="text-xs font-semibold px-3 py-1.5 rounded-lg border hover:bg-white disabled:opacity-40" style={{ color: GREEN }}>
          {busy ? 'Enviando…' : (temCustom ? 'Trocar logo' : 'Enviar logo (PNG)')}
        </button>
        {temCustom && <button onClick={remover} disabled={busy} className="text-xs text-gray-400 hover:text-red-500">Remover</button>}
      </div>
    </div>
  );
}
