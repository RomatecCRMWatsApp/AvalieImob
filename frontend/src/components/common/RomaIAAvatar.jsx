import React, { useState } from 'react';

const SIZES = { sm: 44, md: 72, lg: 108 };

const STATE_STYLES = {
  idle: { opacity: 1, borderColor: 'transparent', boxShadow: 'none' },
  thinking: { opacity: 0.9, borderColor: 'transparent', boxShadow: 'none' },
  typing: { opacity: 0.95, borderColor: 'transparent', boxShadow: 'none' },
  speaking: { 
    opacity: 1, 
    borderColor: '#00FF88', 
    boxShadow: '0 0 12px rgba(0, 255, 136, 0.4), 0 0 24px rgba(0, 255, 136, 0.2)'
  },
};

export default function RomaIAAvatar({ state = 'idle', size = 'md', className = '' }) {
  const pixelSize = SIZES[size];
  const [loaded, setLoaded] = useState(false);
  const styles = STATE_STYLES[state] || STATE_STYLES.idle;

  return (
    <div
      className={`relative inline-flex items-center justify-center rounded-lg overflow-hidden ${className}`}
      style={{
        width: pixelSize,
        height: pixelSize,
        opacity: loaded ? styles.opacity : 0.5,
        transition: 'opacity 0.3s ease',
      }}
    >
      {/* Placeholder/Loader */}
      {!loaded && (
        <div 
          className="absolute inset-0 bg-emerald-900/30 animate-pulse rounded-lg"
          style={{ zIndex: 1 }}
        />
      )}
      
      {/* Avatar WebP Animado */}
      <img
        src="/brand/roma_ia_animated.webp"
        alt="Roma_IA - Assistente de Avaliação Imobiliária"
        width={pixelSize}
        height={pixelSize}
        onLoad={() => setLoaded(true)}
        className="rounded-lg"
        style={{
          width: pixelSize,
          height: pixelSize,
          objectFit: 'cover',
          border: `2px solid ${styles.borderColor}`,
          boxShadow: styles.boxShadow,
          transition: 'border-color 0.3s ease, box-shadow 0.3s ease',
        }}
      />
    </div>
  );
}
