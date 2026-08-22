// @module pages/admin/TrialsAdmin — Acessos de Teste (trial gratuito por N dias).
//
// O admin cria um login (ou libera o teste para quem já é cadastrado), define a
// duração em dias e envia as credenciais por WhatsApp (Z-API) e/ou e-mail.
// O acesso expira SOZINHO no vencimento — sem precisar cancelar nada.
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  KeyRound, Plus, Copy, Check, Send, X, CalendarClock, Loader2, Ban, RefreshCw, Search,
} from 'lucide-react';
import { BrandSpinner } from '../../components/brand/BrandSpinner';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../components/ui/dialog';
import { WhatsAppPreview } from '../../components/admin/WhatsAppPreview';
import { useToast } from '../../hooks/use-toast';
import { trialsAPI } from '../../lib/api';

const PRESETS_DIAS = [3, 7, 15, 30];

const SITUACAO = {
  ativo: { label: 'Em teste', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  expirado: { label: 'Expirado', cls: 'bg-amber-50 text-amber-700 border-amber-200' },
  encerrado: { label: 'Encerrado', cls: 'bg-gray-100 text-gray-500 border-gray-200' },
  convertido: { label: '✓ Assinou', cls: 'bg-blue-50 text-blue-700 border-blue-200' },
  nao_trial: { label: '—', cls: 'bg-gray-100 text-gray-500 border-gray-200' },
};

const fmtData = (v) => {
  if (!v) return '—';
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('pt-BR');
};

const emptyForm = () => ({
  nome: '', email: '', telefone: '', dias: 7, senha: '', observacao: '',
  enviar_whatsapp: true, enviar_email: true,
});

// Espelha services/trial_service.montar_mensagem_trial p/ a prévia ao vivo.
const buildMensagem = (f) => {
  const primeiro = (f.nome || '').trim().split(' ')[0];
  const saud = primeiro ? `Olá, ${primeiro}! 👋\n\n` : 'Olá! 👋\n\n';
  const email = (f.email || '').trim() || 'seu@email.com';
  const senha = (f.senha || '').trim() || 'Teste-K7QX';
  const dias = Number(f.dias) || 0;
  const exp = new Date(Date.now() + dias * 86400000).toLocaleDateString('pt-BR');
  return `${saud}✅ *Seu acesso de teste ao AvalieImob está liberado!*\n\n` +
    `Você tem *${dias} dias* de acesso gratuito à plataforma completa:\n` +
    `• Avaliação de imóveis e PTAM em PDF\n• Contratos, recibos e assinatura digital\n` +
    `• Topografia, georreferenciamento e propostas\n\n` +
    `👤 *Login (e-mail):* ${email}\n🔑 *Senha:* ${senha}\n\n` +
    `_Você pode trocar a senha depois em Configurações._\n\n` +
    `⏰ *Seu teste vai até:* ${exp}\n\n👇 *Acesse agora:*\n${window.location.origin}/login\n\n` +
    `Qualquer dúvida é só me chamar por aqui.\n_RomaTec Consultoria Total — Açailândia/MA_`;
};

const StatCard = ({ label, value, color }) => (
  <div className="bg-white p-5 rounded-xl border border-gray-200">
    <div className="text-xs text-gray-500 mb-1 uppercase tracking-wider">{label}</div>
    <div className={`font-display text-2xl font-bold ${color || 'text-gray-900'}`}>{value}</div>
  </div>
);

const Campo = ({ label, children, hint }) => (
  <div>
    <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
    {children}
    {hint ? <p className="text-[11px] text-gray-400 mt-1">{hint}</p> : null}
  </div>
);

const TrialsAdmin = () => {
  const { toast } = useToast();
  const [trials, setTrials] = useState([]);
  const [resumo, setResumo] = useState({ total: 0, ativos: 0, expirados: 0, convertidos: 0 });
  const [loading, setLoading] = useState(true);
  const [busca, setBusca] = useState('');
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const [resultado, setResultado] = useState(null);   // credenciais após criar
  const [acaoId, setAcaoId] = useState('');
  const [copiado, setCopiado] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await trialsAPI.list();
      setTrials(Array.isArray(d?.trials) ? d.trials : []);
      setResumo(d?.resumo || {});
    } catch (e) {
      toast({ title: 'Erro ao carregar acessos de teste', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setLoading(false); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const mensagemPreview = useMemo(() => buildMensagem(form), [form]);
  const expiraEm = useMemo(
    () => new Date(Date.now() + (Number(form.dias) || 0) * 86400000).toLocaleDateString('pt-BR'),
    [form.dias],
  );

  const filtrados = trials.filter((t) => {
    if (!busca) return true;
    const q = busca.toLowerCase();
    return (t.name || '').toLowerCase().includes(q) || (t.email || '').toLowerCase().includes(q);
  });

  const copiar = async (texto, chave) => {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(chave);
      setTimeout(() => setCopiado(''), 1800);
    } catch { toast({ title: 'Não foi possível copiar', variant: 'destructive' }); }
  };

  const criar = async () => {
    if (!form.email.trim()) {
      toast({ title: 'Informe o e-mail do cliente', variant: 'destructive' });
      return;
    }
    setSaving(true);
    try {
      const r = await trialsAPI.criar({
        nome: form.nome || null,
        email: form.email.trim(),
        telefone: form.telefone || null,
        dias: Number(form.dias) || 7,
        senha: form.senha || null,
        observacao: form.observacao || null,
        enviar_whatsapp: !!form.enviar_whatsapp,
        enviar_email: !!form.enviar_email,
      });
      setResultado(r);
      const wa = r.envios?.whatsapp;
      const mail = r.envios?.email;
      const partes = [];
      if (wa) partes.push(wa.ok ? 'WhatsApp enviado' : `WhatsApp falhou: ${wa.erro}`);
      if (mail) partes.push(mail.ok ? 'e-mail enviado' : `e-mail falhou: ${mail.erro}`);
      toast({
        title: r.criado ? 'Login de teste criado ✓' : 'Teste liberado para conta existente ✓',
        description: partes.join(' · ') || 'Envie as credenciais ao cliente.',
      });
      load();
    } catch (e) {
      toast({ title: 'Erro ao liberar o teste', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSaving(false); }
  };

  const estender = async (t, dias) => {
    setAcaoId(t.id);
    try {
      await trialsAPI.estender(t.id, dias);
      toast({ title: `+${dias} dias para ${t.name || t.email}` });
      load();
    } catch (e) {
      toast({ title: 'Erro ao estender', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setAcaoId(''); }
  };

  const encerrar = async (t) => {
    if (!window.confirm(`Encerrar AGORA o acesso de ${t.name || t.email}?`)) return;
    setAcaoId(t.id);
    try {
      await trialsAPI.encerrar(t.id);
      toast({ title: 'Acesso encerrado' });
      load();
    } catch (e) {
      toast({ title: 'Erro ao encerrar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setAcaoId(''); }
  };

  const reenviar = async (t) => {
    const tel = window.prompt('WhatsApp para reenviar as credenciais (com DDD):', t.phone || '');
    if (tel === null) return;
    const novaSenha = window.confirm('Gerar uma NOVA senha para este acesso?\n\nOK = nova senha · Cancelar = manter a atual');
    setAcaoId(t.id);
    try {
      const r = await trialsAPI.reenviar(t.id, {
        telefone: tel || null, nova_senha: novaSenha,
        enviar_whatsapp: !!tel, enviar_email: true,
      });
      if (r.senha_temporaria) {
        setResultado({ criado: false, user: t, senha_temporaria: r.senha_temporaria, envios: r.envios, mensagem: r.mensagem });
        setOpen(true);
      }
      const wa = r.envios?.whatsapp;
      toast({
        title: wa?.ok ? 'Credenciais reenviadas ✓' : 'Reenvio processado',
        description: wa && !wa.ok ? wa.erro : undefined,
        variant: wa && !wa.ok ? 'destructive' : undefined,
      });
      load();
    } catch (e) {
      toast({ title: 'Erro ao reenviar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setAcaoId(''); }
  };

  const abrirNovo = () => { setForm(emptyForm()); setResultado(null); setOpen(true); };

  if (loading) return <BrandSpinner label="Carregando acessos de teste..." />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-bold text-gray-900 flex items-center gap-2">
            <KeyRound className="w-6 h-6" style={{ color: '#C9A84C' }} /> Acessos de Teste
          </h1>
          <p className="text-sm text-gray-500">
            Libere a plataforma completa por alguns dias — o acesso expira sozinho no prazo.
          </p>
        </div>
        <Button onClick={abrirNovo} style={{ background: '#0C3320' }} className="text-white">
          <Plus className="w-4 h-4 mr-2" /> Novo acesso de teste
        </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Em teste agora" value={resumo.ativos || 0} color="text-emerald-600" />
        <StatCard label="Expirados" value={resumo.expirados || 0} color="text-amber-600" />
        <StatCard label="Viraram assinantes" value={resumo.convertidos || 0} color="text-blue-600" />
        <StatCard label="Total concedidos" value={resumo.total || 0} />
      </div>

      <div className="relative max-w-sm">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <Input value={busca} onChange={(e) => setBusca(e.target.value)}
               placeholder="Buscar por nome ou e-mail..." className="pl-9" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-4 py-3">Cliente</th>
              <th className="text-left px-4 py-3">Situação</th>
              <th className="text-left px-4 py-3">Restam</th>
              <th className="text-left px-4 py-3">Expira em</th>
              <th className="text-left px-4 py-3">Último acesso</th>
              <th className="text-right px-4 py-3">Ações</th>
            </tr>
          </thead>
          <tbody>
            {filtrados.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-10 text-center text-gray-400">
                Nenhum acesso de teste ainda. Clique em “Novo acesso de teste”.
              </td></tr>
            )}
            {filtrados.map((t) => {
              const s = SITUACAO[t.situacao] || SITUACAO.nao_trial;
              const ocupado = acaoId === t.id;
              return (
                <tr key={t.id} className="border-t border-gray-100 hover:bg-gray-50/60">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{t.name || '—'}</div>
                    <div className="text-xs text-gray-500">{t.email}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-1 rounded-full border ${s.cls}`}>{s.label}</span>
                  </td>
                  <td className="px-4 py-3">
                    {t.situacao === 'ativo'
                      ? <span className="font-semibold text-emerald-700">{t.dias_restantes} dia(s)</span>
                      : <span className="text-gray-400">—</span>}
                    {t.trial_dias ? <div className="text-[11px] text-gray-400">de {t.trial_dias} concedidos</div> : null}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{fmtData(t.plan_expires)}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {t.last_login_at ? fmtData(t.last_login_at)
                      : <span className="text-amber-600 text-xs">nunca acessou</span>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1 flex-wrap">
                      {PRESETS_DIAS.slice(0, 2).map((d) => (
                        <Button key={d} size="sm" variant="outline" disabled={ocupado}
                                onClick={() => estender(t, d)} title={`Estender ${d} dias`}>
                          +{d}d
                        </Button>
                      ))}
                      <Button size="sm" variant="outline" disabled={ocupado} onClick={() => reenviar(t)}
                              title="Reenviar credenciais">
                        {ocupado ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                      </Button>
                      {t.situacao === 'ativo' && (
                        <Button size="sm" variant="outline" disabled={ocupado} onClick={() => encerrar(t)}
                                className="text-red-600 hover:text-red-700" title="Encerrar agora">
                          <Ban className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {resultado ? 'Credenciais do acesso de teste' : 'Novo acesso de teste'}
            </DialogTitle>
          </DialogHeader>

          {resultado ? (
            <div className="space-y-4">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                <p className="text-sm text-emerald-800 font-medium mb-3">
                  {resultado.criado
                    ? 'Login criado. Anote/copie agora — a senha não é exibida novamente.'
                    : 'Teste liberado para uma conta que já existia (senha do próprio cliente mantida).'}
                </p>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between gap-2 bg-white rounded-lg px-3 py-2 border">
                    <span className="text-gray-500">E-mail</span>
                    <span className="font-mono">{resultado.user?.email}</span>
                    <Button size="sm" variant="ghost" onClick={() => copiar(resultado.user?.email, 'email')}>
                      {copiado === 'email' ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                    </Button>
                  </div>
                  {resultado.senha_temporaria && (
                    <div className="flex items-center justify-between gap-2 bg-white rounded-lg px-3 py-2 border">
                      <span className="text-gray-500">Senha</span>
                      <span className="font-mono font-bold">{resultado.senha_temporaria}</span>
                      <Button size="sm" variant="ghost" onClick={() => copiar(resultado.senha_temporaria, 'senha')}>
                        {copiado === 'senha' ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                      </Button>
                    </div>
                  )}
                  <div className="flex items-center justify-between gap-2 bg-white rounded-lg px-3 py-2 border">
                    <span className="text-gray-500">Expira em</span>
                    <span className="font-medium">{fmtData(resultado.user?.plan_expires)}</span>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  {resultado.envios?.whatsapp && (
                    <span className={resultado.envios.whatsapp.ok ? 'text-emerald-700' : 'text-red-600'}>
                      {resultado.envios.whatsapp.ok ? '✓ WhatsApp enviado' : `✗ WhatsApp: ${resultado.envios.whatsapp.erro}`}
                    </span>
                  )}
                  {resultado.envios?.email && (
                    <span className={resultado.envios.email.ok ? 'text-emerald-700' : 'text-red-600'}>
                      {resultado.envios.email.ok ? '✓ E-mail enviado' : `✗ E-mail: ${resultado.envios.email.erro}`}
                    </span>
                  )}
                </div>
              </div>
              <Button variant="outline" className="w-full"
                      onClick={() => copiar(resultado.mensagem || '', 'msg')}>
                {copiado === 'msg' ? <Check className="w-4 h-4 mr-2 text-emerald-600" /> : <Copy className="w-4 h-4 mr-2" />}
                Copiar mensagem completa (para colar no WhatsApp)
              </Button>
              <DialogFooter>
                <Button variant="outline" onClick={() => { setResultado(null); setOpen(false); }}>
                  <X className="w-4 h-4 mr-2" /> Fechar
                </Button>
                <Button style={{ background: '#0C3320' }} className="text-white"
                        onClick={() => { setResultado(null); setForm(emptyForm()); }}>
                  <Plus className="w-4 h-4 mr-2" /> Criar outro
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-5">
              <div className="space-y-3">
                <Campo label="Nome do cliente">
                  <Input value={form.nome} onChange={(e) => set('nome', e.target.value)} placeholder="Cristiano Miola" />
                </Campo>
                <Campo label="E-mail (será o login) *"
                       hint="Se o e-mail já for cadastrado, o teste é liberado na conta existente — a senha dele é mantida.">
                  <Input type="email" value={form.email} onChange={(e) => set('email', e.target.value)}
                         placeholder="cliente@email.com" />
                </Campo>
                <Campo label="WhatsApp (com DDD)">
                  <Input value={form.telefone} onChange={(e) => set('telefone', e.target.value)} placeholder="5599991811246" />
                </Campo>

                <Campo label="Duração do teste" hint={`Expira em ${expiraEm} — o acesso é cortado sozinho.`}>
                  <div className="flex flex-wrap items-center gap-2">
                    {PRESETS_DIAS.map((d) => (
                      <button key={d} type="button" onClick={() => set('dias', d)}
                              className={`px-3 py-1.5 rounded-lg border text-sm ${
                                Number(form.dias) === d
                                  ? 'text-white border-transparent'
                                  : 'bg-white text-gray-700 border-gray-300 hover:border-gray-400'}`}
                              style={Number(form.dias) === d ? { background: '#0C3320' } : undefined}>
                        {d} dias
                      </button>
                    ))}
                    <div className="flex items-center gap-1">
                      <Input type="number" min={1} max={365} value={form.dias}
                             onChange={(e) => set('dias', e.target.value)} className="w-20" />
                      <span className="text-xs text-gray-500">dias</span>
                    </div>
                  </div>
                </Campo>

                <Campo label="Senha (opcional)" hint="Em branco, o sistema gera uma senha temporária.">
                  <Input value={form.senha} onChange={(e) => set('senha', e.target.value)} placeholder="gerar automaticamente" />
                </Campo>
                <Campo label="Observação (interna)">
                  <Input value={form.observacao} onChange={(e) => set('observacao', e.target.value)}
                         placeholder="Ex.: indicação do corretor João" />
                </Campo>

                <div className="space-y-2 pt-1">
                  <label className="flex items-center gap-2 text-sm text-gray-700">
                    <input type="checkbox" checked={form.enviar_whatsapp}
                           onChange={(e) => set('enviar_whatsapp', e.target.checked)} />
                    Enviar credenciais por WhatsApp (Z-API)
                  </label>
                  <label className="flex items-center gap-2 text-sm text-gray-700">
                    <input type="checkbox" checked={form.enviar_email}
                           onChange={(e) => set('enviar_email', e.target.checked)} />
                    Enviar credenciais por e-mail
                  </label>
                </div>
              </div>

              <div>
                <div className="text-xs text-gray-500 mb-2 flex items-center gap-1">
                  <CalendarClock className="w-3.5 h-3.5" /> Prévia da mensagem
                </div>
                <WhatsAppPreview mensagem={mensagemPreview} />
              </div>
            </div>
          )}

          {!resultado && (
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
              <Button onClick={criar} disabled={saving} style={{ background: '#0C3320' }} className="text-white">
                {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
                Liberar acesso {form.dias ? `de ${form.dias} dias` : ''}
              </Button>
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TrialsAdmin;
