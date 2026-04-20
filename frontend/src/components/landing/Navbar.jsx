import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { Button } from '../ui/button';
import { BRAND } from '../../mock/mock';

const Navbar = () => {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const isLoggedIn = !!localStorage.getItem('romatec_token');

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const links = [
    { href: '#features', label: 'Funcionalidades' },
    { href: '#services', label: 'Serviços' },
    { href: '#fluxo', label: 'Fluxo' },
    { href: '#planos', label: 'Planos' },
    { href: '#sobre', label: 'Sobre' },
    { href: '#ceo', label: 'CEO' },
    { href: '#contato', label: 'Contato' },
  ];

  return (
    <header className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${scrolled ? 'bg-white/95 backdrop-blur shadow-sm border-b border-emerald-900/10' : 'bg-white/80 backdrop-blur-sm'}`}>
      <div className="max-w-7xl mx-auto px-6 h-24 flex items-center justify-between">
        <Link to="/" className="flex items-center">
          <img src={BRAND.logo} alt="Romatec" className="h-16 w-auto object-contain max-w-[200px]" />
        </Link>

        <nav className="hidden lg:flex items-center gap-8">
          {links.map(l => (
            <a key={l.href} href={l.href} className="text-sm font-medium text-gray-700 hover:text-emerald-900 transition-colors">{l.label}</a>
          ))}
        </nav>

        <div className="hidden lg:flex items-center gap-3">
          {isLoggedIn ? (
            <Link to="/dashboard"><Button className="bg-emerald-900 hover:bg-emerald-800 text-white">Meu Dashboard</Button></Link>
          ) : (
            <>
              <Link to="/login"><Button variant="ghost" className="text-emerald-900 hover:text-emerald-900 hover:bg-emerald-50">Entrar</Button></Link>
              <Link to="/cadastro"><Button className="bg-emerald-900 hover:bg-emerald-800 text-white">Assinar agora</Button></Link>
            </>
          )}
        </div>

        <button className="lg:hidden p-2" onClick={() => setOpen(!open)} aria-label="Menu">
          {open ? <X className="w-6 h-6 text-emerald-900" /> : <Menu className="w-6 h-6 text-emerald-900" />}
        </button>
      </div>

      {open && (
        <div className="lg:hidden bg-white border-t border-emerald-900/10">
          <div className="px-6 py-4 flex flex-col gap-4">
            {links.map(l => (
              <a key={l.href} href={l.href} onClick={() => setOpen(false)} className="text-sm font-medium text-gray-700 hover:text-emerald-900">{l.label}</a>
            ))}
            <div className="flex gap-3 pt-4 border-t border-gray-100">
              {isLoggedIn ? (
                <Link to="/dashboard" className="flex-1"><Button className="w-full bg-emerald-900 hover:bg-emerald-800 text-white">Meu Dashboard</Button></Link>
              ) : (
                <>
                  <Link to="/login" className="flex-1"><Button variant="outline" className="w-full border-emerald-900 text-emerald-900">Entrar</Button></Link>
                  <Link to="/cadastro" className="flex-1"><Button className="w-full bg-emerald-900 hover:bg-emerald-800 text-white">Assinar</Button></Link>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  );
};

export default Navbar;
