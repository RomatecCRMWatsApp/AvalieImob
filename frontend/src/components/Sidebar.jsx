/**
 * Sidebar — menu principal do painel (upgrade visual verde premium / dourado).
 * Mesmas rotas, mesmos itens e mesma regra de admin do menu anterior; muda só a
 * apresentação: grupos por finalidade, recolhíveis, item ativo com marcador
 * dourado e alvos de 44px. Usada na lateral (desktop) e no drawer (mobile).
 */
import React, { useEffect, useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  LayoutDashboard, Users, Building2, BarChart3, FileCheck2, Shield, Beef, Home,
  ClipboardCheck, FileText, FileSignature, Receipt, Sparkles, FileSearch, Award,
  CreditCard, Settings, LogOut, Globe, Palette, Tag, BadgeCheck, Stamp, Inbox, Calculator,
  Compass, MapPin, Send, Megaphone, Mail, Radar, Instagram, Bell, KeyRound, HardHat,
  ChevronDown, X, Layers, CalendarClock, Cpu,
} from 'lucide-react';
import { ptamAPI } from '../lib/api';
import { BrandMark } from './brand/BrandMark';
import AvatarPerfil from './shell/AvatarPerfil';

// ── Menu do AvalieImob (rotas reais /dashboard/*), agrupado por finalidade ──
const MENU = [
  { id: 'overview', section: null, items: [
    { id: 'dashboard', label: 'Visão geral', icon: LayoutDashboard, route: '/dashboard', end: true },
  ]},
  { id: 'cadastros', section: 'Cadastros', items: [
    { id: 'clientes', label: 'Clientes', icon: Users, route: '/dashboard/clientes' },
    { id: 'imoveis', label: 'Imóveis e garantias', icon: Building2, route: '/dashboard/imoveis' },
    { id: 'amostras', label: 'Amostras', icon: BarChart3, route: '/dashboard/amostras' },
  ]},
  { id: 'laudos', section: 'Laudos e avaliações', items: [
    { id: 'processos', label: 'Processos e agenda', icon: CalendarClock, route: '/dashboard/processos' },
    { id: 'ptam', label: 'PTAM e laudos', icon: FileCheck2, route: '/dashboard/ptam', countKey: 'ptam',
      // o tratamento científico (regressão) é aberto de dentro do PTAM — passo 11
      alias: ['/dashboard/inferencia'] },
    { id: 'garantias', label: 'Avaliação de garantias', icon: Shield, route: '/dashboard/garantias' },
    { id: 'semoventes', label: 'Semoventes', icon: Beef, route: '/dashboard/semoventes' },
    { id: 'locacao', label: 'Avaliação de locação', icon: Home, route: '/dashboard/locacao' },
    { id: 'tvi', label: 'Kit TVI', icon: ClipboardCheck, route: '/dashboard/tvi' },
    { id: 'laudos', label: 'Avaliações', icon: FileText, route: '/dashboard/laudos' },
  ]},
  { id: 'documentos', section: 'Contratos e documentos', items: [
    { id: 'propostas', label: 'Propostas', icon: FileText, route: '/dashboard/propostas' },
    { id: 'contratos', label: 'Contratos', icon: FileSignature, route: '/dashboard/contratos' },
    { id: 'exclusividade', label: 'Exclusividade', icon: BadgeCheck, route: '/dashboard/contratos-exclusivos' },
    { id: 'documentos', label: 'Assinar documentos', icon: Stamp, route: '/dashboard/documentos' },
    { id: 'documentos-externos', label: 'Documentos externos', icon: Send, route: '/dashboard/documentos-externos' },
    { id: 'recibos', label: 'Recibos', icon: Receipt, route: '/dashboard/recibos' },
  ]},
  { id: 'geo', section: 'Geoespacial', items: [
    { id: 'georef', label: 'Georreferenciamento', icon: Compass, route: '/dashboard/topografia/georef' },
    { id: 'geo-urbano', label: 'Geo urbano', icon: MapPin, route: '/dashboard/topografia/geo-urbano' },
    { id: 'onr-sigri', label: 'Arquivo ONR (SIG-RI)', icon: Layers, route: '/dashboard/topografia/onr-sigri' },
    { id: 'inss-obra', label: 'INSS de obra', icon: HardHat, route: '/dashboard/inss-obra' },
  ]},
  { id: 'ferramentas', section: 'Ferramentas', items: [
    { id: 'ia', label: 'Roma_IA', icon: Sparkles, route: '/dashboard/ia' },
    { id: 'cnd', label: 'Certidões CND', icon: FileSearch, route: '/dashboard/cnd' },
    { id: 'incra', label: 'Tabelas INCRA', icon: BarChart3, route: '/dashboard/admin/incra' },
  ]},
  { id: 'admin', section: 'Administração', adminOnly: true, items: [
    { id: 'cupons', label: 'Cupons promo', icon: Tag, route: '/dashboard/admin/cupons' },
    { id: 'acessos-teste', label: 'Acessos de teste', icon: KeyRound, route: '/dashboard/admin/acessos-teste' },
    { id: 'usuarios', label: 'Usuários', icon: Users, route: '/dashboard/admin/usuarios' },
    { id: 'leads', label: 'Leads', icon: Inbox, route: '/dashboard/admin/leads' },
    { id: 'privacidade', label: 'Pedidos LGPD', icon: Shield, route: '/dashboard/admin/privacidade' },
    { id: 'prospeccao', label: 'Prospecção', icon: Radar, route: '/dashboard/admin/prospeccao' },
    { id: 'instagram', label: 'Instagram', icon: Instagram, route: '/dashboard/admin/instagram' },
    { id: 'divulgacao', label: 'Divulgação', icon: Megaphone, route: '/dashboard/admin/divulgacao' },
    { id: 'email-config', label: 'E-mail', icon: Mail, route: '/dashboard/admin/email' },
    { id: 'ia-uso', label: 'Uso da IA', icon: Cpu, route: '/dashboard/admin/ia' },
    { id: 'danfse', label: 'DANFSe (temas)', icon: FileText, route: '/dashboard/admin/danfse' },
    { id: 'nfse-emissao', label: 'NFS-e (emissão)', icon: Stamp, route: '/dashboard/admin/nfse-emissao' },
    { id: 'receita-rtc', label: 'Alíquotas CBS/IBS', icon: Calculator, route: '/dashboard/admin/receita-rtc' },
  ]},
  { id: 'conta', section: 'Conta e configurações', items: [
    { id: 'curriculo', label: 'Meu currículo', icon: Award, route: '/dashboard/curriculo' },
    { id: 'marca', label: 'Marca (white-label)', icon: Palette, route: '/dashboard/marca' },
    { id: 'assinatura-digital', label: 'Assinatura digital', icon: FileSignature, route: '/dashboard/assinatura-digital' },
    { id: 'assinaturas', label: 'Assinaturas', icon: Send, route: '/dashboard/assinaturas' },
    { id: 'novidades', label: 'Novidades', icon: Bell, route: '/dashboard/novidades' },
    { id: 'assinatura', label: 'Plano e pagamento', icon: CreditCard, route: '/dashboard/assinatura' },
    { id: 'config', label: 'Configurações', icon: Settings, route: '/dashboard/config' },
  ]},
];

const GRUPOS_KEY = 'avalie_menu_grupos';

function isActive(pathname, item) {
  if (item.end) return pathname === item.route;
  if (pathname === item.route || pathname.startsWith(item.route + '/')) return true;
  return (item.alias || []).some((a) => pathname === a || pathname.startsWith(a + '/'));
}

function NavItem({ item, active, count, onNavigate }) {
  const Icon = item.icon;
  return (
    <Link
      to={item.route}
      onClick={onNavigate}
      className="av-nav-link"
      aria-current={active ? 'page' : undefined}
    >
      <Icon size={18} strokeWidth={1.75} aria-hidden="true" style={{ flexShrink: 0 }} />
      <span style={{ flex: 1, minWidth: 0 }}>{item.label}</span>
      {count > 0 && <span className="av-nav-count" aria-label={`${count} registros`}>{count}</span>}
    </Link>
  );
}

export default function Sidebar({
  user = {},
  onLogout = () => {},
  onNavigate = () => {},
  onClose,
  width = 248,
}) {
  const location = useLocation();
  const [ptamCount, setPtamCount] = useState(0);
  const [abertos, setAbertos] = useState(() => {
    try { return JSON.parse(localStorage.getItem(GRUPOS_KEY) || '{}') || {}; } catch { return {}; }
  });

  useEffect(() => {
    let alive = true;
    ptamAPI.list()
      .then((rows) => { if (alive) setPtamCount(Array.isArray(rows) ? rows.length : 0); })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  const counts = { ptam: ptamCount };
  const name = user?.name || 'Usuário';
  const role = user?.role || 'Avaliador';
  const initials = name.split(' ').filter(Boolean).slice(0, 2).map((n) => n[0]).join('').toUpperCase() || 'U';

  // Itens administrativos: mesma regra de antes (admin/owner/ceo).
  const isAdmin = ['admin', 'owner', 'ceo'].includes(String(user?.role || '').toLowerCase());
  const menu = MENU.filter((g) => !g.adminOnly || isAdmin);

  // Grupo aberto: preferência salva; sem preferência, abre o que contém a rota atual.
  const grupoAberto = (g) => {
    if (!g.section) return true;
    if (g.items.some((it) => isActive(location.pathname, it))) return true;
    return abertos[g.id] ?? false;
  };
  const alternar = (g) => {
    const prox = { ...abertos, [g.id]: !grupoAberto(g) };
    setAbertos(prox);
    try { localStorage.setItem(GRUPOS_KEY, JSON.stringify(prox)); } catch { /* ignore */ }
  };

  return (
    <nav
      id="av-menu-principal"
      aria-label="Menu principal"
      className="av-sidebar"
      style={{ width, minWidth: typeof width === 'number' ? width : undefined, height: '100%',
        display: 'flex', flexDirection: 'column' }}
    >
      {/* Logo oficial */}
      <div style={{ padding: '16px 12px 12px', display: 'flex', alignItems: 'center', gap: 8 }}>
        <Link to="/dashboard" onClick={onNavigate} className="av-on-dark"
          style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 0, padding: 4, borderRadius: 10 }}>
          <BrandMark variant="badge" size={36} title="AvalieImob" />
          <span style={{ minWidth: 0 }}>
            <span style={{ display: 'block', color: '#fff', fontSize: 17, fontWeight: 700, letterSpacing: '-0.01em' }}>AvalieImob</span>
            <span style={{ display: 'block', color: 'var(--av-gold)', fontSize: 9.5, letterSpacing: '0.08em', whiteSpace: 'nowrap', textTransform: 'uppercase', marginTop: 1 }}>Romatec · PTAM · Laudos</span>
          </span>
        </Link>
        {onClose && (
          <button type="button" onClick={onClose} aria-label="Fechar menu"
            style={{ width: 44, height: 44, borderRadius: 10, border: '1px solid rgb(245 242 232 / 0.2)', background: 'transparent', color: 'var(--av-sidebar-text)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', flexShrink: 0 }}>
            <X size={20} aria-hidden="true" />
          </button>
        )}
      </div>

      {/* Itens */}
      <div style={{ flex: 1, overflowY: 'auto', overscrollBehavior: 'contain', paddingBottom: 8 }}>
        {menu.map((group) => {
          const aberto = grupoAberto(group);
          const listaId = `av-grupo-${group.id}`;
          return (
            <div key={group.id} style={{ marginTop: group.section ? 6 : 0 }}>
              {group.section && (
                <button
                  type="button"
                  className="av-nav-group-btn"
                  aria-expanded={aberto}
                  aria-controls={listaId}
                  onClick={() => alternar(group)}
                >
                  <span style={{ flex: 1 }}>{group.section}</span>
                  <ChevronDown size={14} aria-hidden="true"
                    style={{ transform: aberto ? 'rotate(180deg)' : 'none', transition: 'transform var(--av-motion-fast)' }} />
                </button>
              )}
              <div id={listaId} hidden={!aberto} style={{ display: aberto ? 'grid' : 'none', gap: 2 }}>
                {group.items.map((item) => (
                  <NavItem
                    key={item.id}
                    item={item}
                    active={isActive(location.pathname, item)}
                    count={item.countKey ? (counts[item.countKey] || 0) : 0}
                    onNavigate={onNavigate}
                  />
                ))}
              </div>
            </div>
          );
        })}

        {/* Links externos (site público e calculadora — esta só admin, como antes) */}
        <div style={{ borderTop: '1px solid rgb(245 242 232 / 0.08)', marginTop: 10, paddingTop: 8, display: 'grid', gap: 2 }}>
          <Link to="/" onClick={onNavigate} className="av-nav-link">
            <Globe size={18} strokeWidth={1.75} aria-hidden="true" /> <span>Nossos serviços</span>
          </Link>
          {isAdmin && (
            <a href="/quanto-vale-meu-imovel" target="_blank" rel="noopener noreferrer" className="av-nav-link">
              <Calculator size={18} strokeWidth={1.75} aria-hidden="true" /> <span>Calculadora pública</span>
            </a>
          )}
        </div>
      </div>

      {/* Rodapé: usuário + sair */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid rgb(245 242 232 / 0.08)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <AvatarPerfil iniciais={initials} size={34} bg="var(--av-gold)" color="var(--av-brand)" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{name}</div>
          <div style={{ fontSize: 11, color: 'var(--av-sidebar-muted)', textTransform: 'capitalize' }}>{role}</div>
        </div>
        <button type="button" onClick={onLogout} aria-label="Sair da conta" title="Sair da conta"
          style={{ width: 44, height: 44, borderRadius: 10, background: 'none', border: 0, cursor: 'pointer',
            color: 'var(--av-sidebar-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <LogOut size={18} strokeWidth={1.75} aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
