import React, { useState, useEffect } from 'react';
import { MessageCircle, X } from 'lucide-react';
import { BRAND } from '../../mock/mock';

const WhatsAppButton = () => {
  const [visible, setVisible] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 1500);
    return () => clearTimeout(t);
  }, []);

  const phone = (BRAND.whatsapp || '').replace(/\D/g, '');
  const fullNumber = phone.startsWith('55') ? phone : `55${phone}`;
  const defaultMessage = encodeURIComponent('Olá! Vim pelo site do RomaTec AvalieImob e gostaria de saber mais sobre a plataforma.');
  const href = `https://wa.me/${fullNumber}?text=${defaultMessage}`;

  if (!visible) return null;

  return (
    <div className="fixed bottom-6 left-6 z-50 flex flex-col items-start gap-3">
      {expanded && (
        <div className="bg-white rounded-2xl shadow-2xl border border-emerald-900/10 p-5 max-w-xs animate-fade-in-up">
          <div className="flex items-start justify-between gap-3 mb-3">
            <div>
              <div className="font-semibold text-gray-900 text-sm">Fale com a gente</div>
              <div className="text-xs text-gray-500 mt-0.5">Resposta rápida no WhatsApp</div>
            </div>
            <button onClick={() => setExpanded(false)} className="text-gray-400 hover:text-gray-600" aria-label="Fechar">
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="text-sm text-gray-600 leading-relaxed mb-4">
            Olá! 👋 Nossa equipe está pronta para tirar suas dúvidas sobre planos, funcionalidades e personalizações.
          </p>
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="block w-full text-center bg-[#25D366] hover:bg-[#1fb857] text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
          >
            Iniciar conversa
          </a>
          <div className="text-[11px] text-gray-400 text-center mt-2">
            {BRAND.whatsapp}
          </div>
        </div>
      )}

      <button
        onClick={() => setExpanded(!expanded)}
        className="relative w-14 h-14 rounded-full bg-[#25D366] hover:bg-[#1fb857] text-white shadow-lg hover:shadow-xl transition-all hover:scale-105 flex items-center justify-center"
        aria-label="Abrir WhatsApp"
      >
        <MessageCircle className="w-7 h-7" fill="currentColor" />
        <span className="absolute top-0 right-0 w-3.5 h-3.5 bg-amber-400 rounded-full border-2 border-white animate-pulse" />
      </button>
    </div>
  );
};

export default WhatsAppButton;
