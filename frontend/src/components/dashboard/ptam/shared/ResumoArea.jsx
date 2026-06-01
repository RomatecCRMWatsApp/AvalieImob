// @module ptam/shared/ResumoArea — Conversões de área e valor unitário (R$/m², R$/ha, R$/alqueire mineiro)
// Exibido no Step 8 (Cálculos) — NBR 14653.
import React from 'react';
import { M2_PER_HA, M2_PER_ALQ, fmtBR } from '@/utils/areaConversao';
import { isRural } from './RuralDocSection';

const fmtBRL = (v) =>
  (Number(v) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

/**
 * @param {object} props
 * @param {number} props.areaM2      área considerada em m²
 * @param {string} props.tipoImovel  property_type
 * @param {number} props.valorTotal  R$ total calculado pelo módulo de amostras
 */
export function ResumoArea({ areaM2, tipoImovel, valorTotal }) {
  const m2 = Number(areaM2) || 0;
  const total = Number(valorTotal) || 0;
  const rural = isRural(tipoImovel);
  const unitRef = rural ? 'R$/ha' : 'R$/m²';

  const valorM2 = m2 > 0 ? total / m2 : 0;
  const valorHa = m2 > 0 ? total / (m2 / M2_PER_HA) : 0;
  const valorAlq = m2 > 0 ? total / (m2 / M2_PER_ALQ) : 0;

  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden bg-white">
      <div className="grid grid-cols-2 gap-px bg-gray-200">
        {/* Conversões de área */}
        <div className="bg-white">
          <div className="bg-gray-50 px-4 py-2.5 border-b border-gray-200">
            <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
              Área considerada — conversões
            </h4>
          </div>
          <table className="w-full text-sm">
            <tbody>
              <tr className="border-b border-gray-100">
                <td className="px-4 py-2 text-gray-500">m²</td>
                <td className="px-4 py-2 text-right font-medium text-gray-800 tabular-nums">{fmtBR(m2, 2)}</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="px-4 py-2 text-gray-500">Hectares</td>
                <td className="px-4 py-2 text-right font-medium text-gray-800 tabular-nums">{fmtBR(m2 / M2_PER_HA, 6)}</td>
              </tr>
              <tr>
                <td className="px-4 py-2 text-gray-500">Alqueires mineiros</td>
                <td className="px-4 py-2 text-right font-medium text-gray-800 tabular-nums">{fmtBR(m2 / M2_PER_ALQ, 6)}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Valor unitário */}
        <div className="bg-white">
          <div className="bg-emerald-50 px-4 py-2.5 border-b border-emerald-100">
            <h4 className="text-xs font-semibold text-emerald-700 uppercase tracking-wide">Valor unitário</h4>
          </div>
          <table className="w-full text-sm">
            <tbody>
              <tr className="border-b border-gray-100">
                <td className="px-4 py-2 text-gray-500">R$/m²</td>
                <td className="px-4 py-2 text-right font-medium text-gray-800 tabular-nums">{fmtBRL(valorM2)}</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="px-4 py-2 text-gray-500">R$/ha</td>
                <td className="px-4 py-2 text-right font-medium text-gray-800 tabular-nums">{fmtBRL(valorHa)}</td>
              </tr>
              <tr>
                <td className="px-4 py-2 text-gray-500">R$/alqueire mineiro</td>
                <td className="px-4 py-2 text-right font-medium text-gray-800 tabular-nums">{fmtBRL(valorAlq)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <p className="px-4 py-2.5 text-[11px] text-gray-500 border-t border-gray-200">
        Unidade de referência: <strong className="text-gray-700">{unitRef}</strong>
        &nbsp;· NBR 14653 · 1 alq mineiro = 4,84 ha = 48.400 m²
      </p>
    </div>
  );
}

export default ResumoArea;
