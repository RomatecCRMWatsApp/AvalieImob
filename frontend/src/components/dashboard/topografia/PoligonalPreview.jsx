// @module topografia/PoligonalPreview — Preview SVG da poligonal (sem dependências externas).
import React from 'react';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';

export default function PoligonalPreview({ vertices = [], height = 240 }) {
  const pts = (vertices || []).filter(
    (v) => typeof v.longitude === 'number' && typeof v.latitude === 'number'
  );
  if (pts.length < 3) {
    return (
      <div className="flex items-center justify-center text-xs text-gray-400 border border-dashed rounded-lg"
        style={{ height }}>
        Sem coordenadas suficientes para desenhar a poligonal.
      </div>
    );
  }

  const W = 420;
  const H = height;
  const pad = 28;
  const lons = pts.map((p) => p.longitude);
  const lats = pts.map((p) => p.latitude);
  const minX = Math.min(...lons), maxX = Math.max(...lons);
  const minY = Math.min(...lats), maxY = Math.max(...lats);
  const spanX = maxX - minX || 1e-6;
  const spanY = maxY - minY || 1e-6;
  const scale = Math.min((W - 2 * pad) / spanX, (H - 2 * pad) / spanY);
  const offX = (W - spanX * scale) / 2;
  const offY = (H - spanY * scale) / 2;

  // y invertido (latitude cresce para cima)
  const xy = pts.map((p) => ({
    x: offX + (p.longitude - minX) * scale,
    y: H - (offY + (p.latitude - minY) * scale),
    codigo: p.codigo,
  }));
  const poly = xy.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full border rounded-lg bg-white" style={{ height }}>
      <polygon points={poly} fill="rgba(12,51,32,0.08)" stroke={GREEN} strokeWidth="1.5" />
      {xy.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="3" fill={GOLD} stroke={GREEN} strokeWidth="0.8" />
          {pts.length <= 12 && (
            <text x={p.x + 4} y={p.y - 4} fontSize="7" fill={GREEN}>
              {(p.codigo || '').split('-').pop()}
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}
