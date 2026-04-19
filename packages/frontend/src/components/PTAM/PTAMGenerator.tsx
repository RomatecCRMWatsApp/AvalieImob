import React from "react";
import { trpc } from "../../lib/trpc";
import { Button } from "../UI/Button";
import { useNotification } from "../../contexts/NotificationContext";
import { FileText, Download } from "lucide-react";

interface PTAMGeneratorProps {
  avaliacaoId: string;
  avaliacaoTitulo: string;
  onGenerated: () => void;
}

export function PTAMGenerator({ avaliacaoId, avaliacaoTitulo, onGenerated }: PTAMGeneratorProps) {
  const { success, error: notify } = useNotification();

  const gerarMutation = trpc.ptam.gerar.useMutation({
    onSuccess: () => {
      success("PTAM gerado com sucesso!");
      onGenerated();
    },
    onError: (err) => notify(err.message),
  });

  return (
    <div className="bg-green-900/10 border border-green-700/30 rounded-xl p-5">
      <div className="flex items-center gap-3 mb-3">
        <FileText className="w-5 h-5 text-green-400" />
        <div>
          <p className="text-sm font-semibold text-white">Gerar PTAM</p>
          <p className="text-xs text-gray-500">{avaliacaoTitulo}</p>
        </div>
      </div>
      <p className="text-xs text-gray-400 mb-4">
        O PTAM será gerado com base nos cálculos realizados. Certifique-se de ter pelo menos um
        cálculo antes de gerar.
      </p>
      <div className="flex items-center gap-3">
        <Button
          onClick={() => gerarMutation.mutate({ avaliacao_id: avaliacaoId })}
          loading={gerarMutation.isPending}
        >
          <Download className="w-4 h-4" />
          Gerar PTAM (.docx)
        </Button>
      </div>
      {gerarMutation.data && (
        <div className="mt-3 p-3 bg-green-900/20 border border-green-700/30 rounded-lg">
          <p className="text-xs text-green-400">
            ✓ PTAM {gerarMutation.data.numero_ptam} gerado com sucesso!
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            Arquivo: {gerarMutation.data.url_docx}
          </p>
        </div>
      )}
    </div>
  );
}
