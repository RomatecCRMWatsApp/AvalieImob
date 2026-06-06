// @module ptam/TabelaIncraRural — Referência INCRA (Valores de Terra Nua) para laudos rurais.
// Busca a tabela vigente e destaca a faixa correspondente à média da avaliação (R$/ha).
import React, { useEffect, useState } from 'react';
import { incraAPI } from '@/lib/api';
import { getFaixaMatch, faixaContemMedia } from '@/utils/incraFaixa';

const fmtBRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export default function TabelaIncraRural({ mediaAvaliacaoHa = 0, municipio, regiao }) {
  const [tabela, setTabela] = useState(null);
  const [status, setStatus] = useState('loading'); // loading | ok | empty | error

  useEffect(() => {
    let vivo = true;
    setStatus('loading');
    incraAPI
      .tabelaVigente({ municipio: municipio || undefined, regiao: regiao || undefined })
      .then((data) => {
        if (!vivo) return;
        setTabela(data);
        setStatus('ok');
      })
      .catch((err) => {
        if (!vivo) return;
        setStatus(err?.response?.status === 404 ? 'empty' : 'error');
      });
    return () => {
      vivo = false;
    };
  }, [municipio, regiao]);

  if (status === 'loading') {
    return (
      <div className="mt-4 p-4 rounded-xl border border-gray-200 bg-gray-50 text-sm text-gray-500">
        Carregando referência INCRA…
      </div>
    );
  }
  if (status === 'empty') {
    return (
      <div className="mt-4 p-3 rounded-lg border border-amber-200 bg-amber-50 text-xs text-amber-700">
        Tabela INCRA não cadastrada para esta região.
      </div>
    );
  }
  if (status === 'error' || !tabela) {
    return (
      <div className="mt-4 p-3 rounded-lg border border-gray-200 bg-gray-50 text-xs text-gray-500">
        Não foi possível carregar a referência INCRA.
      </div>
    );
  }

  const faixas = Array.isArray(tabela.faixas) ? tabela.faixas : [];
  const idxMatch = getFaixaMatch(faixas, mediaAvaliacaoHa);
  const dentro = faixaContemMedia(faixas, idxMatch, mediaAvaliacaoHa);
  const faixaSel = faixas[idxMatch];

  return (
    <div className="mt-5 rounded-xl border border-gray-200 overflow-hidden">
      <div className="bg-[#0B6E4F] px-4 py-3">
        <h3 className="text-sm font-semibold text-white">REFERÊNCIA INCRA — Valores de Terra Nua</h3>
        <p className="text-[11px] text-emerald-100 mt-0.5">
          Região: {tabela.regiao}
          {tabela.municipio ? ` · Município: ${tabela.municipio}` : ''}
          {' · '}Vigência: {tabela.vigencia} · Fonte: {tabela.fonte}
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-600">
              <th className="text-left font-semibold px-3 py-2">Faixa</th>
              <th className="text-right font-semibold px-3 py-2">Mín R$/ha</th>
              <th className="text-right font-semibold px-3 py-2">Máx R$/ha</th>
              <th className="text-right font-semibold px-3 py-2">Med R$/ha</th>
            </tr>
          </thead>
          <tbody>
            {faixas.map((f, i) => {
              const isMatch = i === idxMatch;
              const cor = !isMatch
                ? ''
                : dentro
                  ? 'bg-blue-100 border-l-4 border-blue-500'
                  : 'bg-red-100 border-l-4 border-red-500';
              const corTexto = !isMatch ? 'text-gray-800' : dentro ? 'text-blue-800' : 'text-red-800';
              return (
                <tr key={i} className={`border-t border-gray-100 ${cor} ${corTexto}`}>
                  <td className="px-3 py-2">{f.faixa}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmtBRL(f.vr_min)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmtBRL(f.vr_max)}</td>
                  <td className={`px-3 py-2 text-right tabular-nums ${isMatch ? 'font-bold' : ''}`}>
                    {fmtBRL(f.vr_medio)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className={`px-4 py-2 text-xs border-t ${dentro ? 'bg-blue-50 text-blue-800 border-blue-200' : 'bg-red-50 text-red-800 border-red-200'}`}>
        ► Valor da avaliação: <strong>{fmtBRL(mediaAvaliacaoHa)}/ha</strong>
        {' — '}
        {dentro
          ? `dentro da faixa: "${faixaSel?.faixa || '—'}"`
          : `faixa mais próxima: "${faixaSel?.faixa || '—'}"`}
      </div>
    </div>
  );
}
