import React, { useState } from "react";
import { trpc } from "../../lib/trpc";
import { Button } from "../UI/Button";
import { Modal } from "../UI/Modal";
import { useNotification } from "../../contexts/NotificationContext";
import { Pencil, Trash2, Eye, MapPin } from "lucide-react";
import { ImovelDetail } from "./ImovelDetail";

interface ImovelListProps {
  onEdit: (id: string) => void;
}

const tipoLabels: Record<string, string> = {
  urbano: "Urbano",
  rural: "Rural",
  misto: "Misto",
};

export function ImovelList({ onEdit }: ImovelListProps) {
  const { success, error: notify } = useNotification();
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [viewId, setViewId] = useState<string | null>(null);

  const imoveis = trpc.imovel.listar.useQuery({ pagina: 1, limite: 100 });
  const utils = trpc.useUtils();

  const deleteMutation = trpc.imovel.deletar.useMutation({
    onSuccess: () => {
      success("Imóvel excluído!");
      setDeleteId(null);
      void utils.imovel.listar.invalidate();
    },
    onError: (err) => notify(err.message),
  });

  if (imoveis.isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-40 bg-gray-900 border border-gray-700/30 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  const list = imoveis.data?.imoveis ?? [];

  if (list.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-700/40 rounded-xl p-12 text-center">
        <MapPin className="w-10 h-10 text-gray-600 mx-auto mb-3" />
        <p className="text-gray-500 text-sm">Nenhum imóvel cadastrado ainda.</p>
        <p className="text-gray-600 text-xs mt-1">Clique em "Novo Imóvel" para começar.</p>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {list.map((imovel) => (
          <div
            key={imovel.id}
            className="bg-gray-900 border border-gray-700/40 rounded-xl p-4 hover:border-gray-600/60 transition-colors group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1 min-w-0">
                <span
                  className={`text-xs px-2 py-0.5 rounded-md font-medium
                  ${imovel.tipo === "urbano" ? "bg-blue-700/20 text-blue-400" : ""}
                  ${imovel.tipo === "rural" ? "bg-green-700/20 text-green-400" : ""}
                  ${imovel.tipo === "misto" ? "bg-purple-700/20 text-purple-400" : ""}
                `}
                >
                  {tipoLabels[imovel.tipo ?? "urbano"]}
                </span>
              </div>
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => setViewId(imovel.id)}
                  className="p-1 hover:bg-green-700/20 rounded text-green-400"
                >
                  <Eye className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => onEdit(imovel.id)}
                  className="p-1 hover:bg-blue-700/20 rounded text-blue-400"
                >
                  <Pencil className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setDeleteId(imovel.id)}
                  className="p-1 hover:bg-red-700/20 rounded text-red-400"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <p className="text-white text-sm font-medium line-clamp-2 mb-2">
              {imovel.endereco}
            </p>
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <MapPin className="w-3 h-3" />
              {imovel.cidade}
              {imovel.estado ? `/${imovel.estado}` : ""}
            </div>
            {imovel.area_total_m2 && (
              <p className="text-xs text-gray-500 mt-1">
                {parseFloat(imovel.area_total_m2).toLocaleString("pt-BR")} m²
              </p>
            )}
          </div>
        ))}
      </div>

      <Modal isOpen={!!deleteId} onClose={() => setDeleteId(null)} title="Confirmar Exclusão" size="sm">
        <p className="text-gray-300 text-sm mb-6">
          Tem certeza que deseja excluir este imóvel?
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

      {viewId && (
        <Modal isOpen onClose={() => setViewId(null)} title="Detalhes do Imóvel" size="lg">
          <ImovelDetail id={viewId} />
        </Modal>
      )}
    </>
  );
}
