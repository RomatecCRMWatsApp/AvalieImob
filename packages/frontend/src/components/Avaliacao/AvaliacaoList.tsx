import React, { useState } from "react";
import { trpc } from "../../lib/trpc";
import { Button } from "../UI/Button";
import { Modal } from "../UI/Modal";
import { useNotification } from "../../contexts/NotificationContext";
import { Trash2, ChevronRight, ClipboardList } from "lucide-react";
import { AmostraForm } from "./AmostraForm";
import { AudioTranscrever } from "./AudioTranscrever";
import { CalculosMostra } from "./CalculosMostra";

interface AvaliacaoListProps {
  onNew: () => void;
}

const statusColors: Record<string, string> = {
  rascunho: "bg-gray-700/40 text-gray-400",
  em_andamento: "bg-blue-700/20 text-blue-400",
  pronto: "bg-yellow-700/20 text-yellow-400",
  emitido: "bg-green-700/20 text-green-400",
};

const statusLabels: Record<string, string> = {
  rascunho: "Rascunho",
  em_andamento: "Em Andamento",
  pronto: "Pronto",
  emitido: "Emitido",
};

type Tab = "amostras" | "audio" | "calculos";

export function AvaliacaoList({ onNew }: AvaliacaoListProps) {
  const { success, error: notify } = useNotification();
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("amostras");

  const avaliacoes = trpc.avaliacao.listar.useQuery({ pagina: 1, limite: 100 });
  const utils = trpc.useUtils();

  const deleteMutation = trpc.avaliacao.deletar.useMutation({
    onSuccess: () => {
      success("Avaliação excluída!");
      setDeleteId(null);
      void utils.avaliacao.listar.invalidate();
    },
    onError: (err) => notify(err.message),
  });

  const atualizarMutation = trpc.avaliacao.atualizar.useMutation({
    onSuccess: () => {
      success("Status atualizado!");
      void utils.avaliacao.listar.invalidate();
    },
    onError: (err) => notify(err.message),
  });

  if (avaliacoes.isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 bg-gray-900 border border-gray-700/30 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  const list = avaliacoes.data?.avaliacoes ?? [];

  if (list.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-700/40 rounded-xl p-12 text-center">
        <ClipboardList className="w-10 h-10 text-gray-600 mx-auto mb-3" />
        <p className="text-gray-500 text-sm">Nenhuma avaliação ainda.</p>
        <Button onClick={onNew} className="mt-4" size="sm">
          Criar primeira avaliação
        </Button>
      </div>
    );
  }

  const selected = selectedId ? list.find((a) => a.id === selectedId) : null;

  const nextStatus: Record<string, string> = {
    rascunho: "em_andamento",
    em_andamento: "pronto",
    pronto: "emitido",
  };

  const nextStatusLabel: Record<string, string> = {
    rascunho: "Iniciar",
    em_andamento: "Marcar Pronto",
    pronto: "Emitir",
  };

  return (
    <>
      <div className="space-y-3">
        {list.map((av) => (
          <div
            key={av.id}
            className="bg-gray-900 border border-gray-700/40 rounded-xl p-4 hover:border-gray-600/60 transition-colors"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-md font-medium ${statusColors[av.status ?? "rascunho"]}`}
                  >
                    {statusLabels[av.status ?? "rascunho"]}
                  </span>
                  <span className="text-xs text-gray-600">{av.numero_ptam}</span>
                </div>
                <p className="text-white font-medium text-sm truncate">{av.titulo}</p>
                {av.finalidade && (
                  <p className="text-gray-500 text-xs mt-0.5">{av.finalidade}</p>
                )}
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                {av.status !== "emitido" && nextStatus[av.status ?? "rascunho"] && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      atualizarMutation.mutate({
                        id: av.id,
                        status: nextStatus[av.status ?? "rascunho"] as
                          | "em_andamento"
                          | "pronto"
                          | "emitido",
                      })
                    }
                    loading={atualizarMutation.isPending}
                  >
                    {nextStatusLabel[av.status ?? "rascunho"]}
                  </Button>
                )}
                <button
                  onClick={() => {
                    setSelectedId(av.id);
                    setActiveTab("amostras");
                  }}
                  className="p-1.5 hover:bg-green-700/20 rounded-lg text-green-400 transition"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
                {av.status !== "emitido" && (
                  <button
                    onClick={() => setDeleteId(av.id)}
                    className="p-1.5 hover:bg-red-700/20 rounded-lg text-red-400 transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Detail modal */}
      {selected && (
        <Modal
          isOpen
          onClose={() => setSelectedId(null)}
          title={selected.titulo}
          size="xl"
        >
          <div className="space-y-4">
            <div className="flex items-center gap-2 border-b border-gray-700/60 pb-4">
              {(["amostras", "audio", "calculos"] as Tab[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition capitalize
                    ${activeTab === tab ? "bg-green-700/20 text-green-400" : "text-gray-500 hover:text-gray-300"}`}
                >
                  {tab === "amostras" ? "Amostras" : tab === "audio" ? "Áudio IA" : "Cálculos"}
                </button>
              ))}
            </div>

            {activeTab === "amostras" && (
              <AmostraTab avaliacaoId={selected.id} />
            )}
            {activeTab === "audio" && (
              <AudioTranscrever avaliacaoId={selected.id} />
            )}
            {activeTab === "calculos" && (
              <CalculosMostra
                avaliacaoId={selected.id}
                metodologia={
                  (selected.metodologia as "comparativo" | "evolutivo" | "misto") ??
                  "comparativo"
                }
              />
            )}
          </div>
        </Modal>
      )}

      {/* Delete confirm */}
      <Modal isOpen={!!deleteId} onClose={() => setDeleteId(null)} title="Confirmar Exclusão" size="sm">
        <p className="text-gray-300 text-sm mb-6">
          Excluir esta avaliação? Amostras e cálculos vinculados também serão removidos.
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
    </>
  );
}

function AmostraTab({ avaliacaoId }: { avaliacaoId: string }) {
  const utils = trpc.useUtils();
  const amostras = trpc.amostra.listarPorAvaliacao.useQuery({ avaliacao_id: avaliacaoId });
  const { error: notify, success } = useNotification();

  const deletarMutation = trpc.amostra.deletar.useMutation({
    onSuccess: () => {
      success("Amostra removida!");
      void utils.amostra.listarPorAvaliacao.invalidate({ avaliacao_id: avaliacaoId });
    },
    onError: (err) => notify(err.message),
  });

  return (
    <div className="space-y-3">
      <AmostraForm
        avaliacaoId={avaliacaoId}
        onAdded={() => void utils.amostra.listarPorAvaliacao.invalidate({ avaliacao_id: avaliacaoId })}
      />

      {amostras.data && amostras.data.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-700/60">
                <th className="text-left py-2 px-3 text-gray-500 font-medium">Descrição</th>
                <th className="text-right py-2 px-3 text-gray-500 font-medium">R$/m²</th>
                <th className="text-right py-2 px-3 text-gray-500 font-medium">Total</th>
                <th className="text-left py-2 px-3 text-gray-500 font-medium">Fonte</th>
                <th className="py-2 px-3" />
              </tr>
            </thead>
            <tbody>
              {amostras.data.map((a) => (
                <tr key={a.id} className="border-b border-gray-800/60 hover:bg-gray-800/20">
                  <td className="py-2 px-3 text-white">{a.descricao}</td>
                  <td className="py-2 px-3 text-right text-green-400 font-mono">
                    {a.valor_unitario_m2
                      ? a.valor_unitario_m2.toLocaleString("pt-BR", {
                          style: "currency",
                          currency: "BRL",
                        })
                      : "—"}
                  </td>
                  <td className="py-2 px-3 text-right text-gray-300 font-mono">
                    {a.valor_total.toLocaleString("pt-BR", {
                      style: "currency",
                      currency: "BRL",
                    })}
                  </td>
                  <td className="py-2 px-3 text-gray-500">{a.fonte ?? "—"}</td>
                  <td className="py-2 px-3">
                    <button
                      onClick={() => deletarMutation.mutate({ id: a.id })}
                      className="p-1 hover:bg-red-700/20 rounded text-red-400 transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {amostras.data?.length === 0 && (
        <p className="text-gray-500 text-xs text-center py-4">
          Nenhuma amostra ainda. Mínimo 3 amostras para o cálculo comparativo.
        </p>
      )}
    </div>
  );
}
