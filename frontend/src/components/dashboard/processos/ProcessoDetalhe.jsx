// @module ProcessoDetalhe — etapas, documentos vinculados, agenda e histórico de um processo.
// Os documentos (PTAM, vistoria, contrato…) continuam nos seus módulos: aqui só ficam
// os vínculos, que abrem o documento original.
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft, Check, Plus, Trash2, Link2, ExternalLink, CalendarPlus, AlertTriangle,
} from 'lucide-react';
import { processosAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';
import { fmtDataHora } from '../../../utils/datasServidor';
import { STATUS_COR, AGENDA_STATUS } from './ProcessosList';

const F = 'w-full rounded-xl border border-gray-300 bg-white px-3 py-2.5 text-sm min-h-[44px]';
const CARD = 'rounded-2xl border border-gray-200 bg-white p-4';
const BTN = 'inline-flex items-center gap-1 rounded-lg border px-3 py-1.5 text-xs min-h-[36px]';

// datetime-local (horário de quem usa) → ISO com fuso, que o servidor guarda em UTC
const localParaIso = (v) => (v ? new Date(v).toISOString() : '');

function msgErro(e, padrao) {
  const d = e?.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg;
  return padrao;
}

function Etapas({ p, aplicar }) {
  const [nova, setNova] = useState('');
  return (
    <section className={CARD}>
      <h2 className="text-sm font-semibold text-gray-800 mb-2">Etapas · {p.progresso}%</h2>
      <ul className="space-y-1">
        {(p.etapas || []).map((e) => (
          <li key={e.id} className="flex items-center gap-2">
            <button type="button" aria-pressed={e.concluida}
              onClick={() => aplicar(processosAPI.editarEtapa(p.id, e.id, { concluida: !e.concluida }))}
              className={`w-6 h-6 rounded-md border flex items-center justify-center shrink-0
                ${e.concluida ? 'bg-emerald-600 border-emerald-600 text-white' : 'border-gray-300 bg-white'}`}>
              {e.concluida && <Check className="w-4 h-4" />}
            </button>
            <span className={`flex-1 text-sm break-words ${e.concluida ? 'line-through text-gray-400' : 'text-gray-800'}`}>
              {e.titulo}
              {e.concluida_em && <span className="ml-2 text-xs text-gray-400 no-underline">{fmtDataHora(e.concluida_em)}</span>}
            </span>
            <button type="button" aria-label="Remover etapa"
              onClick={() => window.confirm('Remover esta etapa?') && aplicar(processosAPI.excluirEtapa(p.id, e.id))}
              className="w-8 h-8 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-600 flex items-center justify-center">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </li>
        ))}
      </ul>
      <form className="mt-3 flex gap-2" onSubmit={(ev) => {
        ev.preventDefault();
        if (nova.trim()) aplicar(processosAPI.novaEtapa(p.id, nova.trim())).then(() => setNova(''));
      }}>
        <input className={F} placeholder="Nova etapa" value={nova} onChange={(e) => setNova(e.target.value)} />
        <button type="submit" className="rounded-xl border border-gray-300 px-3 min-h-[44px]" aria-label="Adicionar etapa"><Plus className="w-4 h-4" /></button>
      </form>
    </section>
  );
}

function Documentos({ p, opcoes, aplicar }) {
  const nav = useNavigate();
  const [tipo, setTipo] = useState('ptam');
  const [disp, setDisp] = useState([]);
  const [escolhido, setEscolhido] = useState('');
  useEffect(() => {
    processosAPI.documentos(tipo).then(setDisp).catch(() => setDisp([]));
    setEscolhido('');
  }, [tipo]);
  const ja = new Set((p.referencias || []).map((r) => `${r.tipo}:${r.id}`));
  return (
    <section className={CARD}>
      <h2 className="text-sm font-semibold text-gray-800 mb-2">Documentos vinculados</h2>
      {(p.referencias || []).length === 0 && <p className="text-sm text-gray-500">Nenhum documento vinculado.</p>}
      <ul className="space-y-2">
        {(p.referencias || []).map((r) => (
          <li key={`${r.tipo}:${r.id}`} className="flex items-center gap-2 text-sm">
            <span className="text-xs rounded bg-emerald-50 text-emerald-800 px-1.5 py-0.5 shrink-0">{r.tipo_rotulo}</span>
            <span className={`flex-1 break-words ${r.existe ? 'text-gray-800' : 'text-gray-400 line-through'}`}>
              {r.rotulo}{!r.existe && ' (apagado no módulo de origem)'}
            </span>
            {r.existe && (
              <button type="button" onClick={() => nav(r.link)} className={`${BTN} border-emerald-200 text-emerald-800`}>
                <ExternalLink className="w-3.5 h-3.5" /> Abrir
              </button>
            )}
            <button type="button" aria-label="Desvincular"
              onClick={() => aplicar(processosAPI.desvincular(p.id, r.tipo, r.id))}
              className="w-8 h-8 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-600 flex items-center justify-center">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </li>
        ))}
      </ul>
      <div className="mt-3 grid grid-cols-1 sm:grid-cols-[auto,1fr,auto] gap-2">
        <select className={F} value={tipo} onChange={(e) => setTipo(e.target.value)} aria-label="Tipo de documento">
          {(opcoes?.referencias || []).map((o) => <option key={o.id} value={o.id}>{o.rotulo}</option>)}
        </select>
        <select className={`${F} min-w-0`} value={escolhido} onChange={(e) => setEscolhido(e.target.value)} aria-label="Documento">
          <option value="">{disp.length ? 'Escolha o documento' : 'Nenhum documento deste tipo'}</option>
          {disp.filter((d) => !ja.has(`${d.tipo}:${d.id}`)).map((d) => <option key={d.id} value={d.id}>{d.rotulo}</option>)}
        </select>
        <button type="button" disabled={!escolhido}
          onClick={() => aplicar(processosAPI.vincular(p.id, tipo, escolhido)).then(() => setEscolhido(''))}
          className="inline-flex items-center justify-center gap-1 rounded-xl bg-[#0C3320] text-white px-3 text-sm min-h-[44px] disabled:opacity-50">
          <Link2 className="w-4 h-4" /> Vincular
        </button>
      </div>
    </section>
  );
}

function Agenda({ p, opcoes, recarregar }) {
  const { toast } = useToast();
  const [f, setF] = useState({ tipo: 'vistoria', inicio: '', duracao_min: 60, local: '', contato: '', observacao: '' });
  const [reag, setReag] = useState({});
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));

  const avisarConflitos = (r) => {
    if (r?.conflitos?.length) {
      toast({
        title: `Atenção: ${r.conflitos.length} compromisso(s) no mesmo horário`,
        description: r.conflitos.map((c) => fmtDataHora(c.inicio) + (c.local ? ` · ${c.local}` : '')).join(' | '),
      });
    }
  };

  const agendar = async (e) => {
    e.preventDefault();
    if (!f.inicio) return toast({ title: 'Informe data e hora', variant: 'destructive' });
    try {
      const r = await processosAPI.agendar(p.id, { ...f, inicio: localParaIso(f.inicio), duracao_min: Number(f.duracao_min) });
      avisarConflitos(r);
      toast({ title: 'Compromisso agendado' });
      setF((x) => ({ ...x, inicio: '', observacao: '' }));
      recarregar();
    } catch (err) {
      toast({ title: 'Não foi possível agendar', description: msgErro(err, ''), variant: 'destructive' });
    }
  };

  const acao = async (c, a, extra = {}) => {
    try {
      const r = await processosAPI.acaoAgenda(p.id, c.id, { acao: a, ...extra });
      avisarConflitos(r);
      setReag((x) => ({ ...x, [c.id]: undefined }));
      recarregar();
    } catch (err) {
      toast({ title: 'Não foi possível', description: msgErro(err, ''), variant: 'destructive' });
    }
  };

  const ordenada = [...(p.agenda || [])].sort((a, b) => String(a.inicio).localeCompare(String(b.inicio)));
  return (
    <section className={CARD}>
      <h2 className="text-sm font-semibold text-gray-800 mb-2">Agenda</h2>
      {ordenada.length === 0 && <p className="text-sm text-gray-500">Nada agendado ainda.</p>}
      <ul className="space-y-2">
        {ordenada.map((c) => {
          const encerrado = c.status === 'cancelado' || c.status === 'realizado';
          return (
            <li key={c.id} className="rounded-xl border border-gray-100 p-3">
              <div className="flex flex-wrap items-baseline gap-x-2">
                <span className="text-sm font-medium text-gray-900">{fmtDataHora(c.inicio)}</span>
                <span className="text-sm text-gray-700">{opcoes?.agenda_tipos?.find((t) => t.id === c.tipo)?.rotulo || c.tipo}</span>
                <span className="text-xs text-gray-500">{c.duracao_min} min · {AGENDA_STATUS[c.status]}</span>
              </div>
              {(c.local || c.contato) && (
                <div className="text-xs text-gray-600 break-words">{[c.local, c.contato].filter(Boolean).join(' · ')}</div>
              )}
              {c.observacao && <div className="text-xs text-gray-500 break-words">{c.observacao}</div>}
              {!encerrado && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {c.status === 'agendado' && <button type="button" onClick={() => acao(c, 'confirmar')} className={`${BTN} border-emerald-200 text-emerald-800`}>Confirmar</button>}
                  <button type="button" onClick={() => acao(c, 'realizado')} className={`${BTN} border-gray-300 text-gray-700`}>Marcar realizado</button>
                  <button type="button" onClick={() => setReag((x) => ({ ...x, [c.id]: x[c.id] === undefined ? '' : undefined }))} className={`${BTN} border-gray-300 text-gray-700`}>Reagendar</button>
                  <button type="button" onClick={() => {
                    const motivo = window.prompt('Motivo do cancelamento (opcional):');
                    if (motivo !== null) acao(c, 'cancelar', { motivo });
                  }} className={`${BTN} border-red-200 text-red-700`}>Cancelar</button>
                </div>
              )}
              {reag[c.id] !== undefined && (
                <div className="mt-2 flex flex-wrap gap-2">
                  <input type="datetime-local" className={`${F} w-auto`} value={reag[c.id]}
                    onChange={(e) => setReag((x) => ({ ...x, [c.id]: e.target.value }))} aria-label="Nova data e hora" />
                  <button type="button" disabled={!reag[c.id]}
                    onClick={() => acao(c, 'reagendar', { novo_inicio: localParaIso(reag[c.id]) })}
                    className="rounded-xl bg-[#0C3320] text-white px-3 text-sm min-h-[44px] disabled:opacity-50">Salvar novo horário</button>
                </div>
              )}
              {(c.historico || []).length > 1 && (
                <details className="mt-1 text-xs text-gray-500">
                  <summary className="cursor-pointer">Histórico</summary>
                  <ul className="mt-1 space-y-0.5">
                    {c.historico.map((h, i) => (
                      <li key={i}>{fmtDataHora(h.quando)} — {h.evento}
                        {h.de ? ` (de ${fmtDataHora(h.de)} para ${fmtDataHora(h.para)})` : ''}</li>
                    ))}
                  </ul>
                </details>
              )}
            </li>
          );
        })}
      </ul>

      <form onSubmit={agendar} className="mt-4 space-y-2 border-t border-gray-100 pt-3">
        <h3 className="flex items-center gap-1 text-xs font-semibold text-gray-600 uppercase tracking-wide">
          <CalendarPlus className="w-3.5 h-3.5" /> Agendar
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <select className={F} value={f.tipo} onChange={set('tipo')} aria-label="Tipo">
            {(opcoes?.agenda_tipos || []).map((t) => <option key={t.id} value={t.id}>{t.rotulo}</option>)}
          </select>
          <input type="datetime-local" className={F} value={f.inicio} onChange={set('inicio')} aria-label="Data e hora" />
          <select className={F} value={f.duracao_min} onChange={set('duracao_min')} aria-label="Duração">
            {[30, 60, 90, 120, 180, 240].map((m) => <option key={m} value={m}>{m >= 60 ? `${m / 60} h` : `${m} min`}</option>)}
          </select>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <input className={F} placeholder="Local" value={f.local} onChange={set('local')} />
          <input className={F} placeholder="Contato no local (nome/telefone)" value={f.contato} onChange={set('contato')} />
        </div>
        <input className={F} placeholder="Observação" value={f.observacao} onChange={set('observacao')} />
        <button type="submit" className="rounded-xl bg-[#0C3320] text-white px-4 py-2.5 text-sm font-semibold min-h-[44px]">Agendar</button>
      </form>
    </section>
  );
}

export default function ProcessoDetalhe() {
  const { id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();
  const [p, setP] = useState(null);
  const [opcoes, setOpcoes] = useState(null);
  const [erro, setErro] = useState('');

  const recarregar = useCallback(() => {
    processosAPI.obter(id).then(setP).catch((e) => setErro(msgErro(e, 'Processo não encontrado')));
  }, [id]);
  useEffect(() => { recarregar(); processosAPI.opcoes().then(setOpcoes).catch(() => {}); }, [recarregar]);

  // executa uma alteração e recarrega a visão completa (rótulos/links atualizados)
  const aplicar = useCallback(async (promessa) => {
    try { await promessa; recarregar(); } catch (e) {
      toast({ title: 'Não foi possível', description: msgErro(e, ''), variant: 'destructive' });
      throw e;
    }
  }, [recarregar, toast]);

  if (erro) return <p className="text-sm text-red-700">{erro}</p>;
  if (!p) return <div className="py-16 flex justify-center"><BrandSpinner label="Carregando…" /></div>;

  const salvarCampo = (campo, valor) => aplicar(processosAPI.editar(p.id, { [campo]: valor })).catch(() => {});

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <button type="button" onClick={() => nav('/dashboard/processos')} className="inline-flex items-center gap-1 text-sm text-emerald-800 hover:underline">
        <ArrowLeft className="w-4 h-4" /> Processos
      </button>
      <section className={CARD}>
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <span className="text-xs font-semibold text-emerald-700">{p.numero}</span>
          <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COR[p.status] || ''}`}>{p.status_rotulo}</span>
        </div>
        <input className="mt-1 w-full text-xl font-semibold text-gray-900 bg-transparent border-b border-transparent focus:border-gray-300 focus:outline-none"
          defaultValue={p.titulo} aria-label="Título"
          onBlur={(e) => e.target.value.trim() && e.target.value !== p.titulo && salvarCampo('titulo', e.target.value)} />
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label className="text-xs text-gray-500">Situação
            <select className={F} value={p.status} onChange={(e) => salvarCampo('status', e.target.value)}>
              {(opcoes?.status || []).map((s) => <option key={s.id} value={s.id}>{s.rotulo}</option>)}
            </select>
          </label>
          <label className="text-xs text-gray-500">Prazo de entrega
            <input type="date" className={F} defaultValue={p.prazo || ''} onBlur={(e) => e.target.value !== (p.prazo || '') && salvarCampo('prazo', e.target.value)} />
          </label>
          <label className="text-xs text-gray-500">Cliente
            <input className={F} defaultValue={p.cliente_nome} onBlur={(e) => e.target.value !== p.cliente_nome && salvarCampo('cliente_nome', e.target.value)} />
          </label>
          <label className="text-xs text-gray-500">Responsável
            <input className={F} defaultValue={p.responsavel} onBlur={(e) => e.target.value !== p.responsavel && salvarCampo('responsavel', e.target.value)} />
          </label>
        </div>
        {p.prazo && p.status !== 'concluido' && p.status !== 'cancelado'
          && new Date(`${p.prazo}T23:59:59`) < new Date() && (
          <p className="mt-2 inline-flex items-center gap-1 text-xs text-red-700"><AlertTriangle className="w-3.5 h-3.5" /> Prazo vencido</p>
        )}
      </section>

      <Etapas p={p} aplicar={aplicar} />
      <Agenda p={p} opcoes={opcoes} recarregar={recarregar} />
      <Documentos p={p} opcoes={opcoes} aplicar={aplicar} />

      <section className={CARD}>
        <details>
          <summary className="text-sm font-semibold text-gray-800 cursor-pointer">Histórico do processo</summary>
          <ul className="mt-2 space-y-1 text-xs text-gray-600">
            {[...(p.historico || [])].reverse().map((h, i) => (
              <li key={i}>{fmtDataHora(h.quando)} — {h.evento}{h.para && !h.de ? ` (${fmtDataHora(h.para)})` : ''}</li>
            ))}
          </ul>
        </details>
      </section>

      <button type="button" onClick={() => {
        if (window.confirm('Excluir este processo? Os documentos vinculados continuam nos seus módulos.')) {
          processosAPI.excluir(p.id).then(() => nav('/dashboard/processos'));
        }
      }} className="text-xs text-red-700 hover:underline">Excluir processo</button>
    </div>
  );
}
