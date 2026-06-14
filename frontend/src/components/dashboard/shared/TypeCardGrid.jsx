// @module dashboard/shared/TypeCardGrid — Card de tipo + grade (reuso Propostas/Contratos).
// Extraído do padrão visual da página de Propostas. Sem cores novas (verde/dourado Romatec).
import React from 'react';
import { ChevronRight, FileText } from 'lucide-react';

/** Um card de tipo. Props:
 *  icon (component) | iconNode, label, descricao?, disponivel (bool), onClick, ariaLabel */
export const TypeCard = ({ icon: Icon, iconNode, label, descricao, disponivel = true, verificado = false, onClick, ariaLabel }) => (
  <button
    type="button"
    disabled={!disponivel}
    onClick={() => disponivel && onClick && onClick()}
    aria-label={ariaLabel || label}
    className={`group relative text-left rounded-2xl p-[18px] border transition-all duration-150
      ${!disponivel
        ? 'bg-gray-50 border-gray-100 opacity-60 cursor-not-allowed dark:bg-[#0e2c1d]'
        : verificado
          ? 'bg-emerald-50 border-emerald-400 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(12,51,32,0.18)] cursor-pointer dark:bg-[#0d3a24] dark:border-[rgba(201,168,76,0.5)]'
          : 'bg-white border-[rgba(12,51,32,0.12)] hover:-translate-y-0.5 hover:border-[rgba(201,168,76,0.55)] hover:shadow-[0_8px_24px_rgba(12,51,32,0.12)] cursor-pointer dark:bg-[#103B26] dark:border-[rgba(201,168,76,0.14)]'}`}
  >
    {disponivel && (
      <ChevronRight className="absolute top-4 right-4 w-4 h-4 text-[#C9A84C] opacity-0 group-hover:opacity-100 transition-opacity" />
    )}
    <div className="flex items-start gap-3">
      <div className={`w-[38px] h-[38px] rounded-xl flex items-center justify-center flex-shrink-0 ${verificado ? 'bg-emerald-600' : 'bg-[rgba(201,168,76,0.16)]'}`}>
        {iconNode || <Icon className={`w-[18px] h-[18px] ${verificado ? 'text-[#F4E3B2]' : 'text-[#C9A84C]'}`} /> || <FileText className="w-[18px] h-[18px] text-[#C9A84C]" />}
      </div>
      <div className="min-w-0">
        <div className={`font-bold text-[15px] leading-tight ${verificado ? 'text-[#C9A84C]' : 'font-semibold text-[#15301F] dark:text-[#F2EFE6]'}`}>{label}</div>
        {descricao && <div className="text-[12px] text-gray-500 leading-tight mt-0.5 line-clamp-1">{descricao}</div>}
        <div className={`text-[11px] mt-1 font-medium ${!disponivel ? 'text-gray-400' : verificado ? 'text-emerald-700' : 'text-emerald-600'}`}>
          {!disponivel ? '○ Em breve' : verificado ? '✓ Configurado e testado' : '● Disponível'}
        </div>
      </div>
    </div>
  </button>
);

/** Grade de tipos. Props:
 *  tipos: [{ id, nome|label, descricao?, categoria?, Icon|icon, status|disponivel }]
 *  categorias?: ordem dos microlabels (se ausente, grade plana)
 *  onPick(tipo) */
export const TypeCardGrid = ({ tipos = [], categorias, onPick }) => {
  const norm = (t) => ({
    ...t,
    _label: t.nome || t.label,
    _icon: t.Icon || t.icon,
    _disp: t.status ? t.status === 'disponivel' : (t.disponivel !== false),
  });
  const lista = tipos.map(norm);

  const grade = (itens) => (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {itens.map((t) => (
        <TypeCard
          key={t.id || t._label}
          icon={t._icon}
          label={t._label}
          descricao={t.descricao}
          disponivel={t._disp}
          verificado={!!t.verificado}
          ariaLabel={`Novo: ${t._label}`}
          onClick={() => onPick && onPick(t)}
        />
      ))}
    </div>
  );

  if (!categorias || categorias.length === 0) return grade(lista);

  return (
    <div className="space-y-5">
      {categorias.map((cat) => {
        const doGrupo = lista.filter((t) => t.categoria === cat);
        if (doGrupo.length === 0) return null;
        return (
          <div key={cat} className="space-y-2">
            <div className="text-[11px] font-semibold tracking-[1.5px] text-gray-400">{cat}</div>
            {grade(doGrupo)}
          </div>
        );
      })}
    </div>
  );
};

export default TypeCardGrid;
