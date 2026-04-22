import React from 'react';

const formatCurrency = (v) =>
  v == null || v === ''
    ? ''
    : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v);

const parseCurrency = (str) => {
  const num = parseFloat(str.replace(/[^\d,.-]/g, '').replace(',', '.'));
  return isNaN(num) ? null : num;
};

function AreaSection({ prefix, label, sectionNum, data, onChange }) {
  const tipoKey  = `${prefix}_tipo`;
  const dadosKey = `${prefix}_dados`;
  const valorKey = `${prefix}_valor`;

  const handle = (key) => (e) => onChange({ ...data, [key]: e.target.value });
  const handleValor = (e) => onChange({ ...data, [valorKey]: parseCurrency(e.target.value) });

  return (
    <div className="border border-green-200 rounded-lg p-4 space-y-4 bg-green-50">
      <h3 className="text-base font-semibold text-green-800">
        Seção {sectionNum} — {label}
      </h3>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">Tipo de Área</label>
        <input
          type="text"
          className="border border-gray-300 rounded-md p-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
          value={data[tipoKey] || ''}
          onChange={handle(tipoKey)}
          placeholder="Ex: Terra Nua, Pastagem, Cultura Perene, Benfeitorias..."
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">
          Dados e Cálculo (descrição, amostras, homogeneização)
        </label>
        <textarea
          rows={6}
          className="border border-gray-300 rounded-md p-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 resize-y"
          value={data[dadosKey] || ''}
          onChange={handle(dadosKey)}
          placeholder="Descreva a metodologia de avaliação, fatores de homogeneização, cálculos e resultado..."
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">Valor Total Calculado (R$)</label>
        <input
          type="text"
          className="border border-gray-300 rounded-md p-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
          defaultValue={data[valorKey] != null ? formatCurrency(data[valorKey]) : ''}
          onBlur={handleValor}
          placeholder="Ex: R$ 850.000,00"
        />
      </div>
    </div>
  );
}

export default function StepAvaliacaoAreas({ data, onChange }) {
  const v1 = data.area_01_valor || 0;
  const v2 = data.area_02_valor || 0;
  const total = v1 + v2;

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-green-700">
        Avaliação por Áreas — Seções 8 e 9 (PTAM nº 7010)
      </h2>
      <p className="text-sm text-gray-500">
        Preencha cada área avaliada conforme o modelo. O total será calculado automaticamente.
      </p>

      <AreaSection
        prefix="area_01"
        label="Área 01"
        sectionNum={8}
        data={data}
        onChange={onChange}
      />

      <AreaSection
        prefix="area_02"
        label="Área 02"
        sectionNum={9}
        data={data}
        onChange={onChange}
      />

      {(v1 > 0 || v2 > 0) && (
        <div className="border border-yellow-400 rounded-lg p-4 bg-yellow-50 text-center">
          <p className="text-sm text-gray-600 mb-1">Valor Total das Áreas</p>
          <p className="text-2xl font-bold text-yellow-700">
            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(total)}
          </p>
        </div>
      )}
    </div>
  );
}
