import React from 'react';
import { Edit, Trash2, Building2, Trees, Wheat } from 'lucide-react';

const typeIcon = (t) => {
  if (t === 'Urbano') return Building2;
  if (t === 'Rural') return Trees;
  return Wheat;
};

const typeColor = (t) => {
  if (t === 'Urbano') return 'bg-blue-50 text-blue-800';
  if (t === 'Rural') return 'bg-emerald-50 text-emerald-800';
  return 'bg-amber-50 text-amber-800';
};

const statusColor = (s) => {
  if (s === 'Concluído') return 'bg-emerald-100 text-emerald-800';
  if (s === 'Em andamento') return 'bg-amber-100 text-amber-800';
  return 'bg-gray-100 text-gray-700';
};

const PropertyCard = ({ property, clientName, onEdit, onRemove }) => {
  const Icon = typeIcon(property.type);
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-lg ${typeColor(property.type)} flex items-center justify-center`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex gap-1">
          <button onClick={onEdit} className="p-1.5 hover:bg-emerald-50 rounded text-emerald-800" aria-label="Editar">
            <Edit className="w-4 h-4" />
          </button>
          <button onClick={onRemove} className="p-1.5 hover:bg-red-50 rounded text-red-600" aria-label="Remover">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div className="text-xs font-semibold text-emerald-700 tracking-wider">{property.ref}</div>
      <div className="font-semibold text-gray-900 mt-1">{property.subtype || property.type}</div>
      <div className="text-xs text-gray-600 mt-1 line-clamp-2">{property.address}</div>
      <div className="text-xs text-gray-500 mt-1">{property.city}</div>
      <div className="grid grid-cols-2 gap-2 mt-4 pt-4 border-t border-gray-100">
        <div>
          <div className="text-[10px] text-gray-500 uppercase">Área</div>
          <div className="text-sm font-semibold">{property.area} m²</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 uppercase">Valor</div>
          <div className="text-sm font-semibold brand-green">
            R$ {Number(property.value || 0).toLocaleString('pt-BR')}
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between mt-3">
        <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(property.status)}`}>{property.status}</span>
        <span className="text-xs text-gray-500 truncate max-w-[150px]">{clientName}</span>
      </div>
    </div>
  );
};

export default PropertyCard;
