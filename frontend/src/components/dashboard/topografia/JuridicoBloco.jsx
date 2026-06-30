// @module topografia/JuridicoBloco — BLOCO JURÍDICO do Usucapião (etapa da advogada).
// Renderizado como a última aba do GeoUrbanoWizard quando tipo_servico==='usucapiao'.
// Posse & Soma de posses · Provas · Partes · Confrontantes & Anuências · Checklist A-G.
// É SEEDADO a partir do bloco técnico (provas←uploads, confrontantes←vértices, checklist).
import React, { useCallback, useEffect, useState } from 'react';
import { Plus, Trash2, FileText, Sparkles } from 'lucide-react';
import { geoUrbanoAPI } from '../../../lib/api';

const GREEN = '#0C3320';
const inp = 'w-full border rounded-lg px-3 py-2 text-sm';
const lbl = 'block text-xs font-medium text-gray-600 mb-1';

const VINCULOS = [
  { v: 'proprio', l: 'Posse própria' },
  { v: 'de_cujus', l: 'De cujus (somada por sucessão)' },
  { v: 'cedente', l: 'Cedente' },
];
const TIPOS_PROVA = ['agua', 'luz', 'iptu', 'telefone', 'contrato', 'benfeitoria', 'comprovante_endereco', 'declaracao', 'foto', 'outro'];
const PAPEIS_PARTE = [
  { v: 'requerente', l: 'Requerente' }, { v: 'conjuge', l: 'Cônjuge' },
  { v: 'advogado', l: 'Advogado(a)' }, { v: 'herdeiro', l: 'Herdeiro(a)' }, { v: 'testemunha', l: 'Testemunha' },
];
const TIPOS_CONFR = [
  { v: 'particular', l: 'Particular' }, { v: 'via_publica', l: 'Via pública' }, { v: 'area_publica', l: 'Área pública' },
];
const STATUS_ANUENCIA = ['pendente', 'assinada', 'recusada', 'notificado'];
const STATUS_CHK = ['pendente', 'anexado', 'dispensado'];
const fmtTipoProva = (t) => ({
  agua: 'Conta de água', luz: 'Conta de luz', iptu: 'IPTU', telefone: 'Telefone', contrato: 'Contrato',
  benfeitoria: 'Benfeitoria', comprovante_endereco: 'Comprovante de endereço', declaracao: 'Declaração',
  foto: 'Foto', outro: 'Outro',
}[t] || t);

const Sec = ({ titulo, children }) => (
  <section className="border rounded-xl p-4">
    <h3 className="text-sm font-semibold mb-3" style={{ color: GREEN }}>{titulo}</h3>
    {children}
  </section>
);

export default function JuridicoBloco({ id, proj, upd, reload, toast }) {
  const P = proj;
  const posse = P.posse || {};
  const [valid, setValid] = useState(null);
  const [checklist, setChecklist] = useState([]);
  const [seedBusy, setSeedBusy] = useState(false);

  const carregar = useCallback(async () => {
    try { setValid(await geoUrbanoAPI.usucapiaoValidacao(id)); } catch (e) { /* */ }
    try { const d = await geoUrbanoAPI.usucapiaoChecklist(id); setChecklist(d.checklist || []); } catch (e) { /* */ }
  }, [id]);
  useEffect(() => { carregar(); }, [carregar]);

  const updPosse = (partial) => upd({ posse: { ...posse, ...partial } });
  const setLista = (campo, arr) => upd({ [campo]: arr });
  const addItem = (campo, item) => setLista(campo, [...(P[campo] || []), item]);
  const updItem = (campo, i, partial) => setLista(campo, (P[campo] || []).map((x, j) => (j === i ? { ...x, ...partial } : x)));
  const rmItem = (campo, i) => setLista(campo, (P[campo] || []).filter((_, j) => j !== i));
  const exigeJustoTitulo = P.modalidade_usucapiao === 'ordinaria';

  const seedar = async () => {
    setSeedBusy(true);
    try {
      await geoUrbanoAPI.usucapiaoSeedJuridico(id);
      toast({ title: 'Bloco jurídico pré-preenchido do técnico ✓' });
      if (reload) await reload();
      await carregar();
    } catch (e) {
      toast({ title: 'Erro ao seedar', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setSeedBusy(false); }
  };

  const verBlob = async (promise, nome) => {
    const win = window.open('', '_blank');
    try {
      const blob = await promise; const url = URL.createObjectURL(blob);
      if (win) win.location.href = url; else window.open(url, '_blank');
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) { if (win) win.close(); toast({ title: 'Erro ao abrir', description: nome || '', variant: 'destructive' }); }
  };

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-3 flex items-center justify-between gap-3">
        <p className="text-xs text-amber-800">
          <b>Etapa da advogada.</b> Estes dados já vêm pré-preenchidos pelo bloco técnico — revise e complete.
        </p>
        <button onClick={seedar} disabled={seedBusy}
          className="text-xs inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border bg-white hover:bg-amber-100 whitespace-nowrap" style={{ color: GREEN }}>
          <Sparkles className="w-3.5 h-3.5" /> {seedBusy ? 'Seedando…' : 'Pré-preencher do técnico'}
        </button>
      </div>

      {/* Posse & Soma de posses */}
      <Sec titulo="Posse & Soma de posses (art. 1.243 CC)">
        <div className="grid sm:grid-cols-2 gap-3 mb-3">
          <div><label className={lbl}>Início da posse</label><input className={inp} value={posse.inicio || ''} onChange={(e) => updPosse({ inicio: e.target.value })} placeholder="2008" /></div>
          <div><label className={lbl}>Origem</label><input className={inp} value={posse.origem || ''} onChange={(e) => updPosse({ origem: e.target.value })} placeholder="ocupação / cessão / compra verbal" /></div>
          <div className="sm:col-span-2"><label className={lbl}>Natureza</label><input className={inp} value={posse.natureza || ''} onChange={(e) => updPosse({ natureza: e.target.value })} placeholder="mansa, pacífica, ininterrupta, com animus domini" /></div>
          {exigeJustoTitulo && (
            <div className="sm:col-span-2"><label className={lbl}>Justo título (exigido na ordinária)</label><input className={inp} value={posse.justo_titulo || ''} onChange={(e) => updPosse({ justo_titulo: e.target.value })} /></div>
          )}
        </div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-gray-600">Períodos</span>
          <button onClick={() => addItem('soma_posses', { possuidor_nome: '', vinculo: 'proprio', inicio: '', fim: '' })} className="text-xs inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50"><Plus className="w-3 h-3" /> Adicionar</button>
        </div>
        <div className="space-y-2">
          {(P.soma_posses || []).map((sp, i) => (
            <div key={i} className="grid sm:grid-cols-12 gap-2 items-end border rounded-lg p-2">
              <div className="sm:col-span-4"><label className={lbl}>Possuidor</label><input className={inp} value={sp.possuidor_nome || ''} onChange={(e) => updItem('soma_posses', i, { possuidor_nome: e.target.value })} /></div>
              <div className="sm:col-span-3"><label className={lbl}>Vínculo</label><select className={inp} value={sp.vinculo || 'proprio'} onChange={(e) => updItem('soma_posses', i, { vinculo: e.target.value })}>{VINCULOS.map((v) => <option key={v.v} value={v.v}>{v.l}</option>)}</select></div>
              <div className="sm:col-span-2"><label className={lbl}>Início</label><input className={inp} value={sp.inicio || ''} onChange={(e) => updItem('soma_posses', i, { inicio: e.target.value })} /></div>
              <div className="sm:col-span-2"><label className={lbl}>Fim</label><input className={inp} value={sp.fim || ''} onChange={(e) => updItem('soma_posses', i, { fim: e.target.value })} placeholder="atual" /></div>
              <div className="sm:col-span-1 flex justify-end"><button onClick={() => rmItem('soma_posses', i)} className="p-2 text-gray-300 hover:text-red-500"><Trash2 className="w-4 h-4" /></button></div>
            </div>
          ))}
        </div>
        {valid && (
          <p className={`text-xs mt-2 ${valid.prazo_ok ? 'text-emerald-700' : 'text-amber-700'}`}>
            {valid.anos_cobertos} ano(s) cobertos{valid.prazo_exigido ? ` de ${valid.prazo_exigido}` : ''} — {valid.prazo_ok ? 'prazo atingido ✓' : `faltam ${valid.faltam_anos}`}
          </p>
        )}
      </Sec>

      {/* Provas */}
      <Sec titulo="Provas de posse (linha do tempo)">
        <div className="flex justify-end mb-2">
          <button onClick={() => addItem('provas_posse', { tipo: 'iptu', ano: '', descricao: '' })} className="text-xs inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50"><Plus className="w-3 h-3" /> Adicionar prova</button>
        </div>
        <div className="space-y-2">
          {(P.provas_posse || []).map((pv, i) => (
            <div key={i} className="grid sm:grid-cols-12 gap-2 items-end border rounded-lg p-2">
              <div className="sm:col-span-3"><label className={lbl}>Tipo</label><select className={inp} value={pv.tipo || 'outro'} onChange={(e) => updItem('provas_posse', i, { tipo: e.target.value })}>{TIPOS_PROVA.map((t) => <option key={t} value={t}>{fmtTipoProva(t)}</option>)}</select></div>
              <div className="sm:col-span-2"><label className={lbl}>Ano</label><input className={inp} value={pv.ano || ''} onChange={(e) => updItem('provas_posse', i, { ano: e.target.value })} /></div>
              <div className="sm:col-span-6"><label className={lbl}>Descrição</label><input className={inp} value={pv.descricao || ''} onChange={(e) => updItem('provas_posse', i, { descricao: e.target.value })} /></div>
              <div className="sm:col-span-1 flex justify-end"><button onClick={() => rmItem('provas_posse', i)} className="p-2 text-gray-300 hover:text-red-500"><Trash2 className="w-4 h-4" /></button></div>
            </div>
          ))}
          {(P.provas_posse || []).length === 0 && <p className="text-xs text-gray-400">Sem provas (use "Pré-preencher do técnico" para puxar os uploads).</p>}
        </div>
      </Sec>

      {/* Partes */}
      <Sec titulo="Partes (requerente, cônjuge, advogado, herdeiros, testemunhas)">
        <div className="flex justify-end mb-2">
          <button onClick={() => addItem('partes', { papel: 'requerente', tipo_pessoa: 'fisica', nome: '' })} className="text-xs inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50"><Plus className="w-3 h-3" /> Adicionar parte</button>
        </div>
        <div className="space-y-3">
          {(P.partes || []).map((pt, i) => (
            <div key={i} className="border rounded-lg p-3 grid sm:grid-cols-12 gap-2 items-end">
              <div className="sm:col-span-3"><label className={lbl}>Papel</label><select className={inp} value={pt.papel || 'requerente'} onChange={(e) => updItem('partes', i, { papel: e.target.value })}>{PAPEIS_PARTE.map((p) => <option key={p.v} value={p.v}>{p.l}</option>)}</select></div>
              <div className="sm:col-span-7"><label className={lbl}>Nome</label><input className={inp} value={pt.nome || pt.razao_social || ''} onChange={(e) => updItem('partes', i, { nome: e.target.value })} /></div>
              <div className="sm:col-span-2 flex justify-end"><button onClick={() => rmItem('partes', i)} className="p-2 text-gray-300 hover:text-red-500"><Trash2 className="w-4 h-4" /></button></div>
              <div className="sm:col-span-3"><label className={lbl}>CPF</label><input className={inp} value={pt.cpf || ''} onChange={(e) => updItem('partes', i, { cpf: e.target.value })} /></div>
              <div className="sm:col-span-3"><label className={lbl}>Estado civil</label><input className={inp} value={pt.estado_civil || ''} onChange={(e) => updItem('partes', i, { estado_civil: e.target.value })} /></div>
              {pt.papel === 'advogado' && (
                <>
                  <div className="sm:col-span-3"><label className={lbl}>OAB</label><input className={inp} value={pt.oab || ''} onChange={(e) => updItem('partes', i, { oab: e.target.value })} /></div>
                  <div className="sm:col-span-2"><label className={lbl}>UF OAB</label><input className={inp} value={pt.uf_oab || ''} onChange={(e) => updItem('partes', i, { uf_oab: e.target.value })} /></div>
                </>
              )}
              <div className="sm:col-span-6"><label className={lbl}>Endereço</label><input className={inp} value={pt.endereco || ''} onChange={(e) => updItem('partes', i, { endereco: e.target.value })} /></div>
            </div>
          ))}
        </div>
        {!(P.partes || []).some((x) => x.papel === 'advogado') && (
          <p className="text-xs text-amber-700 mt-2">⚠ O usucapião extrajudicial exige advogado (art. 216-A).</p>
        )}
      </Sec>

      {/* Confrontantes & Anuências */}
      <Sec titulo="Confrontantes & Anuências">
        <div className="flex justify-end mb-2">
          <button onClick={() => addItem('confrontantes', { lado: '', confrontante: '', tipo: 'particular', anuencia: { status: 'pendente' } })} className="text-xs inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50"><Plus className="w-3 h-3" /> Adicionar</button>
        </div>
        <div className="space-y-2">
          {(P.confrontantes || []).map((cf, i) => (
            <div key={i} className="grid sm:grid-cols-12 gap-2 items-end border rounded-lg p-2">
              <div className="sm:col-span-2"><label className={lbl}>Lado</label><input className={inp} value={cf.lado || ''} onChange={(e) => updItem('confrontantes', i, { lado: e.target.value })} /></div>
              <div className="sm:col-span-3"><label className={lbl}>Confrontante</label><input className={inp} value={cf.confrontante || ''} onChange={(e) => updItem('confrontantes', i, { confrontante: e.target.value })} /></div>
              <div className="sm:col-span-2"><label className={lbl}>Tipo</label><select className={inp} value={cf.tipo || 'particular'} onChange={(e) => updItem('confrontantes', i, { tipo: e.target.value })}>{TIPOS_CONFR.map((t) => <option key={t.v} value={t.v}>{t.l}</option>)}</select></div>
              <div className="sm:col-span-2"><label className={lbl}>Medida (m)</label><input type="number" className={inp} value={cf.medida_m ?? ''} onChange={(e) => updItem('confrontantes', i, { medida_m: e.target.value === '' ? null : Number(e.target.value) })} /></div>
              <div className="sm:col-span-2"><label className={lbl}>Anuência</label><select className={inp} value={cf.anuencia?.status || 'pendente'} onChange={(e) => updItem('confrontantes', i, { anuencia: { ...(cf.anuencia || {}), status: e.target.value } })}>{STATUS_ANUENCIA.map((s) => <option key={s} value={s}>{s}</option>)}</select></div>
              <div className="sm:col-span-1 flex justify-end"><button onClick={() => rmItem('confrontantes', i)} className="p-2 text-gray-300 hover:text-red-500"><Trash2 className="w-4 h-4" /></button></div>
              <div className="sm:col-span-12 flex flex-wrap gap-2">
                <button onClick={() => verBlob(geoUrbanoAPI.usucapiaoAnuenciaPdf(id, cf.confrontante, 'declaracao', P.tema), 'Declaração')} disabled={!cf.confrontante} className="text-[11px] inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50 disabled:opacity-40"><FileText className="w-3 h-3" /> Declaração de anuência</button>
                <button onClick={() => verBlob(geoUrbanoAPI.usucapiaoAnuenciaPdf(id, cf.confrontante, 'notificacao', P.tema), 'Notificação')} disabled={!cf.confrontante} className="text-[11px] inline-flex items-center gap-1 px-2 py-1 rounded border hover:bg-gray-50 disabled:opacity-40"><FileText className="w-3 h-3" /> Notificação</button>
              </div>
            </div>
          ))}
        </div>
        <p className="text-[11px] text-amber-700 mt-2">A coleta por WhatsApp (assinatura desenhada) é da próxima fase; por ora, baixe a declaração e registre a anuência presencial.</p>
      </Sec>

      {/* Checklist A-G */}
      <Sec titulo="Checklist de documentos (Prov. CNJ 149/2023)">
        {checklist.length === 0 && <p className="text-xs text-gray-400">Carregando…</p>}
        {['A', 'B', 'C', 'D', 'E', 'F', 'G'].map((bloco) => {
          const itens = checklist.filter((c) => c.bloco === bloco);
          if (!itens.length) return null;
          return (
            <div key={bloco} className="mb-2">
              <div className="text-[11px] font-bold text-gray-400 mb-1">Bloco {bloco}</div>
              {itens.map((it) => {
                const cur = (P.checklist || []).find((x) => x.chave === it.chave) || it;
                const setStatus = (status) => {
                  const lista = [...(P.checklist || [])];
                  const j = lista.findIndex((x) => x.chave === it.chave);
                  if (j >= 0) lista[j] = { ...lista[j], status }; else lista.push({ ...it, status });
                  upd({ checklist: lista });
                };
                return (
                  <div key={it.chave} className="flex items-center gap-2 text-sm py-0.5">
                    <span className={`w-2 h-2 rounded-full ${cur.status === 'anexado' ? 'bg-emerald-500' : cur.status === 'dispensado' ? 'bg-gray-300' : 'bg-amber-400'}`} />
                    <span className="flex-1">{it.label}{it.obrigatorio ? '' : ' (opcional)'}</span>
                    <select className="text-[11px] border rounded px-1 py-0.5" value={cur.status || 'pendente'} onChange={(e) => setStatus(e.target.value)}>
                      {STATUS_CHK.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                );
              })}
            </div>
          );
        })}
      </Sec>
    </div>
  );
}
