import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Wand2, Loader2, X } from 'lucide-react';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { useToast } from '../../hooks/use-toast';
import { aiAPI } from '../../lib/api';
import RomaIAAvatar from '../common/RomaIAAvatar';

const SUGGESTIONS = [
  { id: 'aperfeicoar', icon: Wand2, title: 'Aperfeiçoar laudo', prompt: 'Aperfeiçoe este texto técnico de um laudo de avaliação imobiliária pelo método comparativo direto: "O imóvel avaliado possui 85m² em boa localização e apresenta-se em bom estado de conservação."' },
  { id: 'fundamentacao', icon: Wand2, title: 'Gerar fundamentação', prompt: 'Gere a fundamentação técnica para um PTAM de apartamento de 85m² em São Luís/MA com 6 amostras pelo Método Comparativo Direto de Dados de Mercado.' },
  { id: 'swot', icon: Wand2, title: 'Análise SWOT rural', prompt: 'Faça uma análise SWOT de uma fazenda de 2500 hectares em Balsas/MA para fins de garantia bancária.' },
  { id: 'memorial', icon: Wand2, title: 'Memorial descritivo', prompt: 'Elabore um memorial descritivo completo para laudo de avaliação de safra de soja como garantia de crédito rural.' },
];

// Session id persisted so conversation survives refresh
const getSessionId = () => {
  let sid = localStorage.getItem('romatec_ai_session');
  if (!sid) {
    sid = `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    localStorage.setItem('romatec_ai_session', sid);
  }
  return sid;
};

const AIAssistant = () => {
  const { toast } = useToast();
  const [sessionId] = useState(getSessionId);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Olá! Sou a Roma_IA, especialista em PTAM e laudos técnicos conforme a NBR 14.653. Posso aperfeiçoar textos, gerar fundamentações, elaborar memórias de cálculo e análises técnicas. Como posso ajudar?' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [avatarState, setAvatarState] = useState('idle');
  const [showWelcomeModal, setShowWelcomeModal] = useState(false);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  // Atualiza estado do avatar baseado no loading
  useEffect(() => {
    if (loading) {
      setAvatarState('thinking');
    } else if (messages.length > 1 && messages[messages.length - 1].role === 'assistant') {
      setAvatarState('speaking');
      // Volta para idle após 3 segundos
      const timer = setTimeout(() => setAvatarState('idle'), 3000);
      return () => clearTimeout(timer);
    } else {
      setAvatarState('idle');
    }
  }, [loading, messages]);

  // Load history on mount
  useEffect(() => {
    aiAPI.history(sessionId).then((hist) => {
      if (hist && hist.length > 0) {
        setMessages(hist.map(h => ({ role: h.role, content: h.content, provider: h.provider })));
      }
    }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const send = async (text) => {
    const content = text || input;
    if (!content.trim() || loading) return;
    setMessages(m => [...m, { role: 'user', content }]);
    setInput('');
    setLoading(true);
    try {
      const res = await aiAPI.chat(sessionId, content);
      setMessages(m => [...m, { role: 'assistant', content: res.reply, provider: res.provider }]);
    } catch (e) {
      toast({ title: 'Erro na IA', description: e.response?.data?.detail || 'Tente novamente', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const newSession = () => {
    localStorage.removeItem('romatec_ai_session');
    window.location.reload();
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6 flex items-start justify-between">
        <div className="flex items-center gap-3 cursor-pointer group" onClick={() => setShowWelcomeModal(true)}>
          <div className="relative">
            <RomaIAAvatar state={avatarState} size="md" />
            <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="text-[10px] text-white">👋</span>
            </div>
          </div>
          <div>
            <h1 className="font-display text-3xl font-bold text-gray-900 group-hover:text-emerald-700 transition-colors">Roma_IA</h1>
            <p className="text-gray-600">Especialista NBR 14.653 · Groq / Gemini / Claude / OpenAI</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={newSession}>Nova conversa</Button>
      </div>

      {messages.length <= 1 && (
        <div className="grid sm:grid-cols-2 gap-3 mb-6">
          {SUGGESTIONS.map((s) => {
            const Icon = s.icon;
            return (
              <button key={s.id} onClick={() => send(s.prompt)} className="text-left p-4 bg-white rounded-xl border border-gray-200 hover:border-emerald-900/30 hover:shadow-md transition">
                <div className="flex items-center gap-2 mb-1"><Icon className="w-4 h-4 text-emerald-700" /><div className="font-semibold text-sm text-gray-900">{s.title}</div></div>
                <div className="text-xs text-gray-500 line-clamp-2">{s.prompt}</div>
              </button>
            );
          })}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 flex flex-col h-[500px]">
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map((m, i) => (
            <div key={`${m.role}-${i}-${m.content.slice(0, 20)}`} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${m.role === 'user' ? 'bg-amber-500 text-white' : ''}`}>
                {m.role === 'user' ? <User className="w-4 h-4" /> : <RomaIAAvatar state={avatarState} size="sm" />}
              </div>
              <div className="group relative max-w-[80%]">
                <div className={`rounded-xl p-3 text-sm whitespace-pre-wrap ${m.role === 'user' ? 'bg-emerald-50 text-gray-900' : 'bg-gray-50 text-gray-800'}`}>{m.content}</div>
                {m.role === 'assistant' && m.provider && (
                  <span className="absolute bottom-[-16px] left-1 text-[10px] text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">via {m.provider}</span>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-3"><div className="w-8 h-8 rounded-full flex-shrink-0"><RomaIAAvatar state="thinking" size="sm" /></div><div className="bg-gray-50 rounded-xl p-3 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin text-emerald-700" /><span className="text-sm text-gray-500">Pensando...</span></div></div>
          )}
          <div ref={endRef} />
        </div>
        <div className="border-t border-gray-100 p-3">
          <div className="flex gap-2">
            <Textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder="Descreva o que deseja aperfeiçoar ou gerar..." className="min-h-[60px] resize-none" disabled={loading} />
            <Button onClick={() => send()} disabled={loading || !input.trim()} className="bg-emerald-900 hover:bg-emerald-800 text-white h-auto"><Send className="w-4 h-4" /></Button>
          </div>
          <div className="text-[11px] text-gray-400 mt-2">Roma_IA · Groq / Gemini / Claude / OpenAI · Conversa persistida no servidor.</div>
        </div>
      </div>

      {/* Modal de Boas-Vindas */}
      {showWelcomeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShowWelcomeModal(false)}>
          <div className="relative bg-white rounded-2xl shadow-2xl overflow-hidden max-w-md w-full mx-4" onClick={e => e.stopPropagation()}>
            {/* Header com botão fechar */}
            <div className="absolute top-3 right-3 z-10">
              <button 
                onClick={() => setShowWelcomeModal(false)}
                className="w-8 h-8 rounded-full bg-black/20 hover:bg-black/40 flex items-center justify-center transition-colors"
              >
                <X className="w-5 h-5 text-white" />
              </button>
            </div>
            
            {/* Vídeo de Boas-Vindas com Áudio - Suporte MP4/WebM */}
            <div className="relative aspect-square bg-emerald-900">
              <video
                autoPlay
                muted={false}
                playsInline
                controls
                className="w-full h-full object-cover"
                onError={(e) => {
                  // Fallback se o vídeo não existir
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'flex';
                }}
              >
                <source src="/brand/roma_ia_animated_bem_vindo.MP4" type="video/mp4" />
                <source src="/brand/roma_ia_animated_bem_vindo.mp4" type="video/mp4" />
                <source src="/brand/roma_ia_animated_bem_vindo.webm" type="video/webm" />
                Seu navegador não suporta vídeo.
              </video>
              <div className="absolute inset-0 hidden items-center justify-center bg-emerald-900 text-white text-center p-6">
                <div>
                  <RomaIAAvatar state="speaking" size="lg" />
                  <p className="mt-4 text-lg font-semibold">Olá! Sou a Roma_IA</p>
                  <p className="text-sm text-emerald-200 mt-2">Sua especialista em avaliação imobiliária</p>
                </div>
              </div>
            </div>
            
            {/* Conteúdo */}
            <div className="p-6 text-center">
              <h2 className="text-xl font-bold text-gray-900 mb-2">Bem-vindo à Roma_IA!</h2>
              <p className="text-gray-600 text-sm mb-4">
                Sou sua assistente especializada em NBR 14.653. Posso ajudar com:
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs text-gray-500 mb-6">
                <div className="bg-gray-50 rounded-lg p-2">✓ Aperfeiçoar laudos</div>
                <div className="bg-gray-50 rounded-lg p-2">✓ Gerar fundamentações</div>
                <div className="bg-gray-50 rounded-lg p-2">✓ Análises SWOT</div>
                <div className="bg-gray-50 rounded-lg p-2">✓ Memoriais descritivos</div>
              </div>
              <Button 
                onClick={() => setShowWelcomeModal(false)}
                className="w-full bg-emerald-900 hover:bg-emerald-800 text-white"
              >
                Começar a conversar
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AIAssistant;
