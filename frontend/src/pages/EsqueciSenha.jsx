import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft, CheckCircle2 } from 'lucide-react';
import SEO from '../components/common/SEO';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import BrandMark from '../components/brand/BrandMark';
import { authAPI } from '../lib/api';

const GREEN = '#0C3320';

export default function EsqueciSenha() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (!email.trim()) { setError('Informe seu e-mail.'); return; }
    setLoading(true);
    try {
      await authAPI.forgotPassword(email.trim());
      setEnviado(true);
    } catch (err) {
      // resposta é genérica de propósito; só erro de rede/limite cai aqui
      const msg = err?.response?.status === 429
        ? 'Muitas solicitações. Aguarde um minuto e tente novamente.'
        : (err?.response?.data?.detail || 'Não foi possível enviar. Tente novamente.');
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <SEO title="Recuperar senha — AvalieImob" noindex />
      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
        <Link to="/" className="flex items-center gap-3 mb-6">
          <BrandMark variant="badge" size={38} title="AvalieImob" />
          <div>
            <div className="font-display text-lg font-bold" style={{ color: GREEN }}>AvalieImob</div>
            <div className="text-[10px] tracking-[0.2em] text-gray-400 uppercase">ROMATEC · PTAM · LAUDOS</div>
          </div>
        </Link>

        {enviado ? (
          <div className="text-center py-4">
            <CheckCircle2 className="w-12 h-12 mx-auto text-emerald-600 mb-3" />
            <h1 className="text-xl font-bold text-gray-900 mb-2">Verifique seu e-mail</h1>
            <p className="text-sm text-gray-600 leading-relaxed">
              Se <strong>{email}</strong> estiver cadastrado, enviamos um link para redefinir
              sua senha. Ele vale por <strong>30 minutos</strong>. Confira também o spam.
            </p>
            <Link to="/login" className="inline-flex items-center gap-1.5 mt-6 text-sm font-semibold text-emerald-800 hover:underline">
              <ArrowLeft className="w-4 h-4" /> Voltar ao login
            </Link>
          </div>
        ) : (
          <>
            <h1 className="text-xl font-bold text-gray-900 mb-1">Recuperar senha</h1>
            <p className="text-sm text-gray-500 mb-6">
              Informe o e-mail da sua conta e enviaremos um link para criar uma nova senha.
            </p>
            <form onSubmit={submit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">E-mail</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                    placeholder="seu@email.com" className="pl-9" autoFocus />
                </div>
              </div>
              {error && <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</div>}
              <Button type="submit" disabled={loading} className="w-full" style={{ background: GREEN }}>
                {loading ? 'Enviando…' : 'Enviar link de redefinição'}
              </Button>
            </form>
            <Link to="/login" className="inline-flex items-center gap-1.5 mt-6 text-sm text-gray-500 hover:text-emerald-800">
              <ArrowLeft className="w-4 h-4" /> Voltar ao login
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
