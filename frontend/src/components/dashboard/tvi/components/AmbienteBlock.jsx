import React, { useState } from 'react';
import { Plus, Trash2, Home } from 'lucide-react';
import PhotoUploader from './PhotoUploader';

const EMPTY_AMBIENTE = () => ({ nome: '', descricao: '', conservacao: '', observacoes: '' });

const AmbienteBlock = ({ vistoriaId, ambientes = [], onChange }) => {
  const [list, setList] = useState(ambientes.length ? ambientes : [EMPTY_AMBIENTE()]);

  const update = (idx, key, val) => {
    const next = list.map((a, i) => i === idx ? { ...a, [key]: val } : a);
    setList(next);
    onChange && onChange(next);
  };

  const add = () => {
    const next = [...list, EMPTY_AMBIENTE()];
    setList(next);
    onChange && onChange(next);
  };

  const remove = (idx) => {
    const next = list.filter((_, i) => i !== idx);
    setList(next);
    onChange && onChange(next);
  };

  const inp = 'w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-emerald-400 bg-white';

  return (
    <div className="space-y-4">
      {list.map((amb, idx) => (
        <div key={idx} className="rounded-xl border border-gray-200 p-4 space-y-3 bg-gray-50/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Home className="w-4 h-4 text-emerald-700" />
              <span className="text-sm font-semibold text-gray-700">Ambiente {idx + 1}</span>
            </div>
            {list.length > 1 && (
              <button type="button" onClick={() => remove(idx)}
                className="w-7 h-7 rounded-lg flex items-center justify-center text-red-400 hover:bg-red-50">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-600">Nome do ambiente</label>
              <input className={inp} value={amb.nome} placeholder="Ex.: Sala de estar"
                onChange={e => update(idx, 'nome', e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-gray-600">Estado de conservação</label>
              <select className={inp} value={amb.conservacao} onChange={e => update(idx, 'conservacao', e.target.value)}>
                <option value="">Selecione...</option>
                {['Novo', 'Ótimo', 'Bom', 'Regular', 'Ruim', 'Péssimo'].map(o => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-600">Descrição</label>
            <textarea rows={2} className={`${inp} resize-none`} value={amb.descricao}
              placeholder="Descreva as características do ambiente..."
              onChange={e => update(idx, 'descricao', e.target.value)} />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-600">Observações</label>
            <textarea rows={2} className={`${inp} resize-none`} value={amb.observacoes}
              placeholder="Vícios, patologias ou observações específicas..."
              onChange={e => update(idx, 'observacoes', e.target.value)} />
          </div>

          {vistoriaId && (
            <PhotoUploader vistoriaId={vistoriaId} ambiente={amb.nome || `Ambiente ${idx + 1}`}
              photos={amb.fotos || []} onUploaded={fotos => update(idx, 'fotos', fotos)} />
          )}
        </div>
      ))}

      <button type="button" onClick={add}
        className="flex items-center gap-2 text-sm text-emerald-700 hover:text-emerald-900 px-3 py-2 rounded-xl hover:bg-emerald-50 transition">
        <Plus className="w-4 h-4" /> Adicionar ambiente
      </button>
    </div>
  );
};

export default AmbienteBlock;
