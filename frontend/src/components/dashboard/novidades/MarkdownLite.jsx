// @module dashboard/novidades/MarkdownLite — Renderer de markdown MÍNIMO e SEGURO (whitelist).
// Suporta apenas: cabeçalhos (#..######), listas (- / *), parágrafos e **negrito** inline.
// Sem HTML cru → sanitizado por construção (sem risco de injeção).
import React from 'react';

const inline = (text) =>
  String(text).split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith('**') && p.endsWith('**')
      ? <strong key={i}>{p.slice(2, -2)}</strong>
      : <React.Fragment key={i}>{p}</React.Fragment>);

const MarkdownLite = ({ text }) => {
  const lines = String(text || '').split('\n');
  const blocks = [];
  let list = null;
  let para = [];
  const flushPara = () => { if (para.length) { blocks.push({ t: 'p', c: para.join(' ') }); para = []; } };
  const flushList = () => { if (list) { blocks.push({ t: 'ul', items: list }); list = null; } };

  lines.forEach((raw) => {
    const l = raw.trimEnd();
    if (/^#{1,6}\s+/.test(l)) {
      flushPara(); flushList();
      blocks.push({ t: 'h', lvl: (l.match(/^#+/)[0]).length, c: l.replace(/^#+\s+/, '') });
    } else if (/^[-*]\s+/.test(l)) {
      flushPara();
      (list = list || []).push(l.replace(/^[-*]\s+/, ''));
    } else if (l.trim() === '') {
      flushPara(); flushList();
    } else {
      flushList(); para.push(l.trim());
    }
  });
  flushPara(); flushList();

  return (
    <div className="space-y-2 text-sm text-gray-700 leading-relaxed">
      {blocks.map((b, i) => {
        if (b.t === 'h') {
          return React.createElement(`h${Math.min(b.lvl + 2, 6)}`,
            { key: i, className: 'font-display font-bold text-gray-900 mt-3 mb-1' }, inline(b.c));
        }
        if (b.t === 'ul') {
          return <ul key={i} className="list-disc ml-5 space-y-0.5">{b.items.map((it, j) => <li key={j}>{inline(it)}</li>)}</ul>;
        }
        return <p key={i}>{inline(b.c)}</p>;
      })}
    </div>
  );
};

export default MarkdownLite;
