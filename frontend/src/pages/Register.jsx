import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Mail, Lock, Briefcase, ArrowRight, Eye, EyeOff } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/use-toast';
import { BRAND } from '../mock/mock';

const Register = () => {
  const nav = useNavigate();
  const { register } = useAuth();
  const { toast } = useToast();
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'Engenheiro Avaliador', crea: '' });
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (!form.name || !form.email || !form.password) {
      setError('Preencha os campos obrigatórios.');
      return;
    }
    setLoading(true);
    try {
      await register(form);
      nav('/dashboard', { replace: true });
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        'Erro ao criar conta. Tente novamente.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="flex items-center justify-center p-6 md:p-12 bg-white order-2 lg:order-1">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-8 flex items-center gap-3">
            <img src={BRAND.logo} alt="" className="h-10 w-auto object-contain max-w-[140px]" />
            <div className="font-display text-xl font-bold brand-green">RomaTec AvalieImob</div>
          </div>
          <h2 className="font-display text-3xl md:text-4xl font-bold text-gray-900 mb-2">Crie sua conta</h2>
          <p className="text-gray-600 mb-8">Comece a emitir laudos com IA em minutos.</p>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Nome completo</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="pl-10 h-11" placeholder="Seu nome" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">E-mail</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="pl-10 h-11" placeholder="voce@email.com" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Profissão</label>
                <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                  <SelectTrigger className="h-11"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Engenheiro Avaliador">Engenheiro Avaliador</SelectItem>
                    <SelectItem value="Corretor de Imóveis">Corretor de Imóveis</SelectItem>
                    <SelectItem value="Perito Judicial">Perito Judicial</SelectItem>
                    <SelectItem value="Assistente Técnico">Assistente Técnico</SelectItem>
                    <SelectItem value="Arquiteto">Arquiteto</SelectItem>
                    <SelectItem value="Engenheiro Agrônomo">Engenheiro Agrônomo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">CRECI / CREA</label>
                <div className="relative">
                  <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input value={form.crea} onChange={(e) => setForm({ ...form, crea: e.target.value })} className="pl-10 h-11" placeholder="Registro" />
                </div>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Senha</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input type={show ? 'text' : 'password'} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="pl-10 pr-10 h-11" placeholder="Mínimo 8 caracteres" />
                <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                  {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
            )}
            <Button type="submit" disabled={loading} className="w-full h-11 bg-emerald-900 hover:bg-emerald-800 text-white font-semibold">
              {loading ? 'Criando conta...' : <>Criar conta <ArrowRight className="ml-2 w-4 h-4" /></>}
            </Button>
            <p className="text-xs text-gray-500 text-center">Ao se cadastrar, você concorda com nossos Termos e Política de Privacidade.</p>
          </form>

          <div className="mt-8 text-center text-sm text-gray-600">
            Já tem conta? <Link to="/login" className="font-semibold text-emerald-800 hover:underline">Entrar</Link>
          </div>
        </div>
      </div>

      <div className="hidden lg:block relative bg-emerald-950 overflow-hidden order-1 lg:order-2">
        <img src="https://images.unsplash.com/photo-1671308819531-1097d5ab5dcc" alt="Rural" className="absolute inset-0 w-full h-full object-cover opacity-30" />
        <div className="absolute inset-0 bg-gradient-to-tl from-emerald-950/95 via-emerald-900/85 to-emerald-800/70" />
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
              Junte-se a <span className="italic text-amber-300">800+</span> profissionais.
            </h1>
            <p className="text-emerald-200/90 text-lg max-w-md">Um ecossistema completo para avaliações urbanas, rurais e de garantias com IA.</p>
            <div className="grid grid-cols-3 gap-4 mt-10">
              <div><div className="font-display text-3xl font-bold text-amber-300">5k+</div><div className="text-xs text-emerald-200">Laudos</div></div>
              <div><div className="font-display text-3xl font-bold text-amber-300">27</div><div className="text-xs text-emerald-200">Estados</div></div>
              <div><div className="font-display text-3xl font-bold text-amber-300">4.9★</div><div className="text-xs text-emerald-200">Avaliação</div></div>
            </div>
          </div>
          <div className="text-xs text-emerald-300">© 2026 RomaTec AvalieImob</div>
        </div>
      </div>
    </div>
  );
};

export default Register;
