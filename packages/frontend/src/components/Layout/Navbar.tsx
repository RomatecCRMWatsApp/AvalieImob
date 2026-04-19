import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { trpc } from "../../lib/trpc";
import { removeToken } from "../../lib/auth";
import {
  Menu,
  X,
  LogOut,
  LayoutDashboard,
  FileText,
  Users,
  Building2,
  Mic2,
  BarChart3,
  ClipboardList,
  ChevronDown,
} from "lucide-react";

const menuItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/dashboard" },
  { icon: ClipboardList, label: "Avaliações", path: "/avaliacoes" },
  { icon: FileText, label: "PTAMs", path: "/ptams" },
  { icon: Building2, label: "Imóveis", path: "/imoveis" },
  { icon: Users, label: "Clientes", path: "/clientes" },
  { icon: Mic2, label: "Áudios", path: "/audios" },
  { icon: BarChart3, label: "Cálculos", path: "/calculos" },
];

export function Navbar() {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const user = trpc.auth.me.useQuery();

  const handleLogout = () => {
    removeToken();
    navigate("/login");
  };

  return (
    <header className="bg-gray-900 border-b border-green-900/30 sticky top-0 z-40 h-16">
      <div className="px-4 sm:px-6 h-full flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-green-500 to-green-800 rounded-lg flex items-center justify-center shadow-lg shadow-green-900/40">
            <span className="text-white font-bold text-xs">AI</span>
          </div>
          <div>
            <span className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-300 text-lg leading-none">
              AvalieImob
            </span>
            <span className="hidden sm:block text-gray-500 text-xs leading-none">
              by Romatec
            </span>
          </div>
        </div>

        {/* Desktop user menu */}
        <div className="hidden md:flex items-center gap-3">
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-800 transition text-sm"
            >
              <div className="w-7 h-7 bg-green-700/30 rounded-full flex items-center justify-center">
                <span className="text-green-400 font-bold text-xs">
                  {user.data?.nome?.charAt(0).toUpperCase() ?? "U"}
                </span>
              </div>
              <span className="text-gray-300 max-w-[120px] truncate">
                {user.data?.nome ?? "..."}
              </span>
              <ChevronDown className="w-3 h-3 text-gray-500" />
            </button>

            {userMenuOpen && (
              <>
                <div
                  className="fixed inset-0"
                  onClick={() => setUserMenuOpen(false)}
                />
                <div className="absolute right-0 mt-1 w-48 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl py-1 z-50">
                  <div className="px-4 py-2 border-b border-gray-700">
                    <p className="text-xs text-gray-400">Logado como</p>
                    <p className="text-sm font-medium text-white truncate">
                      {user.data?.email}
                    </p>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-red-900/20 transition"
                  >
                    <LogOut className="w-4 h-4" />
                    Sair
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2 rounded-lg hover:bg-gray-800 transition"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-green-900/30 bg-gray-900 px-4 py-3 space-y-1">
          {menuItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition
                ${isActive ? "bg-green-700/20 text-green-400" : "text-gray-400 hover:bg-gray-800"}`
              }
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </NavLink>
          ))}
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-red-400 hover:bg-red-900/20 transition"
          >
            <LogOut className="w-4 h-4" />
            Sair
          </button>
        </div>
      )}
    </header>
  );
}
