import React, { useState, useRef, useEffect } from 'react';
import { Link, NavLink, Routes, Route, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Users, Building2, BarChart3, FileText,
  CreditCard, Settings, LogOut, Menu, X, Bell, FileCheck2, Globe,
  Search, ChevronDown, User, Shield, Beef, Award, Home, ClipboardCheck, FileSearch, FileSignature
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { BRAND } from '../mock/mock';
import RomaIAAvatar from '../components/common/RomaIAAvatar';
import { Button } from '../components/ui/button';

import DashOverview from '../components/dashboard/DashOverview';
import Clients from '../components/dashboard/Clients';
import Properties from '../components/dashboard/Properties';
import Evaluations from '../components/dashboard/Evaluations';
import Samples from '../components/dashboard/Samples';
import AIAssistant from '../components/dashboard/AIAssistant';
import SubscriptionPage from '../components/dashboard/SubscriptionPage';
import SettingsPage from '../components/dashboard/SettingsPage';
import PerfilAvaliador from '../components/dashboard/PerfilAvaliador';
import PtamList from '../components/dashboard/ptam/PtamList';
import PtamWizard from '../components/dashboard/ptam/PtamWizard';
import GarantiasList from '../components/dashboard/garantias/GarantiasList';
import GarantiaWizard from '../components/dashboard/garantias/GarantiaWizard';
import SemoventesList from '../components/dashboard/semoventes/SemoventesList';
import SemoventeWizard from '../components/dashboard/semoventes/SemoventeWizard';
import LocacaoList from '../components/dashboard/locacao/LocacaoList';
import LocacaoWizard from '../components/dashboard/locacao/LocacaoWizard';
import TVIList from '../components/dashboard/tvi/TVIList';
import TVINew from '../components/dashboard/tvi/TVINew';
import TVIForm from '../components/dashboard/tvi/TVIForm';
import CNDConsulta from '../components/dashboard/cnd/CNDConsulta';
import CNDHistorico from '../components/dashboard/cnd/CNDHistorico';
import GlobalSearch from '../components/common/GlobalSearch';
import ContratosList from '../components/dashboard/contratos/ContratosList';
import ContratoWizard from '../components/dashboard/contratos/ContratoWizard';

/* ─── Brand ─────────────────────────────────────────────── */
const GOLD       = '#D4A830';
const DARK_GREEN = '#1B4D1B';

/* ─── Navigation groups ─────────────────────────────────── */
const NAV_GROUPS = [
  {
    label: null,
    items: [
      { to: '/dashboard',           icon: LayoutDashboard, label: 'Visão Geral',       end: true },
    ],
  },
  {
    label: 'Cadastros',
    items: [
      { to: '/dashboard/clientes',  icon: Users,           label: 'Clientes' },
      { to: '/dashboard/imoveis',   icon: Building2,       label: 'Imóveis e Garantias' },
      { to: '/dashboard/amostras',  icon: BarChart3,       label: 'Amostras' },
    ],
  },
  {
    label: 'Laudos',
    items: [
      { to: '/dashboard/ptam',       icon: FileCheck2, label: 'PTAM (Laudos)' },
      { to: '/dashboard/garantias',  icon: Shield,     label: 'Aval. de Garantias' },
      { to: '/dashboard/semoventes', icon: Beef,       label: 'Semoventes' },
      { to: '/dashboard/locacao',    icon: Home,       label: 'Aval. Locacao' },
      { to: '/dashboard/tvi',        icon: ClipboardCheck, label: 'Kit TVI' },
      { to: '/dashboard/laudos',     icon: FileText,   label: 'Avaliações' },
    ],
  },
  {
    label: 'Contratos',
    items: [
      { to: '/dashboard/contratos', icon: FileSignature, label: 'Contratos', badge: 'NOVO' },
    ],
  },
  {
    label: 'Ferramentas',
    items: [
      { to: '/dashboard/ia',        custom: 'roma_ia', label: 'Roma_IA' },
      { to: '/dashboard/cnd',       icon: FileSearch,  label: 'Certidões CND' },
    ],
  },
  {
    label: 'Conta',
    items: [
      { to: '/dashboard/curriculo',  icon: Award,      label: 'Meu Currículo' },
      { to: '/dashboard/assinatura', icon: CreditCard, label: 'Assinatura' },
      { to: '/dashboard/config',     icon: Settings,   label: 'Configurações' },
    ],
  },
];

/* ─── Sidebar nav link ───────────────────────────────────── */
const SideLink = ({ item, onClick, onAvatarClick }) => {
  const Icon = item.icon;
  
  // Item customizado Roma_IA
  if (item.custom === 'roma_ia') {
    return (
      <NavLink
        to={item.to}
        end={item.end}
        onClick={onClick}
        className={({ isActive }) =>
          `group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150
           ${isActive
             ? 'text-white shadow-sm'
             : 'text-emerald-100/80 hover:bg-white/10 hover:text-white'
           }`
        }
        style={({ isActive }) => isActive ? { background: GOLD + '22', borderLeft: `3px solid ${GOLD}`, paddingLeft: '9px' } : {}}
      >
        {({ isActive }) => (
          <>
            <div 
              className="cursor-pointer hover:scale-110 transition-transform"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onAvatarClick?.();
              }}
            >
              <RomaIAAvatar state={isActive ? 'speaking' : 'idle'} size="sm" />
            </div>
            <div className="flex flex-col leading-none">
              <span className={isActive ? 'font-semibold' : ''}>Roma_IA</span>
              <span className="text-[10px] opacity-60">Especialista NBR 14.653</span>
            </div>
          </>
        )}
      </NavLink>
    );
  }
  
  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onClick}
      className={({ isActive }) =>
        `group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150
         ${isActive
           ? 'text-white shadow-sm'
           : 'text-emerald-100/80 hover:bg-white/10 hover:text-white'
         }`
      }
      style={({ isActive }) => isActive ? { background: GOLD + '22', borderLeft: `3px solid ${GOLD}`, paddingLeft: '9px' } : {}}
    >
      {({ isActive }) => (
        <>
          <div
            className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors
                        ${isActive ? 'bg-white/15' : 'bg-transparent group-hover:bg-white/10'}`}
          >
            <Icon
              className="w-4 h-4"
              style={{ color: isActive ? GOLD : undefined }}
            />
          </div>
          <span className={isActive ? 'font-semibold' : ''}>{item.label}</span>
            {item.badge && (
              <span className="ml-auto text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-amber-400/20 text-amber-300 tracking-widest">
                {item.badge}
              </span>
            )}
        </>
      )}
    </NavLink>
  );
};

/* ─── Avatar dropdown ────────────────────────────────────── */
const AvatarMenu = ({ user, onLogout }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const initial = user?.name?.[0]?.toUpperCase() || 'U';

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 rounded-xl px-2 py-1.5 hover:bg-gray-100 transition-colors focus:outline-none"
      >
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold text-white"
          style={{ background: DARK_GREEN }}
        >
          {initial}
        </div>
        <div className="hidden sm:block text-left">
          <div className="text-sm font-semibold text-gray-800 leading-tight">{user?.name?.split(' ')[0]}</div>
          <div className="text-[10px] text-gray-400 leading-tight capitalize">{user?.role || 'Avaliador'}</div>
        </div>
        <ChevronDown className={`w-3.5 h-3.5 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-52 bg-white border border-gray-200 rounded-2xl shadow-xl py-1.5 z-50">
          <div className="px-4 py-2.5 border-b border-gray-100">
            <div className="text-sm font-semibold text-gray-900">{user?.name}</div>
            <div className="text-xs text-gray-400 truncate">{user?.email}</div>
          </div>
          <NavLink
            to="/dashboard/curriculo"
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            onClick={() => setOpen(false)}
          >
            <Award className="w-4 h-4 text-gray-400" /> Meu Currículo
          </NavLink>
          <NavLink
            to="/dashboard/config"
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            onClick={() => setOpen(false)}
          >
            <User className="w-4 h-4 text-gray-400" /> Meu perfil
          </NavLink>
          <NavLink
            to="/dashboard/assinatura"
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            onClick={() => setOpen(false)}
          >
            <CreditCard className="w-4 h-4 text-gray-400" /> Assinatura
          </NavLink>
          <div className="border-t border-gray-100 mt-1 pt-1">
            <button
              onClick={() => { setOpen(false); onLogout(); }}
              className="flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors w-full text-left"
            >
              <LogOut className="w-4 h-4" /> Sair
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

/* ─── Notification button ────────────────────────────────── */
const NotifButton = () => {
  const [seen, setSeen] = useState(false);
  return (
    <button
      onClick={() => setSeen(true)}
      className="relative w-9 h-9 rounded-xl hover:bg-gray-100 flex items-center justify-center transition-colors"
      title="Notificações"
    >
      <Bell className="w-4 h-4 text-gray-500" />
      {!seen && (
        <span
          className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full border-2 border-white"
          style={{ background: GOLD }}
        />
      )}
    </button>
  );
};

/* ─── Dashboard shell ────────────────────────────────────── */
const Dashboard = () => {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showWelcomeModal, setShowWelcomeModal] = useState(false);

  const handleLogout = () => {
    logout();
    nav('/');
  };

  return (
    <div className="min-h-screen flex" style={{ background: '#f8fafc' }}>

      {/* ── Sidebar ── */}
      <aside
        className={`fixed lg:sticky top-0 inset-y-0 left-0 z-40 w-72 flex flex-col transition-transform duration-300 h-screen
                    ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
        style={{ background: DARK_GREEN }}
      >
        {/* Logo */}
        <div className="px-3 py-4 flex items-center justify-between border-b" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
          <Link to="/dashboard" className="flex items-center flex-1" onClick={() => setMobileOpen(false)}>
            <img src={BRAND.logo} alt="AvalieImob" className="h-28 w-full object-contain object-left" />
          </Link>
          <button
            className="lg:hidden w-7 h-7 rounded-lg flex items-center justify-center hover:bg-white/10 transition-colors"
            onClick={() => setMobileOpen(false)}
          >
            <X className="w-4 h-4 text-white" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
          {NAV_GROUPS.map((group, gi) => (
            <div key={gi}>
              {group.label && (
                <div
                  className="text-[9px] tracking-[0.18em] font-bold uppercase px-3 mb-1.5"
                  style={{ color: 'rgba(255,255,255,0.35)' }}
                >
                  {group.label}
                </div>
              )}
              <div className="space-y-0.5">
                {group.items.map(item => (
                  <SideLink 
                    key={item.to} 
                    item={item} 
                    onClick={() => setMobileOpen(false)} 
                    onAvatarClick={item.custom === 'roma_ia' ? () => setShowWelcomeModal(true) : undefined}
                  />
                ))}
              </div>
            </div>
          ))}

          {/* External link */}
          <div className="pt-2" style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
            <Link
              to="/"
              onClick={() => setMobileOpen(false)}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-emerald-100/60
                         hover:bg-white/10 hover:text-white transition-all"
            >
              <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-transparent hover:bg-white/10">
                <Globe className="w-4 h-4" />
              </div>
              Nossos Serviços
            </Link>
          </div>
        </nav>

        {/* User footer */}
        <div className="px-4 pb-5 pt-3" style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
          <div className="flex items-center gap-3 px-2 py-2 rounded-xl hover:bg-white/10 transition-colors mb-2">
            <div
              className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
              style={{ background: GOLD, color: DARK_GREEN }}
            >
              {user?.name?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-white truncate">{user?.name}</div>
              <div className="text-[11px] truncate capitalize" style={{ color: 'rgba(255,255,255,0.45)' }}>
                {user?.role || 'Avaliador'}
              </div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium
                       text-red-300/80 hover:bg-red-900/30 hover:text-red-200 transition-all"
          >
            <LogOut className="w-4 h-4" /> Sair da conta
          </button>
        </div>
      </aside>

      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden backdrop-blur-sm"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* ── Main content ── */}
      <main className="flex-1 min-w-0 flex flex-col">

        {/* ── Header ── */}
        <header className="sticky top-0 z-20 bg-white/95 backdrop-blur-md border-b border-gray-200/80 h-16 flex items-center px-4 sm:px-6 gap-3 shadow-sm">
          {/* Mobile menu toggle */}
          <button
            className="lg:hidden w-9 h-9 rounded-xl hover:bg-gray-100 flex items-center justify-center transition-colors"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="w-5 h-5 text-gray-600" />
          </button>

          {/* Search bar */}
          <GlobalSearch />

          <div className="flex items-center gap-1 ml-auto">
            <NotifButton />
            <div className="w-px h-6 bg-gray-200 mx-1" />
            <AvatarMenu user={user} onLogout={handleLogout} />
          </div>
        </header>

        {/* ── Page content ── */}
        <div className="flex-1 p-4 sm:p-6 lg:p-8">
          <Routes>
            <Route index element={<DashOverview />} />
            <Route path="clientes"    element={<Clients />} />
            <Route path="imoveis"     element={<Properties />} />
            <Route path="amostras"    element={<Samples />} />
            <Route path="ptam"        element={<PtamList />} />
            <Route path="ptam/:id"    element={<PtamWizard />} />
            <Route path="garantias"        element={<GarantiasList />} />
            <Route path="garantias/nova"   element={<GarantiaWizard />} />
            <Route path="garantias/:id"    element={<GarantiaWizard />} />
            <Route path="semoventes"        element={<SemoventesList />} />
            <Route path="semoventes/nova"   element={<SemoventeWizard />} />
            <Route path="semoventes/:id"    element={<SemoventeWizard />} />
            <Route path="locacao"           element={<LocacaoList />} />
            <Route path="locacao/nova"      element={<LocacaoWizard />} />
            <Route path="locacao/:id"       element={<LocacaoWizard />} />
            <Route path="tvi"              element={<TVIList />} />
            <Route path="tvi/nova"         element={<TVINew />} />
            <Route path="tvi/:id"          element={<TVIForm />} />
            <Route path="cnd"              element={<CNDConsulta />} />
            <Route path="cnd/historico"    element={<CNDHistorico />} />
            <Route path="contratos"        element={<ContratosList />} />
            <Route path="contratos/novo"   element={<ContratoWizard />} />
            <Route path="contratos/:id"    element={<ContratoWizard />} />
            <Route path="laudos"      element={<Evaluations />} />
            <Route path="ia"          element={<AIAssistant />} />
            <Route path="curriculo"   element={<PerfilAvaliador />} />
            <Route path="assinatura"  element={<SubscriptionPage />} />
            <Route path="config"      element={<SettingsPage />} />
          </Routes>
        </div>
      </main>

      {/* Modal de Boas-Vindas Roma_IA */}
      {showWelcomeModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" 
          onClick={() => setShowWelcomeModal(false)}
        >
          <div 
            className="relative bg-white rounded-2xl shadow-2xl overflow-hidden max-w-md w-full mx-4" 
            onClick={e => e.stopPropagation()}
          >
            {/* Header com botão fechar */}
            <div className="absolute top-3 right-3 z-10">
              <button 
                onClick={() => setShowWelcomeModal(false)}
                className="w-8 h-8 rounded-full bg-black/20 hover:bg-black/40 flex items-center justify-center transition-colors"
              >
                <X className="w-5 h-5 text-white" />
              </button>
            </div>
            
            {/* Vídeo de Boas-Vindas */}
            <div className="relative aspect-square bg-emerald-900">
              <img 
                src="/brand/roma_ia_animated_bem_vindo.webp" 
                alt="Roma_IA - Boas-vindas"
                className="w-full h-full object-cover"
                onError={(e) => {
                  // Fallback se o vídeo não existir
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'flex';
                }}
              />
              <div className="absolute inset-0 hidden items-center justify-center bg-emerald-900 text-white text-center p-6">
                <div>
                  <RomaIAAvatar state="speaking" size="lg" />
                  <p className="mt-4 text-lg font-semibold">Olá! Sou a Roma_IA</p>
                  <p className="text-sm text-emerald-200 mt-2">Sua especialista em avaliação imobiliária</p>
                </div>
              </div>
            </div>
            
            {/* Conteúdo */}
            <div className="p-6 text-center">
              <h2 className="text-xl font-bold text-gray-900 mb-2">Bem-vindo à Roma_IA!</h2>
              <p className="text-gray-600 text-sm mb-4">
                Sou sua assistente especializada em NBR 14.653. Posso ajudar com:
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs text-gray-500 mb-6">
                <div className="bg-gray-50 rounded-lg p-2">✓ Aperfeiçoar laudos</div>
                <div className="bg-gray-50 rounded-lg p-2">✓ Gerar fundamentações</div>
                <div className="bg-gray-50 rounded-lg p-2">✓ Análises SWOT</div>
                <div className="bg-gray-50 rounded-lg p-2">✓ Memoriais descritivos</div>
              </div>
              <Button 
                onClick={() => {
                  setShowWelcomeModal(false);
                  nav('/dashboard/ia');
                }}
                className="w-full bg-emerald-900 hover:bg-emerald-800 text-white"
              >
                Começar a conversar
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
