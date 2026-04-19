import React, { useState, useRef } from "react";
import { trpc } from "../../lib/trpc";
import { Button } from "../UI/Button";
import { useNotification } from "../../contexts/NotificationContext";
import { Mic, StopCircle, Upload, Trash2 } from "lucide-react";

interface AudioTranscreverProps {
  avaliacaoId: string;
}

export function AudioTranscrever({ avaliacaoId }: AudioTranscreverProps) {
  const { success, error: notify } = useNotification();
  const [recording, setRecording] = useState(false);
  const [tipo, setTipo] = useState<"descricao_imovel" | "condicoes_mercado" | "observacoes">(
    "descricao_imovel",
  );
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const transcricoes = trpc.audio.listarPorAvaliacao.useQuery({ avaliacao_id: avaliacaoId });
  const utils = trpc.useUtils();

  const transcreverMutation = trpc.audio.transcrever.useMutation({
    onSuccess: () => {
      success("Áudio transcrito com sucesso!");
      void utils.audio.listarPorAvaliacao.invalidate({ avaliacao_id: avaliacaoId });
    },
    onError: (err) => notify(err.message),
  });

  const deletarMutation = trpc.audio.deletar.useMutation({
    onSuccess: () => {
      success("Transcrição removida!");
      void utils.audio.listarPorAvaliacao.invalidate({ avaliacao_id: avaliacaoId });
    },
    onError: (err) => notify(err.message),
  });

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => chunksRef.current.push(e.data);
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const reader = new FileReader();
        reader.onloadend = () => {
          const b64 = (reader.result as string).split(",")[1];
          transcreverMutation.mutate({
            avaliacao_id: avaliacaoId,
            arquivo_base64: b64,
            tipo,
          });
        };
        reader.readAsDataURL(blob);
        stream.getTracks().forEach((t) => t.stop());
      };
      mr.start();
      mediaRef.current = mr;
      setRecording(true);
    } catch {
      notify("Erro ao acessar microfone. Verifique as permissões.");
    }
  };

  const stopRecording = () => {
    mediaRef.current?.stop();
    setRecording(false);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => {
      const b64 = (reader.result as string).split(",")[1];
      transcreverMutation.mutate({ avaliacao_id: avaliacaoId, arquivo_base64: b64, tipo });
    };
    reader.readAsDataURL(file);
  };

  const tipoLabels: Record<string, string> = {
    descricao_imovel: "Descrição do Imóvel",
    condicoes_mercado: "Condições de Mercado",
    observacoes: "Observações Gerais",
  };

  return (
    <div className="space-y-4">
      <div className="bg-gray-800/40 border border-gray-700/40 rounded-xl p-4">
        <h4 className="text-sm font-semibold text-white mb-3">Transcrever Áudio via Whisper AI</h4>

        <div className="space-y-1 mb-3">
          <label className="block text-xs font-medium text-gray-400">Tipo de Registro</label>
          <select
            value={tipo}
            onChange={(e) =>
              setTipo(e.target.value as "descricao_imovel" | "condicoes_mercado" | "observacoes")
            }
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-600 transition-colors"
          >
            <option value="descricao_imovel">Descrição do Imóvel</option>
            <option value="condicoes_mercado">Condições de Mercado</option>
            <option value="observacoes">Observações Gerais</option>
          </select>
        </div>

        <div className="flex items-center gap-3">
          {!recording ? (
            <Button onClick={startRecording} size="sm" variant="outline" disabled={transcreverMutation.isPending}>
              <Mic className="w-4 h-4" />
              Gravar
            </Button>
          ) : (
            <Button onClick={stopRecording} size="sm" variant="danger">
              <StopCircle className="w-4 h-4" />
              Parar
            </Button>
          )}

          <label className="cursor-pointer">
            <input
              type="file"
              accept="audio/*"
              className="hidden"
              onChange={handleFileUpload}
              disabled={transcreverMutation.isPending || recording}
            />
            <span className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-600 text-gray-400 hover:text-white hover:border-gray-500 transition cursor-pointer">
              <Upload className="w-3.5 h-3.5" />
              Enviar arquivo
            </span>
          </label>

          {transcreverMutation.isPending && (
            <span className="text-xs text-green-400 flex items-center gap-1.5">
              <span className="w-3 h-3 border border-green-400 border-t-transparent rounded-full animate-spin" />
              Transcrevendo...
            </span>
          )}
        </div>
      </div>

      {/* Transcriptions list */}
      {transcricoes.data && transcricoes.data.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            Transcrições ({transcricoes.data.length})
          </p>
          {transcricoes.data.map((t) => (
            <div key={t.id} className="bg-gray-800/40 border border-gray-700/40 rounded-lg p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs bg-green-700/20 text-green-400 px-2 py-0.5 rounded-md">
                  {tipoLabels[t.tipo ?? "observacoes"]}
                </span>
                <button
                  onClick={() => deletarMutation.mutate({ id: t.id })}
                  className="p-1 hover:bg-red-700/20 rounded text-red-400 transition"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
              <p className="text-sm text-gray-300 leading-relaxed">{t.transcricao_texto}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
