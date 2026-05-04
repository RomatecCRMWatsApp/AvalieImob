import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, ArrowRight, Eye, EyeOff } from 'lucide-react';
import SEO from '../components/common/SEO';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/use-toast';
import { BRAND } from '../mock/mock';

const Login = () => {
  const nav = useNavigate();
  const { login } = useAuth();
  const { toast } = useToast();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (!email || !password) {
      setError('Preencha email e senha.');
      return;
    }
    setLoading(true);
    try {
      await login(email, password);
      nav('/dashboard', { replace: true });
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        'Credenciais inválidas. Verifique email e senha.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <SEO
        title="Login"
        description="Acesse sua conta no AvalieImob para emitir PTAMs, laudos tecnicos, TVI e avaliacoes de garantias bancarias."
        url="https://www.romatecavalieimob.com.br/login"
        noindex
      />
      <div className="hidden lg:block relative bg-emerald-950 overflow-hidden">
        <img src="https://images.pexels.com/photos/14465329/pexels-photo-14465329.jpeg" alt="São Paulo" className="absolute inset-0 w-full h-full object-cover opacity-30" />
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-950/95 via-emerald-900/80 to-emerald-900/60" />
        <div className="relative h-full flex flex-col justify-between p-12 text-white">
          <Link to="/" className="flex items-center gap-3">
            <img src={BRAND.logo} alt="" className="h-12 w-auto object-contain max-w-[160px]" />
            <div>
              <div className="font-display text-xl font-bold">RomaTec</div>
              <div className="text-[10px] tracking-[0.2em] text-emerald-200">AVALIEIMOB</div>
            </div>
          </Link>
          <div>
            <h1 className="font-display text-5xl font-bold leading-tight mb-4">
              Avalie com precisão.<br />
              <span className="italic text-amber-300">Decida com confiança.</span>
            </h1>
            <p className="text-emerald-200/90 text-lg max-w-md">Plataforma completa para PTAM, laudos e avaliações — urbanos, rurais e garantias.</p>
          </div>
          <div className="text-xs text-emerald-300">© 2026 RomaTec AvalieImob — {BRAND.location}</div>
        </div>
      </div>

      <div className="flex items-center justify-center p-6 md:p-12 bg-white">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-8 flex items-center gap-3">
            <img src={BRAND.logo} alt="" className="h-10 w-auto object-contain max-w-[140px]" />
            <div className="font-display text-xl font-bold brand-green">RomaTec AvalieImob</div>
          </div>
          <h2 className="font-display text-3xl md:text-4xl font-bold text-gray-900 mb-2">Acesse sua conta</h2>
          <p className="text-gray-600 mb-8">Bem-vindo de volta. Entre com suas credenciais.</p>

          <form onSubmit={submit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">E-mail</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="pl-10 h-11" placeholder="voce@email.com" />
              </div>
            </div>
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="block text-sm font-medium text-gray-700">Senha</label>
                <a href="#" className="text-xs text-emerald-700 hover:underline">Esqueci minha senha</a>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input type={show ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} className="pl-10 pr-10 h-11" placeholder="••••••••" />
                <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
            )}
            <Button type="submit" disabled={loading} className="w-full h-11 bg-emerald-900 hover:bg-emerald-800 text-white font-semibold">
              {loading ? 'Entrando...' : <>Acessar <ArrowRight className="ml-2 w-4 h-4" /></>}
            </Button>
          </form>

          <div className="mt-8 text-center text-sm text-gray-600">
            Ainda não tem conta? <Link to="/cadastro" className="font-semibold text-emerald-800 hover:underline">Cadastre-se</Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
