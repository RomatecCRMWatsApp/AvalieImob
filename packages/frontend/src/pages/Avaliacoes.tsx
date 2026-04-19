import React, { useState } from "react";
import { AvaliacaoList } from "../components/Avaliacao/AvaliacaoList";
import { AvaliacaoForm } from "../components/Avaliacao/AvaliacaoForm";
import { Button } from "../components/UI/Button";
import { ClipboardList, Plus } from "lucide-react";

export function Avaliacoes() {
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-purple-700/20 rounded-xl flex items-center justify-center">
            <ClipboardList className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Avaliações</h1>
            <p className="text-gray-500 text-xs">Gerenciar PTAMs e laudos</p>
          </div>
        </div>
        <Button onClick={() => setShowForm(true)} size="sm">
          <Plus className="w-4 h-4" />
          Nova Avaliação
        </Button>
      </div>

      <AvaliacaoList onNew={() => setShowForm(true)} />

      {showForm && <AvaliacaoForm onClose={() => setShowForm(false)} />}
    </div>
  );
}
