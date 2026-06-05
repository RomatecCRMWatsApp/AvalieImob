// @module ptam/shared/AreaConsideradaSelector — Seletor de área considerada no cálculo
// Cards terreno / construída / personalizada com default automático por tipo de imóvel.
import React, { useEffect, useRef, useState } from 'react';
import { toM2, fromM2, fmtBR } from '@/utils/areaConversao';
import { isRural } from './RuralDocSection';

function defaultOpcao(tipo) {
  return isRural(tipo) ? 'terreno' : 'construida';
}
function defaultUnidade(tipo) {
  return isRural(tipo) ? 'ha' : 'm2';
}

const OPCOES = ['terreno', 'construida', 'soma', 'personalizada'];
const LABELS = {
  terreno: 'Área do terreno',
  construida: 'Área construída',
  soma: 'Terreno + Construída',
  personalizada: 'Personalizada',
};

/**
 * @param {object} props
 * @param {number} props.terrenoM2     área do terreno em m²
 * @param {number} props.construidaM2  área construída em m²
 * @param {string} props.tipoImovel    property_type (rural/fazenda/... → rural)
 * @param {number} props.value         área considerada (sempre em m²)
 * @param {(m2:number)=>void} props.onChange
 */
export function AreaConsideradaSelector({ terrenoM2, construidaM2, tipoImovel, value, onChange, onOpcaoChange }) {
  const [opcao, setOpcao] = useState(defaultOpcao(tipoImovel));
  const [customVal, setCustomVal] = useState('');
  const [customUnit, setCustomUnit] = useState(defaultUnidade(tipoImovel));
  const [autoApplied, setAutoApplied] = useState(true);

  const prevTipo = useRef(tipoImovel);
  const mounted = useRef(false);

  // Aplica default por tipo — sem sobrescrever um valor já preenchido pelo avaliador.
  useEffect(() => {
    const tipoMudou = prevTipo.current !== tipoImovel;
    prevTipo.current = tipoImovel;

    // No mount: só auto-aplica se ainda não houver valor salvo.
    if (!mounted.current) {
      mounted.current = true;
      if (Number(value) > 0) {
        setAutoApplied(false);
        return;
      }
    } else if (!tipoMudou) {
      return; // re-render sem mudança de tipo: nada a fazer aqui
    }

    const op = defaultOpcao(tipoImovel);
    setOpcao(op);
    setCustomUnit(defaultUnidade(tipoImovel));
    setAutoApplied(true);
    onChange(op === 'terreno' ? Number(terrenoM2) || 0 : Number(construidaM2) || 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tipoImovel]);

  // Mantém o valor sincronizado quando o avaliador edita terreno/construída e a opção é uma delas.
  useEffect(() => {
    if (opcao === 'terreno') onChange(Number(terrenoM2) || 0);
    if (opcao === 'construida') onChange(Number(construidaM2) || 0);
    if (opcao === 'soma') onChange((Number(terrenoM2) || 0) + (Number(construidaM2) || 0));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [terrenoM2, construidaM2]);

  function handleSelect(op) {
    setOpcao(op);
    setAutoApplied(false);
    if (onOpcaoChange) onOpcaoChange(op);
    if (op === 'terreno') onChange(Number(terrenoM2) || 0);
    if (op === 'construida') onChange(Number(construidaM2) || 0);
    if (op === 'soma') onChange((Number(terrenoM2) || 0) + (Number(construidaM2) || 0));
    if (op === 'personalizada') {
      const num = parseFloat(String(customVal).replace(',', '.')) || 0;
      onChange(toM2(num, customUnit));
    }
  }

  const du = defaultUnidade(tipoImovel);
  const unitLabel = du === 'ha' ? 'ha' : 'm²';
  const dispVal = (m2) => fmtBR(fromM2(Number(m2) || 0, du), du === 'ha' ? 6 : 2);

  return (
    <div className="col-span-2">
      <div className="flex items-center gap-2 mb-1.5">
        <label className="block text-sm font-medium text-gray-700">
          Área a ser considerada no cálculo <span className="text-red-500">*</span>
        </label>
        {autoApplied && (
          <span className="text-[10px] font-medium uppercase tracking-wide text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5">
            automático por tipo
          </span>
        )}
      </div>

      {autoApplied && (
        <p className="text-xs text-gray-500 mb-2">
          {isRural(tipoImovel)
            ? 'Imóvel rural → área do terreno por padrão. Referência: ha e alqueire mineiro.'
            : 'Imóvel urbano → área construída por padrão. Referência: m².'}
        </p>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {OPCOES.map((op) => {
          const selected = opcao === op;
          const somaM2 = (Number(terrenoM2) || 0) + (Number(construidaM2) || 0);
          const v =
            op === 'personalizada'
              ? (selected ? dispVal(value) : '—')
              : op === 'soma'
                ? dispVal(somaM2)
                : dispVal(op === 'terreno' ? terrenoM2 : construidaM2);
          return (
            <button
              key={op}
              type="button"
              onClick={() => handleSelect(op)}
              className={`flex flex-col items-start gap-0.5 rounded-lg border p-3 text-left transition-colors ${
                selected
                  ? 'border-emerald-500 bg-emerald-50 ring-1 ring-emerald-500'
                  : 'border-gray-200 bg-white hover:border-emerald-300 hover:bg-emerald-50/40'
              }`}
            >
              <span className={`text-xs font-medium ${selected ? 'text-emerald-700' : 'text-gray-500'}`}>
                {LABELS[op]}
              </span>
              <span className={`text-lg font-semibold tabular-nums ${selected ? 'text-emerald-900' : 'text-gray-800'}`}>
                {v}
              </span>
              <span className="text-[11px] text-gray-400">{unitLabel}</span>
            </button>
          );
        })}
      </div>

      {opcao === 'soma' && (
        <div className="mt-2 text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-md px-3 py-2">
          Valor final pelo <strong>Método Evolutivo</strong> (NBR 14653): valor do lote + valor da
          edificação. Defina os valores do <strong>terreno</strong> e da <strong>edificação</strong> na
          etapa <strong>8. Cálculos</strong> (painel Evolutivo, ativado automaticamente).
        </div>
      )}

      {opcao === 'personalizada' && (
        <div className="mt-3 flex gap-2">
          <input
            type="number"
            min={0}
            step="any"
            value={customVal}
            placeholder="Ex: 4,84"
            onChange={(e) => {
              setCustomVal(e.target.value);
              const num = parseFloat(e.target.value.replace(',', '.')) || 0;
              onChange(toM2(num, customUnit));
            }}
            className="flex-1 h-10 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
          />
          <select
            value={customUnit}
            onChange={(e) => {
              const u = e.target.value;
              setCustomUnit(u);
              const num = parseFloat(String(customVal).replace(',', '.')) || 0;
              onChange(toM2(num, u));
            }}
            className="h-10 rounded-md border border-gray-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
          >
            <option value="m2">m²</option>
            <option value="ha">hectare (ha)</option>
            <option value="alq">alqueire mineiro</option>
          </select>
        </div>
      )}
    </div>
  );
}

export default AreaConsideradaSelector;
