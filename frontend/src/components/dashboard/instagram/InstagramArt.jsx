import React, { useState, useEffect, useCallback } from 'react';
import { uploadAPI } from '../../../lib/api';

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

// Rodapé da marca ("A" + @avalieimob) — reusado por todos os templates.
function drawRodape(ctx, w, h, pad) {
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
  ctx.fillStyle = DOURADO;
  ctx.font = `600 ${fSize}px Inter, Arial, sans-serif`;
  ctx.fillText('@avalieimob', bx + boxS + 20, by + boxS / 2);
  ctx.textBaseline = 'top';
}

// Template padrão (só texto): título grande + texto/CTA + rodapé.
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
  let y = pad + 40;
  for (const l of wrapText(ctx, titulo, w - pad * 2)) {
    ctx.fillText(l, pad, y);
    y += tSize * 1.18;
  }

  if (texto) {
    y += 24;
    const cSize = Math.round(w * 0.042);
    ctx.font = `400 ${cSize}px Inter, Arial, sans-serif`;
    ctx.fillStyle = DOURADO;
    for (const l of wrapText(ctx, texto, w - pad * 2)) {
      ctx.fillText(l, pad, y);
      y += cSize * 1.3;
    }
  }

  drawRodape(ctx, w, h, pad);
}

// Template "showcase": print grande da tela do sistema + faixa de texto embaixo.
function drawShowcase(canvas, { img, titulo, texto, w, h }) {
  const ctx = canvas.getContext('2d');
  canvas.width = w;
  canvas.height = h;

  ctx.fillStyle = VERDE;
  ctx.fillRect(0, 0, w, h);

  const m = 60;
  const printTop = m + 10;
  const printBottom = Math.round(h * 0.60);
  const boxW = w - m * 2;
  const boxH = printBottom - printTop;

  // fundo branco + moldura dourada da "tela"
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(m, printTop, boxW, boxH);
  ctx.strokeStyle = DOURADO;
  ctx.lineWidth = 6;
  ctx.strokeRect(m - 3, printTop - 3, boxW + 6, boxH + 6);

  // desenha o print "contain" (mantém proporção, centralizado)
  if (img && img.width) {
    const ar = img.width / img.height;
    const boxAr = boxW / boxH;
    let dw, dh;
    if (ar > boxAr) { dw = boxW; dh = boxW / ar; }
    else { dh = boxH; dw = boxH * ar; }
    const dx = m + (boxW - dw) / 2;
    const dy = printTop + (boxH - dh) / 2;
    ctx.drawImage(img, dx, dy, dw, dh);
  }

  // faixa de texto (título + CTA)
  const pad = 80;
  let y = printBottom + 46;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  ctx.fillStyle = CREME;
  const tSize = Math.round(w * 0.06);
  ctx.font = `700 ${tSize}px "Playfair Display", Georgia, serif`;
  for (const l of wrapText(ctx, titulo, w - pad * 2)) {
    ctx.fillText(l, pad, y);
    y += tSize * 1.15;
  }
  if (texto) {
    y += 14;
    const cSize = Math.round(w * 0.038);
    ctx.font = `400 ${cSize}px Inter, Arial, sans-serif`;
    ctx.fillStyle = DOURADO;
    for (const l of wrapText(ctx, texto, w - pad * 2)) {
      ctx.fillText(l, pad, y);
      y += cSize * 1.3;
    }
  }

  drawRodape(ctx, w, h, pad);
}

function carregarImagem(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();          // same-origin: sem crossOrigin (evita exigir CORS)
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = url;
  });
}

export function paginasDoPost(post) {
  return post.formato === 'carrossel' && (post.slides || []).length
    ? [{ titulo: post.titulo, texto: post.cta }, ...post.slides.map(s => ({ titulo: s.titulo, texto: s.texto }))]
    : [{ titulo: post.titulo, texto: post.cta }];
}

export function dimsDoPost(post) {
  return post.formato === 'carrossel' ? { w: 1080, h: 1350 } : { w: 1080, h: 1080 };
}

function usaShowcase(post) {
  return post.formato === 'post_unico' && !!post.screenshot_id;
}

// Gera os PNGs (dataURL) de um post. Único ponto de desenho — o preview usa estes mesmos PNGs.
// showcase (print + faixa) quando post único com tela anexada; senão o template de texto.
export async function gerarPngsDoPost(post) {
  try { if (document.fonts && document.fonts.ready) await document.fonts.ready; } catch (e) { /* ignore */ }

  if (usaShowcase(post)) {
    let img = null;
    try { img = await carregarImagem(uploadAPI.getImageUrl(post.screenshot_id)); } catch (e) { /* segue sem print */ }
    const c = document.createElement('canvas');
    drawShowcase(c, { img, titulo: post.titulo, texto: post.cta, w: 1080, h: 1350 });
    return [c.toDataURL('image/png')];
  }

  const dims = dimsDoPost(post);
  return paginasDoPost(post).map((pg, i) => {
    const c = document.createElement('canvas');
    drawCard(c, { ...pg, alt: i > 0, w: dims.w, h: dims.h });
    return c.toDataURL('image/png');
  });
}

export default function InstagramArt({ post, onEnviarWhatsapp, enviando }) {
  const [pngs, setPngs] = useState([]);

  const render = useCallback(async () => {
    const urls = await gerarPngsDoPost(post);
    setPngs(urls);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [post]);

  useEffect(() => { render(); }, [render]);

  const baixar = () => {
    pngs.forEach((url, i) => {
      const a = document.createElement('a');
      a.download = `avalieimob-${post.id || 'post'}-${i + 1}.png`;
      a.href = url;
      a.click();
    });
  };

  const copiarLegenda = async () => {
    const tags = (post.hashtags || []).join(' ');
    await navigator.clipboard.writeText(`${post.legenda || ''}\n\n${tags}`.trim());
  };

  const enviarWhatsapp = () => { if (onEnviarWhatsapp) onEnviarWhatsapp(pngs); };

  return (
    <div className="space-y-3">
      <div className="flex gap-3 overflow-x-auto py-2">
        {pngs.map((url, i) => (
          <img key={i} src={url} alt={`arte ${i + 1}`}
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
