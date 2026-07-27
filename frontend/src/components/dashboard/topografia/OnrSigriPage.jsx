// @module topografia/OnrSigriPage — Arquivo ONR (SIG-RI) STANDALONE.
// Fluxo separado dos procedimentos do Geo Urbano: sobe MAPA + MEMORIAL + ART/TRT
// + CERTIDÃO já prontos → extrai a poligonal do memorial → valida → gera o
// pacote shapefile SIG-RI para o mapa.onr.org.br.
import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Upload, Trash2, FileText, Download, RefreshCw, Plus, ArrowLeft, CheckCircle2, MapPin, Copy,
  Eye, ChevronUp, ChevronDown,
} from 'lucide-react';
import { onrSigriAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';
import PoligonalLeaflet from '../../maps/PoligonalLeaflet';

const GREEN = '#0C3320';
const lbl = 'block text-[11px] font-medium text-gray-500 mb-1';
const inp = 'w-full border rounded-lg px-2.5 py-1.5 text-sm';

function Field({ label, value, onChange, type = 'text', placeholder, full }) {
  return (
    <div className={full ? 'sm:col-span-2' : ''}>
      <label className={lbl}>{label}</label>
      <input className={inp} type={type} value={value ?? ''} placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

// 4 obrigatórios (geram o pacote + informações geodésicas — Prov. 195)
const UPLOADS = [
  ['mapa', 'Mapa / Planta (já pronto)', '.pdf,image/*'],
  ['memorial', 'Memorial Descritivo (fonte dos dados)', '.pdf'],
  ['art_trt', 'ART / TRT', '.pdf,image/*'],
  ['certidao', 'Certidão de Matrícula', '.pdf,image/*'],
];
// opcionais — enriquecem os dados/descrição (não são exigidos p/ gerar)
const UPLOADS_OPC = [
  ['bci', 'BCI — Boletim de Cadastro Imobiliário', '.pdf,image/*'],
  ['cnd_iptu', 'Certidão Negativa de IPTU (CND)', '.pdf,image/*'],
  ['doc_proprietario', 'Documento do Proprietário', '.pdf,image/*'],
];

function saveBlob(blob, nome) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = nome; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

const _brNum = (v, d) => Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });

// Texto da "Descrição do polígono" para colar no mapa.onr.org.br (Prov. CNJ 195/2025).
function descricaoPoligono(job) {
  const mat = (job.matriculas || [])[0] || {};
  const prop = (job.partes || [])[0] || {};
  const areaM2 = Number(job.area_declarada_m2 || 0);
  const nv = (job.vertices || []).length;
  const uf = job.uf || '';
  const serventia = job.cartorio?.comarca || job.municipio || '';
  const mc = job.fuso ? (-183 + 6 * Number(job.fuso)) : null;
  let t = `Polígono do imóvel urbano${job.denominacao_imovel ? ` denominado ${job.denominacao_imovel}` : ''}`;
  if (mat.matricula) t += `, matrícula nº ${mat.matricula}${serventia ? ` do Registro de Imóveis de ${serventia}/${uf}` : ''}`;
  if (prop.nome) t += `, de propriedade de ${prop.nome}${prop.cpf ? ` (CPF/CNPJ ${prop.cpf})` : ''}`;
  if (job.municipio) t += `, situado no Município de ${job.municipio}/${uf}`;
  t += '.';
  if (areaM2) t += ` Área de ${_brNum(areaM2, 2)} m² (${_brNum(areaM2 / 10000, 4)} ha)`;
  if (job.perimetro_m) t += `${areaM2 ? ',' : '.'} perímetro de ${_brNum(job.perimetro_m, 2)} m`;
  if (nv) t += `, definido por ${nv} vértices`;
  t += '. Sistema geodésico de referência: SIRGAS 2000 (EPSG:4674)';
  if (job.fuso) t += `, UTM fuso ${job.fuso}${job.hemisferio || 'S'}, MC ${mc}°`;
  t += '.';
  // Cadastro municipal (BCI) + regularidade fiscal (CND de IPTU) — completa a memória
  const bci = job.bci || {};
  const insc = job.inscricao_municipal || bci.inscricao_contribuinte;
  if (insc) t += ` Inscrição municipal nº ${insc}${bci.area_edificada_m2 ? `, área edificada de ${_brNum(bci.area_edificada_m2, 2)} m²` : ''}.`;
  const iptu = job.iptu || {};
  if (iptu.cnd_numero) t += ` IPTU regular — Certidão Negativa nº ${iptu.cnd_numero}${iptu.cnd_validade ? ` (válida até ${String(iptu.cnd_validade).split('-').reverse().join('/')})` : ''}.`;
  else if (iptu.situacao) t += ` Situação do IPTU: ${String(iptu.situacao).replace(/_/g, ' ')}.`;
  t += ' Levantamento conforme ABNT NBR 17047:2022 e Provimento CNJ nº 195/2025.';
  return t;
}

export default function OnrSigriPage() {
  const { toast } = useToast();
  const [jobs, setJobs] = useState(null);
  const [sel, setSel] = useState(null);       // job selecionado
  const [novoNome, setNovoNome] = useState('');
  const [busy, setBusy] = useState(false);

  const carregarLista = useCallback(async () => {
    try { setJobs(await onrSigriAPI.listar()); } catch (e) { setJobs([]); }
  }, []);
  useEffect(() => { carregarLista(); }, [carregarLista]);

  const criar = async () => {
    if (!novoNome.trim()) { toast({ title: 'Informe a denominação do imóvel', variant: 'destructive' }); return; }
    try {
      const j = await onrSigriAPI.criar({ nome: novoNome.trim() });
      setNovoNome(''); await carregarLista(); setSel(j);
    } catch (e) { toast({ title: 'Erro ao criar', variant: 'destructive' }); }
  };

  if (sel) return <Detalhe job={sel} onBack={() => { setSel(null); carregarLista(); }} toast={toast} />;

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <header className="flex items-center gap-3 mb-5">
        <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: GREEN }}>
          <MapPin className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold" style={{ color: GREEN }}>Arquivo ONR (SIG-RI)</h1>
          <p className="text-sm text-gray-500">Suba o mapa pronto + memorial + ART + certidão e gere o shapefile p/ o mapa.onr.org.br.</p>
        </div>
      </header>

      <div className="rounded-xl border bg-white p-4 mb-5">
        <label className={lbl}>Nova geração — denominação do imóvel</label>
        <div className="flex gap-2">
          <input className={inp} placeholder="Ex.: CHÁCARA BOA VISTA — Açailândia/MA" value={novoNome}
            onChange={(e) => setNovoNome(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && criar()} />
          <button onClick={criar} disabled={busy}
            className="px-4 py-2 rounded-lg text-white text-sm font-semibold inline-flex items-center gap-1 whitespace-nowrap" style={{ background: GREEN }}>
            <Plus className="w-4 h-4" /> Novo
          </button>
        </div>
      </div>

      {jobs === null ? <BrandSpinner label="Carregando…" />
        : jobs.length === 0 ? <p className="text-sm text-gray-400">Nenhum arquivo ONR ainda. Crie o primeiro acima.</p>
          : (
            <div className="space-y-2">
              {jobs.map((j) => (
                <button key={j.id} onClick={() => setSel(j)}
                  className="w-full text-left rounded-xl border bg-white p-3 hover:border-emerald-400 transition flex items-center gap-3">
                  {j.preview_b64
                    ? <img src={j.preview_b64} alt="satélite" className="w-24 h-16 object-cover rounded-lg border shrink-0" />
                    : <div className="w-24 h-16 rounded-lg bg-gray-100 flex items-center justify-center text-gray-300 shrink-0"><MapPin className="w-5 h-5" /></div>}
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm truncate" style={{ color: GREEN }}>{j.denominacao_imovel || j.nome}</div>
                    <div className="text-[11px] text-gray-400">{j.numero} · {j.municipio}/{j.uf} · {(j.vertices || []).length} vértice(s)</div>
                    {j.concluido && j.concluido_em && (
                      <div className="text-[10px] text-emerald-600 mt-0.5">✓ Concluído em {new Date(j.concluido_em).toLocaleString('pt-BR')}</div>
                    )}
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 shrink-0">{j.status}</span>
                </button>
              ))}
            </div>
          )}
    </div>
  );
}

function Detalhe({ job: job0, onBack, toast }) {
  const [job, setJob] = useState(job0);
  const [geojson, setGeojson] = useState(null);
  const [valid, setValid] = useState(null);
  const [busy, setBusy] = useState('');
  const [just, setJust] = useState({});
  const [tiposAnx, setTiposAnx] = useState([]);
  const debounce = useRef(null);
  const id = job.id;

  const recarregar = useCallback(async () => {
    try { setJob(await onrSigriAPI.obter(id)); } catch (e) { /* noop */ }
  }, [id]);
  useEffect(() => { onrSigriAPI.tiposAnexo().then(setTiposAnx).catch(() => setTiposAnx([])); }, []);

  // Anexos do processo
  const anexos = (job.anexos || []).slice().sort((a, b) => (a.ordem || 0) - (b.ordem || 0));
  const addAnexos = async (files) => {
    for (const f of Array.from(files || [])) {
      try { const r = await onrSigriAPI.anexoUpload(id, f, 'Outro', f.name); setJob((j) => ({ ...j, anexos: r.anexos })); }
      catch (e) { toast({ title: 'Falha no anexo', variant: 'destructive' }); }
    }
  };
  const setAnexoLocal = (aid, data) => setJob((j) => ({ ...j, anexos: (j.anexos || []).map((a) => (a.id === aid ? { ...a, ...data } : a)) }));
  const salvarAnexo = (aid, data) => { setAnexoLocal(aid, data); onrSigriAPI.anexoAtualizar(id, aid, data).catch(() => {}); };
  const moverAnexo = (aid, dir) => {
    const ids = anexos.map((a) => a.id);
    const i = ids.indexOf(aid);
    const k = i + dir;
    if (k < 0 || k >= ids.length) return;
    [ids[i], ids[k]] = [ids[k], ids[i]];
    onrSigriAPI.anexoOrdem(id, ids).then((r) => setJob((j) => ({ ...j, anexos: r.anexos }))).catch(() => {});
  };
  const verAnexo = async (aid) => {
    const win = window.open('', '_blank');
    try { const b = await onrSigriAPI.anexoView(id, aid); if (win) win.location = URL.createObjectURL(b); }
    catch (e) { if (win) win.close(); toast({ title: 'Falha ao abrir o anexo', variant: 'destructive' }); }
  };

  // edição com autosave (debounce)
  const upd = (patch) => {
    setJob((j) => ({ ...j, ...patch }));
    clearTimeout(debounce.current);
    const dados = patch;
    debounce.current = setTimeout(() => { onrSigriAPI.atualizar(id, dados).catch(() => {}); }, 700);
  };
  // edição de proprietário/matrícula (arrays)
  const updProp = (campo, val) => {
    const p = { ...((job.partes || [])[0] || { papel: 'requerente', tipo_pessoa: 'fisica' }), [campo]: val };
    upd({ partes: [p] });
  };
  const updMat = (campo, val) => {
    const m = { ...((job.matriculas || [])[0] || {}), [campo]: val };
    upd({ matriculas: [m] });
  };

  const enviar = async (tipo, file) => {
    if (!file) return;
    setBusy('up' + tipo);
    try { await onrSigriAPI.upload(id, tipo, file); await recarregar(); }
    catch (e) { toast({ title: 'Falha no upload', variant: 'destructive' }); }
    finally { setBusy(''); }
  };
  const extrair = async () => {
    setBusy('extrair');
    try {
      const r = await onrSigriAPI.extrair(id);
      setJob(r.job || (await onrSigriAPI.obter(id)));
      toast({ title: `Extraído (confiança ${Math.round((r.confianca || 0) * 100)}%)`, description: (r.avisos || []).join(' ') });
    } catch (e) { toast({ title: 'Falha ao extrair', description: e?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(''); }
  };
  const validar = async () => {
    setBusy('validar');
    try { setValid(await onrSigriAPI.validar(id)); } catch (e) { toast({ title: 'Falha ao validar', variant: 'destructive' }); }
    finally { setBusy(''); }
  };
  const justificar = async (codigo) => {
    const texto = (just[codigo] || '').trim();
    if (!texto) { toast({ title: 'Escreva a justificativa', variant: 'destructive' }); return; }
    try { setValid(await onrSigriAPI.justificar(id, codigo, texto)); toast({ title: 'Justificativa registrada' }); }
    catch (e) { toast({ title: 'Falha', variant: 'destructive' }); }
  };
  const carregarSat = async () => {
    setBusy('sat');
    try {
      setGeojson(await onrSigriAPI.geojson(id));
      onrSigriAPI.preview(id).catch(() => {});   // regenera a miniatura do card (best-effort)
    } catch (e) { toast({ title: 'Falha no satélite', variant: 'destructive' }); }
    finally { setBusy(''); }
  };
  const marcarConcluido = (v) => {
    const em = v ? new Date().toISOString() : null;
    setJob((j) => ({ ...j, concluido: v, concluido_em: em }));
    onrSigriAPI.atualizar(id, { concluido: v, concluido_em: em }).catch(() => {});
  };
  const copiarDescricao = async () => {
    try { await navigator.clipboard.writeText(descricaoPoligono(job)); toast({ title: 'Descrição copiada' }); }
    catch (e) { toast({ title: 'Copie manualmente do campo', variant: 'destructive' }); }
  };

  const up = job.uploads || {};
  const prop = (job.partes || [])[0] || {};
  const mat = (job.matriculas || [])[0] || {};
  const nb = job.numero || id;
  // nome do arquivo com vínculo da matrícula (ex.: SIGRI_ONR-2026-0001_Matricula-9809)
  const matTag = mat.matricula ? `_Matricula-${String(mat.matricula).replace(/[^0-9A-Za-z.]/g, '')}` : '';
  const nomeArq = `SIGRI_${nb}${matTag}`;
  const podeGerar = !valid || valid.pode_gerar;

  const renderCard = ([tipo, label, accept]) => {
    const it = (up[tipo] || [])[0];
    return (
      <div key={tipo} className="rounded-lg border p-3">
        <div className="text-xs font-medium text-gray-700 mb-1">{label}</div>
        {it ? (
          <div className="flex items-center justify-between text-[11px] text-emerald-700">
            <span className="truncate">✓ {it.nome}</span>
            <button onClick={() => onrSigriAPI.removerUpload(id, tipo, it.id).then(recarregar)}>
              <Trash2 className="w-3.5 h-3.5 text-gray-400 hover:text-red-500" />
            </button>
          </div>
        ) : (
          <label className="text-xs inline-flex items-center gap-1 text-emerald-700 cursor-pointer hover:underline">
            <Upload className="w-3.5 h-3.5" /> {busy === 'up' + tipo ? 'Enviando…' : 'Enviar arquivo'}
            <input type="file" className="hidden" accept={accept}
              onChange={(e) => enviar(tipo, e.target.files?.[0])} />
          </label>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <button onClick={onBack} className="text-sm text-gray-500 inline-flex items-center gap-1 mb-3 hover:text-gray-800">
        <ArrowLeft className="w-4 h-4" /> Voltar
      </button>
      <h1 className="text-lg font-bold mb-1" style={{ color: GREEN }}>{job.denominacao_imovel || job.nome}</h1>
      <p className="text-[11px] text-gray-400 mb-4">{nb} · status: {job.status}</p>

      {/* 1. Uploads */}
      <section className="rounded-xl border bg-white p-4 mb-4">
        <h2 className="font-semibold mb-1 text-sm" style={{ color: GREEN }}>1. Documentos (já confeccionados)</h2>
        <p className="text-[11px] text-gray-500 mb-2">Obrigatórios (geram o pacote + as informações geodésicas do Prov. 195):</p>
        <div className="grid sm:grid-cols-2 gap-3">{UPLOADS.map(renderCard)}</div>
        <p className="text-[11px] font-semibold text-gray-500 mt-3 mb-2">Opcionais — deixam a extração/descrição mais completa (não exigidos p/ gerar):</p>
        <div className="grid sm:grid-cols-2 gap-3">{UPLOADS_OPC.map(renderCard)}</div>
        <button onClick={extrair} disabled={busy === 'extrair'}
          className="mt-3 px-4 py-2 rounded-lg text-white text-sm font-semibold inline-flex items-center gap-1" style={{ background: GREEN }}>
          <RefreshCw className={`w-4 h-4 ${busy === 'extrair' ? 'animate-spin' : ''}`} /> {busy === 'extrair' ? 'Extraindo…' : 'Extrair tudo (memorial + BCI + IPTU)'}
        </button>
        {job.extracao_avisos?.length > 0 && (
          <ul className="mt-2 text-[11px] text-amber-600 list-disc pl-4">{job.extracao_avisos.map((a, i) => <li key={i}>{a}</li>)}</ul>
        )}
      </section>

      {/* 2. Dados extraídos (editáveis) */}
      <section className="rounded-xl border bg-white p-4 mb-4">
        <h2 className="font-semibold mb-3 text-sm" style={{ color: GREEN }}>2. Dados do imóvel (extraídos — confira/edite)</h2>
        <div className="grid sm:grid-cols-2 gap-3">
          <Field label="Denominação" full value={job.denominacao_imovel} onChange={(v) => upd({ denominacao_imovel: v })} />
          <Field label="Município" value={job.municipio} onChange={(v) => upd({ municipio: v })} />
          <Field label="UF" value={job.uf} onChange={(v) => upd({ uf: v })} />
          <Field label="Código IBGE (7 díg.)" value={job.codigo_ibge} onChange={(v) => upd({ codigo_ibge: (v || '').replace(/\D/g, '').slice(0, 7) })} />
          <Field label="Natureza do ato (NAT_ATO)" value={job.natureza} onChange={(v) => upd({ natureza: v })} />
          <Field label="Área (m²)" type="number" value={job.area_declarada_m2} onChange={(v) => upd({ area_declarada_m2: v === '' ? null : Number(v) })} />
          <Field label="Perímetro (m)" type="number" value={job.perimetro_m} onChange={(v) => upd({ perimetro_m: v === '' ? null : Number(v) })} />
          <Field label="Fuso UTM" type="number" value={job.fuso} onChange={(v) => upd({ fuso: v === '' ? null : Number(v) })} />
          <Field label="ART / TRT nº" value={job.trt_numero} onChange={(v) => upd({ trt_numero: v })} />
          <Field label="Precisão posicional (m)" type="number" value={job.precisao_posicional_m} onChange={(v) => upd({ precisao_posicional_m: v === '' ? null : Number(v) })} />
          <Field label="CIB" value={job.cib} onChange={(v) => upd({ cib: v })} />
          <Field label="Inscrição municipal (IPTU)" value={job.inscricao_municipal} onChange={(v) => upd({ inscricao_municipal: v })} />
          <Field label="Proprietário (nome)" value={prop.nome} onChange={(v) => updProp('nome', v)} />
          <Field label="Proprietário (CPF/CNPJ)" value={prop.cpf} onChange={(v) => updProp('cpf', v)} />
          <Field label="Matrícula nº" value={mat.matricula} onChange={(v) => updMat('matricula', v)} />
          <Field label="CNS da serventia" value={job.cartorio?.cns} onChange={(v) => upd({ cartorio: { ...(job.cartorio || {}), cns: v } })} />
        </div>
      </section>

      {/* 3. Vértices + satélite */}
      <section className="rounded-xl border bg-white p-4 mb-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold text-sm" style={{ color: GREEN }}>3. Poligonal — {(job.vertices || []).length} vértice(s)</h2>
          <button onClick={carregarSat} disabled={busy === 'sat'} className="text-xs inline-flex items-center gap-1 text-emerald-700 hover:underline">
            <RefreshCw className={`w-3.5 h-3.5 ${busy === 'sat' ? 'animate-spin' : ''}`} /> Atualizar satélite
          </button>
        </div>
        <PoligonalLeaflet geojson={geojson} height={280} />
        {(job.vertices || []).length > 0 && (
          <div className="overflow-x-auto mt-3">
            <table className="text-[11px] w-full">
              <thead><tr className="text-left text-gray-500"><th className="py-1">Vértice</th><th>Coord N</th><th>Coord E</th><th>Dist. (m)</th><th>Confrontante</th></tr></thead>
              <tbody>
                {job.vertices.map((v, i) => (
                  <tr key={i} className="border-t"><td className="py-1 font-mono">{v.de}</td><td className="font-mono">{v.coord_n}</td><td className="font-mono">{v.coord_e}</td><td>{v.distancia_m}</td><td>{v.confrontante_lado}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Anexos do processo — classificar / renomear / reordenar / visualizar */}
      <section className="rounded-xl border bg-white p-4 mb-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold text-sm" style={{ color: GREEN }}>Anexos do processo</h2>
          <label className="text-xs inline-flex items-center gap-1 text-emerald-700 cursor-pointer hover:underline">
            <Upload className="w-3.5 h-3.5" /> Anexar arquivo(s)
            <input type="file" multiple className="hidden" accept=".pdf,image/*" onChange={(e) => { addAnexos(e.target.files); e.target.value = ''; }} />
          </label>
        </div>
        {anexos.length === 0 ? (
          <p className="text-[11px] text-gray-400">Nenhum anexo. Adicione certidão, escritura, documento pessoal, CND, mapa… — classifique, renomeie e reordene a sequência.</p>
        ) : (
          <div className="space-y-2">
            {anexos.map((a, idx) => (
              <div key={a.id} className="flex items-center gap-2 rounded-lg border p-2">
                <div className="flex flex-col shrink-0">
                  <button disabled={idx === 0} onClick={() => moverAnexo(a.id, -1)} className="text-gray-400 disabled:opacity-30 hover:text-gray-700"><ChevronUp className="w-3.5 h-3.5" /></button>
                  <button disabled={idx === anexos.length - 1} onClick={() => moverAnexo(a.id, 1)} className="text-gray-400 disabled:opacity-30 hover:text-gray-700"><ChevronDown className="w-3.5 h-3.5" /></button>
                </div>
                <span className="text-[10px] text-gray-400 w-4 text-center shrink-0">{idx + 1}</span>
                <select className="text-[11px] border rounded px-1.5 py-1 w-40 shrink-0" value={a.tipo || 'Outro'} onChange={(e) => salvarAnexo(a.id, { tipo: e.target.value })}>
                  {(tiposAnx.length ? tiposAnx : [a.tipo || 'Outro']).map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
                <input className="flex-1 text-[11px] border rounded px-1.5 py-1 min-w-0" value={a.nome || ''} placeholder="Nome do documento"
                  onChange={(e) => setAnexoLocal(a.id, { nome: e.target.value })}
                  onBlur={() => onrSigriAPI.anexoAtualizar(id, a.id, { nome: a.nome }).catch(() => {})} />
                <button onClick={() => verAnexo(a.id)} className="text-emerald-700 hover:text-emerald-900 shrink-0" title="Visualizar"><Eye className="w-4 h-4" /></button>
                <button onClick={() => onrSigriAPI.anexoExcluir(id, a.id).then(recarregar)} className="text-gray-300 hover:text-red-500 shrink-0" title="Remover"><Trash2 className="w-4 h-4" /></button>
              </div>
            ))}
          </div>
        )}
        <p className="text-[10px] text-gray-400 mt-2">Classifique cada arquivo, renomeie e use ▲▼ para ordenar a sequência. Clique no olho para visualizar pelo site.</p>
      </section>

      {/* 4. Descrição do polígono (para colar no ONR) */}
      <section className="rounded-xl border border-amber-200 bg-amber-50/40 p-4 mb-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold text-sm" style={{ color: GREEN }}>4. Descrição do polígono (colar no mapa.onr.org.br)</h2>
          <button onClick={copiarDescricao} className="text-xs inline-flex items-center gap-1 px-2.5 py-1 rounded text-white" style={{ background: GREEN }}>
            <Copy className="w-3.5 h-3.5" /> Copiar
          </button>
        </div>
        <textarea readOnly className="w-full text-xs border rounded p-2 h-24 bg-white font-mono" value={descricaoPoligono(job)} />
        <p className="text-[10px] text-gray-500 mt-1">Gerada automaticamente dos dados extraídos — cole no campo "Descrição do polígono" do ONR. Atualiza ao editar os dados acima.</p>
      </section>

      {/* 5. Validação + geração */}
      <section className="rounded-xl border bg-white p-4">
        <h2 className="font-semibold mb-2 text-sm" style={{ color: GREEN }}>5. Validar & gerar</h2>
        <div className="grid md:grid-cols-2 gap-4 items-start">
        <div>
        <button onClick={validar} disabled={busy === 'validar'} className="text-xs inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border font-semibold hover:bg-gray-50">
          <RefreshCw className={`w-3.5 h-3.5 ${busy === 'validar' ? 'animate-spin' : ''}`} /> Validar SIG-RI/ONR
        </button>
        {valid && (
          <div className="mt-2 space-y-2">
            <div className={`text-xs font-semibold ${valid.pode_gerar ? 'text-emerald-700' : 'text-red-600'}`}>
              {valid.pode_gerar
                ? `✓ Pronto para gerar · área ${Number(valid.area_calculada_m2 || 0).toLocaleString('pt-BR')} m² · fuso ${valid.fuso ?? '—'}${valid.hemisferio || ''}`
                : `✗ ${valid.erros.length} erro(s) e ${valid.bloqueios_pendentes.length} pendência(s)`}
            </div>
            {valid.erros.map((e) => (
              <div key={e.codigo} className="text-[11px] rounded-md border border-red-200 bg-red-50 px-2 py-1 text-red-700"><b>{e.codigo}</b> — {e.mensagem}</div>
            ))}
            {valid.warnings.map((w) => {
              const pend = valid.bloqueios_pendentes.includes(w.codigo);
              return (
                <div key={w.codigo} className={`text-[11px] rounded-md border px-2 py-1 ${w.bloqueante ? 'border-amber-300 bg-amber-50 text-amber-800' : 'border-gray-200 bg-gray-50 text-gray-600'}`}>
                  <div><b>{w.codigo}</b>{w.bloqueante ? ' (bloqueante)' : ''} — {w.mensagem}</div>
                  {w.bloqueante && pend && (
                    <div className="flex gap-1 mt-1">
                      <input className="flex-1 border rounded px-2 py-1 text-[11px]" placeholder="Justificativa do RT…"
                        value={just[w.codigo] || ''} onChange={(ev) => setJust((s) => ({ ...s, [w.codigo]: ev.target.value }))} />
                      <button onClick={() => justificar(w.codigo)} className="text-[11px] px-2 py-1 rounded text-white whitespace-nowrap" style={{ background: GREEN }}>Justificar</button>
                    </div>
                  )}
                  {w.bloqueante && !pend && <div className="text-emerald-700 mt-0.5">✓ justificado</div>}
                </div>
              );
            })}
          </div>
        )}
        <div className="flex gap-2 flex-wrap mt-3">
          <button disabled={!podeGerar}
            onClick={() => onrSigriAPI.shapefile(id).then((b) => saveBlob(b, `${nomeArq}.zip`)).catch((e) => toast({ title: 'Erro ao gerar', description: e?.response?.data?.detail || 'Confira os vértices/dados.', variant: 'destructive' }))}
            className={`text-xs inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-white ${!podeGerar ? 'opacity-50 cursor-not-allowed' : ''}`} style={{ background: GREEN }}>
            <Download className="w-3.5 h-3.5" /> Shapefile SIG-RI (.zip)
          </button>
          <button onClick={() => onrSigriAPI.kml(id).then((b) => saveBlob(b, `${nomeArq}.kml`)).catch(() => toast({ title: 'Erro no KML', variant: 'destructive' }))}
            className="text-xs inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border hover:bg-gray-50">
            <Download className="w-3.5 h-3.5" /> KML
          </button>
        </div>
        {valid && !podeGerar && <p className="text-[11px] text-red-500 mt-1">Resolva os erros/pendências para liberar o download.</p>}
        <p className="text-[10px] text-gray-400 mt-2 inline-flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Pacote pronto para upload no mapa.onr.org.br (SIRGAS 2000 / EPSG:4674).</p>
        </div>
        <div className="rounded-lg border bg-gray-50 p-3">
          <div className="text-[11px] font-semibold mb-1" style={{ color: GREEN }}>As peças do pacote (.zip)</div>
          <table className="text-[11px] w-full">
            <tbody>
              {[
                ['.shp', 'a geometria (o polígono/vértices)'],
                ['.shx', 'índice que acelera a leitura do .shp'],
                ['.dbf', 'tabela de atributos (matrícula, proprietário, área…)'],
                ['.prj', 'sistema de coordenadas (SIRGAS 2000 / EPSG:4674)'],
                ['.cpg', 'codificação do .dbf (UTF-8) — mantém os acentos corretos'],
              ].map(([e, ds]) => (
                <tr key={e} className="border-t first:border-t-0 align-top">
                  <td className="py-1 pr-2 font-mono font-semibold whitespace-nowrap">{e}</td>
                  <td className="py-1 text-gray-600">{ds}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-[10px] text-gray-400 mt-1">No ONR, suba os 4 arquivos (.shp/.shx/.dbf/.prj) com o <b>mesmo nome</b>, juntos.</p>
        </div>
        </div>
      </section>

      {/* Conclusão — tag com data/hora */}
      <section className={`rounded-xl border p-4 mt-4 ${job.concluido ? 'border-emerald-300 bg-emerald-50/60' : 'bg-white'}`}>
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input type="checkbox" checked={!!job.concluido} onChange={(e) => marcarConcluido(e.target.checked)} />
          <span className="font-semibold" style={{ color: GREEN }}>Marcar como concluído</span>
        </label>
        {job.concluido && job.concluido_em && (
          <p className="text-[11px] text-emerald-700 mt-1 inline-flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> Concluído em {new Date(job.concluido_em).toLocaleString('pt-BR')}
          </p>
        )}
      </section>
    </div>
  );
}
