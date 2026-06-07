// @module ptam/BenfeitoriasRurais — Lista estruturada de benfeitorias (somente imóvel rural).
// Casa sede, casa do vaqueiro, galpão, curral, poço, barreiro/açude, cercas, etc.
// A unidade de medida muda conforme o tipo: área (m²), comprimento (m linear) ou quantidade (un).
// Cada item é salvo no form (benfeitorias_rurais) e vai ao PDF do laudo.
import React from 'react';
import { Plus, Trash2, Home } from 'lucide-react';
import { Input } from '../../ui/input';

// Unidade de medida por tipo: 'm²' (área) · 'm' (comprimento linear) · 'un' (quantidade).
const UNIDADE_POR_TIPO = {
  'Casa Sede': 'm²',
  'Casa do vaqueiro/morador': 'm²',
  'Galpão de máquinas/insumos': 'm²',
  'Barracão / Depósito': 'm²',
  'Curral / Mangueira': 'm²',
  'Brete / Tronco de contenção': 'un',
  'Poço artesiano / Cisterna': 'un',
  'Barreiro / Açude / Represa': 'un',
  'Cercas / Divisórias internas': 'm',
  'Rede elétrica / Energia': 'm',
  'Pomar / Cultura permanente': 'un',
  'Pastagem formada': 'm²',
  'Outro': 'm²',
};
const TIPOS = Object.keys(UNIDADE_POR_TIPO);
const ESTADOS = ['Ótimo', 'Bom', 'Regular', 'Ruim', 'Péssimo'];

const unidadeDe = (tipo) => UNIDADE_POR_TIPO[tipo] || 'm²';
const labelMedida = (uni) => (uni === 'un' ? 'Quantidade' : uni === 'm' ? 'Comprimento (m)' : 'Área (m²)');

const novaBenfeitoria = () => ({
  id: (crypto?.randomUUID && crypto.randomUUID()) || `b-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  tipo: 'Casa Sede',
  unidade: 'm²',
  medida: '',
  descricao: '',
  estado: '',
  valor: '',
});

export default function BenfeitoriasRurais({ form, setForm }) {
  const lista = Array.isArray(form.benfeitorias_rurais) ? form.benfeitorias_rurais : [];

  const setLista = (next) => setForm((f) => ({ ...f, benfeitorias_rurais: next }));
  const add = () => setLista([...lista, novaBenfeitoria()]);
  const remove = (id) => setLista(lista.filter((b) => b.id !== id));
  const update = (id, patch) => setLista(lista.map((b) => (b.id === id ? { ...b, ...patch } : b)));

  return (
    <div className="col-span-2 mt-2 border-t border-gray-100 pt-4">
      <div className="flex items-center justify-between mb-2">
        <span className="flex items-center gap-2 text-sm font-semibold text-gray-800">
          <Home className="w-4 h-4 text-emerald-700" />
          Benfeitorias do imóvel rural
        </span>
        <button
          type="button"
          onClick={add}
          className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 hover:text-emerald-900 border border-emerald-200 hover:bg-emerald-50 rounded-lg px-3 py-1.5"
        >
          <Plus className="w-3.5 h-3.5" /> Adicionar benfeitoria
        </button>
      </div>
      <p className="text-xs text-gray-500 mb-3">
        Liste cada benfeitoria (casa sede, casa do vaqueiro, galpão, curral, poço, açude, cercas…).
        A unidade se ajusta ao tipo (m², metros lineares ou quantidade). Tudo é salvo e vai ao PDF do laudo.
      </p>

      {lista.length === 0 ? (
        <div className="text-center py-6 bg-gray-50 rounded-lg border border-dashed border-gray-200 text-sm text-gray-500">
          Nenhuma benfeitoria cadastrada. Clique em "Adicionar benfeitoria".
        </div>
      ) : (
        <div className="space-y-3">
          {lista.map((b, i) => {
            const uni = b.unidade || unidadeDe(b.tipo);
            return (
              <div key={b.id} className="rounded-xl border border-gray-200 p-3 bg-white">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-emerald-700">Benfeitoria {i + 1}</span>
                  <button type="button" onClick={() => remove(b.id)} title="Remover" className="text-red-500 hover:text-red-700">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="col-span-2 sm:col-span-1">
                    <label className="block text-[11px] font-medium text-gray-600 mb-1">Tipo</label>
                    <select
                      value={b.tipo}
                      onChange={(e) => update(b.id, { tipo: e.target.value, unidade: unidadeDe(e.target.value) })}
                      className="w-full px-2.5 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-emerald-500 bg-white"
                    >
                      {TIPOS.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-gray-600 mb-1">{labelMedida(uni)}</label>
                    <Input
                      type="number" min="0" step={uni === 'un' ? '1' : '0.01'}
                      value={b.medida ?? b.area_m2 ?? ''}
                      onChange={(e) => update(b.id, { medida: e.target.value })}
                      placeholder={uni === 'un' ? '0' : '0,00'}
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-gray-600 mb-1">Estado</label>
                    <select
                      value={b.estado || ''}
                      onChange={(e) => update(b.id, { estado: e.target.value })}
                      className="w-full px-2.5 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-emerald-500 bg-white"
                    >
                      <option value="">—</option>
                      {ESTADOS.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-gray-600 mb-1">Valor estimado (R$)</label>
                    <Input type="number" min="0" step="0.01" value={b.valor}
                      onChange={(e) => update(b.id, { valor: e.target.value })} placeholder="opcional" />
                  </div>
                  <div className="col-span-2 sm:col-span-4">
                    <label className="block text-[11px] font-medium text-gray-600 mb-1">Descrição</label>
                    <Input value={b.descricao}
                      onChange={(e) => update(b.id, { descricao: e.target.value })}
                      placeholder="Ex.: alvenaria, 3 quartos, cobertura em telha cerâmica, construída em 2015..." />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
