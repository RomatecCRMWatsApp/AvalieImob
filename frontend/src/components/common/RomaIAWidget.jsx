import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, Send, User, Loader2, ArrowRight, MessageCircle, PlayCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import RomaIAAvatar from './RomaIAAvatar';
import { BrandMark } from '../brand/BrandMark';
import { aiAPI, atendimentoAPI } from '../../lib/api';
import { FERRAMENTAS, useAberturaFerramenta, useNoPainel } from '../../lib/ferramentas';

/**
 * Roma_IA Chat Widget Flutuante
 * Disponível em todas as páginas (públicas e privadas)
 * Permite que visitantes conversem com a IA sem login
 */
// Fora do painel (site público) o chat é o ROBÔ DE ATENDIMENTO: explica a plataforma,
// qualifica o lead e encaminha ao José (POST /atendimento/*). Dentro do painel
// continua a Roma_IA técnica do assinante (POST /ai/chat).
const SAUDACAO_SITE = 'Olá! 👋 Sou a Roma_IA, atendente do AvalieImob. Posso explicar PTAM e laudos, perícia, georreferenciamento, usucapião, Arquivo ONR, contratos com assinatura pelo WhatsApp e os planos. Você é profissional da área ou precisa de um serviço?';
const SAUDACAO_PAINEL = 'Olá! Sou a Roma_IA, especialista em avaliação imobiliária. Como posso ajudar você hoje?';
const SUGESTOES = [
  'O que o AvalieImob faz?',
  'Quanto custa?',
  'Preciso de um laudo',
  'Georreferenciamento',
  'Arquivo ONR',
  'Contratos e assinatura',
];
const SID_ATEND = 'romatec_atendimento_sessao';
// Vídeo de ajuda: demonstração completa do PTAM em 12 passos (vertical, ~6 min).
const VIDEO_AJUDA = '/video/apresentacoes/AvalieImob_PTAM_Demonstracao_WhatsApp_Vertical_720x1280';

// Card do vídeo no início da conversa. O arquivo (18 MB) só carrega quando a pessoa toca.
function VideoAjuda() {
  const [aberto, setAberto] = useState(false);
  if (!aberto) {
    return (
      <button type="button" onClick={() => setAberto(true)}
        className="ml-9 flex w-[calc(100%-2.25rem)] items-center gap-3 rounded-xl border border-[#C9A84C] bg-[#0C3320] p-2.5 text-left text-white hover:brightness-110">
        <PlayCircle className="w-8 h-8 flex-shrink-0 text-[#E0C264]" />
        <span className="min-w-0">
          <span className="block text-xs font-bold">Veja como fazer um PTAM</span>
          <span className="block text-[11px] text-emerald-100">Vídeo de 6 min · os 12 passos, do cadastro à entrega</span>
        </span>
      </button>
    );
  }
  return (
    <div className="ml-9 rounded-xl overflow-hidden bg-black border border-[#C9A84C]">
      <video controls playsInline autoPlay preload="metadata" poster={`${VIDEO_AJUDA}.jpg`}
        aria-label="Demonstração do PTAM em 12 passos no AvalieImob"
        className="block w-full" style={{ aspectRatio: '9 / 16', maxHeight: '60vh', objectFit: 'contain' }}>
        <source src={`${VIDEO_AJUDA}.mp4`} type="video/mp4" />
        {/* Legenda já gravada na imagem: faixa opcional, sem default. */}
        <track kind="captions" srcLang="pt-BR" label="Português (Brasil)" src={`${VIDEO_AJUDA}.vtt`} />
      </video>
    </div>
  );
}

function sessaoAtendimento() {
  try {
    let sid = localStorage.getItem(SID_ATEND);
    if (!sid) {
      sid = `at_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
      localStorage.setItem(SID_ATEND, sid);
    }
    return sid;
  } catch {
    return `at_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  }
}

function origemVisita() {
  let utm = {};
  try { utm = JSON.parse(sessionStorage.getItem('utm_data') || '{}'); } catch { /* ignore */ }
  return {
    pagina: window.location.pathname,
    referrer: document.referrer || null,
    utm_source: utm.utm_source || null,
    utm_medium: utm.utm_medium || null,
    utm_campaign: utm.utm_campaign || null,
  };
}

const RomaIAWidget = () => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [hidden, setHidden] = useState(() => {
    try { return localStorage.getItem('romatec_widget_hidden') === '1'; } catch { return false; }
  });
  const ocultar = () => {
    setHidden(true); setShowWelcome(false); setIsOpen(false);
    try { localStorage.setItem('romatec_widget_hidden', '1'); } catch { /* ignore */ }
  };
  const mostrar = () => {
    setHidden(false);
    try { localStorage.removeItem('romatec_widget_hidden'); } catch { /* ignore */ }
  };
  // No painel o botão flutuante e a aba lateral saem: o chat abre pelo botão Ferramentas.
  const noPainel = useNoPainel();
  useAberturaFerramenta(FERRAMENTAS.ROMA_IA, useCallback(() => { setShowWelcome(false); setIsOpen(true); }, []));
  const atendimento = !noPainel;
  const [messages, setMessages] = useState([
    { role: 'assistant', content: SAUDACAO_SITE }
  ]);
  const [pedirContato, setPedirContato] = useState(false);
  const [contato, setContato] = useState({ nome: '', whatsapp: '', consentimento: false, website: '' });
  const [enviandoContato, setEnviandoContato] = useState(false);
  const [temContato, setTemContato] = useState(false);
  const historicoCarregado = useRef(false);
  const aberturaRegistrada = useRef(false);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const messagesEndRef = useRef(null);

  // Gera session ID único para visitantes
  useEffect(() => {
    let sid = localStorage.getItem('romatec_widget_session');
    if (!sid) {
      sid = `widget_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      localStorage.setItem('romatec_widget_session', sid);
    }
    setSessionId(sid);
  }, []);

  // Troca de modo (site ↔ painel): saudação certa para cada um.
  useEffect(() => {
    if (!atendimento) {
      setMessages([{ role: 'assistant', content: SAUDACAO_PAINEL }]);
      setPedirContato(false);
      historicoCarregado.current = false;
    }
  }, [atendimento]);

  // Site: retoma a conversa do robô ao abrir (o visitante pode voltar outro dia).
  useEffect(() => {
    if (!atendimento || !isOpen || historicoCarregado.current) return;
    historicoCarregado.current = true;
    const sid = sessaoAtendimento();
    if (!aberturaRegistrada.current) {
      aberturaRegistrada.current = true;
      atendimentoAPI.evento(sid, 'aberto').catch(() => {});
    }
    atendimentoAPI.sessao(sid).then((d) => {
      const msgs = (d.mensagens || []).map((m) => ({ role: m.role, content: m.content }));
      if (msgs.length > 1) {
        if (msgs.length && msgs[msgs.length - 1].role === 'assistant') msgs[msgs.length - 1].acoes = d.acoes || [];
        setMessages(msgs);
      }
      setTemContato(!!d.tem_contato);
    }).catch(() => {});
  }, [atendimento, isOpen]);

  // Scroll automático para última mensagem
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Mostra boas-vindas após 3 segundos na primeira visita
  useEffect(() => {
    const hasSeenWelcome = sessionStorage.getItem('romatec_widget_welcome');
    if (!hasSeenWelcome) {
      const timer = setTimeout(() => {
        setShowWelcome(true);
        sessionStorage.setItem('romatec_widget_welcome', 'true');
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, []);

  const sendMessage = async (text) => {
    const content = text || input;
    if (!content.trim() || loading || !sessionId) return;

    setMessages(m => [...m.map(x => ({ ...x, acoes: undefined })), { role: 'user', content }]);
    setInput('');
    setLoading(true);

    try {
      if (atendimento) {
        const res = await atendimentoAPI.mensagem({ sessao_id: sessaoAtendimento(), mensagem: content.slice(0, 800), ...origemVisita() });
        setMessages(m => [...m, { role: 'assistant', content: res.resposta, acoes: res.acoes || [] }]);
        setTemContato(!!res.tem_contato);
        setPedirContato(!!res.pedir_contato && !res.tem_contato);
      } else {
        const res = await aiAPI.chat(sessionId, content);
        setMessages(m => [...m, { role: 'assistant', content: res.reply, provider: res.provider }]);
      }
    } catch (e) {
      const limite = e?.response?.status === 429;
      setMessages(m => [...m, {
        role: 'assistant',
        content: limite
          ? 'Muitas mensagens seguidas. Aguarde um instante e tente de novo, por favor.'
          : 'Desculpe, estou tendo dificuldades técnicas. Por favor, tente novamente em alguns instantes.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  const clicarAcao = (a) => {
    const evento = { cadastro: 'clique_cadastro', planos: 'clique_planos', whatsapp: 'clique_whatsapp' }[a.tipo];
    if (evento) atendimentoAPI.evento(sessaoAtendimento(), evento).catch(() => {});
    if (/^https?:/.test(a.url)) {
      window.open(a.url, '_blank', 'noopener');
    } else {
      setIsOpen(false);
      navigate(a.url);
    }
  };

  const enviarContato = async (e) => {
    e.preventDefault();
    if (!contato.nome.trim() || contato.whatsapp.replace(/\D/g, '').length < 10) {
      setMessages(m => [...m, { role: 'assistant', content: 'Me passa seu nome e o WhatsApp com DDD, por favor.' }]);
      return;
    }
    if (!contato.consentimento) {
      setMessages(m => [...m, { role: 'assistant', content: 'Para o José te chamar, marque a autorização de contato (LGPD).' }]);
      return;
    }
    setEnviandoContato(true);
    try {
      const res = await atendimentoAPI.contato({ sessao_id: sessaoAtendimento(), ...contato });
      setMessages(m => [...m.map(x => ({ ...x, acoes: undefined })), { role: 'assistant', content: res.resposta, acoes: res.acoes || [] }]);
      setTemContato(true);
      setPedirContato(false);
    } catch (err) {
      const msg = err?.response?.data?.detail;
      setMessages(m => [...m, { role: 'assistant', content: typeof msg === 'string' ? msg : 'Não consegui registrar agora. Tente de novo em instantes.' }]);
    } finally {
      setEnviandoContato(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([{ role: 'assistant', content: atendimento ? SAUDACAO_SITE : SAUDACAO_PAINEL }]);
    setPedirContato(false);
    if (atendimento) {
      try { localStorage.removeItem(SID_ATEND); } catch { /* ignore */ }
      setTemContato(false);
    }
    const newSid = `widget_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    localStorage.setItem('romatec_widget_session', newSid);
    setSessionId(newSid);
  };

  return (
    <>
      {/* Aba discreta para reexibir quando oculto */}
      {!noPainel && hidden && !isOpen && (
        <button
          onClick={mostrar}
          className="fixed top-1/2 right-0 z-[90] bg-emerald-900/90 hover:bg-emerald-800 text-white text-xs font-bold uppercase tracking-[1.5px] px-[7px] py-[14px] rounded-l-[10px] shadow-lg"
          title="Mostrar Roma_IA"
          style={{ writingMode: 'vertical-rl', transform: 'translateY(-50%) rotate(180deg)' }}
        >
          Roma_IA
        </button>
      )}

      {/* Botão Flutuante - Responsivo para Mobile */}
      {!noPainel && !isOpen && !hidden && (
        <div className="fixed top-1/2 -translate-y-1/2 right-3 sm:right-4 z-[100] group">
          <button
            onClick={() => setIsOpen(true)}
            onTouchStart={() => setIsOpen(true)}
            className="touch-manipulation block"
            aria-label="Abrir chat com Roma_IA"
            style={{ WebkitTapHighlightColor: 'transparent' }}
          >
            <div className="relative">
              <div className="absolute inset-0 bg-emerald-500 rounded-full animate-ping opacity-30"></div>
              <div className="relative rounded-full shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-110 active:scale-95">
                <BrandMark variant="circle" size={60} state={loading ? 'thinking' : 'idle'} title="Roma_IA" className="block" />
              </div>
              {/* Badge de notificação */}
              {showWelcome && (
                <div className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white text-xs font-bold animate-bounce">
                  1
                </div>
              )}
            </div>
          </button>
          {/* Botão ocultar */}
          <button
            onClick={ocultar}
            aria-label="Ocultar Roma_IA"
            title="Ocultar assistente"
            className="absolute -top-1 -left-1 w-5 h-5 bg-gray-800/85 hover:bg-gray-900 text-white rounded-full flex items-center justify-center z-[101] shadow"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Tooltip de boas-vindas - Responsivo */}
      {!noPainel && showWelcome && !isOpen && !hidden && (
        <div 
          className="fixed top-1/2 -translate-y-1/2 right-20 sm:right-24 z-[99] bg-white rounded-xl shadow-lg p-3 sm:p-4 max-w-[260px] sm:max-w-xs animate-fade-in-up cursor-pointer"
          onClick={() => {
            setIsOpen(true);
            setShowWelcome(false);
          }}
          onTouchStart={() => {
            setIsOpen(true);
            setShowWelcome(false);
          }}
        >
          <div className="flex items-start gap-2 sm:gap-3">
            <RomaIAAvatar state="speaking" size="sm" />
            <div>
              <p className="text-sm font-medium text-gray-900">Olá! Sou a Roma_IA 👋</p>
              <p className="text-xs text-gray-500 mt-1">Tire suas dúvidas sobre PTAM, laudos, georreferenciamento, ONR e contratos.</p>
            </div>
          </div>
          <div className="absolute top-1/2 -translate-y-1/2 right-[-8px] w-4 h-4 bg-white rotate-45"></div>
        </div>
      )}

      {/* Chat Window - Responsivo para Mobile */}
      {isOpen && (
        <div className="fixed inset-0 sm:inset-auto sm:top-20 sm:right-4 lg:top-24 lg:right-6 z-[1100] sm:w-96 sm:max-w-[calc(100vw-2rem)] sm:max-h-[calc(100vh-6rem)]">
          <div className="bg-white sm:rounded-2xl shadow-2xl overflow-hidden border-0 sm:border border-gray-200 h-full sm:h-auto flex flex-col">
            {/* Header */}
            <div className="bg-emerald-900 p-3 sm:p-4 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-2 sm:gap-3">
                <BrandMark variant="circle" size={32} state={loading ? 'thinking' : 'idle'} title="Roma_IA" />
                <div>
                  <h3 className="text-white font-semibold text-sm">Roma_IA</h3>
                  <p className="text-emerald-200 text-xs">{atendimento ? 'Atendimento AvalieImob · online' : 'Especialista NBR 14.653'}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  onClick={clearChat}
                  className="text-emerald-200 hover:text-white text-xs px-2 py-1 rounded hover:bg-white/10 transition-colors"
                  title="Nova conversa"
                >
                  Limpar
                </button>
                <button 
                  onClick={() => setIsOpen(false)}
                  className="text-white hover:bg-white/10 p-1 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 sm:h-80 overflow-y-auto p-3 sm:p-4 space-y-3 sm:space-y-4 bg-gray-50">
              {messages.map((m, i) => (
                <div 
                  key={i} 
                  className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex-shrink-0 flex items-center justify-center ${m.role === 'user' ? 'bg-amber-500' : ''}`}>
                    {m.role === 'user' ? (
                      <User className="w-3 h-3 sm:w-4 sm:h-4 text-white" />
                    ) : (
                      <RomaIAAvatar state="idle" size="sm" />
                    )}
                  </div>
                  <div className="max-w-[80%] min-w-0">
                    <div className={`rounded-xl p-2 sm:p-3 text-sm whitespace-pre-wrap break-words ${m.role === 'user' ? 'bg-emerald-600 text-white' : 'bg-white text-gray-800 shadow-sm'}`}>
                      {m.content}
                      {m.role === 'assistant' && m.provider && (
                        <span className="block text-[10px] opacity-50 mt-1">via {m.provider}</span>
                      )}
                    </div>
                    {m.role === 'assistant' && m.acoes?.length > 0 && (
                      <div className="mt-2 flex flex-col gap-1.5">
                        {m.acoes.map((a) => (
                          <button key={a.tipo} type="button" onClick={() => clicarAcao(a)}
                            className={`flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-left transition ${
                              a.tipo === 'cadastro' ? 'bg-[#C9A84C] text-[#0C3320] hover:brightness-105'
                                : a.tipo === 'whatsapp' ? 'bg-[#25D366] text-white hover:brightness-95'
                                  : 'bg-white border border-emerald-200 text-emerald-900 hover:bg-emerald-50'}`}>
                            <span className="flex items-center gap-1.5">
                              {a.tipo === 'whatsapp' && <MessageCircle className="w-3.5 h-3.5" />}
                              {a.label}
                            </span>
                            <ArrowRight className="w-3.5 h-3.5 flex-shrink-0" />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex gap-2">
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full flex-shrink-0">
                    <RomaIAAvatar state="thinking" size="sm" />
                  </div>
                  <div className="bg-white rounded-xl p-2 sm:p-3 flex items-center gap-2 shadow-sm">
                    <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
                    <span className="text-sm text-gray-500">Pensando...</span>
                  </div>
                </div>
              )}
              {!loading && messages.length <= 1 && <VideoAjuda />}
              {atendimento && !loading && messages.length <= 1 && (
                <div className="flex flex-wrap gap-1.5 pl-9">
                  {SUGESTOES.map((t) => (
                    <button key={t} type="button" onClick={() => sendMessage(t)}
                      className="rounded-full border border-emerald-300 bg-white px-3 py-1 text-xs text-emerald-900 hover:bg-emerald-50">
                      {t}
                    </button>
                  ))}
                </div>
              )}
              {atendimento && pedirContato && !temContato && (
                <form onSubmit={enviarContato} className="ml-9 rounded-xl border border-[#C9A84C] bg-[#FFFBEB] p-3 space-y-2">
                  <p className="text-xs font-semibold text-[#0C3320]">Deixe seu contato que o José te chama no WhatsApp:</p>
                  <input value={contato.nome} onChange={(e) => setContato(c => ({ ...c, nome: e.target.value }))}
                    placeholder="Seu nome" maxLength={120}
                    className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm" />
                  <input value={contato.whatsapp} onChange={(e) => setContato(c => ({ ...c, whatsapp: e.target.value }))}
                    placeholder="WhatsApp com DDD" inputMode="tel" maxLength={20}
                    className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm" />
                  <input value={contato.website} onChange={(e) => setContato(c => ({ ...c, website: e.target.value }))}
                    name="website" tabIndex={-1} autoComplete="off" aria-hidden="true"
                    style={{ position: 'absolute', left: '-9999px', width: 1, height: 1, opacity: 0 }} />
                  <label className="flex items-start gap-2 text-[11px] text-gray-600">
                    <input type="checkbox" checked={contato.consentimento}
                      onChange={(e) => setContato(c => ({ ...c, consentimento: e.target.checked }))} className="mt-0.5" />
                    <span>Autorizo o contato pelo WhatsApp sobre o meu atendimento (LGPD).</span>
                  </label>
                  <button type="submit" disabled={enviandoContato}
                    className="w-full rounded-lg bg-[#0C3320] py-2 text-xs font-semibold text-white disabled:opacity-60">
                    {enviandoContato ? 'Enviando…' : 'Quero ser atendido'}
                  </button>
                </form>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-3 border-t border-gray-200 bg-white flex-shrink-0">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Digite sua pergunta..."
                  maxLength={800}
                  className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                  disabled={loading}
                />
                <button
                  onClick={() => sendMessage()}
                  disabled={loading || !input.trim()}
                  className="bg-emerald-900 hover:bg-emerald-800 disabled:bg-gray-300 text-white p-2 rounded-lg transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
              <p className="text-[10px] text-gray-400 mt-2 text-center">
                {atendimento ? 'Atendimento automático · o José assume quando você quiser fechar' : 'Powered by Roma_IA · Groq / Gemini / Claude / OpenAI'}
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default RomaIAWidget;
