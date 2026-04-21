// @module ptam/shared/ProprietariosSection — Seção de proprietários do imóvel (inventários, partilhas)
import React from 'react';
import { Button } from '../../../ui/button';
import { Input } from '../../../ui/input';
import { Plus, X } from 'lucide-react';

const emptyProprietario = () => ({ nome: '', cpf_cnpj: '', percentual: '' });

const ProprietariosSection = ({ form, setForm }) => {
  const proprietarios = form.proprietarios && form.proprietarios.length > 0
    ? form.proprietarios
    : [emptyProprietario()];

  const update = (idx, field, value) => {
    const next = proprietarios.map((p, i) => i === idx ? { ...p, [field]: value } : p);
    setForm({ ...form, proprietarios: next });
  };

  const add = () => setForm({ ...form, proprietarios: [...proprietarios, emptyProprietario()] });

  const remove = (idx) => {
    if (proprietarios.length <= 1) return;
    setForm({ ...form, proprietarios: proprietarios.filter((_, i) => i !== idx) });
  };

  return (
    <div className="col-span-2 mt-2">
      <div className="rounded-xl border-2 border-amber-200 bg-amber-50/40 p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-sm font-semibold text-amber-900 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
              Proprietário(s) do Imóvel
            </div>
            <p className="text-xs text-amber-700 mt-0.5">
              Para inventários e partilhas, adicione todos os proprietários.
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            onClick={add}
            className="bg-amber-700 hover:bg-amber-800 text-white text-xs"
          >
            <Plus className="w-3.5 h-3.5 mr-1" /> Adicionar Proprietário
          </Button>
        </div>

        <div className="space-y-3">
          {proprietarios.map((p, idx) => (
            <div key={idx} className="flex items-start gap-3 bg-white rounded-lg border border-amber-200 p-3">
              <div className="flex-1 grid grid-cols-3 gap-3">
                <div className="col-span-3 sm:col-span-1">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Nome completo / Razão social</label>
                  <Input
                    value={p.nome}
                    onChange={(e) => update(idx, 'nome', e.target.value)}
                    placeholder="Nome do proprietário"
                    className="text-sm h-8"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">CPF / CNPJ</label>
                  <Input
                    value={p.cpf_cnpj}
                    onChange={(e) => update(idx, 'cpf_cnpj', e.target.value)}
                    placeholder="000.000.000-00"
                    className="text-sm h-8"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Fração / Percentual</label>
                  <Input
                    value={p.percentual}
                    onChange={(e) => update(idx, 'percentual', e.target.value)}
                    placeholder="50% ou 1/2"
                    className="text-sm h-8"
                  />
                </div>
              </div>
              {proprietarios.length > 1 && (
                <button
                  type="button"
                  onClick={() => remove(idx)}
                  className="mt-5 p-1.5 text-red-400 hover:bg-red-50 rounded flex-shrink-0"
                  title="Remover proprietário"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ProprietariosSection;
