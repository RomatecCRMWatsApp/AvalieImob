import React from 'react';

const base = 'w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-800 ' +
             'focus:outline-none focus:border-emerald-400 transition-colors bg-white';

const FieldRenderer = ({ field, value, onChange }) => {
  const { key, label, opcoes, required, placeholder } = field;
  const tipo = field.tipo || field.type || 'text';

  const handleChange = (e) => {
    const val = tipo === 'checkbox' ? e.target.checked : e.target.value;
    onChange(key, val);
  };

  switch (tipo) {
    case 'textarea':
      return (
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{label}{required && ' *'}</label>
          <textarea
            rows={3}
            className={`${base} resize-none`}
            value={value ?? ''}
            onChange={handleChange}
            placeholder={placeholder || label}
          />
        </div>
      );

    case 'select':
      return (
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{label}{required && ' *'}</label>
          <select className={base} value={value ?? ''} onChange={handleChange}>
            <option value="">Selecione...</option>
            {(opcoes || []).map(op => (
              <option key={op} value={op}>{op}</option>
            ))}
          </select>
        </div>
      );

    case 'checkbox':
      return (
        <div className="flex items-center gap-2 py-1">
          <input
            type="checkbox"
            id={key}
            checked={!!value}
            onChange={handleChange}
            className="w-4 h-4 rounded accent-emerald-700"
          />
          <label htmlFor={key} className="text-sm text-gray-700">{label}</label>
        </div>
      );

    case 'date':
      return (
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{label}{required && ' *'}</label>
          <input type="date" className={base} value={value ?? ''} onChange={handleChange} />
        </div>
      );

    case 'number':
      return (
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{label}{required && ' *'}</label>
          <input
            type="number"
            className={base}
            value={value ?? ''}
            onChange={handleChange}
            placeholder={placeholder || '0'}
          />
        </div>
      );

    default: // text
      return (
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">{label}{required && ' *'}</label>
          <input
            type="text"
            className={base}
            value={value ?? ''}
            onChange={handleChange}
            placeholder={placeholder || label}
          />
        </div>
      );
  }
};

export default FieldRenderer;
