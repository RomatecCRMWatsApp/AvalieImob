import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, Trash2, RefreshCw } from 'lucide-react';
import { useHistorico } from './hooks/useCND';
import CNDStatusBadge from './CNDStatusBadge';

function formatDate(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

function formatDoc(doc) {
  if (!doc) return '-';
  const d = doc.replace(/\D/g, '');
  if (d.length === 11) return d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
  if (d.length === 14) return d.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
  return doc;
}

export default function CNDHistorico() {
  const { historico, loading, error, refresh, remove } = useHistorico();
  const nav = useNavigate();
  const [confirming, setConfirming] = useState(null);

  const handleDelete = async (id) => {
    await remove(id);
    setConfirming(null);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Histórico de Consultas CND</h2>
          <p className="text-sm text-gray-500 mt-0.5">Últimas 50 consultas realizadas</p>
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
        >
          <RefreshCw className="w-4 h-4" /> Atualizar
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-16 text-gray-400">
          <span className="w-5 h-5 border-2 border-gray-300 border-t-emerald-600 rounded-full animate-spin mr-2" />
          Carregando...
        </div>
      )}

      {error && !loading && (
        <div className="rounded-xl bg-red-50 border border-red-200 p-4 text-sm text-red-700">{error}</div>
      )}

      {!loading && !error && historico.length === 0 && (
        <div className="rounded-xl bg-gray-50 border border-gray-200 p-8 text-center text-gray-500 text-sm">
          Nenhuma consulta realizada ainda.
        </div>
      )}

      {!loading && historico.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
                  <th className="text-left px-4 py-3 font-semibold">Documento</th>
                  <th className="text-left px-4 py-3 font-semibold">Nome</th>
                  <th className="text-left px-4 py-3 font-semibold">Data</th>
                  <th className="text-left px-4 py-3 font-semibold">Status</th>
                  <th className="text-right px-4 py-3 font-semibold">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {historico.map(c => (
                  <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-mono text-gray-700">{formatDoc(c.cpf_cnpj)}</td>
                    <td className="px-4 py-3 text-gray-800">{c.nome_parte || '-'}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(c.created_at)}</td>
                    <td className="px-4 py-3"><CNDStatusBadge status={c.status} small /></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => nav(`/dashboard/cnd?id=${c.id}`)}
                          className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-600 transition-colors"
                          title="Ver detalhes"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {confirming === c.id ? (
                          <div className="flex gap-1">
                            <button
                              onClick={() => handleDelete(c.id)}
                              className="text-xs px-2 py-1 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors"
                            >
                              Confirmar
                            </button>
                            <button
                              onClick={() => setConfirming(null)}
                              className="text-xs px-2 py-1 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
                            >
                              Cancelar
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setConfirming(c.id)}
                            className="p-1.5 rounded-lg hover:bg-red-50 text-red-500 transition-colors"
                            title="Excluir (LGPD)"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
