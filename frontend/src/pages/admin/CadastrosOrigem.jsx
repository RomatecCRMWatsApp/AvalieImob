// @module pages/admin/CadastrosOrigem — de onde vieram os cadastros (Google, Bing, direto…).
//
// O dado já é gravado no cadastro (referrer + UTMs). Aqui mostramos o ranking de
// canais, a conversão de cada um e a lista de quem veio de onde. Inclui o painel
// de notificações por e-mail (lead imediato + resumo periódico).
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Globe, Search, RefreshCw, Loader2, Mail, Send, CheckCircle2, Clock, KeyRound,
} from 'lucide-react';
import { BrandSpinner } from '../../components/brand/BrandSpinner';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { useToast } from '../../hooks/use-toast';
import { adminAPI } from '../../lib/api';

const VERDE = '#0C3320';
const DOURADO = '#C9A84C';

const PERIODOS = [
  { dias: 7, label: '7 dias' },
  { dias: 30, label: '30 dias' },
  { dias: 90, label: '90 dias' },
  { dias: 3650, label: 'Tudo' },
];

const SITUACAO = {
  assinante: { label: 'Assinante', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  em_teste: { label: 'Em teste', cls: 'bg-sky-50 text-sky-700 border-sky-200' },
  teste_expirado: { label: 'Teste vencido', cls: 'bg-amber-50 text-amber-700 border-amber-200' },
  expirado: { label: 'Expirado', cls: 'bg-amber-50 text-amber-700 border-amber-200' },
  cadastrado: { label: 'Só cadastrou', cls: 'bg-gray-100 text-gray-600 border-gray-200' },
};

// Cor por tipo de canal — orgânico é o que interessa no SEO.
const COR_TIPO = {
  organico: '#0C3320', pago: '#B8860B', social: '#7C3AED',
  email: '#0369A1', referral: '#475569', direto: '#94A3B8', campanha: '#C9A84C',
};

const dataFmt = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso.endsWith('Z') ? iso : `${iso}Z`);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('pt-BR');
};

const DIAS_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'];

const Card = ({ titulo, valor, cor, hint }) => (
  <div className="rounded-xl bg-white p-4 shadow-sm border border-gray-100">
    <p className="text-xs text-gray-500">{titulo}</p>
    <p className="mt-1 text-2xl font-bold" style={{ color: cor || VERDE }}>{valor}</p>
    {hint ? <p className="text-[11px] text-gray-400 mt-0.5">{hint}</p> : null}
  </div>
);

// ── Painel de notificações por e-mail ───────────────────────────────────────
const PainelNotificacoes = () => {
  const { toast } = useToast();
  const [cfg, setCfg] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [testando, setTestando] = useState('');

  useEffect(() => { adminAPI.notificacoes().then(setCfg).catch(() => {}); }, []);
  if (!cfg) return null;

  const set = (k, v) => setCfg((c) => ({ ...c, [k]: v }));

  const salvar = async (patch) => {
    setSalvando(true);
    try {
      const novo = await adminAPI.salvarNotificacoes({ ...patch });
      setCfg(novo);
      toast({ title: 'Preferências salvas ✓' });
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSalvando(false); }
  };

  const testar = async (tipo) => {
    setTestando(tipo);
    try {
      const r = await adminAPI.testarNotificacao({ tipo, email: cfg.email_destino || undefined, dias: 30 });
      toast({
        title: r.ok ? `E-mail de teste enviado para ${r.para}` : 'Falha no envio',
        description: r.ok ? 'Confira a caixa de entrada (e o spam).' : r.erro,
        variant: r.ok ? undefined : 'destructive',
      });
    } catch (e) {
      toast({ title: 'Erro no teste', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setTestando(''); }
  };

  return (
    <div className="rounded-xl bg-white p-4 shadow-sm border border-gray-100 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <Mail className="w-4 h-4" style={{ color: DOURADO }} />
        <p className="text-xs font-bold uppercase tracking-wide text-gray-500">
          Avisos por e-mail (além do WhatsApp)
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="space-y-3">
          <label className="flex items-start gap-2 text-sm text-gray-700">
            <input type="checkbox" className="mt-0.5" checked={!!cfg.email_lead_ativo}
                   onChange={(e) => salvar({ email_lead_ativo: e.target.checked })} />
            <span>
              <strong>Cada lead novo, na hora</strong>
              <span className="block text-xs text-gray-500">
                Todo lead da calculadora dispara um e-mail com os dados e a estimativa.
              </span>
            </span>
          </label>

          <label className="flex items-start gap-2 text-sm text-gray-700">
            <input type="checkbox" className="mt-0.5" checked={!!cfg.resumo_ativo}
                   onChange={(e) => salvar({ resumo_ativo: e.target.checked })} />
            <span>
              <strong>Resumo periódico</strong>
              <span className="block text-xs text-gray-500">
                Cadastros, canais de origem, leads e assinaturas do período.
              </span>
            </span>
          </label>

          {cfg.resumo_ativo && (
            <div className="flex flex-wrap items-center gap-2 pl-6">
              <select className="px-2 py-1.5 text-sm border border-gray-300 rounded-lg"
                      value={cfg.resumo_freq}
                      onChange={(e) => salvar({ resumo_freq: e.target.value })}>
                <option value="diario">Todo dia</option>
                <option value="semanal">Toda semana</option>
              </select>
              {cfg.resumo_freq === 'semanal' && (
                <select className="px-2 py-1.5 text-sm border border-gray-300 rounded-lg"
                        value={cfg.resumo_dia_semana}
                        onChange={(e) => salvar({ resumo_dia_semana: Number(e.target.value) })}>
                  {DIAS_SEMANA.map((d, i) => <option key={d} value={i}>{d}</option>)}
                </select>
              )}
              <span className="text-sm text-gray-500">às</span>
              <select className="px-2 py-1.5 text-sm border border-gray-300 rounded-lg"
                      value={cfg.resumo_hora}
                      onChange={(e) => salvar({ resumo_hora: Number(e.target.value) })}>
                {Array.from({ length: 24 }, (_, h) => (
                  <option key={h} value={h}>{String(h).padStart(2, '0')}h</option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div className="space-y-2">
          <label className="block text-xs font-medium text-gray-600">Enviar para</label>
          <div className="flex gap-2">
            <Input value={cfg.email_destino || ''} placeholder={cfg.destino_efetivo || 'seu@email.com'}
                   onChange={(e) => set('email_destino', e.target.value)} />
            <Button variant="outline" disabled={salvando}
                    onClick={() => salvar({ email_destino: cfg.email_destino || '' })}>
              {salvando ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Salvar'}
            </Button>
          </div>
          <p className="text-[11px] text-gray-400">
            Em branco, usa o e-mail da conta dona ({cfg.destino_efetivo}).
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            <Button size="sm" variant="outline" disabled={!!testando} onClick={() => testar('lead')}>
              {testando === 'lead' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
              Testar e-mail de lead
            </Button>
            <Button size="sm" variant="outline" disabled={!!testando} onClick={() => testar('resumo')}>
              {testando === 'resumo' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
              Enviar resumo agora
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Aba principal ───────────────────────────────────────────────────────────
const CadastrosOrigem = () => {
  const { toast } = useToast();
  const [dias, setDias] = useState(30);
  const [canal, setCanal] = useState('');
  const [busca, setBusca] = useState('');
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { dias };
      if (canal) params.canal = canal;
      if (busca.trim()) params.q = busca.trim();
      setDados(await adminAPI.cadastrosOrigem(params));
    } catch (e) {
      toast({ title: 'Erro ao carregar cadastros', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setLoading(false); }
  }, [dias, canal, busca, toast]);

  useEffect(() => { load(); }, [dias, canal]);   // eslint-disable-line react-hooks/exhaustive-deps

  const maior = useMemo(
    () => Math.max(1, ...((dados?.canais || []).map((c) => c.total))),
    [dados],
  );

  if (loading && !dados) return <BrandSpinner label="Carregando origem dos cadastros..." />;

  const t = dados?.totais || {};
  const canais = dados?.canais || [];

  return (
    <div>
      <PainelNotificacoes />

      <div className="flex flex-wrap items-center gap-2 mb-4">
        {PERIODOS.map((p) => (
          <button key={p.dias} type="button" onClick={() => setDias(p.dias)}
                  className={`px-3 py-1.5 rounded-lg border text-sm ${
                    dias === p.dias ? 'text-white border-transparent'
                                    : 'bg-white text-gray-700 border-gray-300 hover:border-gray-400'}`}
                  style={dias === p.dias ? { background: VERDE } : undefined}>
            {p.label}
          </button>
        ))}
        <Button variant="outline" size="sm" onClick={load} className="ml-auto">
          <RefreshCw className="w-4 h-4 mr-2" /> Atualizar
        </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <Card titulo="Cadastros no período" valor={t.cadastros ?? 0} />
        <Card titulo="Viraram assinantes" valor={t.assinantes ?? 0} cor="#059669" />
        <Card titulo="Em teste" valor={t.em_teste ?? 0} cor="#0284C7" />
        <Card titulo="Nunca acessaram" valor={t.nunca_acessaram ?? 0} cor="#B45309" />
        <Card titulo="Conversão" valor={`${t.conversao ?? 0}%`} cor={DOURADO}
              hint={`${t.total_base ?? 0} na base total`} />
      </div>

      <div className="rounded-xl bg-white p-4 shadow-sm border border-gray-100 mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Globe className="w-4 h-4" style={{ color: DOURADO }} />
          <p className="text-xs font-bold uppercase tracking-wide text-gray-500">
            De onde vieram os cadastros
          </p>
        </div>
        {canais.length === 0 && (
          <p className="text-sm text-gray-400 py-4">Nenhum cadastro no período selecionado.</p>
        )}
        <div className="space-y-2">
          {canais.map((c) => (
            <button key={c.canal} type="button"
                    onClick={() => setCanal(canal === c.canal ? '' : c.canal)}
                    className={`w-full flex items-center gap-3 text-left rounded-lg px-2 py-1.5 transition ${
                      canal === c.canal ? 'bg-emerald-50' : 'hover:bg-gray-50'}`}>
              <span className="text-sm font-semibold text-gray-800 w-44 shrink-0 truncate"
                    title={c.label}>{c.label}</span>
              <span className="flex-1 h-2.5 rounded-full bg-gray-100 overflow-hidden">
                <span className="block h-full rounded-full"
                      style={{ width: `${Math.max(4, (100 * c.total) / maior)}%`,
                               background: COR_TIPO[c.tipo] || DOURADO }} />
              </span>
              <span className="text-sm font-bold text-gray-900 w-8 text-right">{c.total}</span>
              <span className="text-xs text-gray-500 w-28 text-right">
                {c.assinantes} assinante(s)
              </span>
            </button>
          ))}
        </div>
        {canal && (
          <p className="text-xs mt-3" style={{ color: VERDE }}>
            Filtrando por <strong>{canal}</strong> — clique de novo no canal para limpar.
          </p>
        )}
      </div>

      <div className="flex gap-2 mb-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <Input value={busca} onChange={(e) => setBusca(e.target.value)}
                 onKeyDown={(e) => e.key === 'Enter' && load()}
                 placeholder="Buscar por nome ou e-mail..." className="pl-9" />
        </div>
        <Button variant="outline" onClick={load}>Buscar</Button>
      </div>

      <div className="rounded-xl bg-white shadow-sm border border-gray-100 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-4 py-3">Cliente</th>
              <th className="text-left px-4 py-3">Canal</th>
              <th className="text-left px-4 py-3">Página de entrada</th>
              <th className="text-left px-4 py-3">Situação</th>
              <th className="text-left px-4 py-3">Cadastro</th>
              <th className="text-left px-4 py-3">Último acesso</th>
            </tr>
          </thead>
          <tbody>
            {(dados?.cadastros || []).length === 0 && (
              <tr><td colSpan={6} className="text-center py-10 text-gray-400">
                Nenhum cadastro encontrado.
              </td></tr>
            )}
            {(dados?.cadastros || []).map((c) => {
              const s = SITUACAO[c.situacao] || SITUACAO.cadastrado;
              return (
                <tr key={c.id} className="border-t border-gray-100 hover:bg-gray-50/60">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{c.nome || '—'}</div>
                    <div className="text-xs text-gray-500">{c.email}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold">
                      <span className="w-2 h-2 rounded-full"
                            style={{ background: COR_TIPO[c.tipo] || DOURADO }} />
                      {c.canal_label}
                    </span>
                    {c.campanha ? <div className="text-[11px] text-gray-400">{c.campanha}</div> : null}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-[220px] truncate"
                      title={c.pagina_entrada || c.referrer || ''}>
                    {c.pagina_entrada || '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-1 rounded-full border ${s.cls}`}>
                      {c.situacao === 'assinante' && <CheckCircle2 className="w-3 h-3 inline mr-1" />}
                      {c.situacao === 'em_teste' && <KeyRound className="w-3 h-3 inline mr-1" />}
                      {s.label}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{dataFmt(c.cadastrado_em)}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {c.nunca_acessou
                      ? <span className="text-amber-600 text-xs inline-flex items-center gap-1">
                          <Clock className="w-3 h-3" /> nunca acessou
                        </span>
                      : dataFmt(c.ultimo_acesso)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-[11px] text-gray-400 mt-3">
        A origem vem do <strong>referrer</strong> e das <strong>UTMs</strong> gravados no
        momento do cadastro. “Direto” = digitou o endereço, veio de app/WhatsApp sem link
        rastreável ou navegou dentro do próprio site.
      </p>
    </div>
  );
};

export default CadastrosOrigem;
