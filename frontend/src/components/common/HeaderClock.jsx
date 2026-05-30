// @module HeaderClock — relógio digital + data PT-BR + cidade/UF do perfil logado.
// Estilo terminal verde sobre barra escura. Atualiza a cada segundo.
import React, { useState, useEffect } from 'react';
import { perfilAPI } from '../../lib/api';

const DIAS = ['DOM', 'SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB'];
const MESES = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'];
const p2 = (n) => String(n).padStart(2, '0');

export default function HeaderClock() {
  const [now, setNow] = useState(new Date());
  const [local, setLocal] = useState('');

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let alive = true;
    perfilAPI.get()
      .then((pf) => {
        if (!alive || !pf) return;
        const c = (pf.cidade || '').trim();
        const u = (pf.uf || '').trim();
        if (c || u) setLocal(c && u ? `${c}/${u}` : (c || u));
      })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  const hh = p2(now.getHours());
  const mm = p2(now.getMinutes());
  const ss = p2(now.getSeconds());
  const data = `${DIAS[now.getDay()]}, ${p2(now.getDate())} DE ${MESES[now.getMonth()]} DE ${now.getFullYear()}`;

  return (
    <div
      title="Hora local do sistema"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 11,
        background: 'linear-gradient(135deg, #08110b 0%, #0e1a12 100%)',
        border: '1px solid rgba(76,175,80,0.28)',
        borderRadius: 10,
        padding: '5px 14px',
        fontFamily: "'Share Tech Mono', 'Consolas', 'Courier New', monospace",
        boxShadow: 'inset 0 0 14px rgba(0,0,0,0.55), 0 0 0 1px rgba(0,0,0,0.03)',
        userSelect: 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
        <span style={{
          color: '#5ee08a', fontSize: 20, fontWeight: 700, letterSpacing: '1px',
          textShadow: '0 0 9px rgba(94,224,138,0.65)',
        }}>
          {hh}:{mm}
        </span>
        <span style={{
          color: 'rgba(94,224,138,0.75)', fontSize: 12, fontWeight: 700,
          textShadow: '0 0 6px rgba(94,224,138,0.45)',
        }}>
          :{ss}
        </span>
      </div>

      <div style={{ width: 1, height: 26, background: 'rgba(76,175,80,0.22)' }} />

      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
        <span style={{
          color: 'rgba(200,230,201,0.9)', fontSize: 9.5, fontWeight: 600, letterSpacing: '1.4px',
        }}>
          {data}
        </span>
        <span style={{ color: 'rgba(94,224,138,0.8)', fontSize: 9, letterSpacing: '0.6px' }}>
          ◍ {local || '—'}
        </span>
      </div>
    </div>
  );
}
