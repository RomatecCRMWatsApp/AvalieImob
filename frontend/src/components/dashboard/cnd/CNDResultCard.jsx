import React, { useState } from 'react';
import { Shield, Scale, Building2, Landmark, Search, UserCheck, Download, ExternalLink } from 'lucide-react';
import CNDStatusBadge from './CNDStatusBadge';
import { cndAPI } from '../../../lib/api';

const PROVIDER_META = {
  receita:       { label: 'Receita Federal',              Icon: Shield,    link: 'https://solucoes.receita.fazenda.gov.br/Servicos/certidaointernet/PF/Emitir' },
  pgfn:          { label: 'PGFN - Dívida Ativa',          Icon: Landmark,  link: 'https://solucoes.receita.fazenda.gov.br/Servicos/certidaointernet/PF/Emitir' },
  tst:           { label: 'TST - Certidão Trabalhista',   Icon: Scale,     link: 'https://consulta-certidao.tst.jus.br/' },
  trf1:          { label: 'TRF1 - Justiça Federal',       Icon: Building2, link: 'https://pje.trf1.jus.br/certidao/' },
  tjma:          { label: 'TJMA - Justiça Estadual',      Icon: Building2, link: 'https://jurisconsult.tjma.jus.br/' },
  cnib:          { label: 'CNIB - Indisponibilidade',     Icon: Search,    link: 'https://www.cnib.com.br/' },
  rfb_cadastro:  { label: 'Situação Cadastral CPF/CNPJ',  Icon: UserCheck, link: 'https://www.receita.fazenda.gov.br/Aplicacoes/SSL/ATCTA/cpf/ConsultaPublica.asp' },
};

const BORDER_COLOR = {
  negativa:     'border-l-emerald-500',
  positiva:     'border-l-yellow-400',
  erro:         'border-l-red-500',
  indisponivel: 'border-l-gray-300',
  processando:  'border-l-blue-400',
};

export default function CNDResultCard({ certidao, consultaId }) {
  const [downloading, setDownloading] = useState(false);
  const meta = PROVIDER_META[certidao.provider] || { label: certidao.provider, Icon: Shield, link: '#' };
  const Icon = meta.Icon;
  const borderColor = BORDER_COLOR[certidao.resultado] || 'border-l-gray-300';

  const handleDownload = async () => {
    if (certidao.resultado === 'indisponivel') return;
    setDownloading(true);
    try {
      const res = await cndAPI.downloadCertidao(consultaId, certidao.provider);
      if (res.pdf_base64) {
        const link = document.createElement('a');
        link.href = `data:application/pdf;base64,${res.pdf_base64}`;
        link.download = res.filename || `certidao_${certidao.provider}.pdf`;
        link.click();
      }
    } catch {
      // silently ignore
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className={`bg-white rounded-xl border border-gray-200 border-l-4 ${borderColor} p-4 flex flex-col gap-3`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
            <Icon className="w-4 h-4 text-gray-600" />
          </div>
          <span className="text-sm font-semibold text-gray-800 leading-tight">{meta.label}</span>
        </div>
        <CNDStatusBadge status={certidao.resultado} small />
      </div>

      {certidao.observacao && (
        <p className="text-xs text-gray-500 leading-relaxed">{certidao.observacao}</p>
      )}

      {certidao.tempo_ms && (
        <p className="text-[10px] text-gray-400">{(certidao.tempo_ms / 1000).toFixed(1)}s de consulta</p>
      )}

      <div className="flex gap-2 flex-wrap mt-auto pt-1">
        {certidao.resultado !== 'indisponivel' && certidao.resultado !== 'erro' && (
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-emerald-900 text-white
                       hover:bg-emerald-800 transition-colors disabled:opacity-50"
          >
            <Download className="w-3 h-3" />
            {downloading ? 'Baixando...' : 'PDF'}
          </button>
        )}
        <a
          href={meta.link}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-gray-200
                     text-gray-600 hover:bg-gray-50 transition-colors"
        >
          <ExternalLink className="w-3 h-3" /> Consulta manual
        </a>
      </div>
    </div>
  );
}
