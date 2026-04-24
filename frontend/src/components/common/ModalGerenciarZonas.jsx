// @module common/ModalGerenciarZonas — Modal para listar, editar e excluir zonas do Plano Diretor
import React, { useState, useEffect, useCallback } from 'react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Loader2, Pencil, Trash2, Check, X, Plus, AlertTriangle } from 'lucide-react';
import { zonasAPI } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { ModalNovaZona } from './ModalNovaZona';

function agruparPorMunicipio(zonas) {
  const grupos = {};
  zonas.forEach((z) => {
    const key = z.municipio || '';
    if (!grupos[key]) grupos[key] = [];
    grupos[key].push(z);
  });
  return grupos;
}

function ItemZona({ zona, onAtualizar, onExcluir }) {
  const { toast } = useToast();
  const [editando, setEditando] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [form, setForm] = useState({ codigo: zona.codigo, nome: zona.nome, descricao: zona.descricao || '' });

  const handleSalvar = async () => {
    if (!form.codigo.trim() || !form.nome.trim()) {
      toast({ title: 'Erro', description: 'Código e nome são obrigatórios.', variant: 'destructive' });
      return;
    }
    setSalvando(true);
    try {
      const atualizado = await zonasAPI.atualizar(zona.id, {
        codigo: form.codigo.trim().toUpperCase(),
        nome: form.nome.trim(),
        descricao: form.descricao.trim(),
      });
      toast({ title: 'Zona atualizada' });
      setEditando(false);
      onAtualizar && onAtualizar(atualizado);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Erro ao atualizar zona.';
      toast({ title: 'Erro', description: detail, variant: 'destructive' });
    } finally {
      setSalvando(false);
    }
  };

  const handleExcluir = async () => {
    setSalvando(true);
    try {
      await zonasAPI.excluir(zona.id);
      toast({ title: 'Zona removida' });
      setConfirmando(false);
      onExcluir && onExcluir(zona.id);
    } catch (err) {
      toast({ title: 'Erro ao remover zona', variant: 'destructive' });
    } finally {
      setSalvando(false);
    }
  };

  if (confirmando) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-md">
        <AlertTriangle className="h-4 w-4 text-red-500 shrink-0" />
        <span className="text-sm text-red-700 flex-1">Remover <strong>{zona.codigo}</strong>?</span>
        <Button size="sm" variant="destructive" onClick={handleExcluir} disabled={salvando}>
          {salvando ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Sim'}
        </Button>
        <Button size="sm" variant="outline" onClick={() => setConfirmando(false)} disabled={salvando}>
          Não
        </Button>
      </div>
    );
  }

  if (editando) {
    return (
      <div className="space-y-2 px-3 py-2 border border-blue-200 rounded-md bg-blue-50">
        <div className="flex gap-2">
          <Input
            value={form.codigo}
            onChange={(e) => setForm((f) => ({ ...f, codigo: e.target.value.toUpperCase() }))}
            className="w-24 text-sm h-8"
            maxLength={20}
            placeholder="Código"
          />
          <Input
            value={form.nome}
            onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
            className="flex-1 text-sm h-8"
            placeholder="Nome"
          />
        </div>
        <Input
          value={form.descricao}
          onChange={(e) => setForm((f) => ({ ...f, descricao: e.target.value }))}
          className="text-sm h-8"
          placeholder="Descrição (opcional)"
        />
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={() => setEditando(false)} disabled={salvando}>
            <X className="h-3 w-3" />
          </Button>
          <Button size="sm" onClick={handleSalvar} disabled={salvando}>
            {salvando ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 rounded-md group">
      <span className="font-semibold text-xs text-gray-500 w-14 shrink-0">{zona.codigo}</span>
      <span className="text-sm text-gray-800 flex-1 truncate">{zona.nome}</span>
      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          type="button"
          onClick={() => { setEditando(true); setForm({ codigo: zona.codigo, nome: zona.nome, descricao: zona.descricao || '' }); }}
          className="p-1 text-gray-400 hover:text-blue-600 rounded"
          title="Editar"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => setConfirmando(true)}
          className="p-1 text-gray-400 hover:text-red-600 rounded"
          title="Remover"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

export function ModalGerenciarZonas({ open, onClose }) {
  const [zonas, setZonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNova, setShowNova] = useState(false);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const data = await zonasAPI.listar();
      setZonas(Array.isArray(data) ? data : []);
    } catch {
      setZonas([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) carregar();
  }, [open, carregar]);

  const handleAtualizar = (atualizado) => {
    setZonas((prev) => prev.map((z) => (z.id === atualizado.id ? atualizado : z)));
  };

  const handleExcluir = (id) => {
    setZonas((prev) => prev.filter((z) => z.id !== id));
  };

  const handleNovaSucesso = (nova) => {
    setShowNova(false);
    if (nova) setZonas((prev) => [...prev, nova]);
  };

  const grupos = agruparPorMunicipio(zonas);
  const municipioKeys = Object.keys(grupos).sort();

  return (
    <>
      <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
        <DialogContent className="max-w-lg max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Gerenciar Zonas do Plano Diretor</DialogTitle>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto -mx-6 px-6">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
              </div>
            ) : zonas.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm">
                Nenhuma zona cadastrada.
              </div>
            ) : (
              <div className="space-y-4 py-2">
                {municipioKeys.map((mun) => (
                  <div key={mun}>
                    {mun && (
                      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1 px-3">
                        {mun}
                      </div>
                    )}
                    <div className="space-y-1">
                      {grupos[mun].map((zona) => (
                        <ItemZona
                          key={zona.id}
                          zona={zona}
                          onAtualizar={handleAtualizar}
                          onExcluir={handleExcluir}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-gray-100 flex justify-between items-center">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowNova(true)}
              className="flex items-center gap-2"
            >
              <Plus className="h-4 w-4" />
              Nova Zona
            </Button>
            <Button variant="ghost" onClick={onClose}>Fechar</Button>
          </div>
        </DialogContent>
      </Dialog>

      {showNova && (
        <ModalNovaZona
          open={showNova}
          onClose={() => setShowNova(false)}
          municipioInicial=""
          onSucesso={handleNovaSucesso}
        />
      )}
    </>
  );
}

export default ModalGerenciarZonas;
