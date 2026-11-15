// Aba "Robô de atendimento" em Leads & Cadastros: funil do robô do site
// (conversas → interessados → qualificados → convertidos), assuntos mais
// perguntados, lista de conversas com WhatsApp 1-clique e a conversa completa.
import React, { useCallback, useEffect, useState } from 'react';
import { MessageCircle, X, Trash2, Bot } from 'lucide-react';
import { atendimentoAPI } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { BrandSpinner } from '../../components/brand/BrandSpinner';

const VERDE = '#0C3320';
const DOURADO = '#C9A84C';

const ESTAGIO = {
  curioso: { label: 'Curioso', cor: '#6b7280', bg: '#f3f4f6' },
  interessado: { label: 'Interessado', cor: '#b45309', bg: '#fffbeb' },
  qualificado: { label: 'Qualificado', cor: '#1d4ed8', bg: '#eff6ff' },
  convertido: { label: 'Cadastrou', cor: '#15803d', bg: '#f0fdf4' },
};
const STATUS = {
  novo: 'Novo', em_contato: 'Em contato', fechado: 'Fechado', descartado: 'Descartado',
};
const PERFIL = { profissional: 'Profissional', cliente_servico: 'Quer o serviço', indefinido: '—' };
const ROTULO = {
  plataforma: 'Plataforma', planos: 'Planos', teste: 'Teste grátis', ptam: 'PTAM', laudo: 'Laudo',
  pericia: 'Perícia', inferencia: 'Inferência', rural: 'Rural', garantia: 'Garantias', locacao: 'Locação',
  vistoria: 'Vistoria', contratos: 'Contratos', assinatura: 'Assinatura', propostas: 'Propostas',
  georref: 'Georref.', geo_urbano: 'Geo Urbano', usucapiao: 'Usucapião', reurb: 'REURB', onr: 'ONR',
  inss_obra: 'INSS obra', topografia: 'Topografia', servico: 'Serviço', outro: 'Outro',
};

const comoUTC = (iso) => (iso && !/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? `${iso}Z` : iso);
const dataFmt = (iso) => (iso ? new Date(comoUTC(iso)).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—');
const foneFmt = (f) => {
  const d = (f || '').replace(/\D/g, '').replace(/^55/, '');
  return d.length === 11 ? `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}` : d.length === 10 ? `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}` : f;
};
const LIMIT = 20;

function Badge({ estagio }) {
  const e = ESTAGIO[estagio] || ESTAGIO.curioso;
  return <span className="inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap" style={{ color: e.cor, background: e.bg }}>{e.label}</span>;
}

function Card({ titulo, valor, sub, cor }) {
  return (
    <div className="rounded-xl bg-white p-3 sm:p-4 shadow-sm border border-gray-100 min-w-0">
      <p className="text-[11px] sm:text-xs text-gray-500 leading-tight">{titulo}</p>
      <p className="mt-1 text-xl sm:text-2xl font-bold" style={{ color: cor || VERDE }}>{valor}</p>
      {sub && <p className="text-[11px] text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function AtendimentoBotAdmin() {
  const { toast } = useToast();
  const [dias, setDias] = useState(30);
  const [stats, setStats] = useState(null);
  const [itens, setItens] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [estagio, setEstagio] = useState('');
  const [busca, setBusca] = useState('');
  const [loading, setLoading] = useState(true);
  const [aberta, setAberta] = useState(null);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const params = { dias, page, limit: LIMIT };
      if (estagio) params.estagio = estagio;
      if (busca.trim()) params.q = busca.trim();
      const [st, lista] = await Promise.all([atendimentoAPI.stats(dias), atendimentoAPI.listar(params)]);
      setStats(st);
      setItens(lista.items || []);
      setTotal(lista.total || 0);
    } catch (e) {
      toast({ title: 'Erro ao carregar o robô', description: e.response?.data?.detail, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [dias, page, estagio, busca, toast]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { carregar(); }, [dias, page, estagio]);

  async function abrir(id) {
    try { setAberta(await atendimentoAPI.detalhe(id)); }
    catch { toast({ title: 'Não consegui abrir a conversa', variant: 'destructive' }); }
  }

  async function mudarStatus(id, status_admin) {
    try {
      await atendimentoAPI.atualizar(id, { status_admin });
      setItens((l) => l.map((i) => (i.id === id ? { ...i, status_admin } : i)));
      if (aberta?.id === id) setAberta((a) => ({ ...a, status_admin }));
    } catch { toast({ title: 'Erro ao salvar', variant: 'destructive' }); }
  }

  async function salvarNota() {
    try {
      await atendimentoAPI.atualizar(aberta.id, { nota: aberta.nota || '' });
      toast({ title: 'Anotação salva' });
    } catch { toast({ title: 'Erro ao salvar', variant: 'destructive' }); }
  }

  async function excluir(id) {
    if (!window.confirm('Excluir esta conversa?')) return;
    try {
      await atendimentoAPI.excluir(id);
      setAberta(null);
      carregar();
    } catch { toast({ title: 'Erro ao excluir', variant: 'destructive' }); }
  }

  const pe = stats?.por_estagio || {};
  const qualificados = (pe.qualificado || 0) + (pe.convertido || 0);
  const funil = [
    { k: 'conversas', label: 'Conversaram', v: stats?.conversas || 0, cor: '#9ca3af' },
    { k: 'interessado', label: 'Interessados+', v: (pe.interessado || 0) + qualificados, cor: '#d97706' },
    { k: 'qualificado', label: 'Qualificados', v: qualificados, cor: '#2563eb' },
    { k: 'encaminhados', label: 'Enviados a você', v: stats?.encaminhados || 0, cor: DOURADO },
    { k: 'convertido', label: 'Cadastraram', v: pe.convertido || 0, cor: '#16a34a' },
  ];
  const maxFunil = Math.max(1, funil[0].v);
  const totalPaginas = Math.max(1, Math.ceil(total / LIMIT));

  return (
    <div className="space-y-5 min-w-0">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Bot className="w-5 h-5 flex-shrink-0" style={{ color: VERDE }} />
          <p className="text-sm text-gray-600">Atendimento automático do site: explica a plataforma, qualifica e te avisa no WhatsApp quando o visitante quer fechar.</p>
        </div>
        <div className="inline-flex p-1 rounded-lg bg-gray-100 border border-gray-200">
          {[7, 30, 90, 0].map((d) => (
            <button key={d} type="button" onClick={() => { setPage(1); setDias(d); }}
              className={`px-3 py-1.5 rounded-md text-xs font-medium ${dias === d ? 'bg-white shadow-sm' : 'text-gray-500'}`}
              style={dias === d ? { color: VERDE } : undefined}>
              {d ? `${d} dias` : 'Tudo'}
            </button>
          ))}
        </div>
      </div>

      {!stats && loading ? <div className="py-10 flex justify-center"><BrandSpinner /></div> : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <Card titulo="Conversas" valor={stats?.conversas ?? 0} sub={`${stats?.aberturas ?? 0} abriram o chat`} />
            <Card titulo="Mensagens recebidas" valor={stats?.mensagens_recebidas ?? 0} />
            <Card titulo="Só interessados" valor={pe.interessado ?? 0} cor="#b45309" sub={`${pe.curioso ?? 0} curiosos`} />
            <Card titulo="Qualificados" valor={qualificados} cor="#1d4ed8" sub={`${stats?.taxa_qualificacao ?? 0}% das conversas`} />
            <Card titulo="Enviados a você" valor={stats?.encaminhados ?? 0} cor={DOURADO} sub={`${stats?.com_contato ?? 0} deixaram contato`} />
            <Card titulo="Cadastraram" valor={pe.convertido ?? 0} cor="#15803d" sub={`${stats?.cliques?.cadastro ?? 0} cliques no cadastro`} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl bg-white p-4 shadow-sm border border-gray-100 min-w-0">
              <p className="text-sm font-semibold mb-3" style={{ color: VERDE }}>Funil do robô</p>
              <div className="space-y-2">
                {funil.map((f) => (
                  <div key={f.k} className="flex items-center gap-2 text-xs">
                    <span className="w-28 flex-shrink-0 text-gray-600">{f.label}</span>
                    <div className="flex-1 h-5 bg-gray-100 rounded min-w-0">
                      <div className="h-5 rounded" style={{ width: `${Math.max(f.v ? 4 : 0, (100 * f.v) / maxFunil)}%`, background: f.cor }} />
                    </div>
                    <span className="w-8 text-right font-semibold tabular-nums">{f.v}</span>
                  </div>
                ))}
              </div>
              <p className="text-[11px] text-gray-400 mt-3">
                Pediram para falar com você: {stats?.pediram_humano ?? 0} · Cliques no WhatsApp: {stats?.cliques?.whatsapp ?? 0} · Cliques em planos: {stats?.cliques?.planos ?? 0}
              </p>
            </div>
            <div className="rounded-xl bg-white p-4 shadow-sm border border-gray-100 min-w-0">
              <p className="text-sm font-semibold mb-3" style={{ color: VERDE }}>O que mais perguntam</p>
              {stats?.assuntos?.length ? (
                <div className="flex flex-wrap gap-2">
                  {stats.assuntos.map((a) => (
                    <span key={a.assunto} className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs text-emerald-900">
                      {a.rotulo} <b className="ml-1">{a.total}</b>
                    </span>
                  ))}
                </div>
              ) : <p className="text-xs text-gray-400">Ainda sem conversas no período.</p>}
              <p className="text-[11px] text-gray-400 mt-3">
                Perfil: {stats?.perfis?.profissional || 0} profissionais · {stats?.perfis?.cliente_servico || 0} querem o serviço · {stats?.perfis?.indefinido || 0} não identificados
              </p>
            </div>
          </div>
        </>
      )}

      <div className="rounded-xl bg-white shadow-sm border border-gray-100 min-w-0">
        <div className="p-3 sm:p-4 flex flex-wrap gap-2 items-center border-b border-gray-100">
          <select value={estagio} onChange={(e) => { setPage(1); setEstagio(e.target.value); }}
            className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm min-w-0">
            <option value="">Todos os estágios</option>
            <option value="qualificado">Qualificados</option>
            <option value="encaminhado">Enviados a você</option>
            <option value="interessado">Interessados</option>
            <option value="curioso">Curiosos</option>
            <option value="convertido">Cadastraram</option>
          </select>
          <form onSubmit={(e) => { e.preventDefault(); setPage(1); carregar(); }} className="flex gap-2 flex-1 min-w-[180px]">
            <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar nome, WhatsApp ou palavra da conversa"
              className="flex-1 min-w-0 rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
            <button className="rounded-lg px-3 py-1.5 text-sm text-white" style={{ background: VERDE }}>Buscar</button>
          </form>
        </div>

        {loading ? <div className="py-8 flex justify-center"><BrandSpinner /></div> : itens.length === 0 ? (
          <p className="p-6 text-center text-sm text-gray-400">Nenhuma conversa neste filtro.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {itens.map((c) => (
              <li key={c.id} className="p-3 sm:p-4 flex flex-wrap gap-3 items-start hover:bg-gray-50">
                <button type="button" onClick={() => abrir(c.id)} className="flex-1 min-w-[200px] text-left">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge estagio={c.estagio} />
                    {c.notificado_em && <span className="text-[11px] font-semibold" style={{ color: DOURADO }}>● enviado a você</span>}
                    {c.pediu_humano && <span className="text-[11px] text-red-600">pediu atendente</span>}
                    <span className="font-semibold text-sm text-gray-800">{c.nome || 'Visitante'}</span>
                    <span className="text-xs text-gray-400">{PERFIL[c.perfil] || ''}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 break-words">“{c.ultima_pergunta || '—'}”</p>
                  <p className="text-[11px] text-gray-400 mt-1">
                    {c.assuntos.map((a) => ROTULO[a] || a).join(' · ') || 'sem assunto'} · {c.n_msgs_cliente} msg · {dataFmt(c.atualizado_em)}
                  </p>
                </button>
                <div className="flex items-center gap-2 flex-wrap">
                  {c.whatsapp && (
                    <a href={`https://wa.me/${c.whatsapp}`} target="_blank" rel="noreferrer"
                      className="inline-flex items-center gap-1 rounded-lg bg-[#25D366] px-2.5 py-1.5 text-xs font-semibold text-white">
                      <MessageCircle className="w-3.5 h-3.5" /> {foneFmt(c.whatsapp)}
                    </a>
                  )}
                  <select value={c.status_admin} onChange={(e) => mudarStatus(c.id, e.target.value)}
                    className="rounded-lg border border-gray-300 px-2 py-1 text-xs">
                    {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
              </li>
            ))}
          </ul>
        )}

        {totalPaginas > 1 && (
          <div className="p-3 flex items-center justify-between text-xs text-gray-500 border-t border-gray-100">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="disabled:opacity-40">← Anterior</button>
            <span>Página {page} de {totalPaginas} · {total} conversas</span>
            <button disabled={page >= totalPaginas} onClick={() => setPage((p) => p + 1)} className="disabled:opacity-40">Próxima →</button>
          </div>
        )}
      </div>

      {aberta && (
        <div className="fixed inset-0 z-[1300] bg-black/50 flex justify-end" onClick={() => setAberta(null)}>
          <div className="h-full w-full max-w-lg bg-white flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="p-4 flex items-start justify-between gap-3" style={{ background: VERDE }}>
              <div className="min-w-0">
                <p className="text-white font-semibold truncate">{aberta.nome || 'Visitante'}</p>
                <p className="text-emerald-200 text-xs break-all">
                  {aberta.whatsapp ? foneFmt(aberta.whatsapp) : 'sem WhatsApp'}{aberta.email ? ` · ${aberta.email}` : ''}
                </p>
                <p className="text-emerald-200 text-[11px] mt-1">
                  Origem: {aberta.origem?.utm_source || aberta.origem?.referrer || 'direto'} · página {aberta.origem?.pagina || '/'}
                </p>
              </div>
              <button onClick={() => setAberta(null)} className="text-white p-1"><X className="w-5 h-5" /></button>
            </div>
            <div className="px-4 py-2 flex flex-wrap items-center gap-2 border-b border-gray-100">
              <Badge estagio={aberta.estagio} />
              <span className="text-xs text-gray-500">{PERFIL[aberta.perfil]}</span>
              <select value={aberta.status_admin} onChange={(e) => mudarStatus(aberta.id, e.target.value)}
                className="ml-auto rounded-lg border border-gray-300 px-2 py-1 text-xs">
                {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
              {aberta.whatsapp && (
                <a href={`https://wa.me/${aberta.whatsapp}?text=${encodeURIComponent(`Olá ${aberta.nome?.split(' ')[0] || ''}, aqui é o José da Romatec. Vi sua conversa no site do AvalieImob.`)}`}
                  target="_blank" rel="noreferrer"
                  className="inline-flex items-center gap-1 rounded-lg bg-[#25D366] px-2.5 py-1 text-xs font-semibold text-white">
                  <MessageCircle className="w-3.5 h-3.5" /> Chamar
                </a>
              )}
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
              {aberta.mensagens.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : ''}`}>
                  <div className={`max-w-[85%] rounded-xl p-2.5 text-sm whitespace-pre-wrap break-words ${m.role === 'user' ? 'bg-emerald-600 text-white' : 'bg-white text-gray-800 shadow-sm'}`}>
                    {m.content}
                    <span className="block text-[10px] opacity-60 mt-1">{dataFmt(m.ts)}{m.provedor ? ` · ${m.provedor}` : ''}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-3 border-t border-gray-100 space-y-2">
              <textarea value={aberta.nota || ''} onChange={(e) => setAberta((a) => ({ ...a, nota: e.target.value }))}
                placeholder="Anotação interna (ex.: mandei orçamento, retornar sexta)" rows={2}
                className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm" />
              <div className="flex justify-between">
                <button onClick={() => excluir(aberta.id)} className="inline-flex items-center gap-1 text-xs text-red-600"><Trash2 className="w-3.5 h-3.5" /> Excluir</button>
                <button onClick={salvarNota} className="rounded-lg px-3 py-1.5 text-xs text-white" style={{ background: VERDE }}>Salvar anotação</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
