import React, { useState, useEffect, useRef } from 'react';
import { X, Send, User, Loader2 } from 'lucide-react';
import RomaIAAvatar from './RomaIAAvatar';
import { aiAPI } from '../../lib/api';

/**
 * Roma_IA Chat Widget Flutuante
 * Disponível em todas as páginas (públicas e privadas)
 * Permite que visitantes conversem com a IA sem login
 */
const RomaIAWidget = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Olá! Sou a Roma_IA, especialista em avaliação imobiliária. Como posso ajudar você hoje?' }
  ]);
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
    
    setMessages(m => [...m, { role: 'user', content }]);
    setInput('');
    setLoading(true);
    
    try {
      const res = await aiAPI.chat(sessionId, content);
      setMessages(m => [...m, { role: 'assistant', content: res.reply, provider: res.provider }]);
    } catch (e) {
      setMessages(m => [...m, { 
        role: 'assistant', 
        content: 'Desculpe, estou tendo dificuldades técnicas. Por favor, tente novamente em alguns instantes.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([
      { role: 'assistant', content: 'Olá! Sou a Roma_IA, especialista em avaliação imobiliária. Como posso ajudar você hoje?' }
    ]);
    const newSid = `widget_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    localStorage.setItem('romatec_widget_session', newSid);
    setSessionId(newSid);
  };

  return (
    <>
      {/* Botão Flutuante */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 group"
          aria-label="Abrir chat com Roma_IA"
        >
          <div className="relative">
            <div className="absolute inset-0 bg-emerald-500 rounded-full animate-ping opacity-30"></div>
            <div className="relative bg-emerald-900 hover:bg-emerald-800 rounded-full p-3 shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-110">
              <RomaIAAvatar state="idle" size="md" />
            </div>
            {/* Badge de notificação */}
            {showWelcome && (
              <div className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white text-xs font-bold animate-bounce">
                1
              </div>
            )}
          </div>
        </button>
      )}

      {/* Tooltip de boas-vindas */}
      {showWelcome && !isOpen && (
        <div 
          className="fixed bottom-24 right-6 z-40 bg-white rounded-xl shadow-lg p-4 max-w-xs animate-fade-in-up"
          onClick={() => {
            setIsOpen(true);
            setShowWelcome(false);
          }}
        >
          <div className="flex items-start gap-3">
            <RomaIAAvatar state="speaking" size="sm" />
            <div>
              <p className="text-sm font-medium text-gray-900">Olá! Sou a Roma_IA 👋</p>
              <p className="text-xs text-gray-500 mt-1">Posso ajudar com dúvidas sobre avaliação imobiliária!</p>
            </div>
          </div>
          <div className="absolute bottom-[-8px] right-6 w-4 h-4 bg-white transform rotate-45"></div>
        </div>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-96 max-w-[calc(100vw-2rem)]">
          <div className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-gray-200">
            {/* Header */}
            <div className="bg-emerald-900 p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <RomaIAAvatar state={loading ? 'thinking' : 'speaking'} size="sm" />
                <div>
                  <h3 className="text-white font-semibold text-sm">Roma_IA</h3>
                  <p className="text-emerald-200 text-xs">Especialista NBR 14.653</p>
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
            <div className="h-80 overflow-y-auto p-4 space-y-4 bg-gray-50">
              {messages.map((m, i) => (
                <div 
                  key={i} 
                  className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${m.role === 'user' ? 'bg-amber-500' : ''}`}>
                    {m.role === 'user' ? (
                      <User className="w-4 h-4 text-white" />
                    ) : (
                      <RomaIAAvatar state="idle" size="sm" />
                    )}
                  </div>
                  <div className={`max-w-[75%] rounded-xl p-3 text-sm ${m.role === 'user' ? 'bg-emerald-600 text-white' : 'bg-white text-gray-800 shadow-sm'}`}>
                    {m.content}
                    {m.role === 'assistant' && m.provider && (
                      <span className="block text-[10px] opacity-50 mt-1">via {m.provider}</span>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex gap-2">
                  <div className="w-8 h-8 rounded-full flex-shrink-0">
                    <RomaIAAvatar state="thinking" size="sm" />
                  </div>
                  <div className="bg-white rounded-xl p-3 flex items-center gap-2 shadow-sm">
                    <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
                    <span className="text-sm text-gray-500">Pensando...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-3 border-t border-gray-200 bg-white">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Digite sua pergunta..."
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
                Powered by Roma_IA · Groq / Gemini / Claude / OpenAI
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default RomaIAWidget;
