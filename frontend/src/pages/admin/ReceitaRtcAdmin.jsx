// @module ReceitaRtcAdmin — calculadoras oficiais da Receita (CBS/IBS): situação e tabela interna de alíquotas.
// Só administrador. A tabela interna só é usada quando a calculadora não tem a alíquota da data (2027 em diante).
// Regras: docs/receita-rtc/PENDENCIAS.md §3.
import React, { useCallback, useEffect, useState } from 'react';
import { Calculator, CheckCircle2, XCircle, Loader2, Plus, ShieldCheck, Ban } from 'lucide-react';
import { adminAPI } from '../../lib/api';
import { BrandSpinner } from '../../components/brand/BrandSpinner';
import { fmtDataHora } from '../../utils/datasServidor';

const TRIBUTO = { CBS: 'CBS', IBS_UF: 'IBS estadual', IBS_MUN: 'IBS municipal' };
const SITUACAO = {
  RASCUNHO: 'bg-gray-100 text-gray-700',
  CONFIRMADA: 'bg-emerald-100 text-emerald-800',
  REVOGADA: 'bg-red-100 text-red-700',
};
const VAZIO = { tributo: 'CBS', uf: '', codigo_municipio: '', aliquota: '', vigencia_inicio: '', vigencia_fim: '', fonte: '' };
const inputCls = 'w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm min-h-[44px]';
const dataBr = (iso) => (iso ? iso.split('-').reverse().join('/') : '');
const detalhe = (e, padrao) => (typeof e?.response?.data?.detail === 'string' ? e.response.data.detail : padrao);

export default function ReceitaRtcAdmin() {
  const [status, setStatus] = useState(null);
  const [lista, setLista] = useState(null);
  const [auditoria, setAuditoria] = useState([]);
  const [form, setForm] = useState(VAZIO);
  const [abrirForm, setAbrirForm] = useState(false);
  const [msg, setMsg] = useState(null);
  const [ocupado, setOcupado] = useState(false);

  const carregar = useCallback(() => {
    adminAPI.rtcAliquotas().then((d) => setLista(d.aliquotas || [])).catch(() => setLista([]));
    adminAPI.rtcAuditoria().then((d) => setAuditoria(d.eventos || [])).catch(() => setAuditoria([]));
  }, []);

  useEffect(() => {
    adminAPI.rtcStatus().then(setStatus).catch(() => setStatus({ erro: true }));
    carregar();
  }, [carregar]);

  const acao = async (fn, ok) => {
    setMsg(null); setOcupado(true);
    try { await fn(); setMsg({ ok: true, txt: ok }); carregar(); return true; }
    catch (e) { setMsg({ ok: false, txt: detalhe(e, 'Não foi possível concluir.') }); return false; }
    finally { setOcupado(false); }
  };

  const criar = async () => {
    const dados = { ...form, vigencia_fim: form.vigencia_fim || null };
    if (await acao(() => adminAPI.rtcCriarAliquota(dados), 'Registro criado como rascunho. Confirme depois de validar com o contador.')) {
      setForm(VAZIO); setAbrirForm(false);
    }
  };
  const confirmar = (r) => {
    const quem = window.prompt('Quem validou esta alíquota? (ex.: nome do contador)');
    if (quem) acao(() => adminAPI.rtcConfirmarAliquota(r.id, quem), 'Alíquota confirmada. A partir de agora entra nas simulações.');
  };
  const revogar = (r) => {
    const motivo = window.prompt('Motivo da revogação:');
    if (motivo) acao(() => adminAPI.rtcRevogarAliquota(r.id, motivo), 'Registro revogado.');
  };

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const servicos = status?.servicos || {};

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-[30px] font-bold leading-tight text-[#C9A84C] flex items-center gap-2">
          <Calculator className="w-7 h-7" /> Alíquotas CBS/IBS
        </h1>
        <p className="text-sm text-[#5B7466] dark:text-[#9FB5A6] mt-1">
          Calculadoras oficiais da Receita Federal. A tabela abaixo só é usada quando a calculadora não tem a alíquota
          da data (operações a partir de 2027). Cadastre apenas valores validados pelo contador, com a fonte.
        </p>
      </div>

      <section className="rounded-2xl border border-gray-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-gray-800">Situação</h2>
        {!status && <div className="py-4"><BrandSpinner label="Consultando…" /></div>}
        {status && (
          <ul className="mt-2 text-sm space-y-1.5">
            <li>Simulador para assinantes: <strong>{status.ativo ? 'ligado' : 'desligado'}</strong>
              {!status.ativo && <span className="text-gray-500"> (variável RECEITA_RTC_ENABLED)</span>}</li>
            {!status.configurado && <li className="text-amber-700">Endereços das calculadoras não configurados no servidor.</li>}
            {[['REGULAR', 'Regime regular'], ['SIMPLES', 'Simples Nacional']].map(([k, nome]) => servicos[k] && (
              <li key={k} className="flex items-start gap-2">
                {servicos[k].no_ar ? <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0 text-emerald-600" /> : <XCircle className="w-4 h-4 mt-0.5 shrink-0 text-red-500" />}
                <span className="min-w-0">{nome}: {servicos[k].no_ar ? `no ar · versão ${servicos[k].versao || '—'} · base ${servicos[k].versao_db || '—'}` : 'fora do ar'}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {msg && (
        <div className={`rounded-xl border p-3 text-sm ${msg.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-700'}`}>
          {msg.txt}
        </div>
      )}

      <section className="rounded-2xl border border-gray-200 bg-white p-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h2 className="text-sm font-semibold text-gray-800">Tabela interna</h2>
          <button type="button" onClick={() => setAbrirForm((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-800 text-white px-3 py-2 text-sm min-h-[44px]">
            <Plus className="w-4 h-4" /> Nova alíquota
          </button>
        </div>

        {abrirForm && (
          <div className="mt-3 grid sm:grid-cols-2 gap-3 rounded-xl border border-gray-200 p-3">
            <label className="text-sm">Tributo
              <select className={inputCls} value={form.tributo} onChange={(e) => set('tributo', e.target.value)}>
                {Object.entries(TRIBUTO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </label>
            <label className="text-sm">Alíquota (%)
              <input className={inputCls} inputMode="decimal" value={form.aliquota} onChange={(e) => set('aliquota', e.target.value)} />
            </label>
            {form.tributo !== 'CBS' && (
              <label className="text-sm">UF
                <input className={inputCls} maxLength={2} value={form.uf} onChange={(e) => set('uf', e.target.value.toUpperCase())} />
              </label>
            )}
            {form.tributo === 'IBS_MUN' && (
              <label className="text-sm">Código IBGE do município (7 dígitos)
                <input className={inputCls} inputMode="numeric" value={form.codigo_municipio} onChange={(e) => set('codigo_municipio', e.target.value)} />
              </label>
            )}
            <label className="text-sm">Início da vigência
              <input type="date" className={inputCls} value={form.vigencia_inicio} onChange={(e) => set('vigencia_inicio', e.target.value)} />
            </label>
            <label className="text-sm">Fim da vigência (opcional)
              <input type="date" className={inputCls} value={form.vigencia_fim} onChange={(e) => set('vigencia_fim', e.target.value)} />
            </label>
            <label className="text-sm sm:col-span-2">Fonte (norma, resolução ou documento do contador)
              <input className={inputCls} value={form.fonte} onChange={(e) => set('fonte', e.target.value)} />
            </label>
            <div className="sm:col-span-2 flex justify-end">
              <button type="button" onClick={criar} disabled={ocupado}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-800 text-white px-4 py-2 text-sm min-h-[44px] disabled:opacity-60">
                {ocupado && <Loader2 className="w-4 h-4 animate-spin" />} Salvar como rascunho
              </button>
            </div>
          </div>
        )}

        {lista === null && <div className="py-6"><BrandSpinner label="Carregando…" /></div>}
        {lista?.length === 0 && <p className="text-sm text-gray-500 mt-3">Nenhuma alíquota cadastrada.</p>}
        {lista?.length > 0 && (
          <ul className="mt-3 divide-y divide-gray-100">
            {lista.map((r) => (
              <li key={r.id} className="py-3 text-sm">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <span className="font-medium text-gray-900">{TRIBUTO[r.tributo]}{r.uf ? ` · ${r.uf}` : ''}{r.codigo_municipio ? ` · ${r.codigo_municipio}` : ''}</span>
                  <span className="tabular-nums text-gray-900">{String(r.aliquota).replace('.', ',')}%</span>
                  <span className="text-gray-600">{r.vigencia_fim ? `${dataBr(r.vigencia_inicio)} a ${dataBr(r.vigencia_fim)}` : `desde ${dataBr(r.vigencia_inicio)}`}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${SITUACAO[r.situacao]}`}>{r.situacao.toLowerCase()}</span>
                </div>
                <div className="text-xs text-gray-500 mt-1 break-words">
                  Fonte: {r.fonte}
                  {r.confirmado_por && <> · confirmada por {r.confirmado_por} em {fmtDataHora(r.confirmado_em)}</>}
                  {r.motivo_revogacao && <> · revogada: {r.motivo_revogacao}</>}
                </div>
                {r.situacao !== 'REVOGADA' && (
                  <div className="flex gap-2 mt-2 flex-wrap">
                    {r.situacao === 'RASCUNHO' && (
                      <button type="button" onClick={() => confirmar(r)} disabled={ocupado}
                        className="inline-flex items-center gap-1 rounded-lg border border-emerald-300 text-emerald-800 px-3 py-1.5 text-xs min-h-[40px]">
                        <ShieldCheck className="w-3.5 h-3.5" /> Confirmar
                      </button>
                    )}
                    <button type="button" onClick={() => revogar(r)} disabled={ocupado}
                      className="inline-flex items-center gap-1 rounded-lg border border-red-200 text-red-700 px-3 py-1.5 text-xs min-h-[40px]">
                      <Ban className="w-3.5 h-3.5" /> Revogar
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {auditoria.length > 0 && (
        <details className="rounded-2xl border border-gray-200 bg-white p-4 text-sm">
          <summary className="cursor-pointer font-semibold text-gray-800">Histórico de alterações ({auditoria.length})</summary>
          <ul className="mt-2 space-y-1 text-xs text-gray-600">
            {auditoria.map((e) => (
              <li key={e.id}>{fmtDataHora(e.em)} · {e.acao} · registro {e.registro_id.slice(0, 8)}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
