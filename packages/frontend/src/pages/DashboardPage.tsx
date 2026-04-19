import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { trpc } from "../lib/trpc";
import {
  Menu,
  X,
  LogOut,
  Home,
  FileText,
  Users,
  Building2,
  Mic2,
  BarChart3,
} from "lucide-react";

interface DashboardProps {
  children?: React.ReactNode;
}

export function Dashboard({ children }: DashboardProps) {
  const navigate = useNavigate();
  const [menuAberto, setMenuAberto] = useState(false);

  const user = trpc.auth.me.useQuery();

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("userId");
    localStorage.removeItem("user");
    navigate("/login");
  };

  const menuItems = [
    { icon: Home, label: "Dashboard", path: "/dashboard" },
    { icon: FileText, label: "PTAMs", path: "/dashboard/ptams" },
    { icon: Building2, label: "Imóveis", path: "/dashboard/imoveis" },
    { icon: Users, label: "Clientes", path: "/dashboard/clientes" },
    { icon: Mic2, label: "Áudios", path: "/dashboard/audios" },
    { icon: BarChart3, label: "Cálculos", path: "/dashboard/calculos" },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="bg-gradient-to-r from-gray-900 to-green-900 border-b border-green-700/30 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-r from-green-400 to-yellow-400 rounded-lg flex items-center justify-center">
              <span className="text-gray-950 font-bold text-sm">AI</span>
            </div>
            <h1 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-yellow-400">
              AvalieImob
            </h1>
          </div>

          <div className="hidden md:flex items-center gap-4">
            <span className="text-gray-400 text-sm">
              {user.data?.nome || "Carregando..."}
            </span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-red-600/20 text-red-400 transition"
            >
              <LogOut className="w-4 h-4" />
              Sair
            </button>
          </div>

          <button
            className="md:hidden"
            onClick={() => setMenuAberto(!menuAberto)}
          >
            {menuAberto ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>

        {menuAberto && (
          <nav className="md:hidden border-t border-green-700/30 bg-gray-900 p-4 space-y-2">
            {menuItems.map((item) => (
              <button
                key={item.path}
                onClick={() => {
                  navigate(item.path);
                  setMenuAberto(false);
                }}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-green-600/20 transition text-left"
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </button>
            ))}
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-red-600/20 text-red-400 transition"
            >
              <LogOut className="w-5 h-5" />
              Sair
            </button>
          </nav>
        )}
      </header>

      <div className="flex">
        <aside className="hidden md:block w-64 bg-gray-900 border-r border-green-700/30 p-4 min-h-[calc(100vh-80px)]">
          <nav className="space-y-2">
            {menuItems.map((item) => (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-green-600/20 transition text-left group"
              >
                <item.icon className="w-5 h-5 group-hover:text-green-400 transition" />
                <span className="group-hover:text-green-400 transition">
                  {item.label}
                </span>
              </button>
            ))}
          </nav>
        </aside>

        <main className="flex-1 p-4 sm:p-6 lg:p-8">
          {children || (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="md:col-span-2 lg:col-span-3 bg-gradient-to-r from-gray-900 to-green-900 border border-green-700/30 rounded-lg p-6">
                <h2 className="text-2xl font-bold mb-2">
                  Bem-vindo, {user.data?.nome}! 👋
                </h2>
                <p className="text-gray-400">
                  Sistema de Avaliação Imobiliária Profissional com Método Comparativo
                </p>
              </div>

              {[
                { label: "PTAMs Emitidos", valor: "0", icon: FileText },
                { label: "Imóveis Cadastrados", valor: "0", icon: Building2 },
                { label: "Clientes", valor: "0", icon: Users },
              ].map((stat, idx) => (
                <div
                  key={idx}
                  className="bg-gray-900 border border-gray-700/30 rounded-lg p-6"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-gray-400 text-sm">{stat.label}</p>
                      <p className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-yellow-400 mt-2">
                        {stat.valor}
                      </p>
                    </div>
                    <div className="w-12 h-12 bg-green-600/20 rounded-lg flex items-center justify-center">
                      <stat.icon className="w-6 h-6 text-green-400" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export function DashboardLayout() {
  return <Dashboard />;
}
