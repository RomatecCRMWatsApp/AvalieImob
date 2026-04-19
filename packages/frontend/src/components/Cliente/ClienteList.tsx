import React, { useState } from "react";
import { trpc } from "../../lib/trpc";
import { Button } from "../UI/Button";
import { Modal } from "../UI/Modal";
import { useNotification } from "../../contexts/NotificationContext";
import { Pencil, Trash2, Eye } from "lucide-react";
import { ClienteDetail } from "./ClienteDetail";

interface ClienteListProps {
  onEdit: (id: string) => void;
}

export function ClienteList({ onEdit }: ClienteListProps) {
  const { success, error: notify } = useNotification();
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [viewId, setViewId] = useState<string | null>(null);

  const clientes = trpc.cliente.listar.useQuery();
  const utils = trpc.useUtils();

  const deleteMutation = trpc.cliente.deletar.useMutation({
    onSuccess: () => {
      success("Cliente excluído!");
      setDeleteId(null);
      void utils.cliente.listar.invalidate();
    },
    onError: (err) => notify(err.message),
  });

  if (clientes.isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-14 bg-gray-900 border border-gray-700/30 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (!clientes.data || clientes.data.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-700/40 rounded-xl p-12 text-center">
        <p className="text-gray-500 text-sm">Nenhum cliente cadastrado ainda.</p>
        <p className="text-gray-600 text-xs mt-1">Clique em "Novo Cliente" para começar.</p>
      </div>
    );
  }

  return (
    <>
      <div className="bg-gray-900 border border-gray-700/40 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-gray-700/60 bg-gray-800/40">
            <tr>
              <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium uppercase tracking-wide">
                Razão Social
              </th>
              <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium uppercase tracking-wide hidden md:table-cell">
                CNPJ/CPF
              </th>
              <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium uppercase tracking-wide hidden md:table-cell">
                Localização
              </th>
              <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium uppercase tracking-wide hidden lg:table-cell">
                Contato
              </th>
              <th className="text-center px-4 py-3 text-xs text-gray-400 font-medium uppercase tracking-wide">
                Ações
              </th>
            </tr>
          </thead>
          <tbody>
            {clientes.data.map((cliente) => (
              <tr
                key={cliente.id}
                className="border-b border-gray-800/60 hover:bg-gray-800/20 transition-colors last:border-0"
              >
                <td className="px-4 py-3">
                  <p className="font-medium text-white">{cliente.razao_social}</p>
                  {cliente.email && (
                    <p className="text-xs text-gray-500">{cliente.email}</p>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-400 hidden md:table-cell">
                  {cliente.cnpj_cpf ?? "—"}
                </td>
                <td className="px-4 py-3 text-gray-400 hidden md:table-cell">
                  {cliente.cidade
                    ? `${cliente.cidade}${cliente.estado ? `/${cliente.estado}` : ""}`
                    : "—"}
                </td>
                <td className="px-4 py-3 text-gray-400 hidden lg:table-cell">
                  {cliente.telefone ?? "—"}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-1">
                    <button
                      onClick={() => setViewId(cliente.id)}
                      className="p-1.5 hover:bg-green-700/20 rounded-lg text-green-400 transition"
                      title="Ver detalhes"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onEdit(cliente.id)}
                      className="p-1.5 hover:bg-blue-700/20 rounded-lg text-blue-400 transition"
                      title="Editar"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setDeleteId(cliente.id)}
                      className="p-1.5 hover:bg-red-700/20 rounded-lg text-red-400 transition"
                      title="Excluir"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Delete confirmation */}
      <Modal
        isOpen={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="Confirmar Exclusão"
        size="sm"
      >
        <p className="text-gray-300 text-sm mb-6">
          Tem certeza que deseja excluir este cliente? Todos os imóveis e avaliações vinculados
          também serão removidos.
        </p>
        <div className="flex gap-3">
          <Button variant="ghost" onClick={() => setDeleteId(null)} className="flex-1">
            Cancelar
          </Button>
          <Button
            variant="danger"
            onClick={() => deleteId && deleteMutation.mutate({ id: deleteId })}
            loading={deleteMutation.isPending}
            className="flex-1"
          >
            Excluir
          </Button>
        </div>
      </Modal>

      {/* View detail */}
      {viewId && (
        <Modal
          isOpen
          onClose={() => setViewId(null)}
          title="Detalhes do Cliente"
          size="lg"
        >
          <ClienteDetail id={viewId} />
        </Modal>
      )}
    </>
  );
}
