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

// Cada página carrega seu próprio screenshot_id: a CAPA usa o do post; cada slide, o seu.
export function paginasDoPost(post) {
  return post.formato === 'carrossel' && (post.slides || []).length
    ? [{ titulo: post.titulo, texto: post.cta, screenshot_id: post.screenshot_id },
       ...post.slides.map(s => ({ titulo: s.titulo, texto: s.texto, screenshot_id: s.screenshot_id }))]
    : [{ titulo: post.titulo, texto: post.cta, screenshot_id: post.screenshot_id }];
}

export function dimsDoPost(post) {
  if (post.formato === 'carrossel') return { w: 1080, h: 1350 };
  if (post.formato === 'post_unico' && post.screenshot_id) return { w: 1080, h: 1350 };
  return { w: 1080, h: 1080 };
}

// Gera os PNGs (dataURL) de um post. Único ponto de desenho — o preview usa estes mesmos PNGs.
// Cada página: showcase (print + faixa) se tiver tela anexada; senão o template de texto.
export async function gerarPngsDoPost(post) {
  try { if (document.fonts && document.fonts.ready) await document.fonts.ready; } catch (e) { /* ignore */ }

  const dims = dimsDoPost(post);
  const paginas = paginasDoPost(post);
  const out = [];
  for (let i = 0; i < paginas.length; i++) {
    const pg = paginas[i];
    const c = document.createElement('canvas');
    if (pg.screenshot_id) {
      let img = null;
      try { img = await carregarImagem(uploadAPI.getImageUrl(pg.screenshot_id)); } catch (e) { /* segue sem print */ }
      drawShowcase(c, { img, titulo: pg.titulo, texto: pg.texto, w: dims.w, h: dims.h });
    } else {
      drawCard(c, { titulo: pg.titulo, texto: pg.texto, alt: i > 0, w: dims.w, h: dims.h });
    }
    out.push(c.toDataURL('image/png'));
  }
  return out;
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
