import React, { useEffect, useState } from 'react';

const SIZES = { sm: 44, md: 72, lg: 108 };

export default function RomaIAAvatar({ state = 'idle', size = 'md', className = '' }) {
  const S = SIZES[size];
  const [blink, setBlink] = useState(true);
  const [scan, setScan] = useState(0);
  const [mouthOpen, setMouthOpen] = useState(false);
  const [antennaPulse, setAntennaPulse] = useState(false);

  // Controle de piscar olhos
  useEffect(() => {
    const blinkInterval = setInterval(() => {
      setBlink(false);
      setTimeout(() => setBlink(true), 120);
    }, state === 'thinking' ? 400 : state === 'typing' ? 200 : 2800);
    return () => clearInterval(blinkInterval);
  }, [state]);

  // Scanline
  useEffect(() => {
    const scanInterval = setInterval(() => {
      setScan(s => (s + 2) % S);
    }, 30);
    return () => clearInterval(scanInterval);
  }, [S]);

  // Boca animada (typing/speaking)
  useEffect(() => {
    if (state === 'typing' || state === 'speaking') {
      const mouthInterval = setInterval(() => {
        setMouthOpen(o => !o);
      }, 180);
      return () => clearInterval(mouthInterval);
    } else {
      setMouthOpen(false);
    }
  }, [state]);

  // Antena pulse
  useEffect(() => {
    const antennaInterval = setInterval(() => {
      setAntennaPulse(p => !p);
    }, state === 'speaking' ? 300 : 800);
    return () => clearInterval(antennaInterval);
  }, [state]);

  // Cores por estado
  const stateColors = {
    idle:     { primary: '#00CC66', glow: '#00FF88', accent: '#D4A830' },
    thinking: { primary: '#FFB300', glow: '#FFD700', accent: '#FF8800' },
    typing:   { primary: '#00AAFF', glow: '#44CCFF', accent: '#0088DD' },
    speaking: { primary: '#00FF88', glow: '#88FFCC', accent: '#D4A830' },
  };
  const colors = stateColors[state];

  const padding = S * 0.08;
  const bodyW = S - padding * 2;
  const bodyH = S * 0.72;
  const bodyX = padding;
  const bodyY = S * 0.18;
  const cornerR = S * 0.08;

  return (
    <svg
      width={S}
      height={S}
      viewBox={`0 0 ${S} ${S}`}
      className={className}
      style={{ display: 'block', overflow: 'visible' }}
    >
      <defs>
        {/* Glow filter principal */}
        <filter id={`glow-${size}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation={S * 0.04} result="blur1"/>
          <feGaussianBlur stdDeviation={S * 0.08} result="blur2"/>
          <feMerge>
            <feMergeNode in="blur2"/>
            <feMergeNode in="blur1"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
        {/* Glow forte para antenas */}
        <filter id={`glow-strong-${size}`} x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation={S * 0.06} result="blur"/>
          <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
        {/* Clip para scanline ficar dentro do corpo */}
        <clipPath id={`body-clip-${size}`}>
          <rect x={bodyX+2} y={bodyY+2} width={bodyW-4} height={bodyH-4} rx={cornerR}/>
        </clipPath>
        {/* Gradiente corpo */}
        <linearGradient id={`body-grad-${size}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0D2B0D"/>
          <stop offset="100%" stopColor="#061406"/>
        </linearGradient>
      </defs>

      {/* ── ANTENAS ── */}
      {/* Antena esquerda */}
      <line
        x1={S * 0.3} y1={bodyY}
        x2={S * 0.22} y2={S * 0.04}
        stroke={colors.accent}
        strokeWidth={S * 0.025}
        filter={`url(#glow-${size})`}
        opacity={0.9}
      />
      <circle
        cx={S * 0.22} cy={S * 0.04}
        r={S * 0.045}
        fill={antennaPulse ? colors.accent : '#3a2800'}
        filter={`url(#glow-strong-${size})`}
      />
      {/* Antena direita */}
      <line
        x1={S * 0.7} y1={bodyY}
        x2={S * 0.78} y2={S * 0.04}
        stroke={colors.accent}
        strokeWidth={S * 0.025}
        filter={`url(#glow-${size})`}
        opacity={0.9}
      />
      <circle
        cx={S * 0.78} cy={S * 0.04}
        r={S * 0.045}
        fill={!antennaPulse ? colors.accent : '#3a2800'}
        filter={`url(#glow-strong-${size})`}
      />

      {/* ── CORPO (caixa LED) ── */}
      {/* Glow externo do corpo */}
      <rect
        x={bodyX - S*0.02} y={bodyY - S*0.02}
        width={bodyW + S*0.04} height={bodyH + S*0.04}
        rx={cornerR + 2}
        fill="none"
        stroke={colors.glow}
        strokeWidth={S * 0.02}
        opacity={0.3}
        filter={`url(#glow-${size})`}
      />
      {/* Corpo principal */}
      <rect
        x={bodyX} y={bodyY}
        width={bodyW} height={bodyH}
        rx={cornerR}
        fill={`url(#body-grad-${size})`}
        stroke={colors.primary}
        strokeWidth={S * 0.025}
        filter={`url(#glow-${size})`}
      />

      {/* ── SCANLINE ── */}
      <rect
        x={bodyX+2} y={bodyY + scan}
        width={bodyW-4} height={S * 0.04}
        fill={colors.primary}
        opacity={0.08}
        clipPath={`url(#body-clip-${size})`}
      />

      {/* ── OLHOS LED ── */}
      {/* Olho esquerdo — matriz de pontos LED */}
      {(() => {
        const eyeSize = S * 0.22;
        const eyeLX = bodyX + bodyW * 0.18;
        const eyeY = bodyY + bodyH * 0.2;
        const dotSize = eyeSize / 3;
        // Padrão de olho: todos acesos (idle/speaking), apenas periferia (thinking)
        const pattern = state === 'thinking'
          ? [1,1,1, 1,0,1, 1,1,1]  // anel
          : state === 'typing'
          ? [0,1,0, 1,1,1, 0,1,0]  // cruz
          : [1,1,1, 1,0,1, 1,1,1]; // anel padrão
        return (
          <g filter={`url(#glow-${size})`}>
            {pattern.map((on, i) => {
              const col = i % 3;
              const row = Math.floor(i / 3);
              return (
                <rect
                  key={i}
                  x={eyeLX + col * dotSize + 0.5}
                  y={eyeY + row * dotSize + 0.5}
                  width={dotSize - 1}
                  height={blink ? (dotSize - 1) : 1}
                  rx={1}
                  fill={on ? colors.glow : '#0a1a0a'}
                  opacity={on ? 1 : 0.15}
                />
              );
            })}
          </g>
        );
      })()}

      {/* Olho direito — espelho */}
      {(() => {
        const eyeSize = S * 0.22;
        const eyeRX = bodyX + bodyW * 0.62;
        const eyeY = bodyY + bodyH * 0.2;
        const dotSize = eyeSize / 3;
        const pattern = state === 'thinking'
          ? [1,1,1, 1,0,1, 1,1,1]
          : state === 'typing'
          ? [0,1,0, 1,1,1, 0,1,0]
          : [1,1,1, 1,0,1, 1,1,1];
        return (
          <g filter={`url(#glow-${size})`}>
            {pattern.map((on, i) => {
              const col = i % 3;
              const row = Math.floor(i / 3);
              return (
                <rect
                  key={i}
                  x={eyeRX + col * dotSize + 0.5}
                  y={eyeY + row * dotSize + 0.5}
                  width={dotSize - 1}
                  height={blink ? (dotSize - 1) : 1}
                  rx={1}
                  fill={on ? colors.glow : '#0a1a0a'}
                  opacity={on ? 1 : 0.15}
                />
              );
            })}
          </g>
        );
      })()}

      {/* ── BOCA LED ── */}
      {(() => {
        const mouthY = bodyY + bodyH * 0.58;
        const mouthX = bodyX + bodyW * 0.2;
        const mouthW = bodyW * 0.6;
        const mouthH = state === 'idle' ? S * 0.03
          : mouthOpen ? S * 0.09
          : S * 0.03;
        // Segmentos da boca (5 blocos horizontais)
        const segs = 5;
        const segW = mouthW / segs - 2;
        return (
          <g filter={`url(#glow-${size})`}>
            {Array.from({length: segs}).map((_, i) => (
              <rect
                key={i}
                x={mouthX + i * (mouthW / segs)}
                y={mouthY - mouthH / 2}
                width={segW}
                height={mouthH}
                rx={2}
                fill={colors.primary}
                opacity={i === 2 ? 1 : 0.7}
              />
            ))}
          </g>
        );
      })()}

      {/* ── PLAQUINHA "ROMA_IA" ── */}
      {(() => {
        const plateY = bodyY + bodyH * 0.72;
        const plateH = bodyH * 0.2;
        const plateX = bodyX + bodyW * 0.1;
        const plateW = bodyW * 0.8;
        return (
          <g>
            <rect
              x={plateX} y={plateY}
              width={plateW} height={plateH}
              rx={S * 0.03}
              fill="#0a1a00"
              stroke={colors.accent}
              strokeWidth={S * 0.018}
              filter={`url(#glow-${size})`}
            />
            <text
              x={bodyX + bodyW / 2}
              y={plateY + plateH * 0.72}
              textAnchor="middle"
              fontSize={plateH * 0.58}
              fontFamily="'Courier New', monospace"
              fontWeight="bold"
              fill={colors.accent}
              filter={`url(#glow-${size})`}
              letterSpacing="1"
            >
              ROMA_IA
            </text>
          </g>
        );
      })()}

      {/* ── DOTS DE "THINKING" acima da cabeça ── */}
      {state === 'thinking' && (
        <g>
          {[0,1,2].map(i => (
            <circle
              key={i}
              cx={S * (0.38 + i * 0.12)}
              cy={bodyY - S * 0.06}
              r={S * 0.03}
              fill={colors.glow}
              filter={`url(#glow-strong-${size})`}
              opacity={0.9}
            >
              <animate
                attributeName="opacity"
                values="0.2;1;0.2"
                dur="0.9s"
                begin={`${i * 0.3}s`}
                repeatCount="indefinite"
              />
              <animate
                attributeName="cy"
                values={`${bodyY - S*0.06};${bodyY - S*0.11};${bodyY - S*0.06}`}
                dur="0.9s"
                begin={`${i * 0.3}s`}
                repeatCount="indefinite"
              />
            </circle>
          ))}
        </g>
      )}

      {/* ── AURA (speaking) ── */}
      {state === 'speaking' && (
        <rect
          x={bodyX - S*0.06} y={bodyY - S*0.06}
          width={bodyW + S*0.12} height={bodyH + S*0.12}
          rx={cornerR + S*0.04}
          fill="none"
          stroke={colors.glow}
          strokeWidth={S * 0.015}
          opacity={0.5}
          filter={`url(#glow-strong-${size})`}
        >
          <animate
            attributeName="opacity"
            values="0.2;0.6;0.2"
            dur="0.8s"
            repeatCount="indefinite"
          />
        </rect>
      )}
    </svg>
  );
}
