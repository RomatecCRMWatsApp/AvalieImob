// @page admin/E-mail — diagnóstico da configuração + teste de envio (validação ponta-a-ponta).
import React, { useEffect, useState, useCallback } from 'react';
import { Mail, CheckCircle2, XCircle, Send, RefreshCw, Server, Sparkles, Users } from 'lucide-react';
import { adminAPI } from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../hooks/use-toast';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';

const Chip = ({ ok, label }) => (
  <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full ${
    ok ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
       : 'bg-gray-100 text-gray-500 border border-gray-200'}`}>
    {ok ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />} {label}
  </span>
);

export default function EmailDiagnostico() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [to, setTo] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [welcomeTo, setWelcomeTo] = useState('');
  const [welcomeBusy, setWelcomeBusy] = useState(false);

  const carregar = useCallback(async () => {
    setLoading(true);
    try { setStatus(await adminAPI.emailStatus()); }
    catch { toast({ title: 'Erro ao carregar status', variant: 'destructive' }); }
    finally { setLoading(false); }
  }, [toast]);

  useEffect(() => { carregar(); }, [carregar]);
  useEffect(() => { if (user?.email && !to) setTo(user.email); }, [user, to]);

  const enviarTeste = async () => {
    setResultado(null);
    setEnviando(true);
    try {
      const r = await adminAPI.emailTest(to.trim());
      setResultado(r);
      if (r.ok) toast({ title: 'E-mail de teste enviado ✓', description: `via ${r.provider} → ${r.to}` });
      else toast({ title: 'Falha no envio', description: r.error, variant: 'destructive' });
    } catch (e) {
      const err = e?.response?.data?.detail || e?.message || 'Erro ao enviar.';
      setResultado({ ok: false, error: err });
      toast({ title: 'Falha no envio', description: err, variant: 'destructive' });
    } finally { setEnviando(false); }
  };

  const enviarBoasVindas = async ({ all }) => {
    if (all && !window.confirm('Enviar o e-mail de boas-vindas para TODOS os usuários cadastrados?')) return;
    setWelcomeBusy(true);
    try {
      const body = all ? { all: true } : { to: welcomeTo.trim() };
      const r = await adminAPI.emailWelcome(body);
      toast({
        title: 'Boas-vindas enviadas ✓',
        description: `${r.enviados} destinatário(s)${all ? ' (todos os cadastrados)' : ''}.`,
      });
    } catch (e) {
      toast({
        title: 'Falha ao enviar',
        description: e?.response?.data?.detail || e?.message || 'Erro.',
        variant: 'destructive',
      });
    } finally { setWelcomeBusy(false); }
  };

  const configurado = status?.configured;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <header className="flex items-start gap-3 mb-6">
        <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: GREEN }}>
          <Mail className="w-6 h-6" style={{ color: GOLD }} />
        </div>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: GREEN }}>Configuração de E-mail</h1>
          <p className="text-sm text-gray-500">
            Valide o envio de e-mails — inclusive o link de <strong>redefinição de senha</strong> dos clientes.
          </p>
        </div>
      </header>

      {/* Status */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 mb-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold flex items-center gap-2" style={{ color: GREEN }}>
            <Server className="w-4 h-4" /> Status atual
          </h2>
          <button onClick={carregar} className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg border text-gray-600 hover:bg-gray-50">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Atualizar
          </button>
        </div>
        {loading ? (
          <p className="text-sm text-gray-400">Carregando…</p>
        ) : (
          <>
            <div className={`rounded-xl p-3 mb-4 text-sm ${configurado
              ? 'bg-emerald-50 border border-emerald-100 text-emerald-800'
              : 'bg-amber-50 border border-amber-100 text-amber-800'}`}>
              {configurado
                ? <>✅ E-mail configurado via <strong>{status.provider}</strong>. Remetente: <strong>{status.from_email || '—'}</strong>.</>
                : <>⚠️ <strong>Nenhum provedor configurado</strong> — hoje o sistema só registra no log e <strong>não envia</strong>. Configure as variáveis abaixo no Railway.</>}
            </div>
            <div className="flex flex-wrap gap-2">
              <Chip ok={status.provider === 'SendGrid'} label="SendGrid" />
              <Chip ok={status.provider === 'SMTP'} label="SMTP" />
              <Chip ok={status.smtp_user_set} label="SMTP_USER" />
              <Chip ok={status.smtp_pass_set} label="SMTP_PASS" />
              <Chip ok={status.sendgrid_key_set} label="SENDGRID_API_KEY" />
              <Chip ok={!!status.from_email} label="FROM_EMAIL" />
            </div>
            {status.smtp_host && (
              <p className="text-xs text-gray-400 mt-3 font-mono">SMTP: {status.smtp_host}:{status.smtp_port}</p>
            )}
          </>
        )}
      </div>

      {/* Teste */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 mb-5">
        <h2 className="font-semibold mb-3" style={{ color: GREEN }}>Enviar e-mail de teste</h2>
        <div className="flex flex-col sm:flex-row gap-2">
          <input type="email" value={to} onChange={(e) => setTo(e.target.value)}
            placeholder="seu@email.com" className="flex-1 border rounded-lg px-3 py-2 text-sm" />
          <button onClick={enviarTeste} disabled={enviando || !to.trim()}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-50"
            style={{ background: GREEN }}>
            <Send className="w-4 h-4" /> {enviando ? 'Enviando…' : 'Enviar teste'}
          </button>
        </div>
        {resultado && (
          <div className={`mt-3 rounded-lg p-3 text-sm ${resultado.ok
            ? 'bg-emerald-50 border border-emerald-100 text-emerald-800'
            : 'bg-red-50 border border-red-100 text-red-700'}`}>
            {resultado.ok
              ? <>✓ Enviado via <strong>{resultado.provider}</strong> para <strong>{resultado.to}</strong>. Confira a caixa de entrada (e o spam).</>
              : <>✗ <strong>Falhou:</strong> <span className="font-mono break-all">{resultado.error}</span></>}
          </div>
        )}
      </div>

      {/* Boas-vindas */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 mb-5">
        <h2 className="font-semibold mb-1 flex items-center gap-2" style={{ color: GREEN }}>
          <Sparkles className="w-4 h-4" style={{ color: GOLD }} /> E-mail de boas-vindas
        </h2>
        <p className="text-xs text-gray-500 mb-3">
          Mensagem completa apresentando <strong>todos os módulos</strong> da plataforma. Reenvie para
          um cliente específico ou dispare para <strong>todos os já cadastrados</strong> (no e-mail de cadastro de cada um).
        </p>
        <div className="flex flex-col sm:flex-row gap-2">
          <input type="email" value={welcomeTo} onChange={(e) => setWelcomeTo(e.target.value)}
            placeholder="email-do-cliente@exemplo.com" className="flex-1 border rounded-lg px-3 py-2 text-sm" />
          <button onClick={() => enviarBoasVindas({ all: false })} disabled={welcomeBusy || !welcomeTo.trim()}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-50"
            style={{ background: GREEN }}>
            <Send className="w-4 h-4" /> {welcomeBusy ? 'Enviando…' : 'Enviar a este e-mail'}
          </button>
        </div>
        <button onClick={() => enviarBoasVindas({ all: true })} disabled={welcomeBusy}
          className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-50"
          style={{ background: GOLD }}>
          <Users className="w-4 h-4" /> {welcomeBusy ? 'Enviando…' : 'Enviar para todos os cadastrados'}
        </button>
      </div>

      {/* Guia */}
      <div className="rounded-2xl border border-gray-200 bg-gray-50 p-5 text-sm text-gray-600">
        <h2 className="font-semibold mb-2" style={{ color: GREEN }}>Como configurar (Railway → Variables)</h2>
        <p className="mb-3">Escolha <strong>uma</strong> das opções e adicione as variáveis no serviço do Railway (depois faça um redeploy):</p>
        <p className="font-semibold text-gray-700 mb-1">Opção A — SMTP (e-mail do seu domínio)</p>
        <pre className="bg-white border rounded-lg p-3 text-xs overflow-x-auto mb-3">{`SMTP_HOST=smtp.seuprovedor.com
SMTP_PORT=587
SMTP_USER=contato@romatecavalieimob.com.br
SMTP_PASS=sua-senha-ou-app-password
FROM_EMAIL=contato@romatecavalieimob.com.br`}</pre>
        <p className="font-semibold text-gray-700 mb-1">Opção B — SendGrid (grátis até 100/dia)</p>
        <pre className="bg-white border rounded-lg p-3 text-xs overflow-x-auto mb-3">{`SENDGRID_API_KEY=SG.xxxxxxxx
FROM_EMAIL=contato@romatecavalieimob.com.br`}</pre>
        <p className="text-xs text-gray-500">
          Dica: o remetente (<code>FROM_EMAIL</code>) precisa ser um endereço <strong>verificado</strong> no provedor,
          senão o e-mail é recusado ou cai no spam. Após setar, clique em <em>Atualizar</em> e depois <em>Enviar teste</em>.
        </p>
      </div>
    </div>
  );
}
