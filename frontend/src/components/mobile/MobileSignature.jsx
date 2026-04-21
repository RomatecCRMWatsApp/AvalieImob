// @module MobileSignature — canvas touch-optimized para assinatura em campo
import React, { useRef, useEffect, useState } from 'react';
import { Trash2, Check } from 'lucide-react';

const MobileSignature = ({ value, onChange }) => {
  const canvasRef = useRef(null);
  const drawing = useRef(false);
  const lastPos = useRef(null);
  const [hasSig, setHasSig] = useState(!!value);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    // High-DPI
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    if (value) {
      const img = new Image();
      img.onload = () => ctx.drawImage(img, 0, 0, rect.width, rect.height);
      img.src = value;
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const getPos = (e, canvas) => {
    const r = canvas.getBoundingClientRect();
    const src = e.touches ? e.touches[0] : e;
    return {
      x: (src.clientX - r.left),
      y: (src.clientY - r.top),
    };
  };

  const start = (e) => {
    e.preventDefault();
    drawing.current = true;
    const pos = getPos(e, canvasRef.current);
    lastPos.current = pos;
    const ctx = canvasRef.current.getContext('2d');
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
  };

  const draw = (e) => {
    e.preventDefault();
    if (!drawing.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#1B4D1B';
    const pos = getPos(e, canvas);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
    lastPos.current = pos;
    setHasSig(true);
  };

  const stop = (e) => {
    e?.preventDefault();
    drawing.current = false;
    lastPos.current = null;
  };

  const clear = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const r = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, r.width, r.height);
    setHasSig(false);
    onChange && onChange(null);
  };

  const save = () => {
    const b64 = canvasRef.current.toDataURL('image/png');
    onChange && onChange(b64);
  };

  return (
    <div className="space-y-3">
      <div
        className="rounded-xl border-2 border-dashed border-gray-300 bg-white overflow-hidden"
        style={{ touchAction: 'none', minHeight: '160px' }}
      >
        <canvas
          ref={canvasRef}
          className="w-full"
          style={{ height: '160px', display: 'block', cursor: 'crosshair' }}
          onMouseDown={start} onMouseMove={draw} onMouseUp={stop} onMouseLeave={stop}
          onTouchStart={start} onTouchMove={draw} onTouchEnd={stop}
        />
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400">Assine com o dedo ou caneta</span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={clear}
            className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 px-3 py-2 rounded-xl hover:bg-red-50 min-h-[44px] min-w-[44px]"
          >
            <Trash2 className="w-4 h-4" /> Limpar
          </button>
          <button
            type="button"
            onClick={save}
            disabled={!hasSig}
            className="flex items-center gap-1 text-xs text-emerald-700 hover:text-emerald-900 px-3 py-2 rounded-xl hover:bg-emerald-50 min-h-[44px] disabled:opacity-40"
          >
            <Check className="w-4 h-4" /> Confirmar
          </button>
        </div>
      </div>
    </div>
  );
};

export default MobileSignature;
