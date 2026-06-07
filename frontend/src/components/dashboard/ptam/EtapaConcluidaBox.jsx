// @module ptam/EtapaConcluidaBox — Caixa "Etapa concluída" ao final de cada etapa do wizard.
// Marca form.etapas_concluidas[stepIndex], carimba data/hora em form.etapas_concluidas_em[stepIndex]
// e salva na hora. Alimenta o % de andamento e a estatística do processo por etapa.
import React from 'react';
import { CheckCircle2, Clock } from 'lucide-react';
import { fmtDataHora } from '../../../utils/datasServidor';

export default function EtapaConcluidaBox({ stepIndex, label, form, onToggle }) {
  const marcada = !!(form?.etapas_concluidas && form.etapas_concluidas[stepIndex]);
  const carimbo = form?.etapas_concluidas_em && form.etapas_concluidas_em[stepIndex];

  return (
    <div className={`mt-6 rounded-xl border-2 p-4 transition ${
      marcada ? 'border-emerald-300 bg-emerald-50' : 'border-gray-200 bg-gray-50'
    }`}>
      <div className="flex items-start justify-between gap-3">
        <label className="flex items-start gap-3 cursor-pointer select-none flex-1">
          <input
            type="checkbox"
            checked={marcada}
            onChange={(e) => onToggle(stepIndex, e.target.checked)}
            className="mt-0.5 w-5 h-5 accent-emerald-600"
          />
          <div>
            <div className="font-semibold text-gray-900 flex items-center gap-2">
              <CheckCircle2 className={`w-4 h-4 ${marcada ? 'text-emerald-600' : 'text-gray-400'}`} />
              Etapa concluída{label ? ` — ${label}` : ''}
            </div>
            <p className="text-xs text-gray-600 mt-1">
              Marque ao terminar esta etapa — salva na hora e alimenta o andamento (%) do laudo no card.
            </p>
          </div>
        </label>

        {marcada && carimbo && (
          <div className="shrink-0 text-right">
            <div className="text-[10px] uppercase tracking-wide text-emerald-600">Concluída em</div>
            <div className="text-xs font-semibold text-emerald-800 flex items-center gap-1 justify-end">
              <Clock className="w-3 h-3" />{fmtDataHora(carimbo)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
