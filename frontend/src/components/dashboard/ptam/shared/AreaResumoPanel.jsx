// @module ptam/shared/AreaResumoPanel — Resumo dinâmico da área considerada
// Input grande + toggle m²/ha + 3 boxes (m² / hectares / alqueires mineiros) atualizados em tempo real.
import React, { useEffect, useRef, useState } from 'react';
import { Info } from 'lucide-react';
import { M2_PER_HA, M2_PER_ALQ, toM2, fromM2, fmtBR } from '@/utils/areaConversao';
import { isRural } from './RuralDocSection';

/**
 * @param {object} props
 * @param {number} props.value        sempre em m² (estado do form pai)
 * @param {(m2:number)=>void} props.onChange
 * @param {string} props.tipoImovel   property_type
 */
export function AreaResumoPanel({ value, onChange, tipoImovel }) {
  const rural = isRural(tipoImovel);
  const defaultUnit = rural ? 'ha' : 'm2';
  const [unit, setUnit] = useState(defaultUnit);
  const [raw, setRaw] = useState(
    Number(value) > 0 ? fmtBR(fromM2(value, defaultUnit), defaultUnit === 'ha' ? 6 : 2) : ''
  );

  // Reflete alterações externas do value (ex.: vindas do AreaConsideradaSelector) no input.
  const lastEmitted = useRef(value);
  useEffect(() => {
    if (Number(value) === Number(lastEmitted.current)) return;
    lastEmitted.current = value;
    setRaw(Number(value) > 0 ? fmtBR(fromM2(value, unit), unit === 'ha' ? 6 : 2) : '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  function handleInput(v) {
    setRaw(v);
    const num = parseFloat(String(v).replace(',', '.'));
    if (!isNaN(num) && num >= 0) {
      const m2 = toM2(num, unit);
      lastEmitted.current = m2;
      onChange(m2);
    } else if (v === '') {
      lastEmitted.current = 0;
      onChange(0);
    }
  }

  function handleToggle(u) {
    setUnit(u);
    if (Number(value) > 0) setRaw(fmtBR(fromM2(value, u), u === 'ha' ? 6 : 2));
    else setRaw('');
  }

  const m2 = Number(value) || 0;
  const ha = m2 / M2_PER_HA;
  const alq = m2 / M2_PER_ALQ;
  const hasVal = raw !== '' && !isNaN(parseFloat(String(raw).replace(',', '.')));

  const unitRef = rural || unit === 'ha' ? 'R$/ha  e  R$/alqueire mineiro' : 'R$/m²';

  const Box = ({ label, val, unitLbl, highlight }) => (
    <div
      className={`flex flex-col gap-0.5 px-4 py-3 border-r border-gray-200 last:border-r-0 ${
        highlight ? 'bg-emerald-50' : 'bg-white'
      }`}
    >
      <span
        className={`text-[11px] uppercase tracking-wide ${
          highlight ? 'text-emerald-700' : 'text-gray-400'
        }`}
      >
        {label}
      </span>
      <span className={`text-lg font-semibold tabular-nums ${highlight ? 'text-emerald-900' : 'text-gray-800'}`}>
        {hasVal ? val : '—'}
      </span>
      <span className={`text-[11px] ${highlight ? 'text-emerald-600' : 'text-gray-400'}`}>{unitLbl}</span>
    </div>
  );

  return (
    <div className="col-span-2 rounded-lg border border-gray-200 overflow-hidden bg-white">
      {/* Linha de entrada */}
      <div className="flex items-stretch border-b border-gray-200">
        <div className="flex-1 flex flex-col gap-1.5 px-4 py-3 border-r border-gray-200">
          <span className="text-[11px] uppercase tracking-wide text-gray-400">
            Área considerada no cálculo
          </span>
          <input
            type="number"
            min={0}
            step="any"
            placeholder="0"
            value={raw}
            onChange={(e) => handleInput(e.target.value)}
            className="w-full bg-transparent border-none outline-none text-2xl font-medium text-gray-900 leading-tight placeholder:text-gray-300"
          />
        </div>
        <div className="flex flex-col min-w-[96px]">
          {['m2', 'ha'].map((u, i) => {
            const active = unit === u;
            return (
              <button
                key={u}
                type="button"
                onClick={() => handleToggle(u)}
                className={`flex-1 flex items-center justify-center gap-1.5 px-4 text-sm font-medium transition-colors ${
                  i === 0 ? 'border-b border-gray-200' : ''
                } ${active ? 'bg-emerald-50 text-emerald-800' : 'text-gray-500 hover:bg-gray-50'}`}
              >
                <span
                  className={`w-[7px] h-[7px] rounded-full ${active ? 'bg-emerald-500' : 'bg-gray-300'}`}
                />
                {u === 'm2' ? 'm²' : 'ha'}
              </button>
            );
          })}
        </div>
      </div>

      {/* 3 boxes de resultado */}
      <div className="grid grid-cols-3 border-b border-gray-200">
        <Box label="metros quadrados" val={fmtBR(m2, 2)} unitLbl="m²" highlight={unit === 'ha' || !hasVal} />
        <Box label="hectares" val={fmtBR(ha, 6)} unitLbl="ha" highlight={unit === 'm2' || !hasVal} />
        <Box label="alqueires mineiros" val={fmtBR(alq, 6)} unitLbl="alq · 4,84 ha" highlight />
      </div>

      {/* Rodapé */}
      <div className="flex items-center gap-1.5 px-4 py-2.5 text-[11px] text-gray-500">
        <Info className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
        <span>
          Unidade de referência do laudo: <strong className="text-gray-700">{unitRef}</strong>
          &ensp;·&ensp;1 ha = 10.000 m²&ensp;·&ensp;1 alq mineiro = 4,84 ha = 48.400 m² (NBR 14653)
        </span>
      </div>
    </div>
  );
}

export default AreaResumoPanel;
