// @component admin/ReativacaoCard — campanha de reativação dos cadastros que não ativaram.
// Sequência de 4 e-mails (dias 1/3/7/14) e para. Lê a fila direto da base de
// usuários: quem ativa sai sozinho, quem se cadastra entra sozinho.
import React, { useCallback, useEffect, useState } from 'react';
import { UserCheck, Send, Loader2, RefreshCw, Mail } from 'lucide-react';
import { reativacaoAPI } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';

const ReativacaoCard = () => {
  const { toast } = useToast();
  const [st, setSt] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [rodando, setRodando] = useState(false);
  const [teste, setTeste] = useState('');
  const [testeEtapa, setTesteEtapa] = useState(0);
  const [testePerfil, setTestePerfil] = useState('nunca');

  const carregar = useCallback(async () => {
    setCarregando(true);
    try { setSt(await reativacaoAPI.status()); }
    catch (e) {
      // Sem `detail` o toast não dizia nada — mostra status HTTP ou erro de rede.
      const det = e.response?.data?.detail
        || (e.response ? `HTTP ${e.response.status}` : e.message || 'sem resposta do servidor');
      toast({ title: 'Erro ao carregar reativação', description: det, variant: 'destructive' });
    }
    finally { setCarregando(false); }
  }, [toast]);
  useEffect(() => { carregar(); }, [carregar]);

  const cfg = st?.config || {};

  const salvar = async (campos) => {
    setSalvando(true);
    try {
      await reativacaoAPI.salvarConfig(campos);
      await carregar();
      toast({ title: 'Configuração salva' });
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSalvando(false); }
  };

  const enviarTeste = async () => {
    if (!teste.includes('@')) return toast({ title: 'Informe um e-mail válido', variant: 'destructive' });
    try {
      const r = await reativacaoAPI.enviarTeste({ email: teste.trim(), etapa: testeEtapa, perfil: testePerfil });
      toast({ title: `Etapa ${r.etapa} enviada`, description: r.assunto });
    } catch (e) {
      toast({ title: 'Falha no envio', description: e.response?.data?.detail, variant: 'destructive' });
    }
  };

  const rodarAgora = async () => {
    if (!window.confirm(`Enviar agora para ${st?.na_fila_agora ?? 0} pessoa(s) na fila?`)) return;
    setRodando(true);
    try {
      const r = await reativacaoAPI.rodarAgora({});
      toast({ title: `${r.enviados} e-mail(s) enviados` });
      carregar();
    } catch (e) {
      toast({ title: 'Erro ao disparar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setRodando(false); }
  };

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 mb-5">
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <h2 className="font-semibold flex items-center gap-2" style={{ color: GREEN }}>
          <UserCheck className="w-4 h-4" style={{ color: GOLD }} /> Reativação — cadastrados que não assinaram
        </h2>
        <button onClick={carregar} className="text-xs flex items-center gap-1 text-gray-500 hover:text-gray-700">
          <RefreshCw className="w-3 h-3" /> Atualizar
        </button>
      </div>

      <p className="text-xs text-gray-500 mb-4">
        Sequência de <strong>4 e-mails</strong> (dias {(st?.etapas_dias || [1, 3, 7, 14]).join(', ')} após o cadastro) e
        depois <strong>para</strong>. Quem ativa a assinatura sai da fila automaticamente; quem se cadastra entra sozinho.
        Envio diário indefinido não é usado de propósito — queimaria a reputação do domínio e derrubaria junto os
        e-mails de senha e de pagamento.
      </p>

      {carregando ? (
        <div className="py-8 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-gray-400" /></div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            {[
              ['Na fila agora', st?.na_fila_agora ?? 0, GOLD],
              ['Cadastrados sem plano', st?.total_inativos ?? 0, '#6B8072'],
              ['Descadastraram', st?.descadastrados ?? 0, '#b91c1c'],
              ['Disparo', cfg.ativo ? `${cfg.hora}h` : 'desligado', cfg.ativo ? '#1E6B38' : '#999'],
            ].map(([label, valor, cor]) => (
              <div key={label} className="rounded-lg border border-gray-200 px-3 py-2">
                <div className="font-display text-xl font-bold leading-none" style={{ color: cor }}>{valor}</div>
                <div className="text-[10px] text-gray-500 mt-1">{label}</div>
              </div>
            ))}
          </div>

          {/* Quem receberia agora */}
          {(st?.destinatarios || []).length > 0 && (
            <div className="mb-4 rounded-lg bg-amber-50 border border-amber-200 p-3">
              <div className="text-[11px] font-bold uppercase tracking-wider text-amber-700 mb-1">
                Receberiam no próximo disparo
              </div>
              <ul className="text-xs text-amber-900 space-y-0.5 max-h-32 overflow-y-auto">
                {st.destinatarios.map((d) => (
                  <li key={d.email}>• {d.nome || d.email} <span className="text-amber-600">— etapa {d.etapa}</span></li>
                ))}
              </ul>
            </div>
          )}

          {/* Automático */}
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={!!cfg.ativo}
                disabled={salvando}
                onChange={(e) => salvar({ ativo: e.target.checked })}
              />
              Disparo automático diário
            </label>
            <label className="text-sm flex items-center gap-1">
              às
              <select
                className="border border-gray-300 rounded px-2 py-1 text-sm"
                value={cfg.hora ?? 9}
                onChange={(e) => salvar({ hora: Number(e.target.value) })}
              >
                {Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{h}h</option>)}
              </select>
              (Brasília)
            </label>
            <label className="text-sm flex items-center gap-1">
              máx.
              <input
                type="number" min={1} max={200}
                className="border border-gray-300 rounded px-2 py-1 text-sm w-20"
                defaultValue={cfg.limite_dia ?? 50}
                onBlur={(e) => salvar({ limite_dia: Number(e.target.value) })}
              />
              e-mails/dia
            </label>
            <button
              onClick={rodarAgora}
              disabled={rodando || !st?.na_fila_agora}
              className="ml-auto text-sm px-3 py-1.5 rounded-lg text-white flex items-center gap-1 disabled:opacity-40"
              style={{ background: GREEN }}
            >
              {rodando ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
              Enviar agora
            </button>
          </div>

          {/* Teste */}
          <div className="border-t border-gray-100 pt-3">
            <div className="text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">
              Testar o texto antes
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={teste} onChange={(e) => setTeste(e.target.value)}
                placeholder="seu@email.com"
                className="border border-gray-300 rounded px-3 py-1.5 text-sm flex-1 min-w-[200px]"
              />
              <select
                className="border border-gray-300 rounded px-2 py-1.5 text-sm"
                value={testeEtapa} onChange={(e) => setTesteEtapa(Number(e.target.value))}
              >
                {(st?.etapas_dias || [1, 3, 7, 14]).map((d, i) => (
                  <option key={i} value={i}>Etapa {i + 1} (dia {d})</option>
                ))}
              </select>
              <select
                className="border border-gray-300 rounded px-2 py-1.5 text-sm"
                value={testePerfil} onChange={(e) => setTestePerfil(e.target.value)}
              >
                <option value="nunca">Nunca acessou</option>
                <option value="checkout">Parou no checkout</option>
              </select>
              <button
                onClick={enviarTeste}
                className="text-sm px-3 py-1.5 rounded-lg border flex items-center gap-1"
                style={{ borderColor: GOLD, color: GREEN }}
              >
                <Mail className="w-3.5 h-3.5" /> Enviar teste
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ReativacaoCard;
