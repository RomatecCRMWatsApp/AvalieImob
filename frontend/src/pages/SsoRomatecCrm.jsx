import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, ExternalLink } from 'lucide-react';
import SEO from '../components/common/SEO';
import BrandMark from '../components/brand/BrandMark';
import { BrandSpinner } from '../components/brand/BrandSpinner';
import { authAPI } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

const GREEN = '#0C3320';
const MSG_PADRAO = 'Link de acesso inválido ou expirado.';

// Entrada pelo Romatec CRM (SSO). O CRM abre /sso#token=<jwt>: o token vem no
// FRAGMENTO (não vai ao servidor nem a logs de acesso) e é de uso único.
function lerTokenDoFragmento() {
  const hash = (window.location.hash || '').replace(/^#/, '');
  const token = new URLSearchParams(hash).get('token');
  // Remove o token da barra de endereço/histórico IMEDIATAMENTE.
  if (hash) {
    window.history.replaceState(null, '', window.location.pathname + window.location.search);
  }
  return token;
}

export default function SsoRomatecCrm() {
  const nav = useNavigate();
  const { setSession } = useAuth();
  const [error, setError] = useState('');
  // O link é de uso único: garante UMA chamada mesmo com o efeito duplo do StrictMode.
  const iniciado = useRef(false);

  useEffect(() => {
    if (iniciado.current) return;
    iniciado.current = true;
    const token = lerTokenDoFragmento();
    if (!token) {
      setError(MSG_PADRAO);
      return;
    }
    authAPI.ssoRomatecCrm(token)
      .then((res) => {
        if (res?.token && res?.user) {
          setSession(res);
          nav('/dashboard', { replace: true });
        } else {
          setError(MSG_PADRAO);
        }
      })
      .catch((err) => {
        const detail = err?.response?.data?.detail;
        setError(typeof detail === 'string' && detail ? detail : MSG_PADRAO);
      });
  }, [nav, setSession]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <SEO title="Entrando pelo Romatec CRM — AvalieImob" noindex />
      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
        <Link to="/" className="flex items-center gap-3 mb-6">
          <BrandMark variant="badge" size={38} title="AvalieImob" />
          <div>
            <div className="font-display text-lg font-bold" style={{ color: GREEN }}>AvalieImob</div>
            <div className="text-[10px] tracking-[0.2em] text-gray-400 uppercase">ROMATEC · PTAM · LAUDOS</div>
          </div>
        </Link>

        {!error ? (
          <div className="py-6">
            <BrandSpinner label="Entrando pelo Romatec CRM…" />
          </div>
        ) : (
          <>
            <h1 className="text-xl font-bold text-gray-900 mb-3">Não foi possível entrar</h1>
            <div className="flex items-start gap-2 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 mb-6">
              <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Gere um novo link de acesso no Romatec CRM ou entre com seu e-mail e senha.
            </p>
            <div className="flex flex-col gap-2">
              <a href="https://romateccrm.com" rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-1.5 rounded-md px-4 py-2 text-sm font-medium text-white"
                style={{ background: GREEN }}>
                Voltar ao Romatec CRM <ExternalLink className="w-4 h-4" />
              </a>
              <Link to="/login" className="inline-flex items-center justify-center gap-1.5 mt-2 text-sm text-gray-500 hover:text-emerald-800">
                <ArrowLeft className="w-4 h-4" /> Ir para o login do AvalieImob
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
