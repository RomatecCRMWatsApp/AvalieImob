// Requerimento de Cancelamento de parcela SIGEF (Ofício Circular 814/2026/INCRA).
// Seletor de Justificativa Pré-estabelecida + condições de deferimento automático (i–viii)
// + checklist de documentos + aferição ao vivo + download do requerimento.
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Loader2, Download, Eye, CheckCircle2, AlertTriangle, Circle, MinusCircle, Info,
  Paperclip, FileText, XCircle, Wand2, FileStack,
} from 'lucide-react';
import { georefAPI, aiAPI } from '../../../lib/api';
import RichTextEditor from '../../ui/RichTextEditor';
import { paraEditorHtml } from '../../ui/RichField';
import { AiButton } from '../ptam/shared/primitives';
import { useToast } from '../../../hooks/use-toast';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';

const num = (v) => {
  if (v === null || v === undefined || v === '') return null;
  const n = parseFloat(String(v).replace(',', '.').replace(/[^\d.-]/g, ''));
  return Number.isNaN(n) ? null : n;
};

// 3-estados: pendente → ok → na → pendente
const nextStatus = (s) => (s === 'ok' ? 'na' : s === 'na' ? 'pendente' : 'ok');
const STATUS_META = {
  ok: { icon: CheckCircle2, color: '#059669', label: 'OK' },
  na: { icon: MinusCircle, color: '#9ca3af', label: 'N/A' },
  pendente: { icon: Circle, color: '#d1d5db', label: 'Pendente' },
};

export default function CancelamentoBloco({ proj, onChange, busy }) {
  const { toast } = useToast();
  const [justs, setJusts] = useState([]);
  const [downloading, setDownloading] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [uploadingKey, setUploadingKey] = useState('');
  const [odsVal, setOdsVal] = useState(null);
  const [odsBusy, setOdsBusy] = useState(false);
  const [dossieBusy, setDossieBusy] = useState(false);
  const codeFilled = useRef(false);
  const lastAutoJust = useRef(null);
  const canc = useMemo(() => proj.cancelamento || {}, [proj.cancelamento]);

  useEffect(() => {
    georefAPI.cancelamentoJustificativas()
      .then((r) => setJusts(r.justificativas || []))
      .catch(() => setJusts([]));
  }, []);

  const sel = useMemo(() => justs.find((j) => j.id === canc.justificativa), [justs, canc.justificativa]);

  // Auto-preenche o CÓDIGO da parcela com a certificação SIGEF do imóvel (1x, se vazio).
  useEffect(() => {
    if (codeFilled.current) return;
    const sigef = proj.imovel?.certificacao_sigef;
    if (sigef && !canc.codigo_parcela_sigef) {
      onChange({ codigo_parcela_sigef: sigef });
      codeFilled.current = true;
    }
  }, [proj.imovel?.certificacao_sigef]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-preenche o DETALHAMENTO com o texto padrão do INCRA da justificativa escolhida.
  // Só sobrescreve quando o campo está vazio ou ainda contém um auto-preenchimento anterior.
  useEffect(() => {
    if (!sel || !justs.length) return;
    if (lastAutoJust.current === sel.id) return;
    const strip = (h) => (h || '').replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim();
    const cur = strip(canc.justificativa_texto);
    const ehAuto = !cur || justs.some((j) => (j.descricao || '').trim() === cur);
    if (ehAuto && cur !== (sel.descricao || '').trim()) {
      onChange({ justificativa_texto: `<p>${sel.descricao || ''}</p>` });
    }
    lastAutoJust.current = sel.id;
  }, [sel, justs]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAiDetalhe = async () => {
    if (!sel) { toast({ title: 'Selecione a justificativa primeiro', variant: 'destructive' }); return; }
    const im = proj.imovel || {};
    const atual = (canc.justificativa_texto || '').replace(/<[^>]*>/g, ' ').trim();
    const prompt =
      'Você redige um REQUERIMENTO DE CANCELAMENTO de parcela georreferenciada junto ao INCRA/SIGEF ' +
      '(Ofício Circular nº 814/2026). Redija o DETALHAMENTO da justificativa técnica de forma formal, ' +
      'objetiva e em português-BR (3 a 6 frases), coerente com a justificativa e o imóvel. Retorne APENAS ' +
      'o texto, sem títulos nem rótulos.\n\n' +
      `Justificativa pré-estabelecida: ${sel.num}. ${sel.titulo} — ${sel.descricao}\n` +
      `Imóvel: ${im.denominacao || im.denominacao_matricula || '—'}, matrícula ${im.matricula || '—'}, ` +
      `INCRA/SNCR ${im.cod_incra || '—'}, ${im.municipio || '—'}/${im.uf || '—'}.\n` +
      `Código da parcela SIGEF: ${canc.codigo_parcela_sigef || im.certificacao_sigef || '—'}.\n` +
      `Texto atual:\n${atual || '(vazio — gere um detalhamento inicial adequado)'}`;
    setAiLoading(true);
    try {
      const res = await aiAPI.chat(`georef_cancel_${proj.id}_${Date.now()}`, prompt);
      const texto = (res?.reply || '').trim();
      if (texto) {
        const html = texto.split(/\n{2,}/).map((p) => `<p>${p.replace(/\n/g, '<br/>')}</p>`).join('');
        onChange({ justificativa_texto: html });
        lastAutoJust.current = sel.id; // passa a ser texto do usuário/IA — não sobrescrever
        toast({ title: 'Detalhamento aperfeiçoado com IA' });
      }
    } catch (err) {
      toast({ title: 'Erro na IA', description: err?.response?.data?.detail || 'Tente novamente', variant: 'destructive' });
    } finally { setAiLoading(false); }
  };

  // Aferição das 8 condições de deferimento automático (mesma lógica do backend).
  const { cond, deferAuto } = useMemo(() => {
    const a = num(canc.area_parcela_ha);
    const b = num(canc.area_ods_ha);
    const dPct = a != null && b != null && a !== 0 ? (Math.abs(a - b) / a) * 100 : null;
    const dAbs = a != null && b != null ? Math.abs(a - b) : null;
    const c = [
      { t: 'O requerente é o responsável técnico pela certificação.', ok: canc.requerente_e_rt !== false },
      { t: 'A natureza da parcela objeto do cancelamento é particular.', ok: (canc.natureza || 'particular') === 'particular' },
      { t: 'A parcela objeto do cancelamento não tem registro confirmado no SIGEF.', ok: !canc.registro_confirmado },
      { t: 'A Planilha ODS associada tem apenas uma aba de perímetro.', ok: canc.ods_uma_aba !== false },
      { t: 'A área na Planilha ODS difere menos de 10% da parcela.', ok: dPct == null ? null : dPct < 10, det: dPct == null ? 'informe as áreas' : `${dPct.toFixed(2).replace('.', ',')}%` },
      { t: 'A área na Planilha ODS difere menos de 25 ha da parcela.', ok: dAbs == null ? null : dAbs < 25, det: dAbs == null ? 'informe as áreas' : `${dAbs.toFixed(4).replace('.', ',')} ha` },
      { t: 'A parcela não é oriunda de cancelamento deferido automaticamente.', ok: !canc.oriunda_cancelamento_auto },
      { t: 'O código SNCR do imóvel não está inibido.', ok: !canc.sncr_inibido },
    ];
    return { cond: c, deferAuto: !!sel && c.every((x) => x.ok === true) };
  }, [canc, sel]);

  const exigeOds = sel ? sel.exige_ods !== false && !canc.origem_contrato_destinacao_particular : true;

  const docs = useMemo(() => {
    if (!sel) return [];
    const st = canc.docs_status || {};
    const lista = (sel.documentos || []).map((label, i) => ({ key: `${sel.id}_${i}`, label, status: st[`${sel.id}_${i}`] || 'pendente' }));
    if (exigeOds) lista.push({ key: `${sel.id}_ods`, label: 'Planilha ODS associada no campo "nova certificação" (obrigatória)', status: st[`${sel.id}_ods`] || 'pendente' });
    return lista;
  }, [sel, canc.docs_status, exigeOds]);

  const okCount = docs.filter((d) => d.status === 'ok').length;

  const toggleDoc = (key) => {
    const st = { ...(canc.docs_status || {}) };
    st[key] = nextStatus(st[key] || 'pendente');
    onChange({ docs_status: st });
  };

  const anexos = canc.docs_anexos || {};
  const odsEntry = Object.entries(anexos).find(([, v]) => v && v.is_ods);
  const odsChave = odsEntry && odsEntry[0];
  const temAnexo = Object.keys(anexos).length > 0;

  const abrirBlob = (blob) => {
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  };

  const uploadAnexo = async (chave, file) => {
    setUploadingKey(chave);
    try {
      const r = await georefAPI.cancelamentoUpload(proj.id, chave, file);
      const patch = {
        docs_anexos: { ...(canc.docs_anexos || {}), [chave]: r.anexo },
        docs_status: { ...(canc.docs_status || {}), [chave]: 'ok' },
      };
      const res = r.validacao && r.validacao.resumo;
      if (res && res.area_ha != null && !canc.area_ods_ha) patch.area_ods_ha = res.area_ha;
      if (res && res.abas_perimetro) patch.ods_uma_aba = res.abas_perimetro.length === 1;
      onChange(patch);
      if (r.validacao) {
        setOdsVal(r.validacao);
        toast({
          title: r.validacao.ok ? 'Planilha ODS anexada e conferida ✓' : 'ODS anexada — há erros a corrigir',
          description: r.validacao.ok ? 'Área e condições preenchidas automaticamente.' : undefined,
          variant: r.validacao.ok ? undefined : 'destructive',
        });
      } else {
        toast({ title: 'Documento anexado ✓' });
      }
    } catch (e) {
      toast({ title: 'Falha ao anexar', description: e?.response?.data?.detail || 'Tente novamente', variant: 'destructive' });
    } finally { setUploadingKey(''); }
  };

  const removeAnexo = async (chave) => {
    try {
      await georefAPI.cancelamentoRemoverAnexo(proj.id, chave);
      const na = { ...(canc.docs_anexos || {}) }; delete na[chave];
      const ns = { ...(canc.docs_status || {}) }; if (ns[chave] === 'ok') ns[chave] = 'pendente';
      onChange({ docs_anexos: na, docs_status: ns });
      if (odsChave === chave) setOdsVal(null);
    } catch (e) {
      toast({ title: 'Falha ao remover', variant: 'destructive' });
    }
  };

  const verAnexo = async (chave, asPdf) => {
    try {
      const blob = await georefAPI.cancelamentoAnexoBlob(proj.id, chave, asPdf ? 'pdf' : undefined);
      abrirBlob(blob);
    } catch (e) {
      toast({ title: 'Falha ao abrir o anexo', variant: 'destructive' });
    }
  };

  const validarOds = async () => {
    setOdsBusy(true);
    try { setOdsVal(await georefAPI.cancelamentoValidarOds(proj.id)); }
    catch (e) { toast({ title: 'Falha na conferência', description: e?.response?.data?.detail || '', variant: 'destructive' }); }
    finally { setOdsBusy(false); }
  };

  const corrigirOds = async () => {
    setOdsBusy(true);
    try {
      const r = await georefAPI.cancelamentoCorrigirOds(proj.id);
      setOdsVal(r.validacao);
      const res = r.validacao && r.validacao.resumo;
      const patch = {};
      if (res && res.area_ha != null) patch.area_ods_ha = res.area_ha;
      if (res && res.abas_perimetro) patch.ods_uma_aba = res.abas_perimetro.length === 1;
      const nat = res && res.identificacao && res.identificacao.natureza;
      if (nat && nat.toLowerCase().startsWith('particular')) patch.natureza = 'particular';
      if (Object.keys(patch).length) onChange(patch);
      toast({ title: 'Correção aplicada', description: (r.aplicados || []).join(' · ') || 'Requerimento harmonizado com a ODS.' });
    } catch (e) {
      toast({ title: 'Falha na correção', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setOdsBusy(false); }
  };

  const baixarDossie = async (fmt) => {
    setDossieBusy(true);
    try {
      const blob = await georefAPI.cancelamentoDossie(proj.id, fmt === 'download' ? 'download' : undefined);
      const url = URL.createObjectURL(blob);
      if (fmt === 'download') {
        const a = document.createElement('a'); a.href = url; a.download = 'Dossie_cancelamento.pdf'; a.click();
      } else { window.open(url, '_blank'); }
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (e) {
      toast({ title: 'Falha ao gerar o dossiê', variant: 'destructive' });
    } finally { setDossieBusy(false); }
  };

  const baixar = async (fmt) => {
    setDownloading(fmt);
    try {
      const blob = await georefAPI.documento(proj.id, 'requerimento_cancelamento', 'pdf', proj.tema_pdf, fmt === 'download' ? 'download' : undefined);
      const url = URL.createObjectURL(blob);
      if (fmt === 'download') {
        const a = document.createElement('a');
        a.href = url; a.download = `Requerimento_cancelamento.pdf`; a.click();
      } else {
        window.open(url, '_blank');
      }
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } finally { setDownloading(''); }
  };

  const set = (patch) => onChange(patch);
  const inputCls = 'w-full border rounded-lg px-3 py-2 text-sm';
  const chk = 'flex items-center gap-2 text-sm border rounded-lg px-3 py-2 cursor-pointer';

  return (
    <div className="space-y-5">
      <div className="rounded-xl p-4 text-sm" style={{ background: '#f5f2e8', border: `1px solid ${GOLD}` }}>
        <p className="font-semibold" style={{ color: GREEN }}>Requerimento de Cancelamento de Parcela — SIGEF/INCRA</p>
        <p className="text-gray-600 mt-1">
          Base: <strong>Ofício Circular nº 814/2026/DF/SEDE/INCRA</strong> (Processo SEI nº 54000.080781/2026-84).
          Selecione a <strong>Justificativa Pré-estabelecida</strong> — o checklist de documentos exigidos e as
          condições de deferimento automático se ajustam automaticamente.
        </p>
      </div>

      {/* Justificativa + código da parcela */}
      <div className="grid sm:grid-cols-2 gap-3">
        <label className="block">
          <span className="text-xs font-semibold text-gray-600">Justificativa Pré-estabelecida</span>
          <select className={inputCls} value={canc.justificativa || ''}
            onChange={(e) => set({ justificativa: e.target.value })}>
            <option value="">— selecione —</option>
            {justs.map((j) => <option key={j.id} value={j.id}>{j.num}. {j.titulo}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-semibold text-gray-600">Código da parcela SIGEF a cancelar</span>
          <input className={inputCls} value={canc.codigo_parcela_sigef || ''}
            placeholder="ex.: código da parcela no SIGEF"
            onChange={(e) => set({ codigo_parcela_sigef: e.target.value })} />
        </label>
      </div>

      {sel && (
        <p className="text-xs text-gray-500 -mt-2">
          {justs.find((j) => j.id === sel.id) ? '' : ''}Assinante do requerimento: <strong>{sel.assinante || 'Detentor'}</strong>.
        </p>
      )}

      {/* Detalhamento da justificativa — rich text auto-preenchido + IA */}
      <div className="block">
        <span className="text-xs font-semibold text-gray-600">Detalhamento da justificativa (editável)</span>
        <RichTextEditor
          value={paraEditorHtml(canc.justificativa_texto || '')}
          onChange={(html) => set({ justificativa_texto: html })}
          onBlurHtml={(html) => set({ justificativa_texto: html })}
          placeholder="Preenchido automaticamente com o texto do INCRA — edite ou aperfeiçoe com IA."
          minHeight={96}
          showAiButton={false}
        />
        <div className="flex justify-end mt-1">
          <AiButton onClick={handleAiDetalhe} loading={aiLoading} />
        </div>
      </div>

      {/* Condições de deferimento automático */}
      <div className="rounded-xl border border-gray-200 p-4">
        <p className="font-semibold text-sm mb-3" style={{ color: GREEN }}>
          Condições de deferimento automático (item 1 do Ofício Circular)
        </p>
        <div className="grid sm:grid-cols-2 gap-3 mb-3">
          <label className="block">
            <span className="text-xs font-semibold text-gray-600">Natureza da parcela</span>
            <select className={inputCls} value={canc.natureza || 'particular'}
              onChange={(e) => set({ natureza: e.target.value })}>
              <option value="particular">Particular</option>
              <option value="publica">Pública</option>
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs font-semibold text-gray-600">Área da parcela (ha)</span>
              <input className={inputCls} value={canc.area_parcela_ha || ''} placeholder="0,0000"
                onChange={(e) => set({ area_parcela_ha: e.target.value })} />
            </label>
            <label className="block">
              <span className="text-xs font-semibold text-gray-600">Área da Planilha ODS (ha)</span>
              <input className={inputCls} value={canc.area_ods_ha || ''} placeholder="0,0000"
                onChange={(e) => set({ area_ods_ha: e.target.value })} />
            </label>
          </div>
        </div>
        <div className="grid sm:grid-cols-2 gap-2 mb-3">
          <label className={chk}><input type="checkbox" checked={canc.requerente_e_rt !== false}
            onChange={(e) => set({ requerente_e_rt: e.target.checked })} /> Requerente é o RT da certificação</label>
          <label className={chk}><input type="checkbox" checked={canc.ods_uma_aba !== false}
            onChange={(e) => set({ ods_uma_aba: e.target.checked })} /> Planilha ODS com uma única aba de perímetro</label>
          <label className={chk}><input type="checkbox" checked={!!canc.registro_confirmado}
            onChange={(e) => set({ registro_confirmado: e.target.checked })} /> Parcela TEM registro confirmado no SIGEF</label>
          <label className={chk}><input type="checkbox" checked={!!canc.oriunda_cancelamento_auto}
            onChange={(e) => set({ oriunda_cancelamento_auto: e.target.checked })} /> Parcela oriunda de cancelamento automático</label>
          <label className={chk}><input type="checkbox" checked={!!canc.sncr_inibido}
            onChange={(e) => set({ sncr_inibido: e.target.checked })} /> Código SNCR está inibido</label>
          <label className={chk}><input type="checkbox" checked={!!canc.origem_contrato_destinacao_particular}
            onChange={(e) => set({ origem_contrato_destinacao_particular: e.target.checked })} /> Parcela de contrato / destinação particular (dispensa ODS)</label>
        </div>
        <ul className="space-y-1.5">
          {cond.map((c, i) => {
            const Ic = c.ok === true ? CheckCircle2 : c.ok === false ? AlertTriangle : Circle;
            const col = c.ok === true ? '#059669' : c.ok === false ? '#dc2626' : '#9ca3af';
            return (
              <li key={i} className="flex items-start gap-2 text-xs">
                <Ic className="w-4 h-4 mt-px shrink-0" style={{ color: col }} />
                <span className="text-gray-600">{c.t}{c.det ? <span className="text-gray-400"> — {c.det}</span> : null}</span>
              </li>
            );
          })}
        </ul>
        <div className={`mt-3 rounded-lg p-2.5 text-xs font-medium ${deferAuto
          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
          : 'bg-amber-50 text-amber-800 border border-amber-200'}`}>
          {deferAuto
            ? '✓ Condições atendidas — o SIGEF tende a processar o cancelamento por DEFERIMENTO AUTOMÁTICO.'
            : 'As condições acima não estão todas atendidas — se não houver erros, o requerimento poderá ser protocolado e direcionado à análise do INCRA (ALERTA).'}
        </div>
      </div>

      {/* Checklist de documentos */}
      {sel && (
        <div className="rounded-xl border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="font-semibold text-sm" style={{ color: GREEN }}>Documentos exigidos — {sel.num}. {sel.titulo}</p>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ background: '#f5f2e8', color: GREEN }}>
              {okCount}/{docs.length}
            </span>
          </div>
          <ul className="space-y-2">
            {docs.map((d) => {
              const m = STATUS_META[d.status] || STATUS_META.pendente;
              const Ic = m.icon;
              const anexo = anexos[d.key];
              const isOds = d.key.endsWith('_ods');
              return (
                <li key={d.key} className="border-b border-gray-100 pb-2 last:border-0">
                  <div className="flex items-start gap-2">
                    <button type="button" onClick={() => toggleDoc(d.key)}
                      className="flex items-start gap-2 flex-1 text-left text-xs hover:bg-gray-50 rounded-lg px-1.5 py-1">
                      <Ic className="w-4 h-4 mt-px shrink-0" style={{ color: m.color }} />
                      <span className={`flex-1 ${d.status === 'ok' ? 'text-gray-700' : d.status === 'na' ? 'text-gray-400 line-through' : 'text-gray-600'}`}>{d.label}</span>
                    </button>
                    <span className="text-[10px] font-semibold uppercase tracking-wide mt-1.5" style={{ color: m.color }}>{m.label}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-1 ml-6">
                    {anexo ? (
                      <>
                        <FileText className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                        <span className="text-[11px] text-gray-500 truncate max-w-[210px]" title={anexo.filename}>{anexo.filename}</span>
                        <button type="button" onClick={() => verAnexo(d.key, isOds)}
                          className="text-[11px] font-semibold underline" style={{ color: GREEN }}>
                          {isOds ? 'ver PDF' : 'ver'}
                        </button>
                        <button type="button" onClick={() => removeAnexo(d.key)}
                          className="text-[11px] text-red-600 hover:underline">remover</button>
                      </>
                    ) : (
                      <label className="text-[11px] inline-flex items-center gap-1 cursor-pointer font-semibold" style={{ color: GREEN }}>
                        {uploadingKey === d.key
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <Paperclip className="w-3.5 h-3.5" />}
                        {uploadingKey === d.key ? 'enviando…' : (isOds ? 'Anexar Planilha ODS (.ods)' : 'Anexar documento')}
                        <input type="file" className="hidden" accept={isOds ? '.ods' : 'application/pdf,image/*'}
                          onChange={(e) => { const f = e.target.files && e.target.files[0]; if (f) uploadAnexo(d.key, f); e.target.value = ''; }} />
                      </label>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
          <p className="text-[11px] text-gray-400 mt-2">Anexe cada documento (vai ao dossiê). Toque no texto do item para alternar Pendente → OK → N/A. A Planilha ODS é convertida em PDF e conferida automaticamente.</p>
        </div>
      )}

      {/* Motor de conferência da Planilha ODS */}
      {odsChave && (
        <div className="rounded-xl border p-4" style={{ borderColor: GOLD, background: '#fbfaf5' }}>
          <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
            <p className="font-semibold text-sm flex items-center gap-1.5" style={{ color: GREEN }}>
              <FileStack className="w-4 h-4" style={{ color: GOLD }} /> Conferência da Planilha ODS (padrões SIGEF)
            </p>
            <div className="flex gap-2">
              <button type="button" onClick={() => verAnexo(odsChave, true)}
                className="text-xs font-semibold inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border" style={{ color: GREEN }}>
                <Eye className="w-3.5 h-3.5" /> Ver PDF
              </button>
              <button type="button" onClick={validarOds} disabled={odsBusy}
                className="text-xs font-semibold inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-white disabled:opacity-50" style={{ background: GREEN }}>
                {odsBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />} Conferir
              </button>
            </div>
          </div>
          {odsVal ? (
            <div className="space-y-2">
              {odsVal.resumo && (
                <div className="text-[11px] text-gray-600 grid sm:grid-cols-2 gap-x-4 gap-y-0.5">
                  <span>Sistema: <strong>{odsVal.resumo.sistema_referencia || '—'}</strong></span>
                  <span>Abas de perímetro: <strong>{(odsVal.resumo.abas_perimetro || []).length}</strong></span>
                  <span>Vértices: <strong>{odsVal.resumo.n_vertices || 0}</strong></span>
                  <span>Área calculada: <strong>{odsVal.resumo.area_ha != null ? `${Number(odsVal.resumo.area_ha).toFixed(4).replace('.', ',')} ha` : '—'}</strong></span>
                </div>
              )}
              {[['erros', 'Erros (impeditivos)', '#dc2626', XCircle],
                ['alertas', 'Alertas (análise INCRA)', '#d97706', AlertTriangle],
                ['info', 'Conferências OK', '#059669', CheckCircle2]].map(([campo, titulo, cor, Ic]) => {
                const itens = odsVal[campo] || [];
                if (!itens.length) return null;
                return (
                  <div key={campo}>
                    <p className="text-[11px] font-semibold" style={{ color: cor }}>{titulo}</p>
                    <ul className="mt-0.5 space-y-0.5">
                      {itens.map((it, i) => (
                        <li key={i} className="flex items-start gap-1.5 text-[11px] text-gray-600">
                          <Ic className="w-3.5 h-3.5 mt-px shrink-0" style={{ color: cor }} />
                          <span>{it.msg}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
              <div className={`rounded-lg p-2 text-[11px] font-medium ${odsVal.ok
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-red-50 text-red-700 border border-red-200'}`}>
                {odsVal.ok
                  ? '✓ Planilha ODS sem erros impeditivos.'
                  : '✗ Corrija os erros na Planilha ODS (no software de topografia) antes de protocolar no SIGEF.'}
              </div>
              <button type="button" onClick={corrigirOds} disabled={odsBusy}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold disabled:opacity-50" style={{ background: GOLD, color: GREEN }}>
                {odsBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />} Corrigir automaticamente (harmonizar com a ODS)
              </button>
              <p className="text-[10px] text-gray-400">
                A correção preenche área, aba de perímetro e a identificação do imóvel a partir da ODS.
                Erros de estrutura/coordenada devem ser corrigidos na própria planilha.
              </p>
            </div>
          ) : (
            <p className="text-xs text-gray-400">Clique em <strong>Conferir</strong> para validar a planilha anexada conforme os padrões do SIGEF.</p>
          )}
        </div>
      )}

      {/* Avisos do fluxo SIGEF */}
      <div className="rounded-xl border border-sky-200 bg-sky-50 p-3 text-xs text-sky-900 space-y-1.5">
        <p className="flex items-center gap-1.5 font-semibold"><Info className="w-3.5 h-3.5" /> Regras do requerimento (Ofício 814/2026)</p>
        <p>• Após o protocolo com a Planilha ODS, o status fica <strong>"EM VERIFICAÇÃO"</strong>: confira se está conforme. Após <strong>24h</strong> nesse status, o SIGEF indefere automaticamente (item 2.4).</p>
        <p>• Validações: <strong>ERRO</strong> indefere; <strong>ALERTA</strong> direciona à análise do INCRA; <strong>INFO</strong> não impede o protocolo (item 2.5).</p>
        <p>• Alteração de vértice/coordenada na ODS só é possível se estiver <strong>apenas</strong> na parcela objeto do cancelamento (item 2.3).</p>
      </div>

      {/* Download */}
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={() => baixar('view')} disabled={!!downloading || busy}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-50"
          style={{ background: GREEN }}>
          {downloading === 'view' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />} Ver requerimento
        </button>
        <button type="button" onClick={() => baixar('download')} disabled={!!downloading || busy}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold disabled:opacity-50"
          style={{ background: GOLD, color: GREEN }}>
          {downloading === 'download' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />} Baixar Requerimento de Cancelamento
        </button>
        {temAnexo && (
          <button type="button" onClick={() => baixarDossie('download')} disabled={dossieBusy}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-50"
            style={{ background: GREEN }}>
            {dossieBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileStack className="w-4 h-4" />} Baixar Dossiê (requerimento + anexos)
          </button>
        )}
      </div>
    </div>
  );
}
