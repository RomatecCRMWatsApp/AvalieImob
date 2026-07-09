import React, { useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Lock, Eye, EyeOff, ArrowLeft } from 'lucide-react';
import SEO from '../components/common/SEO';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import BrandMark from '../components/brand/BrandMark';
import { authAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

const GREEN = '#0C3320';

export default function RedefinirSenha() {
  const { token } = useParams();
  const nav = useNavigate();
  const { setSession } = useAuth();
  const [senha, setSenha] = useState('');
  const [conf, setConf] = useState('');
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (senha.length < 8) { setError('A senha deve ter pelo menos 8 caracteres.'); return; }
    if (senha !== conf) { setError('As senhas não conferem.'); return; }
    setLoading(true);
    try {
      const res = await authAPI.resetPassword(token, senha);
      if (setSession && res?.token) {
        setSession(res);
        nav('/dashboard', { replace: true });
      } else {
        nav('/login', { replace: true });
      }
    } catch (err) {
      const msg = err?.response?.data?.detail
        || 'Link inválido ou expirado. Solicite um novo.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <SEO title="Redefinir senha — AvalieImob" noindex />
      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
        <Link to="/" className="flex items-center gap-3 mb-6">
          <BrandMark variant="badge" size={38} title="AvalieImob" />
          <div>
            <div className="font-display text-lg font-bold" style={{ color: GREEN }}>AvalieImob</div>
            <div className="text-[10px] tracking-[0.2em] text-gray-400 uppercase">ROMATEC · PTAM · LAUDOS</div>
          </div>
        </Link>

        <h1 className="text-xl font-bold text-gray-900 mb-1">Criar nova senha</h1>
        <p className="text-sm text-gray-500 mb-6">Escolha uma senha com pelo menos 8 caracteres.</p>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Nova senha</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <Input type={show ? 'text' : 'password'} value={senha} onChange={(e) => setSenha(e.target.value)}
                placeholder="Mínimo 8 caracteres" className="pl-9 pr-9" autoFocus />
              <button type="button" onClick={() => setShow((s) => !s)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400" aria-label="Mostrar senha">
                {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Confirmar nova senha</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <Input type={show ? 'text' : 'password'} value={conf} onChange={(e) => setConf(e.target.value)}
                placeholder="Repita a senha" className="pl-9" />
            </div>
          </div>
          {error && <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</div>}
          <Button type="submit" disabled={loading} className="w-full" style={{ background: GREEN }}>
            {loading ? 'Salvando…' : 'Redefinir senha e entrar'}
          </Button>
        </form>

        <Link to="/login" className="inline-flex items-center gap-1.5 mt-6 text-sm text-gray-500 hover:text-emerald-800">
          <ArrowLeft className="w-4 h-4" /> Voltar ao login
        </Link>
      </div>
    </div>
  );
}
