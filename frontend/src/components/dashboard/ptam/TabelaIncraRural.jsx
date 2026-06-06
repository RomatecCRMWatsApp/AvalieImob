// @module ptam/TabelaIncraRural — Referência INCRA/RAMT (Valores de Terra) para laudos rurais.
// Layout RAMT: cabeçalho (Região/Polo/Fonte/Norma), tabela VTI mín/médio/máx + N amostras com
// destaque da tipologia correspondente à média da avaliação (R$/ha), fatores e notas técnicas.
import React, { useEffect, useState } from 'react';
import { incraAPI } from '@/lib/api';
import { getFaixaMatch, faixaContemMedia } from '@/utils/incraFaixa';

// Valor exato (sem arredondar): inteiro sem casas; mantém 2 casas se houver decimais.
const fmtHa = (v) => {
  const n = Number(v || 0);
  return n % 1 === 0
    ? n.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
    : n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};
const fmtBRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

// Nota técnica padrão (RAMT-MA) — usada quando a tabela não traz notas próprias.
const NOTAS_PADRAO =
  '(1) VTI = Valor Total do Imóvel (inclui benfeitorias); para obter VTN deduzir benfeitorias ' +
  'conforme laudo de vistoria. (2) Faixas mín/máx estimadas pelo perito aplicando ±30% sobre a ' +
  'média amostral, conforme metodologia INCRA PPR. (3) Atualização monetária obrigatória via ' +
  'IPCA-E entre data-base jul/2022 e data da avaliação (NBR 14653-3, item 8.2.1). (4) Dados de ' +
  'pesquisa primária do avaliador devem complementar e prevalecer sobre os referenciais do RAMT ' +
  'quando disponíveis (NBR 14653-3, item 8.1). (5) Fonte: INCRA/SR-21-MA — RAMT-MA 2022, ' +
  'SEI n.º 15897588 / PPR SR(MA) 15854957.';

function Card({ label, value }) {
  return (
    <div className="flex-1 min-w-[120px] rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-gray-400">{label}</div>
      <div className="text-sm font-semibold text-gray-800 leading-snug">{value || '—'}</div>
    </div>
  );
}

export default function TabelaIncraRural({ mediaAvaliacaoHa = 0, municipio, regiao }) {
  const [tabela, setTabela] = useState(null);
  const [status, setStatus] = useState('loading'); // loading | ok | empty | error

  useEffect(() => {
    let vivo = true;
    setStatus('loading');
    incraAPI
      .tabelaVigente({ municipio: municipio || undefined, regiao: regiao || undefined })
      .then((data) => { if (vivo) { setTabela(data); setStatus('ok'); } })
      .catch((err) => { if (vivo) setStatus(err?.response?.status === 404 ? 'empty' : 'error'); });
    return () => { vivo = false; };
  }, [municipio, regiao]);

  if (status === 'loading') {
    return <div className="mt-4 p-4 rounded-xl border border-gray-200 bg-gray-50 text-sm text-gray-500">Carregando referência INCRA…</div>;
  }
  if (status === 'empty') {
    return <div className="mt-4 p-3 rounded-lg border border-amber-200 bg-amber-50 text-xs text-amber-700">Tabela INCRA não cadastrada para esta região.</div>;
  }
  if (status === 'error' || !tabela) {
    return <div className="mt-4 p-3 rounded-lg border border-gray-200 bg-gray-50 text-xs text-gray-500">Não foi possível carregar a referência INCRA.</div>;
  }

  const faixas = Array.isArray(tabela.faixas) ? tabela.faixas : [];
  const fatores = Array.isArray(tabela.fatores) ? tabela.fatores : [];
  const idxMatch = getFaixaMatch(faixas, mediaAvaliacaoHa);
  const dentro = faixaContemMedia(faixas, idxMatch, mediaAvaliacaoHa);
  const faixaSel = faixas[idxMatch];

  return (
    <div className="mt-5 rounded-xl border border-gray-200 overflow-hidden bg-white">
      <div className="bg-[#0B6E4F] px-4 py-2.5">
        <h3 className="text-sm font-semibold text-white">REFERÊNCIA INCRA — Valores de Terra (RAMT)</h3>
      </div>

      {/* Cabeçalho — cards */}
      <div className="flex flex-wrap gap-2 p-3 border-b border-gray-100">
        <Card label="Região" value={tabela.regiao} />
        <Card label="Polo regional" value={tabela.polo_regional || tabela.municipio} />
        <Card label="Fonte" value={`${tabela.fonte || '—'}${tabela.vigencia ? ` · ${tabela.vigencia}` : ''}`} />
        <Card label="Norma" value={tabela.norma || 'NBR 14653-3:2019'} />
      </div>

      {/* Tabela de tipologias / VTI */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm min-w-[620px]">
          <thead>
            <tr className="bg-gray-50 text-gray-600 text-xs">
              <th className="text-left font-semibold px-3 py-2">Tipologia de uso</th>
              <th className="text-right font-semibold px-3 py-2">VTI mín. (R$/ha)</th>
              <th className="text-right font-semibold px-3 py-2">VTI médio (R$/ha)</th>
              <th className="text-right font-semibold px-3 py-2">VTI máx. (R$/ha)</th>
              <th className="text-right font-semibold px-3 py-2">N amostras</th>
            </tr>
          </thead>
          <tbody>
            {faixas.map((f, i) => {
              const isMatch = i === idxMatch;
              const cor = !isMatch ? '' : dentro ? 'bg-blue-100 border-l-4 border-blue-500' : 'bg-red-100 border-l-4 border-red-500';
              const corTexto = !isMatch ? 'text-gray-800' : dentro ? 'text-blue-800' : 'text-red-800';
              return (
                <tr key={i} className={`border-t border-gray-100 ${cor} ${corTexto}`}>
                  <td className="px-3 py-2">{f.faixa}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmtHa(f.vr_min)}</td>
                  <td className={`px-3 py-2 text-right tabular-nums font-bold`}>{fmtHa(f.vr_medio)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmtHa(f.vr_max)}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-gray-500">{f.n_amostras ?? '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legenda do valor avaliando */}
      <div className={`px-4 py-2 text-xs border-t ${dentro ? 'bg-blue-50 text-blue-800 border-blue-200' : 'bg-red-50 text-red-800 border-red-200'}`}>
        ► Valor da avaliação: <strong>{fmtBRL(mediaAvaliacaoHa)}/ha</strong>{' — '}
        {dentro ? `dentro da faixa: "${faixaSel?.faixa || '—'}"` : `faixa mais próxima: "${faixaSel?.faixa || '—'}"`}
      </div>

      {/* Fatores de homogeneização */}
      {fatores.length > 0 && (
        <div className="border-t border-gray-100">
          <div className="px-4 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wide bg-gray-50">
            Fatores de homogeneização sugeridos — {tabela.norma || 'NBR 14653-3'}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[520px]">
              <thead>
                <tr className="text-gray-500 text-xs">
                  <th className="text-left font-medium px-3 py-1.5">Fator</th>
                  <th className="text-left font-medium px-3 py-1.5">Variável</th>
                  <th className="text-right font-medium px-3 py-1.5">Faixa de ajuste</th>
                </tr>
              </thead>
              <tbody>
                {fatores.map((ft, i) => (
                  <tr key={i} className="border-t border-gray-100">
                    <td className="px-3 py-1.5 font-medium text-gray-700">{ft.fator}</td>
                    <td className="px-3 py-1.5 text-gray-600">{ft.variavel}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums text-gray-700">{ft.faixa_ajuste}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Notas técnicas (da tabela; se não houver, usa a nota padrão RAMT) */}
      <div className="border-t border-gray-100 px-4 py-2.5 text-[11px] text-gray-500 leading-relaxed bg-gray-50">
        <span className="font-semibold text-gray-600">Notas técnicas: </span>{tabela.notas || NOTAS_PADRAO}
      </div>
    </div>
  );
}
