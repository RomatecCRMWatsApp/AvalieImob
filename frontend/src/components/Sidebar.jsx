/**
 * Sidebar Dark Elegante — AvalieImob / Romatec (Opção 2 aprovada)
 * Adaptada ao projeto real: react-router-dom, menu completo do AvalieImob,
 * badge real de PTAM, logout via AuthContext, gatilho Roma_IA.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import {
  LayoutDashboard, Users, Building2, BarChart3, FileCheck2, Shield, Beef, Home,
  ClipboardCheck, FileText, FileSignature, Receipt, Sparkles, FileSearch, Award,
  CreditCard, Settings, LogOut, Globe, Search, Palette, Tag,
} from 'lucide-react';
import { ptamAPI } from '../lib/api';

// ── Tokens ─────────────────────────────────────────────────────────────────
const T = {
  bg: '#0F1A10',
  bgHover: '#172318',
  bgActive: 'rgba(27,94,32,0.35)',
  bgLogo: '#1B5E20',
  borderActive: '#4CAF50',
  borderDiv: 'rgba(255,255,255,0.06)',
  borderLogo: 'rgba(255,255,255,0.15)',
  textMuted: 'rgba(255,255,255,0.45)',
  textSection: 'rgba(255,255,255,0.22)',
  textActive: '#C8E6C9',
  iconInactive: 'rgba(255,255,255,0.32)',
  iconActive: '#81C784',
  gold: '#B8860B',
};

// ── Menu real do AvalieImob (rotas /dashboard/*) ─────────────────────────────
const MENU = [
  { section: null, items: [
    { id: 'dashboard', label: 'Visão Geral', icon: LayoutDashboard, route: '/dashboard', end: true },
  ]},
  { section: 'Cadastros', items: [
    { id: 'clientes', label: 'Clientes', icon: Users, route: '/dashboard/clientes' },
    { id: 'imoveis', label: 'Imóveis e Garantias', icon: Building2, route: '/dashboard/imoveis' },
    { id: 'amostras', label: 'Amostras', icon: BarChart3, route: '/dashboard/amostras' },
  ]},
  { section: 'Laudos', items: [
    { id: 'ptam', label: 'PTAM (Laudos)', icon: FileCheck2, route: '/dashboard/ptam', notifKey: 'ptam' },
    { id: 'garantias', label: 'Aval. de Garantias', icon: Shield, route: '/dashboard/garantias' },
    { id: 'semoventes', label: 'Semoventes', icon: Beef, route: '/dashboard/semoventes' },
    { id: 'locacao', label: 'Aval. Locação', icon: Home, route: '/dashboard/locacao' },
    { id: 'tvi', label: 'Kit TVI', icon: ClipboardCheck, route: '/dashboard/tvi' },
    { id: 'laudos', label: 'Avaliações', icon: FileText, route: '/dashboard/laudos' },
  ]},
  { section: 'Contratos', items: [
    { id: 'contratos', label: 'Contratos', icon: FileSignature, route: '/dashboard/contratos', tag: 'NOVO' },
    { id: 'recibos', label: 'Recibos', icon: Receipt, route: '/dashboard/recibos', tag: 'NOVO' },
  ]},
  { section: 'Ferramentas', items: [
    { id: 'ia', label: 'Roma_IA', icon: Sparkles, route: '/dashboard/ia' },
    { id: 'cnd', label: 'Certidões CND', icon: FileSearch, route: '/dashboard/cnd' },
    { id: 'incra', label: 'Tabelas INCRA', icon: BarChart3, route: '/dashboard/admin/incra' },
  ]},
  { section: 'Conta', items: [
    { id: 'curriculo', label: 'Meu Currículo', icon: Award, route: '/dashboard/curriculo' },
    { id: 'marca', label: 'Marca (White-label)', icon: Palette, route: '/dashboard/marca', tag: 'NOVO' },
    { id: 'assinatura', label: 'Assinatura', icon: CreditCard, route: '/dashboard/assinatura' },
    { id: 'config', label: 'Configurações', icon: Settings, route: '/dashboard/config' },
  ]},
];

function isActive(pathname, item) {
  if (item.end) return pathname === item.route;
  return pathname === item.route || pathname.startsWith(item.route + '/');
}

function NavItem({ item, active, notification, tag, onClick }) {
  const [hovered, setHovered] = useState(false);
  const Icon = item.icon;
  return (
    <div
      role="button"
      tabIndex={0}
      aria-current={active ? 'page' : undefined}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '9px 16px',
        cursor: 'pointer', transition: 'background 0.15s ease',
        background: active ? T.bgActive : hovered ? T.bgHover : 'transparent',
        borderLeft: active ? `2px solid ${T.borderActive}` : '2px solid transparent',
        position: 'relative', userSelect: 'none', outline: 'none',
      }}
    >
      {active && (
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 60,
          background: 'linear-gradient(90deg, rgba(76,175,80,0.08) 0%, transparent 100%)',
          pointerEvents: 'none' }} />
      )}
      <span style={{ color: active ? T.iconActive : hovered ? 'rgba(255,255,255,0.55)' : T.iconInactive,
        display: 'flex', flexShrink: 0, transition: 'color 0.15s ease' }}>
        <Icon size={18} strokeWidth={1.6} />
      </span>
      <span style={{ fontSize: 13, color: active ? T.textActive : hovered ? 'rgba(255,255,255,0.6)' : T.textMuted,
        fontWeight: active ? 500 : 400, transition: 'color 0.15s ease', flex: 1 }}>
        {item.label}
      </span>
      {notification > 0 && (
        <div style={{ background: T.gold, color: '#fff', fontSize: 10, fontWeight: 600,
          minWidth: 18, height: 18, borderRadius: 99, display: 'flex', alignItems: 'center',
          justifyContent: 'center', padding: '0 5px', boxShadow: '0 0 8px rgba(184,134,11,0.4)' }}>
          {notification}
        </div>
      )}
      {tag && notification <= 0 && (
        <div style={{ background: 'rgba(76,175,80,0.18)', color: '#A5D6A7', fontSize: 8.5,
          fontWeight: 700, letterSpacing: '0.5px', padding: '2px 6px', borderRadius: 5 }}>
          {tag}
        </div>
      )}
    </div>
  );
}

function Divider() {
  return <div style={{ height: 1, background: T.borderDiv, margin: '6px 0' }} />;
}

export default function Sidebar({
  user = {},
  onLogout = () => {},
  onNavigate = () => {},
  width = 240,
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const [ptamCount, setPtamCount] = useState(0);

  useEffect(() => {
    let alive = true;
    ptamAPI.list()
      .then((rows) => { if (alive) setPtamCount(Array.isArray(rows) ? rows.length : 0); })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  const notifications = { ptam: ptamCount };
  const name = user?.name || 'Usuário';
  const role = user?.role || 'Avaliador';
  const initials = name.split(' ').filter(Boolean).slice(0, 2).map((n) => n[0]).join('').toUpperCase() || 'U';

  const go = (route) => { navigate(route); onNavigate(); };

  // Item exclusivo de admin/CEO: Cupons Promocionais.
  const isAdmin = ['admin', 'owner', 'ceo'].includes(String(user?.role || '').toLowerCase());
  const menu = MENU.map((g) =>
    g.section === 'Ferramentas' && isAdmin
      ? { ...g, items: [...g.items, { id: 'cupons', label: 'Cupons Promo', icon: Tag, route: '/dashboard/admin/cupons' }] }
      : g
  );

  return (
    <nav aria-label="Menu principal" style={{
      width, minWidth: width, height: '100vh', background: T.bg, display: 'flex',
      flexDirection: 'column', fontFamily: "'DM Sans', system-ui, -apple-system, sans-serif",
      overflowY: 'auto', overflowX: 'hidden',
    }}>
      {/* Logo */}
      <div style={{ paddingTop: 18 }}>
        <div style={{ padding: '0 16px 16px' }}>
          <Link to="/dashboard" onClick={onNavigate} style={{ textDecoration: 'none' }}>
            <div style={{ background: T.bgLogo, borderRadius: 10, padding: '10px 14px',
              display: 'flex', alignItems: 'center', gap: 10, border: `1px solid ${T.borderLogo}` }}>
              <div style={{ width: 32, height: 32, background: 'rgba(255,255,255,0.12)', borderRadius: 8,
                display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#C8E6C9', flexShrink: 0 }}>
                <Home size={20} strokeWidth={1.8} />
              </div>
              <div>
                <div style={{ color: '#fff', fontSize: 14, fontWeight: 600, letterSpacing: '0.2px' }}>AvalieImob</div>
                <div style={{ color: 'rgba(255,255,255,0.45)', fontSize: 10, marginTop: 1 }}>Romatec · PTAM · Laudos</div>
              </div>
            </div>
          </Link>
        </div>
        <Divider />
      </div>

      {/* Menu */}
      <div style={{ flex: 1, paddingTop: 4 }}>
        {menu.map((group, gi) => (
          <div key={gi}>
            {group.section && (
              <>
                {gi > 0 && <Divider />}
                <div style={{ fontSize: 9, fontWeight: 600, letterSpacing: '1.2px',
                  color: T.textSection, textTransform: 'uppercase', padding: '10px 16px 4px' }}>
                  {group.section}
                </div>
              </>
            )}
            {group.items.map((item) => (
              <NavItem
                key={item.id}
                item={item}
                active={isActive(location.pathname, item)}
                notification={item.notifKey ? (notifications[item.notifKey] || 0) : 0}
                tag={item.tag}
                onClick={() => go(item.route)}
              />
            ))}
          </div>
        ))}

        {/* Nossos Serviços (site público) */}
        <div style={{ borderTop: `1px solid ${T.borderDiv}`, marginTop: 6 }}>
          <NavItem
            item={{ id: 'site', label: 'Nossos Serviços', icon: Globe, route: '/' }}
            active={false}
            notification={0}
            onClick={() => go('/')}
          />
        </div>
      </div>

      {/* Rodapé: usuário + logout */}
      <div style={{ padding: '12px 16px', borderTop: `1px solid ${T.borderDiv}`,
        display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 32, height: 32, borderRadius: '50%', background: T.bgLogo,
          border: '1px solid rgba(76,175,80,0.3)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', fontSize: 11, fontWeight: 600, color: '#C8E6C9', flexShrink: 0 }}>
          {initials}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 500, color: 'rgba(255,255,255,0.75)',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{name}</div>
          <div style={{ fontSize: 10, color: T.textMuted, textTransform: 'capitalize' }}>{role}</div>
        </div>
        <button onClick={onLogout} title="Sair da conta" style={{ background: 'none', border: 'none',
          cursor: 'pointer', color: 'rgba(255,255,255,0.25)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', padding: 4, borderRadius: 6, flexShrink: 0 }}
          onMouseEnter={(e) => { e.currentTarget.style.color = '#ef5350'; e.currentTarget.style.background = 'rgba(239,83,80,0.1)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.25)'; e.currentTarget.style.background = 'none'; }}>
          <LogOut size={16} strokeWidth={1.6} />
        </button>
      </div>
    </nav>
  );
}
