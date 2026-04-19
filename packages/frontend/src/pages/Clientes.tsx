import React, { useState } from "react";
import { ClienteList } from "../components/Cliente/ClienteList";
import { ClienteForm } from "../components/Cliente/ClienteForm";
import { Button } from "../components/UI/Button";
import { Users, Plus } from "lucide-react";

export function Clientes() {
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
          <div className="w-9 h-9 bg-blue-700/20 rounded-xl flex items-center justify-center">
            <Users className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Clientes</h1>
            <p className="text-gray-500 text-xs">Gerenciar base de clientes</p>
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
          Novo Cliente
        </Button>
      </div>

      <ClienteList onEdit={handleEdit} />

      {showForm && <ClienteForm editId={editId} onClose={handleClose} />}
    </div>
  );
}
