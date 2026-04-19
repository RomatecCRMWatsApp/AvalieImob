import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { LogOut, Home, Users, FileText, Settings } from "lucide-react";

export function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Navbar */}
      <nav className="bg-slate-900 border-b border-green-900/30 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <Link to="/dashboard" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-green-400 to-green-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">RI</span>
              </div>
              <span className="text-white font-bold text-lg hidden sm:inline">
                AvalieImob
              </span>
            </Link>

            {/* Menu Links */}
            {user && (
              <div className="hidden md:flex gap-8">
                <Link
                  to="/dashboard"
                  className="text-slate-300 hover:text-green-400 transition flex items-center gap-2"
                >
                  <Home size={18} />
                  <span>Dashboard</span>
                </Link>
                <Link
                  to="/clientes"
                  className="text-slate-300 hover:text-green-400 transition flex items-center gap-2"
                >
                  <Users size={18} />
                  <span>Clientes</span>
                </Link>
                <Link
                  to="/avaliacoes"
                  className="text-slate-300 hover:text-green-400 transition flex items-center gap-2"
                >
                  <FileText size={18} />
                  <span>Avaliações</span>
                </Link>
              </div>
            )}

            {/* User Menu */}
            <div className="flex items-center gap-4">
              {user ? (
                <>
                  <div className="text-right hidden sm:block">
                    <p className="text-white text-sm font-medium">{user.nome}</p>
                    <p className="text-slate-400 text-xs">{user.role}</p>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="p-2 hover:bg-slate-800 rounded-lg transition text-slate-300 hover:text-red-400"
                  >
                    <LogOut size={20} />
                  </button>
                </>
              ) : (
                <Link
                  to="/login"
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition"
                >
                  Login
                </Link>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 border-t border-green-900/30 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <p className="text-slate-400 text-sm text-center">
            © 2025 Romatec AvalieImob. Todos os direitos reservados.
          </p>
        </div>
      </footer>
    </div>
  );
}
