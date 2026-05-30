// TopBar Dark Elegante — AvalieImob / Romatec (adaptado para React/CRA).
// Relógio neon + pill dourada de localização (geolocalização via Nominatim).
import React, { useEffect, useState, useRef } from 'react';
import { Menu } from 'lucide-react';

const T = {
  bg: '#0F1A10', bgSearch: 'rgba(255,255,255,0.05)', bgClock: '#0A1A0B', bgAvatar: '#1B5E20',
  bgVer: 'rgba(255,255,255,0.05)', borderMain: 'rgba(255,255,255,0.06)', borderSearch: 'rgba(255,255,255,0.08)',
  borderClock: '#1B5E20', borderAvatar: 'rgba(76,175,80,0.3)', borderLoc: 'rgba(184,134,11,0.25)',
  bgLoc: 'rgba(184,134,11,0.12)', green: '#4CAF50', greenDim: '#2E7D32', gold: '#B8860B',
  goldText: '#D4A017', textDate: 'rgba(255,255,255,0.35)', textVer: 'rgba(255,255,255,0.25)',
  avatarText: '#C8E6C9',
};

const IconMapPin = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" />
  </svg>
);
const IconBell = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" />
  </svg>
);
const IconChevron = () => (
  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

const PAD = (n) => String(n).padStart(2, '0');
const DIAS = ['DOM', 'SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB'];
const MESES = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'];
const formatDate = (d) => `${DIAS[d.getDay()]}, ${PAD(d.getDate())} ${MESES[d.getMonth()]} ${d.getFullYear()}`;

function useLocalizacao() {
  const [local, setLocal] = useState('Açailândia, MA');
  useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${coords.latitude}&lon=${coords.longitude}&format=json&accept-language=pt-BR`
          );
          const data = await res.json();
          const a = data?.address || {};
          const cidade = a.city || a.town || a.municipality || a.village || '';
          const iso = a['ISO3166-2-lvl4'] ? String(a['ISO3166-2-lvl4']).split('-')[1] : '';
          const estado = iso || a.state || '';
          if (cidade) setLocal(estado ? `${cidade}, ${estado}` : cidade);
        } catch { /* mantém fallback */ }
      },
      () => { /* sem permissão → fallback */ }
    );
  }, []);
  return local;
}

const dropBtn = {
  width: '100%', padding: '9px 14px', background: 'none', border: 'none',
  textAlign: 'left', fontSize: 13, cursor: 'pointer', display: 'block',
};

export default function TopBar({
  version = 'v1.0',
  deployDate = '',
  onMenu,
  searchSlot,
  onNotif,
  notifCount = 0,
  user = { name: 'Usuário', role: 'Admin', initials: 'U' },
  onLogout,
  onProfile,
}) {
  const [now, setNow] = useState(new Date());
  const [menuOpen, setMenu] = useState(false);
  const [compacto, setCompacto] = useState(false);
  const menuRef = useRef(null);
  const localizacao = useLocalizacao();

  // Mostra a faixa extra (data/local/versao) só abaixo de lg (1024px), espelhando
  // os utilitarios `lg:` da barra principal. Evita duplicacao no desktop.
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(max-width: 1023px)');
    const upd = () => setCompacto(mq.matches);
    upd();
    if (mq.addEventListener) mq.addEventListener('change', upd);
    else mq.addListener(upd);
    return () => {
      if (mq.removeEventListener) mq.removeEventListener('change', upd);
      else mq.removeListener(upd);
    };
  }, []);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    const handler = (e) => { if (menuRef.current && !menuRef.current.contains(e.target)) setMenu(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const hh = PAD(now.getHours());
  const mm = PAD(now.getMinutes());
  const ss = PAD(now.getSeconds());
  const nome = user?.name || 'Usuário';
  const iniciais = user?.initials
    || (nome.split(' ').filter(Boolean).slice(0, 2).map((n) => n[0]).join('').toUpperCase() || 'U');

  return (
    <div style={{ position: 'sticky', top: 0, zIndex: 100 }}>
    <header
      aria-label="Barra de navegação principal"
      style={{
        height: 52, background: T.bg, borderBottom: `1px solid ${T.borderMain}`,
        display: 'flex', alignItems: 'center', padding: '0 12px', gap: 10,
        fontFamily: "'DM Sans', system-ui, sans-serif",
      }}
    >
      {onMenu && (
        <button onClick={onMenu} aria-label="Abrir menu" className="lg:hidden" style={{
          width: 34, height: 34, background: T.bgSearch, border: `1px solid ${T.borderSearch}`,
          borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'rgba(255,255,255,0.6)', flexShrink: 0, cursor: 'pointer',
        }}>
          <Menu size={18} />
        </button>
      )}

      {/* Busca real (GlobalSearch) */}
      <div style={{ flex: 1, maxWidth: 360, minWidth: 0 }}>{searchSlot}</div>

      {/* Centro: relógio + data + localização */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, minWidth: 0 }}>
        <div role="timer" aria-label={`Horário ${hh}:${mm}:${ss}`} style={{
          background: T.bgClock, border: `1px solid ${T.borderClock}`, borderRadius: 8,
          padding: '5px 12px', display: 'flex', alignItems: 'baseline', gap: 2, flexShrink: 0,
        }}>
          <span style={{ fontSize: 20, fontWeight: 600, color: T.green, fontFamily: "'Courier New', monospace", letterSpacing: '2px', lineHeight: 1 }}>
            {hh}:{mm}
          </span>
          <span style={{ fontSize: 12, color: T.greenDim, fontFamily: "'Courier New', monospace" }}>:{ss}</span>
        </div>
        <span className="hidden xl:inline" style={{ fontSize: 11, color: T.textDate, letterSpacing: '0.5px', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>
          {formatDate(now)}
        </span>
        <div className="hidden lg:flex" style={{
          background: T.bgLoc, border: `1px solid ${T.borderLoc}`, borderRadius: 99,
          padding: '4px 12px', alignItems: 'center', gap: 6, whiteSpace: 'nowrap',
        }}>
          <span style={{ color: T.gold, display: 'flex' }}><IconMapPin /></span>
          <span style={{ fontSize: 12, color: T.goldText, fontWeight: 500 }}>{localizacao}</span>
        </div>
      </div>

      {/* Direita: versão + sino + avatar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <span className="hidden sm:inline" style={{
          fontSize: 11, fontWeight: 700, color: T.goldText, background: T.bgLoc, padding: '3px 10px',
          borderRadius: 99, border: `1px solid ${T.borderLoc}`, whiteSpace: 'nowrap', letterSpacing: '0.3px',
          boxShadow: '0 0 0 1px rgba(184,134,11,0.06)',
        }}>
          {version}{deployDate ? ` · ${deployDate}` : ''}
        </span>

        <button onClick={onNotif} aria-label="Notificações" style={{
          width: 32, height: 32, background: T.bgSearch, border: `1px solid ${T.borderSearch}`,
          borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
          position: 'relative', cursor: 'pointer', color: 'rgba(255,255,255,0.5)', flexShrink: 0,
        }}>
          <IconBell />
          {notifCount > 0 && (
            <span style={{ position: 'absolute', top: 6, right: 6, width: 6, height: 6, background: T.gold, borderRadius: '50%', boxShadow: `0 0 0 1.5px ${T.bg}` }} />
          )}
        </button>

        <div ref={menuRef} style={{ position: 'relative' }}>
          <button onClick={() => setMenu((v) => !v)} aria-label="Menu do usuário" aria-expanded={menuOpen} style={{
            display: 'flex', alignItems: 'center', gap: 7, background: T.bgSearch,
            border: `1px solid ${T.borderSearch}`, borderRadius: 8, padding: '4px 10px 4px 4px',
            cursor: 'pointer', color: T.avatarText,
          }}>
            <div style={{
              width: 26, height: 26, background: T.bgAvatar, border: `1px solid ${T.borderAvatar}`,
              borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 10, fontWeight: 600, flexShrink: 0,
            }}>{iniciais}</div>
            <span className="hidden sm:inline" style={{ fontSize: 12, fontWeight: 500, color: 'rgba(255,255,255,0.7)', maxWidth: 90, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {nome.split(' ')[0]}
            </span>
            <span style={{ color: 'rgba(255,255,255,0.25)', display: 'flex', marginLeft: 2 }}><IconChevron /></span>
          </button>

          {menuOpen && (
            <div style={{
              position: 'absolute', top: 'calc(100% + 6px)', right: 0, background: '#111E12',
              border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, minWidth: 190, zIndex: 200,
              overflow: 'hidden', boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
            }}>
              <div style={{ padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: '#E8F5E9' }}>{nome}</div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginTop: 2 }}>{user?.role || 'Admin'}</div>
              </div>
              <button
                onClick={() => { if (onProfile) onProfile(); setMenu(false); }}
                style={{ ...dropBtn, color: 'rgba(255,255,255,0.55)' }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
              >
                Meu perfil
              </button>
              <div style={{ height: 1, background: 'rgba(255,255,255,0.06)' }} />
              <button
                onClick={() => { if (onLogout) onLogout(); setMenu(false); }}
                style={{ ...dropBtn, color: '#ef5350' }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(239,83,80,0.08)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
              >
                Sair da conta
              </button>
            </div>
          )}
        </div>
      </div>
    </header>

      {/* Faixa compacta (abaixo de lg): data, localização e versão */}
      {compacto && (
      <div style={{
        background: T.bg, borderBottom: `1px solid ${T.borderMain}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 12, padding: '4px 10px', flexWrap: 'wrap',
        fontFamily: "'DM Sans', system-ui, sans-serif",
      }}>
        <span style={{ fontSize: 10, color: T.textDate, letterSpacing: '0.4px', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>
          {formatDate(now)}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: T.goldText }}>
          <IconMapPin />
          <span style={{ fontSize: 10.5, fontWeight: 500, whiteSpace: 'nowrap' }}>{localizacao}</span>
        </span>
        <span style={{ fontSize: 10, color: T.goldText, fontWeight: 600, whiteSpace: 'nowrap' }}>
          {version}{deployDate ? ` · ${deployDate}` : ''}
        </span>
      </div>
      )}
    </div>
  );
}
