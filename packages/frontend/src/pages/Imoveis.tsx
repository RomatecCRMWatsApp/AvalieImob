import React, { useState } from "react";
import { ImovelList } from "../components/Imovel/ImovelList";
import { ImovelForm } from "../components/Imovel/ImovelForm";
import { Button } from "../components/UI/Button";
import { Building2, Plus } from "lucide-react";

export function Imoveis() {
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);

  const handleEdit = (id: string) => {
    setEditId(id);
    setShowForm(true);
  };

  const handleClose = () => {
    setShowForm(false);
    setEditId(null);
  };

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-yellow-700/20 rounded-xl flex items-center justify-center">
            <Building2 className="w-5 h-5 text-yellow-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Imóveis</h1>
            <p className="text-gray-500 text-xs">Cadastro de propriedades</p>
          </div>
        </div>
        <Button
          onClick={() => {
            setEditId(null);
            setShowForm(true);
          }}
          size="sm"
        >
          <Plus className="w-4 h-4" />
          Novo Imóvel
        </Button>
      </div>

      <ImovelList onEdit={handleEdit} />

      {showForm && <ImovelForm editId={editId} onClose={handleClose} />}
    </div>
  );
}
