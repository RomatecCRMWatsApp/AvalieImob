import React, { useRef, useEffect, useCallback } from 'react';

const VERDE = '#0C3320';
const VERDE_ALT = '#0f3a25';
const DOURADO = '#C9A84C';
const CREME = '#f3f1e6';

function wrapText(ctx, text, maxWidth) {
  const words = (text || '').split(/\s+/).filter(Boolean);
  const lines = [];
  let line = '';
  for (const w of words) {
    const test = line ? line + ' ' + w : w;
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = w;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function drawCard(canvas, { titulo, texto, alt, w, h }) {
  const ctx = canvas.getContext('2d');
  canvas.width = w;
  canvas.height = h;

  ctx.fillStyle = alt ? VERDE_ALT : VERDE;
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = DOURADO;
  ctx.lineWidth = 6;
  ctx.strokeRect(40, 40, w - 80, h - 80);

  const pad = 90;

  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  ctx.fillStyle = CREME;
  const tSize = Math.round(w * 0.075);
  ctx.font = `700 ${tSize}px "Playfair Display", Georgia, serif`;
  const linhasT = wrapText(ctx, titulo, w - pad * 2);
  let y = pad + 40;
  for (const l of linhasT) {
    ctx.fillText(l, pad, y);
    y += tSize * 1.18;
  }

  if (texto) {
    y += 24;
    const cSize = Math.round(w * 0.042);
    ctx.font = `400 ${cSize}px Inter, Arial, sans-serif`;
    ctx.fillStyle = DOURADO;
    const linhasC = wrapText(ctx, texto, w - pad * 2);
    for (const l of linhasC) {
      ctx.fillText(l, pad, y);
      y += cSize * 1.3;
    }
  }

  const fSize = Math.round(w * 0.036);
  const boxS = Math.round(fSize * 1.4);
  const bx = pad;
  const by = h - pad - boxS;
  const r = 10;
  ctx.fillStyle = DOURADO;
  ctx.beginPath();
  ctx.moveTo(bx + r, by);
  ctx.arcTo(bx + boxS, by, bx + boxS, by + boxS, r);
  ctx.arcTo(bx + boxS, by + boxS, bx, by + boxS, r);
  ctx.arcTo(bx, by + boxS, bx, by, r);
  ctx.arcTo(bx, by, bx + boxS, by, r);
  ctx.fill();
  ctx.fillStyle = VERDE;
  ctx.font = `700 ${Math.round(boxS * 0.6)}px "Playfair Display", Georgia, serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('A', bx + boxS / 2, by + boxS / 2 + 2);

  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = DOURADO;
  ctx.font = `600 ${fSize}px Inter, Arial, sans-serif`;
  ctx.fillText('@avalieimob', bx + boxS + 20, by + boxS / 2);

  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
}

export function paginasDoPost(post) {
  return post.formato === 'carrossel' && (post.slides || []).length
    ? [{ titulo: post.titulo, texto: post.cta }, ...post.slides.map(s => ({ titulo: s.titulo, texto: s.texto }))]
    : [{ titulo: post.titulo, texto: post.cta }];
}

export function dimsDoPost(post) {
  return post.formato === 'carrossel' ? { w: 1080, h: 1350 } : { w: 1080, h: 1080 };
}

// Gera os PNGs (dataURL) de um post SEM precisar do componente montado (canvas offscreen).
// Usado pela automação pós-aprovação (aprovar no calendário → enviar sem abrir a arte).
export async function gerarPngsDoPost(post) {
  if (document.fonts && document.fonts.ready) {
    try { await document.fonts.ready; } catch (e) { /* ignore */ }
  }
  const dims = dimsDoPost(post);
  return paginasDoPost(post).map((pg, i) => {
    const c = document.createElement('canvas');
    drawCard(c, { ...pg, alt: i > 0, w: dims.w, h: dims.h });
    return c.toDataURL('image/png');
  });
}

export default function InstagramArt({ post, onEnviarWhatsapp, enviando }) {
  const refs = useRef([]);

  const paginas = paginasDoPost(post);
  const dims = dimsDoPost(post);

  const desenhar = useCallback(async () => {
    if (document.fonts && document.fonts.ready) {
      try { await document.fonts.ready; } catch (e) { /* ignore */ }
    }
    paginas.forEach((pg, i) => {
      const c = refs.current[i];
      if (c) drawCard(c, { ...pg, alt: i > 0, w: dims.w, h: dims.h });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [post]);

  useEffect(() => { desenhar(); }, [desenhar]);

  const baixar = () => {
    paginas.forEach((_, i) => {
      const c = refs.current[i];
      if (!c) return;
      const a = document.createElement('a');
      a.download = `avalieimob-${post.id || 'post'}-${i + 1}.png`;
      a.href = c.toDataURL('image/png');
      a.click();
    });
  };

  const copiarLegenda = async () => {
    const tags = (post.hashtags || []).join(' ');
    await navigator.clipboard.writeText(`${post.legenda || ''}\n\n${tags}`.trim());
  };

  const enviarWhatsapp = () => {
    if (!onEnviarWhatsapp) return;
    const imagens = paginas
      .map((_, i) => (refs.current[i] ? refs.current[i].toDataURL('image/png') : null))
      .filter(Boolean);
    onEnviarWhatsapp(imagens);
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-3 overflow-x-auto py-2">
        {paginas.map((pg, i) => (
          <canvas key={i} ref={el => (refs.current[i] = el)}
                  style={{ width: 220, height: 'auto', borderRadius: 8, flexShrink: 0 }} />
        ))}
      </div>
      <div className="flex gap-2 flex-wrap">
        <button onClick={baixar} className="bg-[#C9A84C] text-[#0C3320] font-semibold rounded px-4 py-2">Baixar arte (PNG)</button>
        <button onClick={copiarLegenda} className="border rounded px-4 py-2">Copiar legenda</button>
        {onEnviarWhatsapp && (
          <button onClick={enviarWhatsapp} disabled={enviando}
                  className="bg-green-600 text-white font-semibold rounded px-4 py-2 disabled:opacity-50">
            {enviando ? 'Enviando…' : 'Enviar pro meu WhatsApp'}
          </button>
        )}
        <a href="https://www.instagram.com/avalieimob" target="_blank" rel="noreferrer" className="bg-[#0C3320] text-white rounded px-4 py-2">Abrir Instagram</a>
      </div>
    </div>
  );
}
