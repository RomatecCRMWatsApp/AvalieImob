import React, { useState, useRef, useEffect } from 'react';
import { Sparkles, Send, Bot, User, Wand2, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { useToast } from '../../hooks/use-toast';
import { aiAPI } from '../../lib/api';

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
    { role: 'assistant', content: 'Olá! Sou a IA do RomaTec AvalieImob, especialista em PTAM e laudos técnicos conforme a NBR 14.653. Posso aperfeiçoar textos, gerar fundamentações, elaborar memórias de cálculo e análises técnicas. Como posso ajudar?' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  // Load history on mount
  useEffect(() => {
    aiAPI.history(sessionId).then((hist) => {
      if (hist && hist.length > 0) {
        setMessages(hist.map(h => ({ role: h.role, content: h.content })));
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
      setMessages(m => [...m, { role: 'assistant', content: res.reply }]);
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
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-700 to-emerald-900 flex items-center justify-center"><Sparkles className="w-6 h-6 text-white" /></div>
          <div>
            <h1 className="font-display text-3xl font-bold text-gray-900">Assistente IA</h1>
            <p className="text-gray-600">GPT-5-mini especializado em NBR 14.653.</p>
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
              <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${m.role === 'user' ? 'bg-amber-500 text-white' : 'bg-emerald-900 text-white'}`}>
                {m.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              <div className={`max-w-[80%] rounded-xl p-3 text-sm whitespace-pre-wrap ${m.role === 'user' ? 'bg-emerald-50 text-gray-900' : 'bg-gray-50 text-gray-800'}`}>{m.content}</div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-3"><div className="w-8 h-8 rounded-full bg-emerald-900 text-white flex items-center justify-center"><Bot className="w-4 h-4" /></div><div className="bg-gray-50 rounded-xl p-3 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin text-emerald-700" /><span className="text-sm text-gray-500">Pensando...</span></div></div>
          )}
          <div ref={endRef} />
        </div>
        <div className="border-t border-gray-100 p-3">
          <div className="flex gap-2">
            <Textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder="Descreva o que deseja aperfeiçoar ou gerar..." className="min-h-[60px] resize-none" disabled={loading} />
            <Button onClick={() => send()} disabled={loading || !input.trim()} className="bg-emerald-900 hover:bg-emerald-800 text-white h-auto"><Send className="w-4 h-4" /></Button>
          </div>
          <div className="text-[11px] text-gray-400 mt-2">Powered by GPT-5-mini · Conversa persistida no servidor.</div>
        </div>
      </div>
    </div>
  );
};

export default AIAssistant;
