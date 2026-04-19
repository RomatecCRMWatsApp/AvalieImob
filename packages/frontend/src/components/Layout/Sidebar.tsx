import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  Users,
  Building2,
  Mic2,
  BarChart3,
  ClipboardList,
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

export function Sidebar() {
  return (
    <aside className="hidden md:flex flex-col w-64 bg-gray-900 border-r border-green-900/30 min-h-[calc(100vh-64px)] flex-shrink-0">
      <nav className="p-3 space-y-0.5">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all text-sm font-medium
              ${
                isActive
                  ? "bg-green-700/20 text-green-400 border border-green-700/30"
                  : "text-gray-400 hover:bg-gray-800/70 hover:text-gray-200"
              }`
            }
          >
            <item.icon className="w-4 h-4 flex-shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
