// @module common/ModalNovaZona — Modal para cadastro de nova zona do Plano Diretor
import React, { useState } from 'react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Loader2 } from 'lucide-react';
import { zonasAPI } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';

const UF_LIST = [
  'AC','AL','AM','AP','BA','CE','DF','ES','GO','MA','MG','MS','MT',
  'PA','PB','PE','PI','PR','RJ','RN','RO','RR','RS','SC','SE','SP','TO',
];

export function ModalNovaZona({ open, onClose, municipioInicial = '', onSucesso }) {
  const { toast } = useToast();
  const [form, setForm] = useState({
    codigo: '',
    nome: '',
    descricao: '',
    municipio: municipioInicial,
    uf: '',
  });
  const [salvando, setSalvando] = useState(false);
  const [erros, setErros] = useState({});

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const validar = () => {
    const e = {};
    if (!form.codigo.trim()) e.codigo = 'Código obrigatório';
    if (!form.nome.trim()) e.nome = 'Nome obrigatório';
    return e;
  };

  const handleSalvar = async () => {
    const e = validar();
    if (Object.keys(e).length > 0) { setErros(e); return; }
    setErros({});
    setSalvando(true);
    try {
      const nova = await zonasAPI.criar({
        codigo: form.codigo.trim().toUpperCase(),
        nome: form.nome.trim(),
        descricao: form.descricao.trim(),
        municipio: form.municipio.trim(),
        uf: form.uf.trim(),
      });
      toast({ title: 'Zona cadastrada', description: `${nova.codigo} — ${nova.nome}` });
      onSucesso && onSucesso(nova);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Erro ao cadastrar zona.';
      toast({ title: 'Erro', description: detail, variant: 'destructive' });
    } finally {
      setSalvando(false);
    }
  };

  const handleClose = () => {
    setForm({ codigo: '', nome: '', descricao: '', municipio: municipioInicial, uf: '' });
    setErros({});
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) handleClose(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Nova Zona do Plano Diretor</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Código */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Código <span className="text-red-500">*</span>
            </label>
            <Input
              value={form.codigo}
              onChange={(e) => set('codigo', e.target.value.toUpperCase())}
              placeholder="ZR1, ZC, ZEIS..."
              maxLength={20}
              className={erros.codigo ? 'border-red-400' : ''}
            />
            {erros.codigo && <p className="text-xs text-red-500 mt-1">{erros.codigo}</p>}
          </div>

          {/* Nome */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome <span className="text-red-500">*</span>
            </label>
            <Input
              value={form.nome}
              onChange={(e) => set('nome', e.target.value)}
              placeholder="Zona Residencial 1..."
              className={erros.nome ? 'border-red-400' : ''}
            />
            {erros.nome && <p className="text-xs text-red-500 mt-1">{erros.nome}</p>}
          </div>

          {/* Município + UF */}
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Município</label>
              <Input
                value={form.municipio}
                onChange={(e) => set('municipio', e.target.value)}
                placeholder="Nome da cidade..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">UF</label>
              <select
                value={form.uf}
                onChange={(e) => set('uf', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">UF</option>
                {UF_LIST.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
              </select>
            </div>
          </div>

          {/* Descrição */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
            <Textarea
              value={form.descricao}
              onChange={(e) => set('descricao', e.target.value)}
              placeholder="Descrição do uso e ocupação do solo..."
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={salvando}>
            Cancelar
          </Button>
          <Button onClick={handleSalvar} disabled={salvando}>
            {salvando && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Cadastrar Zona
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ModalNovaZona;
