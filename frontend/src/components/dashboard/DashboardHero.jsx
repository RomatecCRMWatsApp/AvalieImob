// @module dashboard/DashboardHero — saudação compacta do painel (upgrade visual).
// Verde profundo, sem quadriculado; um único título em serif; ações principais
// reais (Novo laudo em dourado, Novo cliente, Nova amostra). Credenciais e empresa
// vêm do perfil do usuário logado e aparecem só a partir do tablet.
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FilePlus2, UserPlus, BarChart2 } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { perfilAPI } from '../../lib/api';

// NUNCA voltar a fixar credenciais aqui. Este hero é visto por TODOS os
// assinantes — texto fixo mostrava o CRECI/CNAI/CFT do dono da plataforma a
// qualquer usuário novo (vazamento de registro profissional alheio).
// Tudo abaixo vem do perfil do usuário LOGADO.

/** Ex.: "CNAI 000000 · CRECI/UF 0.000" — montado dos registros do próprio usuário. */
const credenciaisDoPerfil = (perfil) => {
  const regs = Array.isArray(perfil?.registros) ? perfil.registros : [];
  return regs
    .filter((r) => r && r.numero)
    .map((r) => `${r.tipo || ''}${r.uf ? `/${r.uf}` : ''} ${r.numero}`.trim())
    .join(' · ');
};

/** "Empresa · Cidade / UF" do próprio usuário (partes ausentes são omitidas).
 *  Evita "AÇAILÂNDIA/MA / MA" quando a cidade já foi cadastrada com a UF. */
const cabecalhoDoPerfil = (perfil, user) => {
  const empresa = perfil?.empresa_nome || user?.company || '';
  const cidade = String(perfil?.cidade || '').trim();
  const uf = String(perfil?.uf || '').trim();
  const cidadeJaTemUf = uf && new RegExp(`[/\\-,\\s]${uf}\\s*$`, 'i').test(cidade);
  const local = cidadeJaTemUf ? cidade : [cidade, uf].filter(Boolean).join(' / ');
  return [empresa, local].filter(Boolean).join(' · ');
};

/** Curvas de nível — único detalhe técnico, pequeno, à direita (decorativo). */
const Curvas = () => (
  <svg className="av-contour hidden sm:block" viewBox="0 0 240 200" width="240" fill="none" aria-hidden="true" focusable="false">
    <g stroke="#d0ad4e" strokeWidth="1">
      <path d="M240 18c-46 4-70 30-96 30S96 30 60 44 18 92 0 104" />
      <path d="M240 46c-40 6-58 30-86 32s-44-14-74-2-44 50-80 58" />
      <path d="M240 78c-34 6-52 26-76 28s-40-8-66 4-36 44-98 62" />
      <path d="M240 112c-30 4-44 20-66 22s-34-4-56 8-34 40-62 58" />
      <path d="M240 148c-24 2-38 14-56 16s-28-2-46 6-24 22-44 30" />
    </g>
  </svg>
);

const DashboardHero = ({ greeting, firstName, today, rascunhos }) => {
  const nav = useNavigate();
  const { user } = useAuth();
  const [perfil, setPerfil] = useState(null);

  useEffect(() => {
    let vivo = true;
    perfilAPI.get()
      .then((p) => { if (vivo) setPerfil(p || {}); })
      .catch(() => { if (vivo) setPerfil({}); });
    return () => { vivo = false; };
  }, []);

  const credenciais = credenciaisDoPerfil(perfil);
  const cabecalho = cabecalhoDoPerfil(perfil, user);

  return (
    <section
      aria-labelledby="av-saudacao"
      className="relative overflow-hidden rounded-2xl"
      style={{ background: 'var(--av-brand)', color: '#fff' }}
    >
      <Curvas />
      <div className="relative p-5 sm:p-7 flex flex-col md:flex-row md:items-end md:justify-between gap-5">
        <div className="min-w-0">
          {cabecalho && (
            <p className="av-eyebrow-gold hidden sm:block" style={{ marginBottom: 6 }}>{cabecalho}</p>
          )}
          <h1 id="av-saudacao" className="av-display" style={{ fontSize: 'clamp(1.6rem, 1.3rem + 1.2vw, 2.25rem)', fontWeight: 600, lineHeight: 1.15 }}>
            {greeting}, <span style={{ color: 'var(--av-gold)' }}>{firstName}.</span>
          </h1>
          <p style={{ marginTop: 6, fontSize: 14, color: 'rgb(245 242 232 / 0.78)' }}>
            <span>{today ? today.charAt(0).toUpperCase() + today.slice(1) : ''}</span>
            {rascunhos > 0 && (
              <> · {rascunhos} laudo{rascunhos > 1 ? 's' : ''} em rascunho</>
            )}
          </p>

          <div className="flex flex-wrap gap-3" style={{ marginTop: 18 }}>
            <button type="button" onClick={() => nav('/dashboard/ptam')} className="av-btn av-btn-gold av-on-dark">
              <FilePlus2 size={18} aria-hidden="true" /> Novo laudo
            </button>
            <button type="button" onClick={() => nav('/dashboard/clientes')} className="av-btn av-btn-ghost-dark av-on-dark">
              <UserPlus size={18} aria-hidden="true" /> Novo cliente
            </button>
            <button type="button" onClick={() => nav('/dashboard/amostras')} className="av-btn av-btn-ghost-dark av-on-dark">
              <BarChart2 size={18} aria-hidden="true" /> Nova amostra
            </button>
          </div>
        </div>

        {/* Contexto profissional: só a partir do tablet, para não pesar a primeira dobra no celular */}
        <div className="hidden md:block md:text-right" style={{ maxWidth: 320, fontSize: 13 }}>
          {credenciais ? (
            <p style={{ color: 'rgb(245 242 232 / 0.78)' }}>{credenciais}</p>
          ) : perfil && (
            <button
              type="button"
              onClick={() => nav('/dashboard/config')}
              className="underline underline-offset-2 av-on-dark"
              style={{ color: 'var(--av-gold)', background: 'none', border: 0, cursor: 'pointer', minHeight: 44 }}
            >
              Cadastre seus registros profissionais (CRECI, CNAI, CFT)
            </button>
          )}
        </div>
      </div>
    </section>
  );
};

export default DashboardHero;
