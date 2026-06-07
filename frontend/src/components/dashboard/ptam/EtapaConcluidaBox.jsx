// @module ptam/EtapaConcluidaBox — Caixa "Etapa concluída" ao final de cada etapa do wizard.
// Marca form.etapas_concluidas[stepIndex] e alimenta o % de andamento do laudo no card.
import React from 'react';
import { CheckCircle2 } from 'lucide-react';

export default function EtapaConcluidaBox({ stepIndex, label, form, setForm }) {
  const marcada = !!(form?.etapas_concluidas && form.etapas_concluidas[stepIndex]);

  const toggle = (e) => {
    const checked = e.target.checked;
    setForm((f) => ({
      ...f,
      etapas_concluidas: { ...(f.etapas_concluidas || {}), [stepIndex]: checked },
    }));
  };

  return (
    <div className={`mt-6 rounded-xl border-2 p-4 transition ${
      marcada ? 'border-emerald-300 bg-emerald-50' : 'border-gray-200 bg-gray-50'
    }`}>
      <label className="flex items-start gap-3 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={marcada}
          onChange={toggle}
          className="mt-0.5 w-5 h-5 accent-emerald-600"
        />
        <div>
          <div className="font-semibold text-gray-900 flex items-center gap-2">
            <CheckCircle2 className={`w-4 h-4 ${marcada ? 'text-emerald-600' : 'text-gray-400'}`} />
            Etapa concluída{label ? ` — ${label}` : ''}
          </div>
          <p className="text-xs text-gray-600 mt-1">
            Marque ao terminar esta etapa e salve. Alimenta o andamento (%) do laudo no card.
          </p>
        </div>
      </label>
    </div>
  );
}
