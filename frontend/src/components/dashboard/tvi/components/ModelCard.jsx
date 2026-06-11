// @module tvi/ModelCard — Card de modelo TVI no tema Romatec (verde-escuro + dourado).
import React from 'react';
import {
  ShieldCheck, FileCheck2, HardHat, Scale, ClipboardList, KeyRound,
  TreePine, Store, Wrench, Layers, ChevronRight,
} from 'lucide-react';

// Mapa de ícones por categoria (lucide, monocromático com tint dourado).
const CATEGORY_ICONS = {
  'Segurança': ShieldCheck,
  'Regularização': FileCheck2,
  'Obras': HardHat,
  'Judicial': Scale,
  'Geral': ClipboardList,
  'Locação': KeyRound,
  'Rural': TreePine,
  'Comercial': Store,
  'Instalações': Wrench,
  'Complementares': Layers,
};

export const iconForCategoria = (cat) => CATEGORY_ICONS[cat] || ClipboardList;

const ModelCard = ({ model, onSelect }) => {
  const Icon = iconForCategoria(model.categoria);

  return (
    <button
      type="button"
      onClick={() => onSelect(model)}
      aria-label={`Iniciar vistoria: ${model.nome}`}
      className="group relative w-full h-full text-left rounded-2xl p-[18px] cursor-pointer
                 transition-all duration-150 ease-out motion-reduce:transform-none
                 bg-white border border-[rgba(12,51,32,0.12)]
                 hover:-translate-y-0.5 hover:border-[rgba(201,168,76,0.55)] hover:shadow-[0_8px_24px_rgba(12,51,32,0.12)]
                 focus:outline-none focus-visible:ring-[3px] focus-visible:ring-[rgba(201,168,76,0.45)]
                 dark:bg-[#103B26] dark:border-[rgba(201,168,76,0.14)]
                 dark:hover:border-[rgba(201,168,76,0.45)] dark:hover:shadow-[0_8px_24px_rgba(0,0,0,0.35)]"
    >
      <ChevronRight className="absolute top-4 right-4 w-4 h-4 text-[#C9A84C] opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="flex items-start gap-3">
        <div className="w-[38px] h-[38px] rounded-xl flex items-center justify-center flex-shrink-0 bg-[rgba(201,168,76,0.16)]">
          <Icon className="w-[18px] h-[18px] text-[#C9A84C]" />
        </div>
        <div className="flex-1 min-w-0 pr-4">
          <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-[#5B7466] dark:text-[#9FB5A6]">
            {model.categoria || 'Modelo'}
          </span>
          <div className="mt-1 font-semibold text-[15px] leading-[1.35] line-clamp-2 text-[#15301F] dark:text-[#F2EFE6]">
            {model.nome}
          </div>
        </div>
      </div>
    </button>
  );
};

export default ModelCard;
