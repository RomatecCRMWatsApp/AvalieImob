import React, { useState } from "react";
import { trpc } from "../../lib/trpc";
import { Modal } from "../UI/Modal";
import { PTAMViewer } from "./PTAMViewer";
import { PTAMGenerator } from "./PTAMGenerator";
import { FileText, Plus } from "lucide-react";
import { Button } from "../UI/Button";

export function PTAMList() {
  const [showGenerator, setShowGenerator] = useState(false);
  const [genAvaliacaoId, setGenAvaliacaoId] = useState("");
  const [genAvaliacaoTitulo, setGenAvaliacaoTitulo] = useState("");

  const ptams = trpc.ptam.listar.useQuery();
  const avaliacoes = trpc.avaliacao.listar.useQuery({ pagina: 1, limite: 100 });
  const utils = trpc.useUtils();

  if (ptams.isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 bg-gray-900 border border-gray-700/30 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  const list = ptams.data ?? [];
  const pendingAvaliacoes = (avaliacoes.data?.avaliacoes ?? []).filter(
    (av) => av.status === "pronto",
  );

  return (
    <div className="space-y-4">
      {pendingAvaliacoes.length > 0 && (
        <div className="bg-yellow-900/10 border border-yellow-700/30 rounded-xl p-4">
          <p className="text-sm font-medium text-yellow-400 mb-3">
            Avaliações prontas para emissão ({pendingAvaliacoes.length})
          </p>
          <div className="space-y-2">
            {pendingAvaliacoes.map((av) => (
              <div key={av.id} className="flex items-center justify-between py-2">
                <p className="text-sm text-gray-300">{av.titulo}</p>
                <Button
                  size="sm"
                  onClick={() => {
                    setGenAvaliacaoId(av.id);
                    setGenAvaliacaoTitulo(av.titulo);
                    setShowGenerator(true);
                  }}
                >
                  <Plus className="w-3.5 h-3.5" />
                  Gerar PTAM
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {list.length === 0 ? (
        <div className="bg-gray-900 border border-gray-700/40 rounded-xl p-12 text-center">
          <FileText className="w-10 h-10 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Nenhum PTAM emitido ainda.</p>
          <p className="text-gray-600 text-xs mt-1">
            Conclua uma avaliação (status Pronto) e clique em Gerar PTAM.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            PTAMs Emitidos ({list.length})
          </p>
          {list.map((item) => (
            <PTAMViewer key={item.ptam_emitidos.id} ptam={item} />
          ))}
        </div>
      )}

      {showGenerator && (
        <Modal isOpen onClose={() => setShowGenerator(false)} title="Gerar PTAM" size="md">
          <PTAMGenerator
            avaliacaoId={genAvaliacaoId}
            avaliacaoTitulo={genAvaliacaoTitulo}
            onGenerated={() => {
              setShowGenerator(false);
              void utils.ptam.listar.invalidate();
              void utils.avaliacao.listar.invalidate();
            }}
          />
        </Modal>
      )}
    </div>
  );
}
