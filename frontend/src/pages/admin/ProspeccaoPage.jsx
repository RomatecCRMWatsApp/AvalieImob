// @page admin/Prospecção — CRM de imobiliárias/corretores + campanha de e-mail (proposta).
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Radar, Send, RefreshCw, Download, Upload, Trash2, Eye, Loader2, StopCircle,
  Mail, AlertTriangle, X, CalendarClock, Server, MessageCircle,
} from 'lucide-react';
import { prospeccaoAPI, adminAPI } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';
const STATUS_LABELS = ['Não contatado', 'Aguardando retorno', 'Em conversa', 'Parceria fechada', 'Sem interesse'];
const STATUS_STYLE = [
  { bg: '#eee', fg: '#555' }, { bg: '#fff3cd', fg: '#8a6d00' }, { bg: '#d6e9ff', fg: '#0a4d8a' },
  { bg: '#d4edda', fg: '#1e6b34' }, { bg: '#f8d7da', fg: '#8a1f2b' },
];

const onlyDigits = (s) => (s || '').replace(/\D/g, '');

// Mensagem pronta para pedir o e-mail da imobiliária pelo WhatsApp (captação do e-mail).
const MSG_PEDIR_EMAIL = (nome) =>
  `Olá, ${nome || 'tudo bem'}! Aqui é a equipe da Romatec / AvalieImob. 😊\n\n` +
  'Temos uma plataforma para corretores e imobiliárias: avaliação de imóveis (PTAM / laudos NBR 14.653), ' +
  'contratos com assinatura digital pelo WhatsApp e georreferenciamento.\n\n' +
  'Gostaríamos de enviar uma proposta de parceria (é gratuito para testar). ' +
  'Qual o melhor e-mail de vocês para o envio? Obrigado!';

export default function ProspeccaoPage() {
  const { toast } = useToast();
  const [prospects, setProspects] = useState([]);
  const [cidades, setCidades] = useState([]);
  const [stats, setStats] = useState(null);
  const [camp, setCamp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fCidade, setFCidade] = useState('');
  const [fStatus, setFStatus] = useState('');
  const [busca, setBusca] = useState('');
  const [busy, setBusy] = useState('');
  const [limite, setLimite] = useState(40);
  const [intervalo, setIntervalo] = useState(20);
  const [teste, setTeste] = useState('');
  const [showImport, setShowImport] = useState(false);
  const [colado, setColado] = useState('');
  const [proposta, setProposta] = useState(null);
  const [auto, setAuto] = useState(null);
  const [provedor, setProvedor] = useState(null);
  const pollRef = useRef(null);

  const carregar = useCallback(async () => {
    try {
      const [l, s, c] = await Promise.all([
        prospeccaoAPI.listar({ cidade: fCidade, status: fStatus, busca }),
        prospeccaoAPI.stats(),
        prospeccaoAPI.campanhaStatus(),
      ]);
      setProspects(l.prospects || []);
      setCidades(l.cidades || []);
      setStats(s);
      setCamp(c);
    } catch {
      toast({ title: 'Erro ao carregar', variant: 'destructive' });
    } finally { setLoading(false); }
  }, [fCidade, fStatus, busca, toast]);

  useEffect(() => { carregar(); }, [carregar]);
  useEffect(() => {
    prospeccaoAPI.getAuto().then(setAuto).catch(() => {});
    adminAPI.emailStatus().then(setProvedor).catch(() => {});
  }, []);

  const salvarAuto = async (patch) => {
    const novo = { ...(auto || { ativo: false, hora: 9, limite_dia: 40, intervalo: 30 }), ...patch };
    setAuto(novo);
    try {
      await prospeccaoAPI.setAuto({
        ativo: !!novo.ativo, hora: Number(novo.hora), limite_dia: Number(novo.limite_dia), intervalo: Number(novo.intervalo),
      });
    } catch { toast({ title: 'Falha ao salvar agendamento', variant: 'destructive' }); }
  };

  // Poll do status da campanha enquanto estiver enviando.
  useEffect(() => {
    if (camp?.enviando && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const c = await prospeccaoAPI.campanhaStatus();
          setCamp(c);
          if (!c.enviando) { clearInterval(pollRef.current); pollRef.current = null; carregar(); }
        } catch { /* */ }
      }, 8000);
    }
    return () => { if (pollRef.current && !camp?.enviando) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [camp?.enviando, carregar]);

  const setStatusProspect = async (id, val) => {
    setProspects((ps) => ps.map((p) => (p.id === id ? { ...p, status: val } : p)));
    try { await prospeccaoAPI.atualizar(id, { status: val }); prospeccaoAPI.stats().then(setStats); }
    catch { toast({ title: 'Falha ao salvar status', variant: 'destructive' }); }
  };
  const setObs = async (id, val) => {
    try { await prospeccaoAPI.atualizar(id, { obs: val }); } catch { /* */ }
  };
  const salvarEmail = async (id, val) => {
    setProspects((ps) => ps.map((p) => (p.id === id ? { ...p, email: val } : p)));
    try {
      await prospeccaoAPI.atualizar(id, { email: val });
      prospeccaoAPI.stats().then(setStats);
      prospeccaoAPI.campanhaStatus().then(setCamp);
      if (val) toast({ title: 'E-mail salvo ✓', description: 'Agora esta imobiliária entra na campanha.' });
    } catch { toast({ title: 'Falha ao salvar e-mail', variant: 'destructive' }); }
  };
  const pedirEmailWa = (p) => {
    if (!p.telefone) return;
    window.open(`https://wa.me/${onlyDigits(p.telefone)}?text=${encodeURIComponent(MSG_PEDIR_EMAIL(p.nome))}`, '_blank');
  };
  const excluir = async (id) => {
    if (!window.confirm('Excluir este contato?')) return;
    await prospeccaoAPI.excluir(id);
    carregar();
  };

  const seed = async () => {
    setBusy('seed');
    try {
      const r = await prospeccaoAPI.seed();
      toast({ title: `Lista da região importada`, description: `${r.importados} novos (de ${r.total_lista}).` });
      carregar();
    } catch { toast({ title: 'Falha ao importar', variant: 'destructive' }); }
    finally { setBusy(''); }
  };

  const importarColado = async () => {
    const linhas = colado.split('\n').map((l) => l.trim()).filter(Boolean);
    const prospectsArr = linhas.map((l) => {
      const c = l.split(/[;|\t]/).map((x) => x.trim());
      return { nome: c[0] || '', cidade: c[1] || '', email: c[2] || '', telefone: c[3] || '', endereco: c[4] || '' };
    }).filter((p) => p.nome);
    if (!prospectsArr.length) { toast({ title: 'Cole ao menos uma linha (nome; cidade; email; telefone; endereço)', variant: 'destructive' }); return; }
    setBusy('import');
    try {
      const r = await prospeccaoAPI.importar(prospectsArr);
      toast({ title: 'Importado', description: `${r.importados} novos de ${r.recebidos}.` });
      setColado(''); setShowImport(false); carregar();
    } catch { toast({ title: 'Falha ao importar', variant: 'destructive' }); }
    finally { setBusy(''); }
  };

  const verProposta = async () => {
    try { setProposta(await prospeccaoAPI.propostaPreview()); }
    catch { toast({ title: 'Falha ao carregar a proposta', variant: 'destructive' }); }
  };

  const enviarTeste = async () => {
    if (!teste.trim()) return;
    setBusy('teste');
    try {
      await prospeccaoAPI.enviarCampanha({ teste_email: teste.trim() });
      toast({ title: 'E-mail de teste enviado ✓', description: teste.trim() });
    } catch (e) { toast({ title: 'Falha no teste', description: e?.response?.data?.detail || '', variant: 'destructive' }); }
    finally { setBusy(''); }
  };

  const iniciarDisparo = async () => {
    if (!window.confirm(`Disparar a proposta para até ${limite} imobiliárias (1 a cada ${intervalo}s)?`)) return;
    setBusy('disparo');
    try {
      const r = await prospeccaoAPI.enviarCampanha({ limite: Number(limite), intervalo: Number(intervalo) });
      toast({ title: 'Disparo iniciado', description: `${r.elegiveis} elegíveis · enviando até ${r.limite}.` });
      setCamp((c) => ({ ...(c || {}), enviando: true }));
    } catch (e) { toast({ title: 'Não iniciou', description: e?.response?.data?.detail || '', variant: 'destructive' }); }
    finally { setBusy(''); }
  };

  const parar = async () => { await prospeccaoAPI.pararCampanha(); toast({ title: 'Parando…' }); };
  const resetErros = async () => {
    const r = await prospeccaoAPI.resetErros();
    toast({ title: `${r.reabilitados} reabilitados para reenvio` });
    carregar();
  };

  const StatChip = ({ n, label }) => (
    <div className="bg-white border rounded-lg px-3.5 py-2 text-xs text-gray-600" style={{ borderLeft: `4px solid ${GOLD}` }}>
      <b className="block text-lg" style={{ color: GREEN }}>{n ?? 0}</b>{label}
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <header className="flex items-start gap-3 mb-5">
        <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: GREEN }}>
          <Radar className="w-6 h-6" style={{ color: GOLD }} />
        </div>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: GREEN }}>Prospecção &amp; Campanhas</h1>
          <p className="text-sm text-gray-500">
            Imobiliárias e corretores da região — envie a <strong>proposta de parceria</strong> por e-mail (em lotes) e capte novos clientes para o sistema.
          </p>
        </div>
      </header>

      {/* Stats */}
      <div className="flex flex-wrap gap-2 mb-5">
        <StatChip n={stats?.total} label="Contatos" />
        <StatChip n={stats?.com_email} label="Com e-mail" />
        <StatChip n={stats?.elegiveis} label="A enviar (elegíveis)" />
        <StatChip n={stats?.enviados} label="E-mails enviados" />
        {(stats?.por_status || []).map((s) => <StatChip key={s.status} n={s.n} label={s.label} />)}
      </div>

      {/* Campanha */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 mb-5">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <h2 className="font-semibold flex items-center gap-2" style={{ color: GREEN }}>
            <Mail className="w-4 h-4" style={{ color: GOLD }} /> Campanha de e-mail (proposta de parceria)
          </h2>
          <button onClick={verProposta} className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg border" style={{ color: GREEN }}>
            <Eye className="w-3.5 h-3.5" /> Ver proposta
          </button>
        </div>

        {provedor && (
          <div className="mb-3 text-xs flex items-center gap-1.5 rounded-lg px-3 py-1.5"
            style={provedor.provider === 'SendGrid'
              ? { background: '#ecfdf5', color: '#065f46' }
              : { background: '#f5f2e8', color: '#7a5c00' }}>
            <Server className="w-3.5 h-3.5 shrink-0" />
            {provedor.provider === 'SendGrid'
              ? <span>Enviando via <strong>SendGrid</strong> — provedor dedicado, ideal para volume (nacional).</span>
              : provedor.provider === 'SMTP'
              ? <span>Enviando via <strong>SMTP</strong> ({provedor.smtp_host || 'cPanel'}) — bom para a região. Para o <strong>nacional</strong>, configure <strong>SendGrid</strong> em Painel ▸ E-mail (melhor entregabilidade + descadastro automático).</span>
              : <span><strong>Nenhum provedor configurado</strong> — configure em Painel ▸ E-mail antes de disparar.</span>}
          </div>
        )}

        {camp?.enviando ? (
          <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 mb-3 text-sm text-amber-800 flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Enviando… {camp.enviados} enviados de {camp.com_email} com e-mail.
            <button onClick={parar} className="ml-auto inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-lg bg-white border text-red-600">
              <StopCircle className="w-3.5 h-3.5" /> Parar
            </button>
          </div>
        ) : (
          <p className="text-xs text-gray-500 mb-3">
            <strong>{camp?.elegiveis ?? 0}</strong> imobiliárias elegíveis (com e-mail, ainda não enviadas).
            Envio em lotes com intervalo para proteger a reputação do domínio.
          </p>
        )}

        <div className="grid sm:grid-cols-4 gap-3 mb-3">
          <label className="block">
            <span className="text-xs font-semibold text-gray-600">E-mails nesta rodada</span>
            <input type="number" min="1" max="300" value={limite} onChange={(e) => setLimite(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" />
          </label>
          <label className="block">
            <span className="text-xs font-semibold text-gray-600">Intervalo (segundos)</span>
            <input type="number" min="1" max="300" value={intervalo} onChange={(e) => setIntervalo(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" />
          </label>
          <label className="block sm:col-span-2">
            <span className="text-xs font-semibold text-gray-600">Testar (envia 1 e-mail para você)</span>
            <div className="flex gap-2">
              <input type="email" value={teste} onChange={(e) => setTeste(e.target.value)} placeholder="seu@email.com" className="flex-1 border rounded-lg px-3 py-2 text-sm" />
              <button onClick={enviarTeste} disabled={busy === 'teste' || !teste.trim()} className="px-3 py-2 rounded-lg text-sm font-semibold border disabled:opacity-50" style={{ color: GREEN }}>
                {busy === 'teste' ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Testar'}
              </button>
            </div>
          </label>
        </div>

        <div className="flex flex-wrap gap-2">
          <button onClick={iniciarDisparo} disabled={busy === 'disparo' || camp?.enviando}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-50" style={{ background: GREEN }}>
            {busy === 'disparo' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Iniciar disparo
          </button>
          {!!camp?.com_erro && (
            <button onClick={resetErros} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border text-amber-700">
              <AlertTriangle className="w-4 h-4" /> Reabilitar {camp.com_erro} com erro
            </button>
          )}
        </div>

        {/* Envio automático diário */}
        <div className="mt-4 pt-4 border-t border-gray-100">
          <label className="flex items-center gap-2 text-sm font-semibold cursor-pointer" style={{ color: GREEN }}>
            <input type="checkbox" checked={!!auto?.ativo} onChange={(e) => salvarAuto({ ativo: e.target.checked })} />
            <CalendarClock className="w-4 h-4" style={{ color: GOLD }} /> Envio automático diário
          </label>
          {auto?.ativo && (
            <div className="grid sm:grid-cols-3 gap-3 mt-3">
              <label className="block"><span className="text-xs font-semibold text-gray-600">Horário (0–23h · Brasília)</span>
                <input type="number" min="0" max="23" value={auto.hora} onChange={(e) => salvarAuto({ hora: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" /></label>
              <label className="block"><span className="text-xs font-semibold text-gray-600">E-mails por dia</span>
                <input type="number" min="1" max="500" value={auto.limite_dia} onChange={(e) => salvarAuto({ limite_dia: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" /></label>
              <label className="block"><span className="text-xs font-semibold text-gray-600">Intervalo (s)</span>
                <input type="number" min="1" max="300" value={auto.intervalo} onChange={(e) => salvarAuto({ intervalo: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" /></label>
            </div>
          )}
          <p className="text-[11px] text-gray-400 mt-2">
            {auto?.ativo
              ? `Todo dia às ${auto.hora}h (horário de Brasília) o sistema dispara sozinho até ${auto.limite_dia} e-mails, respeitando o intervalo, até esgotar a lista de elegíveis.`
              : 'Ative para o sistema disparar sozinho todo dia, no horário definido, sem você precisar clicar.'}
          </p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap gap-2 items-center mb-3">
        <select value={fCidade} onChange={(e) => setFCidade(e.target.value)} className="border rounded-lg px-3 py-2 text-sm bg-white">
          <option value="">Todas as cidades</option>
          {cidades.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={fStatus} onChange={(e) => setFStatus(e.target.value)} className="border rounded-lg px-3 py-2 text-sm bg-white">
          <option value="">Todos os status</option>
          {STATUS_LABELS.map((l, i) => <option key={i} value={i}>{l}</option>)}
        </select>
        <input type="text" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por nome…" className="border rounded-lg px-3 py-2 text-sm" />
        <div className="flex-1" />
        <button onClick={seed} disabled={busy === 'seed'} className="inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-2 rounded-lg border disabled:opacity-50" style={{ color: GREEN }}>
          {busy === 'seed' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />} Importar lista da região
        </button>
        <button onClick={() => setShowImport(true)} className="inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-2 rounded-lg text-white" style={{ background: GOLD, color: GREEN }}>
          <Upload className="w-4 h-4" /> Importar (colar)
        </button>
      </div>

      {/* Tabela */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
        <table className="w-full text-sm" style={{ minWidth: 900 }}>
          <thead>
            <tr style={{ background: GREEN }} className="text-white text-xs uppercase">
              <th className="text-left px-3 py-2.5" style={{ width: 110 }}>Cidade</th>
              <th className="text-left px-3 py-2.5">Empresa / Corretor</th>
              <th className="text-left px-3 py-2.5" style={{ width: 130 }}>Telefone</th>
              <th className="text-left px-3 py-2.5" style={{ width: 190 }}>E-mail</th>
              <th className="text-left px-3 py-2.5" style={{ width: 150 }}>Status</th>
              <th className="text-left px-3 py-2.5" style={{ width: 190 }}>Observações</th>
              <th style={{ width: 40 }}></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-gray-400"><Loader2 className="w-5 h-5 animate-spin inline" /></td></tr>
            ) : prospects.length === 0 ? (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-gray-400 text-sm">
                Nenhum contato. Clique em <strong>Importar lista da região</strong> para começar.
              </td></tr>
            ) : prospects.map((p) => {
              const st = STATUS_STYLE[p.status] || STATUS_STYLE[0];
              return (
                <tr key={p.id} className="border-b border-gray-100 hover:bg-gray-50 align-top">
                  <td className="px-3 py-2.5">
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap" style={{ background: '#e7efe9', color: GREEN }}>{p.cidade}</span>
                  </td>
                  <td className="px-3 py-2.5 font-semibold text-gray-800">
                    {p.nome}
                    {p.email_enviado && <span className="ml-1.5 text-[10px] font-semibold text-emerald-600" title={p.email_enviado_em}>✓ enviado</span>}
                    {p.email_erro && <span className="ml-1.5 text-[10px] font-semibold text-red-500" title={p.email_erro}>⚠ erro</span>}
                    {p.opt_out && <span className="ml-1.5 text-[10px] font-semibold text-gray-400">descadastrado</span>}
                  </td>
                  <td className="px-3 py-2.5">
                    {p.telefone ? (
                      <div className="space-y-1">
                        <a href={`https://wa.me/${onlyDigits(p.telefone)}`} target="_blank" rel="noreferrer" className="font-semibold block" style={{ color: GREEN }}>{p.telefone}</a>
                        {!p.email && (
                          <button onClick={() => pedirEmailWa(p)} title="Abrir o WhatsApp com a mensagem pronta pedindo o e-mail"
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 hover:underline">
                            <MessageCircle className="w-3 h-3" /> pedir e-mail
                          </button>
                        )}
                      </div>
                    ) : <span className="text-gray-400 text-xs italic">—</span>}
                  </td>
                  <td className="px-3 py-2.5">
                    <input type="email" defaultValue={p.email || ''} placeholder="colar e-mail…"
                      onBlur={(e) => { const v = e.target.value.trim(); if (v !== (p.email || '')) salvarEmail(p.id, v); }}
                      className="w-full text-xs border rounded px-2 py-1"
                      style={{ borderColor: p.email ? '#d1d5db' : GOLD, background: p.email ? '#fff' : '#fffdf5' }} />
                  </td>
                  <td className="px-3 py-2.5">
                    <select value={p.status} onChange={(e) => setStatusProspect(p.id, Number(e.target.value))}
                      className="w-full rounded px-2 py-1 text-xs font-semibold border" style={{ background: st.bg, color: st.fg }}>
                      {STATUS_LABELS.map((l, i) => <option key={i} value={i}>{l}</option>)}
                    </select>
                  </td>
                  <td className="px-3 py-2.5">
                    <textarea defaultValue={p.obs} onBlur={(e) => setObs(p.id, e.target.value)} placeholder="Anotação…"
                      className="w-full text-xs border rounded px-2 py-1 resize-y" style={{ minHeight: 32 }} />
                  </td>
                  <td className="px-2 py-2.5">
                    <button onClick={() => excluir(p.id)} className="text-gray-300 hover:text-red-500"><Trash2 className="w-4 h-4" /></button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-[11px] text-gray-400 mt-3">
        Sem e-mail? Clique em <strong>"pedir e-mail"</strong> (abre o WhatsApp com a mensagem pronta); quando responderem,
        <strong> cole o e-mail</strong> na coluna E-mail — a imobiliária entra na campanha na hora. Dados públicos (PJ);
        todo e-mail inclui link de <strong>descadastro</strong> (LGPD). Descoberta automática por API (Google Places) fica disponível ao configurar a chave no servidor.
      </p>

      {/* Modal importar */}
      {showImport && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowImport(false)}>
          <div className="bg-white rounded-2xl p-5 max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold" style={{ color: GREEN }}>Importar contatos (colar)</h3>
              <button onClick={() => setShowImport(false)}><X className="w-5 h-5 text-gray-400" /></button>
            </div>
            <p className="text-xs text-gray-500 mb-2">Uma imobiliária por linha, campos separados por <code>;</code> :<br />
              <code>Nome ; Cidade ; E-mail ; Telefone ; Endereço</code></p>
            <textarea value={colado} onChange={(e) => setColado(e.target.value)} rows={8}
              placeholder="Imobiliária X ; Imperatriz ; contato@x.com.br ; +55 99 90000-0000 ; Av. Central, 100"
              className="w-full border rounded-lg px-3 py-2 text-sm font-mono" />
            <div className="flex justify-end gap-2 mt-3">
              <button onClick={() => setShowImport(false)} className="px-4 py-2 rounded-lg text-sm border">Cancelar</button>
              <button onClick={importarColado} disabled={busy === 'import'} className="px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-50" style={{ background: GREEN }}>
                {busy === 'import' ? 'Importando…' : 'Importar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal proposta */}
      {proposta && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setProposta(null)}>
          <div className="bg-white rounded-2xl overflow-hidden max-w-xl w-full h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-2.5 border-b">
              <h3 className="font-semibold text-sm" style={{ color: GREEN }}>Prévia da proposta (e-mail)</h3>
              <button onClick={() => setProposta(null)}><X className="w-5 h-5 text-gray-400" /></button>
            </div>
            <iframe title="proposta" srcDoc={proposta} className="flex-1 w-full" />
          </div>
        </div>
      )}
    </div>
  );
}
