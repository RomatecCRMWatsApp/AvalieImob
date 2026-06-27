// @module documentos-externos/ModalUpload — upload do PDF externo + metadados + toggle ICP.
import React, { useState } from 'react';
import { X, UploadCloud } from 'lucide-react';
import { documentosExternosAPI } from '../../../lib/api';

export default function ModalUpload({ onClose, onCreated }) {
  const [titulo, setTitulo] = useState('');
  const [descricao, setDescricao] = useState('');
  const [requerIcp, setRequerIcp] = useState(true);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [erro, setErro] = useState('');

  const enviar = async () => {
    if (!file) { setErro('Selecione um PDF.'); return; }
    if (!titulo.trim()) { setErro('Informe um título.'); return; }
    setBusy(true); setErro('');
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('titulo', titulo.trim());
      fd.append('descricao', descricao.trim());
      fd.append('requer_icp_rt', requerIcp ? 'true' : 'false');
      const doc = await documentosExternosAPI.upload(fd);
      onCreated && onCreated(doc);
    } catch (e) {
      setErro(e?.response?.data?.detail || 'Falha ao enviar.');
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold text-emerald-950">Novo documento externo</h3>
          <button onClick={onClose}><X /></button>
        </div>
        <label className="block border-2 border-dashed border-emerald-300 rounded-xl p-6 text-center cursor-pointer mb-4">
          <UploadCloud className="mx-auto mb-2 text-emerald-700" />
          <span className="text-sm">{file ? file.name : 'Selecionar PDF (máx 25 MB)'}</span>
          <input type="file" accept="application/pdf" className="hidden"
                 onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </label>
        <input className="w-full border rounded-lg p-2 mb-3" placeholder="Título"
               value={titulo} onChange={(e) => setTitulo(e.target.value)} />
        <textarea className="w-full border rounded-lg p-2 mb-3" placeholder="Descrição (opcional)"
                  value={descricao} onChange={(e) => setDescricao(e.target.value)} />
        <label className="flex items-center gap-2 mb-4 text-sm">
          <input type="checkbox" checked={requerIcp} onChange={(e) => setRequerIcp(e.target.checked)} />
          Exigir assinatura ICP-Brasil do RT no final
        </label>
        {erro && <div className="text-red-600 text-sm mb-3">{erro}</div>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border rounded-lg">Cancelar</button>
          <button onClick={enviar} disabled={busy}
                  className="px-4 py-2 bg-emerald-700 text-white rounded-lg disabled:opacity-50">
            {busy ? 'Enviando…' : 'Criar'}
          </button>
        </div>
      </div>
    </div>
  );
}
