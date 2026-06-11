// @module tvi/VistoriaAverbacaoForm — Formulário da Vistoria de Obra para Averbação (6 abas)
// Catálogos via GET /tvi/catalogos/averbacao (nunca hardcoda). Autosave debounce 1,5s.
// Cálculo de divergência e conclusão geral ao vivo (preview); servidor é a fonte da verdade.
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Save, Loader2, Building2, Ruler, ListChecks, ShieldCheck,
  FileCheck2, Gavel, FileDown, FileText as FileTextIcon,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { tviAPI } from '../../../lib/api';
import PhotoUploader from './components/PhotoUploader';

/* ── primitivos ──────────────────────────────────────────────────────────── */
const Chip = ({ active, onClick, children }) => (
  <button
    type="button" onClick={onClick}
    className={`px-3 py-2 rounded-xl text-sm font-medium border transition min-h-[40px]
      ${active ? 'bg-emerald-900 text-white border-emerald-900' : 'bg-white text-gray-700 border-gray-200 hover:border-emerald-300'}`}
  >{children}</button>
);

const ChipGroup = ({ options, value, onChange }) => (
  <div className="flex flex-wrap gap-2">
    {options.map((o) => (
      <Chip key={o.value} active={value === o.value} onClick={() => onChange(o.value)}>{o.label}</Chip>
    ))}
  </div>
);

const Seg = ({ value, onChange, options }) => (
  <div className="inline-flex rounded-lg overflow-hidden border border-gray-200">
    {options.map((o) => (
      <button
        key={o.value} type="button" onClick={() => onChange(o.value)}
        className={`px-3 py-1.5 text-xs font-semibold transition ${value === o.value ? o.cls : 'bg-white text-gray-500 hover:bg-gray-50'}`}
      >{o.label}</button>
    ))}
  </div>
);

const Field = ({ label, children }) => (
  <div className="space-y-1">
    <label className="text-xs font-medium text-gray-600">{label}</label>
    {children}
  </div>
);

const Inp = (props) => (
  <input {...props} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-emerald-400" />
);

const fmtNum = (v) => {
  if (v == null || v === '' || isNaN(Number(v))) return '—';
  return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

/* ── componente ──────────────────────────────────────────────────────────── */
const TABS = [
  { id: 'dados', label: 'Dados', icon: Building2 },
  { id: 'areas', label: 'Áreas', icon: Ruler },
  { id: 'etapas', label: 'Etapas', icon: ListChecks },
  { id: 'sistemas', label: 'Sistemas', icon: ShieldCheck },
  { id: 'documentos', label: 'Documentos', icon: FileCheck2 },
  { id: 'parecer', label: 'Parecer', icon: Gavel },
];

export default function VistoriaAverbacaoForm({ id, vistoria, model }) {
  const nav = useNavigate();
  const { toast } = useToast();
  const [form, setForm] = useState(vistoria || {});
  const [cat, setCat] = useState(null);
  const [tab, setTab] = useState('dados');
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [photos, setPhotos] = useState([]);
  const debRef = useRef(null);
  const firstLoad = useRef(true);

  // Carrega as fotos da vistoria (todas as abas/ambientes).
  useEffect(() => {
    if (!id) return;
    tviAPI.listPhotos(id).then((ps) => setPhotos(Array.isArray(ps) ? ps : [])).catch(() => {});
  }, [id]);

  const photosOf = useCallback(
    (ambiente) => photos.filter((p) => (p.ambiente || '') === ambiente),
    [photos],
  );
  const setPhotosFor = useCallback((ambiente, list) => {
    setPhotos((prev) => [
      ...prev.filter((p) => (p.ambiente || '') !== ambiente),
      ...(list || []).map((x) => ({ ...x, ambiente })),
    ]);
  }, []);

  // Carrega catálogos e inicializa o subdoc averbacao se vazio.
  useEffect(() => {
    let alive = true;
    tviAPI.catalogosAverbacao().then((c) => {
      if (!alive) return;
      setCat(c);
      setForm((f) => {
        const av = { ...(f.averbacao || {}) };
        if (!av.destinacao) av.destinacao = 'residencial';
        if (!av.confronto) av.confronto = {};
        if (!Array.isArray(av.etapas) || !av.etapas.length) {
          av.etapas = c.etapas.map((e) => ({ etapa_id: e.id, percentual: 0 }));
        }
        if (!Array.isArray(av.sistemas) || !av.sistemas.length) {
          av.sistemas = c.sistemas.map((s) => ({ sistema_id: s.id, conformidade: 'PENDENTE', patologias: [], severidade: null, observacao: '' }));
        }
        if (!Array.isArray(av.documentos) || !av.documentos.length) {
          av.documentos = c.documentos.map((d) => ({ doc_id: d.id, situacao: 'PENDENTE_AVALIACAO', observacao: '' }));
        }
        return { ...f, averbacao: av };
      });
    }).catch(() => toast({ title: 'Erro ao carregar catálogos', variant: 'destructive' }));
    return () => { alive = false; };
  }, [toast]);

  const av = form.averbacao || {};
  const conf = av.confronto || {};
  const soResidencial = (av.destinacao || 'residencial') === 'residencial';

  /* ── autosave ── */
  const save = useCallback(async (silent = true) => {
    if (!id) return;
    setSaving(true);
    try {
      // Não fazemos merge do retorno no form para não re-disparar o autosave;
      // o preview de divergência/conclusão é calculado no cliente (calc) e o
      // servidor persiste os valores oficiais.
      await tviAPI.update(id, form);
      setSavedAt(new Date());
      if (!silent) toast({ title: 'Vistoria salva' });
    } catch (e) {
      if (!silent) toast({ title: 'Erro ao salvar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSaving(false); }
  }, [id, form, toast]);

  useEffect(() => {
    if (firstLoad.current) { firstLoad.current = false; return; }
    if (debRef.current) clearTimeout(debRef.current);
    debRef.current = setTimeout(() => save(true), 1500);
    return () => debRef.current && clearTimeout(debRef.current);
  }, [form, save]);

  /* ── setters ── */
  const setRoot = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const setAv = (k, v) => setForm((f) => ({ ...f, averbacao: { ...(f.averbacao || {}), [k]: v } }));
  const setConf = (k, v) => setForm((f) => ({ ...f, averbacao: { ...(f.averbacao || {}), confronto: { ...((f.averbacao || {}).confronto || {}), [k]: v } } }));
  const setEtapa = (eid, pct) => setForm((f) => {
    const etapas = ((f.averbacao || {}).etapas || []).map((e) => e.etapa_id === eid ? { ...e, percentual: pct } : e);
    return { ...f, averbacao: { ...f.averbacao, etapas } };
  });
  const setSistema = (sid, patch) => setForm((f) => {
    const sistemas = ((f.averbacao || {}).sistemas || []).map((s) => s.sistema_id === sid ? { ...s, ...patch } : s);
    return { ...f, averbacao: { ...f.averbacao, sistemas } };
  });
  const setDoc = (did, patch) => setForm((f) => {
    const documentos = ((f.averbacao || {}).documentos || []).map((d) => d.doc_id === did ? { ...d, ...patch } : d);
    return { ...f, averbacao: { ...f.averbacao, documentos } };
  });

  /* ── cálculos ao vivo (preview) ── */
  const calc = useMemo(() => {
    const tol = cat?.tolerancia_divergencia || { verde: 2, ambar: 10 };
    const aProj = parseFloat(conf.area_projeto_m2);
    const aMed = parseFloat(conf.area_medida_m2);
    const aTerr = parseFloat(conf.area_terreno_m2);
    let divM2 = null, divPct = null, taxa = null;
    if (aProj > 0 && !isNaN(aMed)) { divM2 = aMed - aProj; divPct = (divM2 / aProj) * 100; }
    if (aTerr > 0 && !isNaN(aMed)) taxa = (aMed / aTerr) * 100;
    let faixa = 'verde';
    if (divPct != null) {
      const ap = Math.abs(divPct);
      faixa = ap <= tol.verde ? 'verde' : ap <= tol.ambar ? 'ambar' : 'vermelho';
    }
    const pesos = {}; (cat?.etapas || []).forEach((e) => { pesos[e.id] = e.peso; });
    let sp = 0, sw = 0;
    (av.etapas || []).forEach((e) => { const w = pesos[e.etapa_id]; if (w) { sp += w; sw += w * (e.percentual || 0); } });
    const conclusao = sp ? sw / sp : 0;
    return { divM2, divPct, taxa, faixa, conclusao };
  }, [conf, av.etapas, cat]);

  const faixaInfo = {
    verde: { cls: 'bg-emerald-50 border-emerald-200 text-emerald-800', txt: 'Averbação direta' },
    ambar: { cls: 'bg-amber-50 border-amber-200 text-amber-800', txt: 'Verificar exigência de as-built' },
    vermelho: { cls: 'bg-red-50 border-red-200 text-red-800', txt: 'Regularização prévia recomendada' },
  }[calc.faixa];

  /* ── export ── */
  const baixar = async (tipo) => {
    setExporting(true);
    try {
      await save(true);
      const blob = tipo === 'pdf' ? await tviAPI.exportPdf(id) : await tviAPI.exportDocx(id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(form.numero_tvi || 'AVERBACAO').replace(/\//g, '-')}.${tipo}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast({ title: 'Erro ao exportar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setExporting(false); }
  };

  if (!cat) return <div className="py-20 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-emerald-700" /></div>;

  const sistemasVis = (cat.sistemas || []).filter((s) => !(s.comercial && soResidencial));
  const docsVis = (cat.documentos || []).filter((d) => !(d.comercial && soResidencial));
  const sevOpts = [
    { value: 'leve', label: 'Leve', cls: 'bg-yellow-500 text-white' },
    { value: 'moderada', label: 'Moderada', cls: 'bg-orange-500 text-white' },
    { value: 'grave', label: 'Grave', cls: 'bg-red-600 text-white' },
  ];

  return (
    <div className="max-w-4xl mx-auto pb-24 space-y-5">
      {/* Topbar */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => nav('/dashboard/tvi')}><ArrowLeft className="w-4 h-4 mr-1" /> Voltar</Button>
        <div className="flex items-center gap-2">
          {savedAt && <span className="text-xs text-gray-400">Salvo {savedAt.toLocaleTimeString('pt-BR')} ✓</span>}
          {saving && <Loader2 className="w-4 h-4 animate-spin text-emerald-700" />}
          <Button variant="outline" onClick={() => save(false)} disabled={saving}><Save className="w-4 h-4 mr-1" /> Salvar</Button>
        </div>
      </div>

      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="font-semibold text-gray-900">{model?.nome || 'Vistoria de Obra para Averbação'}</div>
            <div className="text-sm text-gray-500">{form.numero_tvi || ''}</div>
          </div>
          <span className="text-[10px] px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full font-semibold">TRT Obrigatória</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-gray-200 p-2 grid grid-cols-3 sm:grid-cols-6 gap-1 sticky top-2 z-10">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`flex flex-col items-center gap-1 px-2 py-2 rounded-lg text-xs font-medium transition
                ${tab === t.id ? 'bg-emerald-900 text-white' : 'text-gray-600 hover:bg-gray-50'}`}>
              <Icon className="w-4 h-4" />{t.label}
            </button>
          );
        })}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        {/* ── DADOS ── */}
        {tab === 'dados' && (
          <>
            <Field label="Destinação">
              <ChipGroup
                options={(cat.destinacoes || []).map((d) => ({ value: d, label: d.charAt(0).toUpperCase() + d.slice(1) }))}
                value={av.destinacao} onChange={(v) => setAv('destinacao', v)} />
            </Field>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Endereço"><Inp value={form.imovel_endereco || ''} onChange={(e) => setRoot('imovel_endereco', e.target.value)} /></Field>
              <Field label="Matrícula *"><Inp value={form.imovel_matricula || ''} onChange={(e) => setRoot('imovel_matricula', e.target.value)} /></Field>
              <Field label="Cartório *"><Inp value={av.cartorio || ''} onChange={(e) => setAv('cartorio', e.target.value)} /></Field>
              <Field label="Inscrição municipal"><Inp value={av.inscricao_municipal || ''} onChange={(e) => setAv('inscricao_municipal', e.target.value)} /></Field>
              <Field label="CNO da obra"><Inp value={av.cno || ''} onChange={(e) => setAv('cno', e.target.value)} /></Field>
              <Field label="Alvará nº"><Inp value={av.alvara_numero || ''} onChange={(e) => setAv('alvara_numero', e.target.value)} /></Field>
              <Field label="Habite-se nº"><Inp value={av.habitese_numero || ''} onChange={(e) => setAv('habitese_numero', e.target.value)} /></Field>
              <Field label="Pavimentos"><Inp type="number" value={av.pavimentos ?? ''} onChange={(e) => setAv('pavimentos', e.target.value === '' ? null : parseInt(e.target.value))} /></Field>
              <Field label="Proprietário / Requerente"><Inp value={av.requerente_nome || ''} onChange={(e) => setAv('requerente_nome', e.target.value)} /></Field>
              <Field label="RT da execução (se distinto)"><Inp value={av.rt_execucao || ''} onChange={(e) => setAv('rt_execucao', e.target.value)} /></Field>
              <Field label="Padrão NBR 12721"><Inp value={av.padrao_construtivo || ''} onChange={(e) => setAv('padrao_construtivo', e.target.value)} placeholder="Ex.: Normal / Alto" /></Field>
              <Field label="Tipo de edificação"><Inp value={av.tipo_edificacao || ''} onChange={(e) => setAv('tipo_edificacao', e.target.value)} /></Field>
            </div>
          </>
        )}

        {/* ── ÁREAS ── */}
        {tab === 'areas' && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Área de projeto (m²)"><Inp type="number" value={conf.area_projeto_m2 ?? ''} onChange={(e) => setConf('area_projeto_m2', e.target.value === '' ? null : parseFloat(e.target.value))} /></Field>
              <Field label="Área medida in loco (m²) *"><Inp type="number" value={conf.area_medida_m2 ?? ''} onChange={(e) => setConf('area_medida_m2', e.target.value === '' ? null : parseFloat(e.target.value))} /></Field>
              <Field label="Área da matrícula (m²)"><Inp type="number" value={conf.area_matricula_m2 ?? ''} onChange={(e) => setConf('area_matricula_m2', e.target.value === '' ? null : parseFloat(e.target.value))} /></Field>
              <Field label="Área do terreno (m²)"><Inp type="number" value={conf.area_terreno_m2 ?? ''} onChange={(e) => setConf('area_terreno_m2', e.target.value === '' ? null : parseFloat(e.target.value))} /></Field>
            </div>
            {/* Card de divergência (3 estados) */}
            <div className={`rounded-xl border p-4 ${faixaInfo.cls}`}>
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide opacity-70">Divergência executado × aprovado</div>
                  <div className="text-2xl font-bold">{calc.divM2 != null ? `${fmtNum(Math.abs(calc.divM2))} m²` : '—'}{calc.divPct != null && <span className="text-base font-semibold ml-2">({fmtNum(Math.abs(calc.divPct))}%)</span>}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs opacity-70">Taxa de ocupação</div>
                  <div className="text-lg font-bold">{calc.taxa != null ? `${fmtNum(calc.taxa)}%` : '—'}</div>
                </div>
              </div>
              <div className="mt-2 text-sm font-semibold">{faixaInfo.txt}</div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Recuo frontal (m)"><Inp type="number" value={conf.recuo_frontal_m ?? ''} onChange={(e) => setConf('recuo_frontal_m', e.target.value === '' ? null : parseFloat(e.target.value))} /></Field>
              <Field label="Recuos laterais"><Inp value={conf.recuos_laterais || ''} onChange={(e) => setConf('recuos_laterais', e.target.value)} /></Field>
            </div>
            <Field label="Conformidade de implantação">
              <ChipGroup options={[
                { value: 'conforme', label: 'Conforme' },
                { value: 'divergencia_leve', label: 'Divergência leve' },
                { value: 'divergencia_relevante', label: 'Divergência relevante' },
              ]} value={conf.implantacao || 'conforme'} onChange={(v) => setConf('implantacao', v)} />
            </Field>
            <Field label="Detalhamento por pavimento/anexo">
              <textarea rows={3} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
                value={conf.detalhe_pavimentos || ''} onChange={(e) => setConf('detalhe_pavimentos', e.target.value)} />
            </Field>
            <div className="border-t border-gray-100 pt-4">
              <div className="text-sm font-semibold text-emerald-800 mb-2">Fotos — Fachada e Medições</div>
              <PhotoUploader vistoriaId={id} ambiente="Fachada e Medições"
                photos={photosOf('Fachada e Medições')}
                onUploaded={(list) => setPhotosFor('Fachada e Medições', list)} />
            </div>
          </>
        )}

        {/* ── ETAPAS ── */}
        {tab === 'etapas' && (
          <>
            <div className={`rounded-xl border p-4 ${calc.conclusao >= 95 ? 'bg-emerald-50 border-emerald-200' : 'bg-gray-50 border-gray-200'}`}>
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">Conclusão geral (ponderada)</div>
              <div className="text-3xl font-bold text-emerald-900">{fmtNum(calc.conclusao).replace(',00', '')}%</div>
            </div>
            <div className="space-y-4">
              {(cat.etapas || []).map((e) => {
                const cur = (av.etapas || []).find((x) => x.etapa_id === e.id)?.percentual ?? 0;
                return (
                  <div key={e.id}>
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-gray-700">{e.nome} <span className="text-gray-400">· peso {e.peso}</span></span>
                      <span className="font-bold text-emerald-800">{cur}%</span>
                    </div>
                    <input type="range" min={0} max={100} step={5} value={cur}
                      onChange={(ev) => setEtapa(e.id, parseInt(ev.target.value))}
                      className="w-full accent-emerald-700" />
                  </div>
                );
              })}
            </div>
          </>
        )}

        {/* ── SISTEMAS ── */}
        {tab === 'sistemas' && (
          <div className="space-y-3">
            {sistemasVis.map((s) => {
              const item = (av.sistemas || []).find((x) => x.sistema_id === s.id) || {};
              return (
                <div key={s.id} className="border border-gray-200 rounded-xl p-3">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div>
                      <div className="text-sm font-medium text-gray-800">{s.nome}</div>
                      {s.norma && <div className="text-[11px] text-gray-400">{s.norma}</div>}
                    </div>
                    <Seg value={item.conformidade} onChange={(v) => setSistema(s.id, { conformidade: v })} options={[
                      { value: 'C', label: 'C', cls: 'bg-emerald-600 text-white' },
                      { value: 'NC', label: 'NC', cls: 'bg-red-600 text-white' },
                      { value: 'NA', label: 'NA', cls: 'bg-gray-400 text-white' },
                    ]} />
                  </div>
                  {item.conformidade === 'NC' && (
                    <div className="mt-3 space-y-3 border-t border-gray-100 pt-3">
                      <div className="flex flex-wrap gap-1.5">
                        {(cat.patologias || []).map((p) => {
                          const on = (item.patologias || []).includes(p);
                          return (
                            <button key={p} type="button"
                              onClick={() => setSistema(s.id, { patologias: on ? item.patologias.filter((x) => x !== p) : [...(item.patologias || []), p] })}
                              className={`px-2 py-1 rounded-lg text-[11px] border ${on ? 'bg-red-600 text-white border-red-600' : 'bg-white text-gray-600 border-gray-200'}`}>{p}</button>
                          );
                        })}
                      </div>
                      <Seg value={item.severidade} onChange={(v) => setSistema(s.id, { severidade: v })} options={sevOpts} />
                      <textarea rows={2} placeholder="Observação..." className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
                        value={item.observacao || ''} onChange={(e) => setSistema(s.id, { observacao: e.target.value })} />
                      <PhotoUploader vistoriaId={id} ambiente={s.nome}
                        photos={photosOf(s.nome)}
                        onUploaded={(list) => setPhotosFor(s.nome, list)} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* ── DOCUMENTOS ── */}
        {tab === 'documentos' && (
          <div className="space-y-2">
            {docsVis.map((d) => {
              const item = (av.documentos || []).find((x) => x.doc_id === d.id) || {};
              return (
                <div key={d.id} className="flex items-center justify-between gap-2 border border-gray-200 rounded-xl p-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-800">{d.nome}</div>
                    <div className="text-[11px] text-gray-400">{d.base}</div>
                  </div>
                  <Seg value={item.situacao} onChange={(v) => setDoc(d.id, { situacao: v })} options={[
                    { value: 'OK', label: 'OK', cls: 'bg-emerald-600 text-white' },
                    { value: 'PEND', label: 'PEND', cls: 'bg-amber-500 text-white' },
                    { value: 'NA', label: 'NA', cls: 'bg-gray-400 text-white' },
                  ]} />
                </div>
              );
            })}
            <p className="text-[11px] text-gray-400 pt-1">Itens marcados como PEND viram pendências impeditivas no relatório.</p>
          </div>
        )}

        {/* ── PARECER ── */}
        {tab === 'parecer' && (
          <>
            <Field label="Situação da obra">
              <ChipGroup options={[
                { value: 'concluida', label: 'Concluída' },
                { value: 'concluida_pendencias', label: 'Concluída c/ pendências' },
                { value: 'em_conclusao', label: 'Em conclusão' },
              ]} value={av.situacao_obra || 'concluida'} onChange={(v) => setAv('situacao_obra', v)} />
            </Field>
            <Field label="Compatibilidade com o projeto">
              <ChipGroup options={[
                { value: 'total', label: 'Total' },
                { value: 'regularizavel', label: 'Divergência regularizável' },
                { value: 'relevante', label: 'Divergência relevante' },
              ]} value={av.compatibilidade || 'total'} onChange={(v) => setAv('compatibilidade', v)} />
            </Field>
            <Field label="Parecer para averbação">
              <ChipGroup options={[
                { value: 'apta', label: 'Apta' },
                { value: 'apta_apos_saneamento', label: 'Apta após saneamento' },
                { value: 'inapta', label: 'Inapta' },
              ]} value={av.parecer || 'apta'} onChange={(v) => setAv('parecer', v)} />
            </Field>
            <Field label="Necessita as-built?">
              <ChipGroup options={[{ value: true, label: 'Sim' }, { value: false, label: 'Não' }]}
                value={!!av.necessita_asbuilt} onChange={(v) => setAv('necessita_asbuilt', v)} />
            </Field>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Recomendações">
                <textarea rows={3} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
                  value={av.recomendacoes || ''} onChange={(e) => setAv('recomendacoes', e.target.value)} />
              </Field>
              <Field label="Prazo de saneamento"><Inp value={av.prazo_saneamento || ''} onChange={(e) => setAv('prazo_saneamento', e.target.value)} /></Field>
              <Field label="ART/TRT nº"><Inp value={form.art_trt_numero || ''} onChange={(e) => setRoot('art_trt_numero', e.target.value)} /></Field>
              <Field label="Responsável técnico"><Inp value={form.responsavel_nome || ''} onChange={(e) => setRoot('responsavel_nome', e.target.value)} /></Field>
            </div>
          </>
        )}
      </div>

      {/* Export */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-wrap gap-2">
        <Button onClick={() => baixar('pdf')} disabled={exporting} className="bg-emerald-900 hover:bg-emerald-800 text-white gap-1">
          {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />} Exportar PDF
        </Button>
        <Button onClick={() => baixar('docx')} disabled={exporting} variant="outline" className="gap-1">
          <FileTextIcon className="w-4 h-4" /> DOCX
        </Button>
      </div>
    </div>
  );
}
