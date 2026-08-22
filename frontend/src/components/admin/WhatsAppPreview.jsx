// @module components/admin/WhatsAppPreview — balão de prévia de mensagem WhatsApp.
// Compartilhado entre Cupons Promocionais e Acessos de Teste (evita duplicar o render).
import React from 'react';

// Formata *negrito*, ~tachado~ e _itálico_ + quebras de linha, como o WhatsApp.
export const renderWa = (texto) => String(texto || '').split('\n').map((linha, i) => {
  const parts = [];
  const re = /(\*[^*]+\*|~[^~]+~|_[^_]+_)/g;
  let last = 0; let m;
  while ((m = re.exec(linha))) {
    if (m.index > last) parts.push(linha.slice(last, m.index));
    const tok = m[0];
    const txt = tok.slice(1, -1);
    if (tok.startsWith('*')) parts.push(<strong key={`${i}-${m.index}`}>{txt}</strong>);
    else if (tok.startsWith('~')) parts.push(<span key={`${i}-${m.index}`} style={{ textDecoration: 'line-through' }}>{txt}</span>);
    else parts.push(<em key={`${i}-${m.index}`}>{txt}</em>);
    last = m.index + tok.length;
  }
  if (last < linha.length) parts.push(linha.slice(last));
  return <div key={i} style={{ minHeight: linha === '' ? 8 : undefined }}>{parts.length ? parts : linha}</div>;
});

export const WhatsAppPreview = ({ mensagem, titulo = 'RomaTec AvalieImob' }) => (
  <div className="rounded-xl overflow-hidden border border-gray-200" style={{ background: '#ECE5DD' }}>
    <div className="flex items-center gap-2 px-3 py-2" style={{ background: '#075E54' }}>
      <span className="w-6 h-6 rounded-full bg-emerald-300 flex items-center justify-center text-emerald-900 text-xs font-bold">R</span>
      <span className="text-white text-sm font-medium">{titulo}</span>
    </div>
    <div className="p-3">
      <div className="bg-white rounded-lg p-3 text-[13px] text-gray-800 shadow-sm max-w-[88%] leading-snug whitespace-pre-wrap break-words">
        {renderWa(mensagem)}
        <div className="text-[10px] text-gray-400 text-right mt-1">14:30 ✓✓</div>
      </div>
    </div>
  </div>
);

export default WhatsAppPreview;
