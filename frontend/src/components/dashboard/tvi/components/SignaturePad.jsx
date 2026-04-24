import React, { useRef, useEffect, useState } from 'react';
import { Trash2, Check } from 'lucide-react';

const SignaturePad = ({ value, onChange }) => {
  const canvasRef = useRef(null);
  const drawing = useRef(false);
  const [hasSig, setHasSig] = useState(!!value);

  useEffect(() => {
    if (value && canvasRef.current) {
      const img = new Image();
      img.onload = () => {
        const ctx = canvasRef.current.getContext('2d');
        ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
        ctx.drawImage(img, 0, 0);
      };
      img.src = value;
    }
  }, [value]);

  const getPos = (e, canvas) => {
    const r = canvas.getBoundingClientRect();
    const src = e.touches ? e.touches[0] : e;
    return { x: src.clientX - r.left, y: src.clientY - r.top };
  };

  const start = (e) => {
    drawing.current = true;
    const ctx = canvasRef.current.getContext('2d');
    const { x, y } = getPos(e, canvasRef.current);
    ctx.beginPath();
    ctx.moveTo(x, y);
    e.preventDefault();
  };

  const draw = (e) => {
    if (!drawing.current) return;
    const ctx = canvasRef.current.getContext('2d');
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#1B4D1B';
    const { x, y } = getPos(e, canvasRef.current);
    ctx.lineTo(x, y);
    ctx.stroke();
    setHasSig(true);
    e.preventDefault();
  };

  const stop = () => { drawing.current = false; };

  const clear = () => {
    const ctx = canvasRef.current.getContext('2d');
    ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    setHasSig(false);
    onChange && onChange(null);
  };

  const save = () => {
    const b64 = canvasRef.current.toDataURL('image/png');
    onChange && onChange(b64);
  };

  return (
    <div className="space-y-2">
      <div className="rounded-xl border-2 border-dashed border-gray-300 overflow-hidden bg-white" style={{ touchAction: 'none' }}>
        <canvas
          ref={canvasRef}
          width={600}
          height={150}
          className="w-full cursor-crosshair"
          onMouseDown={start} onMouseMove={draw} onMouseUp={stop} onMouseLeave={stop}
          onTouchStart={start} onTouchMove={draw} onTouchEnd={stop}
        />
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400">Assine dentro da área acima</span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={clear}
            className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded-lg hover:bg-red-50"
          >
            <Trash2 className="w-3 h-3" /> Limpar
          </button>
          <button
            type="button"
            onClick={save}
            disabled={!hasSig}
            className="flex items-center gap-1 text-xs text-emerald-700 hover:text-emerald-900 px-2 py-1 rounded-lg hover:bg-emerald-50 disabled:opacity-40"
          >
            <Check className="w-3 h-3" /> Confirmar
          </button>
        </div>
      </div>
    </div>
  );
};

export default SignaturePad;
