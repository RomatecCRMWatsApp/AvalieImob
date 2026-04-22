import React from 'react';

const base = 'w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-800 ' +
             'focus:outline-none focus:border-emerald-400 transition-colors bg-white';

const FieldRenderer = ({ field, value, onChange }) => {
  const fieldKey = field.key || field.id;
  const label = field.label || '';
  const tipo = field.tipo || field.type || 'text';
  const opcoes = field.opcoes || [];
  const required = field.required || field.obrigatorio || false;
  const placeholder = field.placeholder || '';
  const ajuda = field.ajuda || '';

  const change = (val) => onChange(fieldKey, val);

  switch (tipo) {
    case 'textarea':
    case 'caixa_texto':
      return (
        <div className="sm:col-span-2 space-y-1">
          <label className="text-xs font-medium text-gray-600">{label}{required && ' *'}</label>
          <textarea rows={3} className={`${base} resize-none`} value={value ?? ''} onChange={e => change(e.target.value)} placeholder={placeholder || label} />
          {ajuda && <p className="text-[10px] text-gray-400">{ajuda}</p>}
        </div>
      );

    case 'select':
      return (
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{label}{required && ' *'}</label>
          <select className={base} value={value ?? ''} onChange={e => change(e.target.value)}>
            <option value="">Selecione...</option>
            {opcoes.map(op => <option key={op} value={op}>{op}</option>)}
          </select>
          {ajuda && <p className="text-[10px] text-gray-400">{ajuda}</p>}
        </div>
      );

    case 'multiselect':
    case 'multicheck': {
      const selected = Array.isArray(value) ? value : [];
      const toggle = (op) => {
        const next = selected.includes(op) ? selected.filter(x => x !== op) : [...selected, op];
        change(next);
      };
      return (
        <div className="sm:col-span-2 space-y-1">
          <label className="text-xs font-medium text-gray-600">{label}{required && ' *'}</label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 p-3 bg-gray-50 rounded-xl border border-gray-200">
            {opcoes.map(op => (
              <label key={op} className="flex items-center gap-1.5 text-xs text-gray-700 cursor-pointer">
                <input type="checkbox" checked={selected.includes(op)} onChange={() => toggle(op)} className="w-3.5 h-3.5 rounded accent-emerald-700" />
                {op}
              </label>
            ))}
          </div>
          {ajuda && <p className="text-[10px] text-gray-400">{ajuda}</p>}
        </div>
      );
    }

    case 'tabela': {
      const rows = Array.isArray(value) ? value : [{}];
      const cols = opcoes.length > 0 ? opcoes : ['Item', 'Valor'];
      const updateRow = (i, col, val) => {
        const next = [...rows];
        next[i] = { ...next[i], [col]: val };
        change(next);
      };
      const addRow = () => change([...rows, {}]);
      const removeRow = (i) => change(rows.filter((_, idx) => idx !== i));
      return (
        <div className="sm:col-span-2 space-y-1">
          <label className="text-xs font-medium text-gray-600">{label}{required && ' *'}</label>
          <div className="overflow-x-auto rounded-xl border border-gray-200">
            <table className="w-full text-xs">
              <thead><tr className="bg-gray-50">{cols.map(c => <th key={c} className="px-2 py-1.5 text-left font-medium text-gray-600 border-b">{c}</th>)}<th className="w-8 border-b"></th></tr></thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={i} className="border-b last:border-0">
                    {cols.map(c => <td key={c} className="px-1 py-1"><input type="text" className="w-full px-2 py-1 rounded border border-gray-100 text-xs" value={row[c] ?? ''} onChange={e => updateRow(i, c, e.target.value)} /></td>)}
                    <td className="px-1"><button type="button" onClick={() => removeRow(i)} className="text-red-400 hover:text-red-600 text-xs">✕</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button type="button" onClick={addRow} className="text-xs text-emerald-700 hover:text-emerald-900 font-medium">+ Adicionar linha</button>
          {ajuda && <p className="text-[10px] text-gray-400 mt-1">{ajuda}</p>}
        </div>
      );
    }

    case 'checkbox':
      return (
        <div className="flex items-center gap-2 py-1">
          <input type="checkbox" id={fieldKey} checked={!!value} onChange={e => change(e.target.checked)} className="w-4 h-4 rounded accent-emerald-700" />
          <label htmlFor={fieldKey} className="text-sm text-gray-700">{label}</label>
        </div>
      );

    case 'date':
      return (
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{label}{required && ' *'}</label>
          <input type="date" className={base} value={value ?? ''} onChange={e => change(e.target.value)} />
        </div>
      );

    case 'number':
      return (
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{label}{required && ' *'}</label>
          <input type="number" className={base} value={value ?? ''} onChange={e => change(e.target.value)} placeholder={placeholder || '0'} />
        </div>
      );

    default: // text
      return (
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{label}{required && ' *'}</label>
          <input type="text" className={base} value={value ?? ''} onChange={e => change(e.target.value)} placeholder={placeholder || label} />
        </div>
      );
  }
};

export default FieldRenderer;
