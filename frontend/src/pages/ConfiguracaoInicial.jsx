// @page ConfiguracaoInicial — assistente pós-pagamento: guia o assinante pelo que
// falta configurar para os documentos saírem completos.
//
// NÃO duplica formulário: cada passo leva à tela real (Configurações, Certificados,
// Integrações). O progresso vem do servidor (/perfil-avaliador/completude), então
// ao voltar o item já aparece concluído — sem estado local para dessincronizar.
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2, Circle, ArrowRight, ArrowLeft, RefreshCw,
  PartyPopper, MessageCircle, AlertTriangle,
} from 'lucide-react';
import { perfilAPI } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { BrandSpinner } from '../components/brand/BrandSpinner';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';
const SUPORTE_WA = '5599991811246';

const ConfiguracaoInicial = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [passo, setPasso] = useState(0);
  const [pulados, setPulados] = useState([]);

  const carregar = useCallback(async () => {
    try { setDados(await perfilAPI.completude()); }
    catch (e) { toast({ title: 'Erro ao carregar', description: e.response?.data?.detail, variant: 'destructive' }); }
    finally { setCarregando(false); }
  }, [toast]);
  useEffect(() => { carregar(); }, [carregar]);

  if (carregando) return <div className="py-24 flex justify-center"><BrandSpinner label="Preparando…" /></div>;

  const itens = dados?.itens || [];
  const pendentes = itens.filter((i) => !i.ok && !pulados.includes(i.chave));
  const atual = pendentes[passo];
  const feitos = itens.filter((i) => i.ok).length;
  const faltamEssenciais = itens.filter((i) => i.essencial && !i.ok);

  const pular = () => {
    if (atual) setPulados((p) => [...p, atual.chave]);
    setPasso(0);
  };

  // ── Tela final ────────────────────────────────────────────────────────────
  if (!atual) {
    const tudoPronto = faltamEssenciais.length === 0;
    return (
      <div className="max-w-2xl mx-auto py-10 px-4">
        <div className="rounded-2xl p-8 text-center" style={{ background: GREEN, color: '#f3f1e6' }}>
          {tudoPronto ? (
            <>
              <PartyPopper className="w-10 h-10 mx-auto mb-3" style={{ color: GOLD }} />
              <h1 className="font-display text-2xl mb-2">Tudo pronto, pode emitir</h1>
              <p className="text-sm opacity-80">
                Seus laudos vão sair completos — com registro profissional, assinatura e seus dados.
              </p>
            </>
          ) : (
            <>
              <AlertTriangle className="w-10 h-10 mx-auto mb-3" style={{ color: GOLD }} />
              <h1 className="font-display text-2xl mb-2">Ainda falta o essencial</h1>
              <p className="text-sm opacity-80">
                Você pulou {faltamEssenciais.length} item(ns) que afetam o conteúdo do laudo.
                Dá para emitir assim mesmo — mas o documento sai incompleto.
              </p>
            </>
          )}
          <div className="mt-4 text-xs opacity-70">{feitos} de {itens.length} itens configurados</div>
        </div>

        {faltamEssenciais.length > 0 && (
          <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4">
            <div className="text-xs font-bold uppercase tracking-wider text-amber-700 mb-2">Pendentes</div>
            <ul className="space-y-1.5 text-sm text-amber-900">
              {faltamEssenciais.map((i) => (
                <li key={i.chave}>
                  <button onClick={() => nav(i.rota)} className="underline underline-offset-2 text-left">
                    {i.titulo}
                  </button>
                  <span className="block text-xs text-amber-700">{i.impacto}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-6 flex flex-wrap gap-3 justify-center">
          <button onClick={() => nav('/dashboard')} className="px-5 py-2.5 rounded-lg text-white text-sm" style={{ background: GREEN }}>
            Ir para o sistema
          </button>
          <button
            onClick={() => { setPulados([]); setPasso(0); carregar(); }}
            className="px-5 py-2.5 rounded-lg border text-sm flex items-center gap-1"
            style={{ borderColor: GOLD, color: GREEN }}
          >
            <RefreshCw className="w-4 h-4" /> Revisar pendentes
          </button>
          <a
            href={`https://wa.me/${SUPORTE_WA}?text=${encodeURIComponent('Olá! Preciso de ajuda para configurar minha conta no AvalieImob.')}`}
            target="_blank" rel="noreferrer"
            className="px-5 py-2.5 rounded-lg border text-sm flex items-center gap-1"
            style={{ borderColor: '#25D366', color: '#128C7E' }}
          >
            <MessageCircle className="w-4 h-4" /> Falar com o suporte
          </a>
        </div>
      </div>
    );
  }

  // ── Passo a passo ─────────────────────────────────────────────────────────
  const pct = Math.round((feitos / (itens.length || 1)) * 100);

  const veioDoPagamento = new URLSearchParams(window.location.search).get('payment') === 'success';

  return (
    <div className="max-w-2xl mx-auto py-10 px-4">
      {veioDoPagamento && (
        <div className="mb-5 rounded-xl p-4 text-center" style={{ background: GREEN, color: '#f3f1e6' }}>
          <div className="font-display text-lg">Pagamento aprovado — bem-vindo!</div>
          <div className="text-xs opacity-80 mt-1">
            Falta pouco: vamos configurar o que faz seus laudos saírem completos.
          </div>
        </div>
      )}

      <div className="mb-6">
        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
          <span>Configuração inicial</span>
          <span>{feitos} de {itens.length}</span>
        </div>
        <div className="h-1.5 rounded-full bg-gray-200 overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: GOLD }} />
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
            style={atual.essencial ? { background: '#fef3c7', color: '#92400e' } : { background: '#f3f4f6', color: '#6b7280' }}>
            {atual.essencial ? 'Essencial' : 'Complementar'}
          </span>
          <span className="text-xs text-gray-400">{atual.grupo}</span>
        </div>

        <h2 className="font-display text-xl mt-2" style={{ color: GREEN }}>{atual.titulo}</h2>

        <div className="mt-3 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2">
          <div className="text-[10px] font-bold uppercase tracking-wider text-amber-700">Se ficar em branco</div>
          <div className="text-sm text-amber-900 mt-0.5">{atual.impacto}</div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <button
            onClick={() => nav(atual.rota)}
            className="px-4 py-2 rounded-lg text-white text-sm flex items-center gap-1"
            style={{ background: GREEN }}
          >
            Configurar agora <ArrowRight className="w-4 h-4" />
          </button>
          <button onClick={pular} className="px-4 py-2 rounded-lg border border-gray-300 text-sm text-gray-600">
            Pular por enquanto
          </button>
          <button
            onClick={carregar}
            className="px-3 py-2 rounded-lg text-sm text-gray-500 flex items-center gap-1"
            title="Já configurei — atualizar"
          >
            <RefreshCw className="w-4 h-4" /> Já fiz
          </button>
        </div>

        <p className="mt-4 text-xs text-gray-400">
          Nada aqui bloqueia o sistema. Você pode pular tudo e configurar depois em Configurações.
        </p>
      </div>

      {/* Lista lateral compacta */}
      <div className="mt-5 rounded-xl border border-gray-200 bg-white divide-y divide-gray-100">
        {itens.map((i) => (
          <div key={i.chave} className="flex items-center gap-2 px-4 py-2 text-sm">
            {i.ok
              ? <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              : <Circle className="w-4 h-4 text-gray-300 flex-shrink-0" />}
            <span className={i.ok ? 'text-gray-400 line-through' : 'text-gray-700'}>{i.titulo}</span>
            {i.essencial && !i.ok && (
              <span className="ml-auto text-[10px] font-bold uppercase text-amber-600">essencial</span>
            )}
          </div>
        ))}
      </div>

      {pendentes.length > 1 && (
        <div className="mt-4 flex justify-between text-sm">
          <button
            onClick={() => setPasso((p) => Math.max(0, p - 1))}
            disabled={passo === 0}
            className="flex items-center gap-1 text-gray-500 disabled:opacity-30"
          >
            <ArrowLeft className="w-4 h-4" /> Anterior
          </button>
          <button
            onClick={() => setPasso((p) => Math.min(pendentes.length - 1, p + 1))}
            disabled={passo >= pendentes.length - 1}
            className="flex items-center gap-1 text-gray-500 disabled:opacity-30"
          >
            Próximo <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};

export default ConfiguracaoInicial;
