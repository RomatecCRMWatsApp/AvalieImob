// TopBar — cabeçalho compacto do painel (upgrade visual verde/dourado/creme).
// Busca, atualização, Ferramentas, Novidades e conta. Data, localização e versão
// ficam no menu da conta (antes: relógio + data + local + versão repetidos).
import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Menu, RefreshCw, Bell, ChevronDown, MapPin, CalendarDays, Info, User, LogOut } from 'lucide-react';
import { BUILD_NUMBER } from '../version';
import { BrandMark } from './brand/BrandMark';
import ToolsLauncher from './shell/ToolsLauncher';

// Detecta nova versão publicada: consulta /version.json (sem cache) e compara
// o build publicado com o build carregado nesta sessão.
function useUpdateAvailable() {
  const [disponivel, setDisponivel] = useState(false);
  useEffect(() => {
    let alive = true;
    const check = async () => {
      try {
        const r = await fetch(`/version.json?_=${Date.now()}`, { cache: 'no-store' });
        if (!r.ok) return;
        const data = await r.json();
        if (alive && Number(data.build) > Number(BUILD_NUMBER)) setDisponivel(true);
      } catch { /* offline/erro — ignora */ }
    };
    check();
    const t = setInterval(check, 60000);
    const onFocus = () => check();
    window.addEventListener('focus', onFocus);
    return () => { alive = false; clearInterval(t); window.removeEventListener('focus', onFocus); };
  }, []);
  return disponivel;
}

// Reload limpo: remove service worker + caches e recarrega na versão nova.
async function aplicarAtualizacao() {
  try {
    if ('serviceWorker' in navigator) {
      const regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map((r) => r.unregister()));
    }
    if (window.caches) {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
    }
  } catch { /* segue para o reload mesmo assim */ }
  window.location.reload(true);
}

function useLocalizacao() {
  const [local, setLocal] = useState('Açailândia, MA');
  useEffect(() => {
    if (!navigator.geolocation) return;
    let cancelled = false;
    const buscar = () => {
      if (cancelled) return;
      navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        // Só confia na localização quando a precisão é boa (GPS, ~celular). No desktop a
        // geolocalização usa IP/Wi-Fi e cai na cidade do PROVEDOR (ex.: Fortaleza/CE) —
        // nesse caso (precisão > 3km) mantém o padrão "Açailândia, MA".
        if (coords.accuracy && coords.accuracy > 3000) return;
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${coords.latitude}&lon=${coords.longitude}&format=json&accept-language=pt-BR`
          );
          const data = await res.json();
          const a = data?.address || {};
          const cidade = a.city || a.town || a.municipality || a.village || '';
          const iso = a['ISO3166-2-lvl4'] ? String(a['ISO3166-2-lvl4']).split('-')[1] : '';
          const estado = iso || a.state || '';
          if (cidade && !cancelled) setLocal(estado ? `${cidade}, ${estado}` : cidade);
        } catch { /* mantém fallback */ }
      },
        () => { /* sem permissão → fallback */ },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 600000 }
      );
    };
    // Só busca a localização se o usuário JÁ concedeu permissão antes — evita o
    // prompt de localização a cada carregamento e o "[Violation]" no console
    // quando a Permissions-Policy não permite. Se a Permissions API não existir,
    // mantém só o fallback "Açailândia, MA".
    if (navigator.permissions?.query) {
      navigator.permissions.query({ name: 'geolocation' })
        .then((status) => { if (status.state === 'granted') buscar(); })
        .catch(() => { /* sem Permissions API → mantém fallback */ });
    }
    return () => { cancelled = true; };
  }, []);
  return local;
}


const formatDate = (d) => d.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' });

function AccountMenu({ user, version, deployDate, onProfile, onLogout }) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);
  const btnRef = useRef(null);
  const localizacao = useLocalizacao();
  const nome = user?.name || 'Usuário';
  const iniciais = user?.initials
    || (nome.split(' ').filter(Boolean).slice(0, 2).map((n) => n[0]).join('').toUpperCase() || 'U');

  useEffect(() => {
    if (!open) return undefined;
    const fora = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false); };
    const tecla = (e) => { if (e.key === 'Escape') { setOpen(false); btnRef.current?.focus(); } };
    document.addEventListener('mousedown', fora);
    document.addEventListener('keydown', tecla);
    return () => { document.removeEventListener('mousedown', fora); document.removeEventListener('keydown', tecla); };
  }, [open]);

  const info = { display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--av-text-secondary)', padding: '2px 0' };

  return (
    <div ref={wrapRef} style={{ position: 'relative' }}>
      <button
        ref={btnRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Conta de ${nome}`}
        aria-haspopup="menu"
        aria-expanded={open}
        className="av-icon-btn"
        style={{ width: 'auto', padding: '0 8px 0 4px', gap: 8 }}
      >
        <span style={{
          width: 34, height: 34, borderRadius: 999, background: 'var(--av-brand)', color: 'var(--av-gold)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700,
        }}>{iniciais}</span>
        <span className="hidden md:inline" style={{ fontSize: 14, fontWeight: 500, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {nome.split(' ')[0]}
        </span>
        <ChevronDown size={14} aria-hidden="true" className="hidden md:inline" />
      </button>

      {open && (
        <div role="menu" aria-label="Conta" className="av-popover" style={{ minWidth: 260 }}>
          <div style={{ padding: '10px 12px 8px', borderBottom: '1px solid var(--av-border)', marginBottom: 4 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{nome}</div>
            <div style={{ fontSize: 12, color: 'var(--av-text-secondary)', textTransform: 'capitalize' }}>{user?.role || 'Avaliador'}</div>
            <div style={{ marginTop: 8 }}>
              <div style={info}><CalendarDays size={14} aria-hidden="true" /> <span style={{ textTransform: 'capitalize' }}>{formatDate(new Date())}</span></div>
              <div style={info}><MapPin size={14} aria-hidden="true" /> {localizacao}</div>
            </div>
          </div>
          <button type="button" role="menuitem" className="av-menu-item" onClick={() => { setOpen(false); onProfile && onProfile(); }}>
            <User size={16} aria-hidden="true" /> Meu perfil
          </button>
          <Link role="menuitem" to="/dashboard/novidades" className="av-menu-item" onClick={() => setOpen(false)}>
            <Info size={16} aria-hidden="true" />
            <span>Novidades<small>Versão {version}{deployDate ? ` · ${deployDate}` : ''}</small></span>
          </Link>
          <div style={{ height: 1, background: 'var(--av-border)', margin: '4px 8px' }} />
          <button type="button" role="menuitem" className="av-menu-item" style={{ color: '#a52a2a' }} onClick={() => { setOpen(false); onLogout && onLogout(); }}>
            <LogOut size={16} aria-hidden="true" /> Sair da conta
          </button>
        </div>
      )}
    </div>
  );
}

export default function TopBar({
  version = 'v1.0',
  deployDate = '',
  onMenu,
  menuOpen = false,
  menuButtonRef,
  searchSlot,
  onNotif,
  notifCount = 0,
  user = { name: 'Usuário', role: 'Admin', initials: 'U' },
  onLogout,
  onProfile,
}) {
  const updateAvailable = useUpdateAvailable();

  return (
    <header className="av-header" aria-label="Cabeçalho do painel">
      <div style={{ minHeight: 64, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }} className="px-4 lg:px-6">
        {onMenu && (
          <button
            ref={menuButtonRef}
            type="button"
            onClick={onMenu}
            aria-label="Abrir menu"
            aria-expanded={menuOpen}
            aria-controls="av-menu-principal"
            className="av-icon-btn av-menu-btn"
          >
            <Menu size={20} aria-hidden="true" />
          </button>
        )}

        {/* Logo oficial no mobile/tablet (no desktop ele está na sidebar) */}
        <Link to="/dashboard" className="lg:hidden flex items-center gap-2 min-w-0" style={{ textDecoration: 'none', color: 'var(--av-text)' }} aria-label="AvalieImob — Visão geral">
          <BrandMark variant="badge" size={32} title="AvalieImob" />
          <span className="hidden min-[420px]:inline" style={{ fontWeight: 700, fontSize: 16, letterSpacing: '-0.01em' }}>AvalieImob</span>
        </Link>

        {/* Busca: no desktop fica no cabeçalho; no mobile ganha linha própria */}
        <div className="order-last basis-full pb-3 sm:order-none sm:basis-auto sm:pb-0 sm:flex-1 flex" style={{ minWidth: 0, maxWidth: 480 }}>{searchSlot}</div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0, marginLeft: 'auto', minHeight: 64 }}>
          {updateAvailable && (
            <button
              type="button"
              onClick={aplicarAtualizacao}
              title="Nova versão disponível — clique para atualizar"
              className="av-btn av-btn-gold"
              style={{ minHeight: 44, padding: '0 12px' }}
            >
              <RefreshCw size={15} aria-hidden="true" /> <span className="hidden md:inline">Atualizar</span>
              <span className="md:hidden sr-only">Atualizar</span>
            </button>
          )}
          <ToolsLauncher />
          <button type="button" onClick={onNotif} aria-label={notifCount > 0 ? `Novidades (${notifCount} não lidas)` : 'Novidades'} className="av-icon-btn">
            <Bell size={18} aria-hidden="true" />
            {notifCount > 0 && (
              <span aria-hidden="true" style={{ position: 'absolute', top: 9, right: 10, width: 8, height: 8, background: 'var(--av-gold)', borderRadius: '50%', boxShadow: '0 0 0 2px #fff' }} />
            )}
          </button>
          <AccountMenu user={user} version={version} deployDate={deployDate} onProfile={onProfile} onLogout={onLogout} />
        </div>
      </div>

    </header>
  );
}
