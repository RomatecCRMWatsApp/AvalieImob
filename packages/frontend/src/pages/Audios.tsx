import React from "react";
import { Mic2 } from "lucide-react";

export function Audios() {
  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-red-700/20 rounded-xl flex items-center justify-center">
          <Mic2 className="w-5 h-5 text-red-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Áudios</h1>
          <p className="text-gray-500 text-xs">Transcrições via Whisper AI</p>
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-700/40 rounded-xl p-8 text-center">
        <Mic2 className="w-12 h-12 text-gray-600 mx-auto mb-3" />
        <p className="text-gray-400 text-sm">
          Acesse as transcrições de áudio dentro de cada Avaliação.
        </p>
        <p className="text-gray-600 text-xs mt-2">
          Menu Avaliações → selecione uma avaliação → aba "Áudio IA"
        </p>
      </div>
    </div>
  );
}
