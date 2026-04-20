import React, { useState, useEffect } from 'react';
import { MessageCircle, X, Phone } from 'lucide-react';

const SPECIALISTS = [
  {
    id: 'jr',
    name: 'Jose Romario P. Bezerra',
    role: 'Diretor Comercial / CEO',
    phone: '(99) 9 9181-1246',
    initials: 'JR',
    avatarColor: 'bg-emerald-600',
    whatsappHref: 'https://wa.me/5599991811246?text=Ol%C3%A1!%20Gostaria%20de%20saber%20mais%20sobre%20o%20AvalieImob',
    telHref: 'tel:+5599991811246',
  },
  {
    id: 'dc',
    name: 'Daniele Cavalcante Vieira',
    role: 'Especialista em Imóveis',
    phone: '(99) 9 9206-2871',
    initials: 'DC',
    avatarColor: 'bg-amber-500',
    whatsappHref: 'https://wa.me/5599992062871?text=Ol%C3%A1!%20Gostaria%20de%20saber%20mais%20sobre%20o%20AvalieImob',
    telHref: 'tel:+5599992062871',
  },
];

const WhatsAppButton = () => {
  const [visible, setVisible] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 1500);
    return () => clearTimeout(t);
  }, []);

  if (!visible) return null;

  return (
    <div className="fixed bottom-6 left-6 z-50 flex flex-col items-start gap-3">
      {expanded && (
        <div className="bg-gray-900 rounded-2xl shadow-2xl border border-emerald-800/40 p-5 w-72 animate-fade-in-up">
          <div className="flex items-start justify-between gap-3 mb-4">
            <div>
              <div className="font-semibold text-white text-sm">Fale com um Especialista</div>
              <div className="text-xs text-emerald-400 mt-0.5">Selecione e entre em contato</div>
            </div>
            <button
              onClick={() => setExpanded(false)}
              className="text-gray-400 hover:text-white transition-colors"
              aria-label="Fechar"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-3">
            {SPECIALISTS.map((s) => (
              <div
                key={s.id}
                className="bg-white/5 border border-white/10 rounded-xl p-3 hover:border-emerald-500/40 hover:bg-white/10 transition-all"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div
                    className={`w-10 h-10 rounded-full ${s.avatarColor} flex items-center justify-center text-white font-bold text-sm flex-shrink-0`}
                  >
                    {s.initials}
                  </div>
                  <div className="min-w-0">
                    <div className="font-semibold text-white text-xs leading-tight truncate">{s.name}</div>
                    <div className="text-emerald-400 text-[11px] leading-tight">{s.role}</div>
                    <div className="text-gray-400 text-[11px]">{s.phone}</div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <a
                    href={s.whatsappHref}
                    target="_blank"
                    rel="noreferrer"
                    className="flex-1 text-center bg-[#25D366] hover:bg-[#1fb857] text-white font-semibold py-1.5 rounded-lg text-xs transition-colors"
                  >
                    WhatsApp
                  </a>
                  <a
                    href={s.telHref}
                    className="flex-1 text-center bg-white/10 hover:bg-white/20 text-white font-semibold py-1.5 rounded-lg text-xs transition-colors flex items-center justify-center gap-1"
                  >
                    <Phone className="w-3 h-3" />
                    Ligar
                  </a>
                </div>
              </div>
            ))}
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
