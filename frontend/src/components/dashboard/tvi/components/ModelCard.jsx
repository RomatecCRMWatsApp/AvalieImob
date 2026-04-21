import React from 'react';
import { ClipboardCheck } from 'lucide-react';

const CATEGORY_ICONS = {
  Geral: '🏠', Locação: '🔑', Rural: '🌾', Regularização: '📋',
  Obras: '🔨', Judicial: '⚖️', Segurança: '🛡️', Comercial: '🏪',
  Instalações: '⚡', Complementares: '📎',
};

const ModelCard = ({ model, onSelect }) => {
  const icon = CATEGORY_ICONS[model.categoria] || '📄';

  return (
    <button
      onClick={() => onSelect(model)}
      className="group w-full text-left bg-white rounded-xl border border-gray-200
                 p-4 hover:border-emerald-400 hover:shadow-md transition-all duration-150
                 focus:outline-none focus:ring-2 focus:ring-emerald-300"
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-emerald-900/8 flex items-center justify-center
                        flex-shrink-0 group-hover:bg-emerald-900/15 transition-colors text-xl">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <ClipboardCheck className="w-3 h-3 text-emerald-700 flex-shrink-0" />
            <span className="text-[10px] font-semibold text-emerald-700 tracking-wide uppercase">
              {model.categoria}
            </span>
          </div>
          <div className="font-semibold text-gray-900 text-sm leading-snug line-clamp-2">
            {model.nome}
          </div>
          {model.descricao && (
            <div className="text-xs text-gray-500 mt-1 line-clamp-2">
              {model.descricao}
            </div>
          )}
          {model.campos_count != null && (
            <div className="text-[10px] text-gray-400 mt-2">
              {model.campos_count} campos
            </div>
          )}
        </div>
      </div>
    </button>
  );
};

export default ModelCard;
