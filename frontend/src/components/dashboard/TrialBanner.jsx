// @module components/dashboard/TrialBanner — faixa de contagem regressiva do acesso de teste.
//
// Aparece só para quem está em TESTE (plan "trial"). Nos últimos 3 dias fica
// âmbar para criar urgência; some para assinantes pagos e contas normais.
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { KeyRound, ArrowRight } from 'lucide-react';
import { paymentsAPI } from '../../lib/api';

const TrialBanner = () => {
  const [info, setInfo] = useState(null);

  useEffect(() => {
    let vivo = true;
    paymentsAPI.status()
      .then((d) => { if (vivo) setInfo(d); })
      .catch(() => {});          // silencioso: o banner é acessório
    return () => { vivo = false; };
  }, []);

  if (!info?.trial || info.trial_situacao !== 'ativo') return null;

  const dias = Number(info.trial_dias_restantes || 0);
  const urgente = dias <= 3;
  const cor = urgente
    ? { bg: '#FEF3C7', borda: '#F59E0B', texto: '#92400E' }
    : { bg: '#ECFDF5', borda: '#0C3320', texto: '#0C3320' };

  return (
    <div className="mb-4 rounded-xl border px-4 py-3 flex flex-wrap items-center justify-between gap-3"
         style={{ background: cor.bg, borderColor: cor.borda }}>
      <div className="flex items-center gap-3">
        <span className="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
              style={{ background: cor.borda }}>
          <KeyRound className="w-4 h-4 text-white" />
        </span>
        <div>
          <div className="font-semibold text-sm" style={{ color: cor.texto }}>
            {dias === 1
              ? 'Último dia do seu acesso de teste'
              : `Acesso de teste — faltam ${dias} dias`}
          </div>
          <div className="text-xs" style={{ color: cor.texto, opacity: 0.85 }}>
            Você está usando a plataforma completa gratuitamente. Assine para não perder seus laudos e documentos.
          </div>
        </div>
      </div>
      <Link to="/dashboard/assinatura"
            className="inline-flex items-center gap-1.5 text-sm font-semibold px-4 py-2 rounded-lg text-white"
            style={{ background: cor.borda }}>
        Assinar agora <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  );
};

export default TrialBanner;
