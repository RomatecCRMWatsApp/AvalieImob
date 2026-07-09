// Requerimento de Cancelamento de parcela SIGEF (Ofício Circular 814/2026/INCRA).
// Seletor de Justificativa Pré-estabelecida + condições de deferimento automático (i–viii)
// + checklist de documentos + aferição ao vivo + download do requerimento.
import React, { useEffect, useMemo, useState } from 'react';
import { Loader2, Download, Eye, CheckCircle2, AlertTriangle, Circle, MinusCircle, Info } from 'lucide-react';
import { georefAPI } from '../../../lib/api';

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
  const [justs, setJusts] = useState([]);
  const [downloading, setDownloading] = useState('');
  const canc = useMemo(() => proj.cancelamento || {}, [proj.cancelamento]);

  useEffect(() => {
    georefAPI.cancelamentoJustificativas()
      .then((r) => setJusts(r.justificativas || []))
      .catch(() => setJusts([]));
  }, []);

  const sel = useMemo(() => justs.find((j) => j.id === canc.justificativa), [justs, canc.justificativa]);

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

      {/* Texto complementar da justificativa */}
      <label className="block">
        <span className="text-xs font-semibold text-gray-600">Detalhamento da justificativa (opcional)</span>
        <textarea className={inputCls} rows={2} value={canc.justificativa_texto || ''}
          placeholder="Complemente a justificativa técnica, se necessário (senão, usa-se o texto padrão do INCRA)."
          onChange={(e) => set({ justificativa_texto: e.target.value })} />
      </label>

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
          <ul className="space-y-1.5">
            {docs.map((d) => {
              const m = STATUS_META[d.status] || STATUS_META.pendente;
              const Ic = m.icon;
              return (
                <li key={d.key}>
                  <button type="button" onClick={() => toggleDoc(d.key)}
                    className="w-full flex items-start gap-2 text-left text-xs hover:bg-gray-50 rounded-lg px-2 py-1.5">
                    <Ic className="w-4 h-4 mt-px shrink-0" style={{ color: m.color }} />
                    <span className={`flex-1 ${d.status === 'ok' ? 'text-gray-700' : d.status === 'na' ? 'text-gray-400 line-through' : 'text-gray-600'}`}>{d.label}</span>
                    <span className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: m.color }}>{m.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
          <p className="text-[11px] text-gray-400 mt-2">Toque em cada item para alternar: Pendente → OK → N/A.</p>
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
      </div>
    </div>
  );
}
