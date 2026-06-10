// @module dashboard/LaudosChart — Gráfico de produção de laudos (design v4).
// Barras com recharts: mês de pico em verde médio, atual em dourado, demais em verde claro.
import React, { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

const COL_NORMAL = '#C8E6D0';
const COL_PICO   = '#1E6B38';
const COL_ATUAL  = '#C9A84C';

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white rounded-lg shadow-md px-3 py-2 text-xs" style={{ border: '1px solid var(--dash-green-light)' }}>
      <div className="font-semibold" style={{ color: 'var(--dash-text)' }}>{label}</div>
      <div style={{ color: 'var(--dash-muted)' }}>
        {payload[0].value} laudo{payload[0].value === 1 ? '' : 's'}
      </div>
    </div>
  );
};

const LaudosChart = ({ data = [] }) => {
  // índice do mês de pico e do mês atual (último da série)
  const { maxIdx, currentIdx } = useMemo(() => {
    if (!data.length) return { maxIdx: -1, currentIdx: -1 };
    const max = Math.max(...data.map((d) => d.total));
    return {
      maxIdx: data.findIndex((d) => d.total === max),
      currentIdx: data.length - 1,
    };
  }, [data]);

  const colorFor = (i) => {
    if (i === currentIdx) return COL_ATUAL;
    if (i === maxIdx)     return COL_PICO;
    return COL_NORMAL;
  };

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="dash-display" style={{ fontSize: 18, color: 'var(--dash-text)' }}>
            Produção de laudos
          </h3>
          <p style={{ fontSize: 11, color: 'var(--dash-muted)' }}>Últimos 6 meses</p>
        </div>
        <div className="flex items-center gap-3 text-[10px] font-semibold" style={{ color: 'var(--dash-muted)' }}>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm inline-block" style={{ background: COL_PICO }} />Pico</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm inline-block" style={{ background: COL_ATUAL }} />Atual</span>
        </div>
      </div>

      <div className="flex-1 min-h-[200px]">
        {data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-sm" style={{ color: 'var(--dash-muted)' }}>
            Sem dados de produção ainda.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%" minHeight={200}>
            <BarChart data={data} margin={{ top: 8, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="#DFF0E6" />
              <XAxis
                dataKey="mes"
                tick={{ fontSize: 11, fill: '#6B8072' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 11, fill: '#6B8072' }}
                axisLine={false}
                tickLine={false}
                width={32}
              />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(30,107,56,0.06)' }} />
              <Bar dataKey="total" radius={[6, 6, 0, 0]} maxBarSize={48}>
                {data.map((_, i) => (
                  <Cell key={i} fill={colorFor(i)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default LaudosChart;
