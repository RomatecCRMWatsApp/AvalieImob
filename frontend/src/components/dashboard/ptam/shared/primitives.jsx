// @module ptam/shared/primitives — Componentes primitivos compartilhados entre steps PTAM
import React from 'react';
import { Button } from '../../../ui/button';
import { Sparkles } from 'lucide-react';

export const Field = ({ label, children, full, half }) => (
  <div className={full ? 'col-span-2' : half ? 'col-span-1' : ''}>
    <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
    {children}
  </div>
);

export const AiButton = ({ onClick, loading }) => (
  <Button
    type="button" size="sm" variant="ghost"
    className="text-emerald-700 hover:text-emerald-900 hover:bg-emerald-50"
    onClick={onClick} disabled={loading}
  >
    <Sparkles className="w-3.5 h-3.5 mr-1" />
    {loading ? '...' : 'Aperfeiçoar com IA'}
  </Button>
);

export const SectionHeader = ({ title, subtitle }) => (
  <div className="mb-6">
    <h2 className="font-display text-xl font-bold text-gray-900">{title}</h2>
    {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
  </div>
);

export const StatBox = ({ label, value, unit = '' }) => (
  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 text-center">
    <div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">{label}</div>
    <div className="text-2xl font-bold text-emerald-900">
      {typeof value === 'number' ? value.toLocaleString('pt-BR', { maximumFractionDigits: 2 }) : value}
    </div>
    {unit && <div className="text-xs text-gray-500 mt-0.5">{unit}</div>}
  </div>
);
