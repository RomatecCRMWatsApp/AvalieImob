import React, { useState } from 'react';
import { Link, NavLink, Routes, Route, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, Building2, BarChart3, FileText, Sparkles, CreditCard, Settings, LogOut, Menu, X, Bell, FileCheck2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { useAuth } from '../contexts/AuthContext';
import { BRAND } from '../mock/mock';

import DashOverview from '../components/dashboard/DashOverview';
import Clients from '../components/dashboard/Clients';
import Properties from '../components/dashboard/Properties';
import Evaluations from '../components/dashboard/Evaluations';
import Samples from '../components/dashboard/Samples';
import AIAssistant from '../components/dashboard/AIAssistant';
import SubscriptionPage from '../components/dashboard/SubscriptionPage';
import SettingsPage from '../components/dashboard/SettingsPage';
import PtamList from '../components/dashboard/ptam/PtamList';
import PtamWizard from '../components/dashboard/ptam/PtamWizard';

const NAV = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Visão Geral', end: true },
  { to: '/dashboard/clientes', icon: Users, label: 'Clientes' },
  { to: '/dashboard/imoveis', icon: Building2, label: 'Imóveis e Garantias' },
  { to: '/dashboard/amostras', icon: BarChart3, label: 'Amostras' },
  { to: '/dashboard/ptam', icon: FileCheck2, label: 'PTAM (Laudos)' },
  { to: '/dashboard/laudos', icon: FileText, label: 'Avaliações' },
  { to: '/dashboard/ia', icon: Sparkles, label: 'Assistente IA' },
  { to: '/dashboard/assinatura', icon: CreditCard, label: 'Assinatura' },
  { to: '/dashboard/config', icon: Settings, label: 'Configurações' },
];

const Dashboard = () => {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    nav('/');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className={`fixed lg:sticky top-0 inset-y-0 left-0 z-40 w-72 bg-emerald-950 text-white flex flex-col transition-transform duration-300 h-screen ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
        <div className="p-6 border-b border-white/10 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <img src={BRAND.logo} alt="" className="h-10 w-10 bg-white/10 rounded p-1" />
            <div>
              <div className="font-display text-lg font-bold">RomaTec</div>
              <div className="text-[10px] tracking-[0.2em] text-emerald-300">AVALIEIMOB</div>
            </div>
          </Link>
          <button className="lg:hidden" onClick={() => setMobileOpen(false)}><X className="w-5 h-5" /></button>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {NAV.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink key={item.to} to={item.to} end={item.end} onClick={() => setMobileOpen(false)}
                className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${isActive ? 'bg-white text-emerald-900' : 'text-emerald-100 hover:bg-white/10'}`}>
                <Icon className="w-4 h-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="p-4 border-t border-white/10">
          <div className="flex items-center gap-3 mb-3 p-2">
            <div className="w-9 h-9 rounded-full bg-amber-500 flex items-center justify-center text-emerald-950 font-bold">
              {user?.name?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold truncate">{user?.name}</div>
              <div className="text-[11px] text-emerald-300 truncate">{user?.role}</div>
            </div>
          </div>
          <Button onClick={handleLogout} variant="ghost" className="w-full justify-start text-emerald-100 hover:bg-white/10 hover:text-white">
            <LogOut className="w-4 h-4 mr-2" /> Sair
          </Button>
        </div>
      </aside>

      {mobileOpen && <div className="fixed inset-0 bg-black/40 z-30 lg:hidden" onClick={() => setMobileOpen(false)} />}

      {/* Main */}
      <main className="flex-1 min-w-0">
        <header className="sticky top-0 z-20 bg-white/90 backdrop-blur border-b border-gray-200 h-16 flex items-center px-6">
          <button className="lg:hidden mr-4" onClick={() => setMobileOpen(true)}><Menu className="w-5 h-5 text-gray-600" /></button>
          <div className="flex-1" />
          <button className="relative w-10 h-10 rounded-lg hover:bg-gray-100 flex items-center justify-center">
            <Bell className="w-4 h-4 text-gray-600" />
            <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-amber-500" />
          </button>
        </header>

        <div className="p-6 lg:p-8">
          <Routes>
            <Route index element={<DashOverview />} />
            <Route path="clientes" element={<Clients />} />
            <Route path="imoveis" element={<Properties />} />
            <Route path="amostras" element={<Samples />} />
            <Route path="ptam" element={<PtamList />} />
            <Route path="ptam/:id" element={<PtamWizard />} />
            <Route path="laudos" element={<Evaluations />} />
            <Route path="ia" element={<AIAssistant />} />
            <Route path="assinatura" element={<SubscriptionPage />} />
            <Route path="config" element={<SettingsPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
