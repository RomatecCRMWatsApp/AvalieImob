// @module locacao/shared/primitives — Primitivos compartilhados entre steps de Locação
import React from 'react';

export const Field = ({ label, children, className = '' }) => (
  <div className={`space-y-1.5 ${className}`}>
    <label className="block text-sm font-medium text-gray-700">{label}</label>
    {children}
  </div>
);

export const Input = ({ className = '', ...props }) => (
  <input
    className={`w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400 ${className}`}
    {...props}
  />
);

export const Textarea = ({ rows = 3, className = '', ...props }) => (
  <textarea
    rows={rows}
    className={`w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400 resize-none ${className}`}
    {...props}
  />
);

export const Select = ({ options, placeholder, className = '', ...props }) => (
  <select
    className={`w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400 ${className}`}
    {...props}
  >
    {placeholder && <option value="">{placeholder}</option>}
    {options.map(o => (
      <option key={o.value} value={o.value}>{o.label}</option>
    ))}
  </select>
);

export const SectionTitle = ({ children }) => (
  <h3 className="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-4">{children}</h3>
);

export const Grid = ({ cols = 2, children }) => (
  <div className={`grid grid-cols-1 ${cols === 2 ? 'md:grid-cols-2' : cols === 3 ? 'md:grid-cols-3' : ''} gap-4`}>
    {children}
  </div>
);
