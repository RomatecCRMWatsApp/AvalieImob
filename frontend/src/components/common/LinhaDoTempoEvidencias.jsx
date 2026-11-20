// @module LinhaDoTempoEvidencias — modal SOMENTE LEITURA com a linha do tempo de um
// laudo (PTAM) ou de uma vistoria (TVI): versões, lacres, fotos com GPS, assinaturas
// e eventos do link. Não altera nada; serve para conferência e auditoria.
import React, { useEffect, useState } from 'react';
import {
  X, FileText, History, Lock, ShieldCheck, ShieldAlert, Camera, PenLine, Link2, Eye,
  Send, Share2, ClipboardCheck, Copy,
} from 'lucide-react';
import { evidenciasAPI } from '../../lib/api';
import { fmtDataHora } from '../../utils/datasServidor';
import { BrandSpinner } from '../brand/BrandSpinner';

const ICONES = {
  criado: FileText, versao: History, lacre: Lock, assinatura: ShieldCheck,
  assinatura_invalidada: ShieldAlert, foto: Camera, vistoria: ClipboardCheck,
  link_gerado: Link2, link_reativado: Link2, link_desativado: Link2,
  link_enviado: Send, link_visualizado: Eye, compartilhado: Share2,
};

function Evento({ ev }) {
  const Icone = ICONES[ev.tipo] || (ev.tipo === 'assinatura' ? PenLine : History);
  const destaque = ev.tipo === 'lacre' || ev.tipo === 'assinatura';
  return (
    <li className="relative pl-6 pb-4">
      <span className={`absolute -left-3.5 top-0 w-7 h-7 rounded-full flex items-center justify-center
        ${destaque ? 'bg-[#C9A84C] text-[#0C3320]' : 'bg-emerald-50 text-emerald-800'}`}>
        <Icone className="w-3.5 h-3.5" />
      </span>
      <div className="text-xs text-gray-500">{fmtDataHora(ev.quando) || 'sem data'}</div>
      <div className="text-sm font-medium text-gray-900">{ev.titulo}</div>
      {ev.detalhe && <div className="text-xs text-gray-600 break-words">{ev.detalhe}</div>}
      {ev.referencia && <div className="text-xs text-gray-600 break-all">Ref.: {ev.referencia}</div>}
      {ev.hash_sha256 && (
        <button type="button" title="Copiar SHA-256"
          onClick={() => navigator.clipboard?.writeText(ev.hash_sha256)}
          className="mt-1 inline-flex items-center gap-1 text-[11px] font-mono text-gray-500 hover:text-emerald-800 break-all text-left">
          <Copy className="w-3 h-3 shrink-0" /> SHA-256 {ev.hash_sha256.slice(0, 16)}…
        </button>
      )}
      {ev.url && ev.tipo === 'foto' && (
        <a href={ev.url} target="_blank" rel="noreferrer"
          className="block mt-1 text-xs text-emerald-800 hover:underline">Ver foto</a>
      )}
    </li>
  );
}

export default function LinhaDoTempoEvidencias({ tipo, id, titulo, onClose }) {
  const [eventos, setEventos] = useState(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    let vivo = true;
    (tipo === 'tvi' ? evidenciasAPI.tvi(id) : evidenciasAPI.ptam(id))
      .then((r) => vivo && setEventos(r?.eventos || []))
      .catch((e) => vivo && setErro(e?.response?.data?.detail || 'Não foi possível carregar.'));
    return () => { vivo = false; };
  }, [tipo, id]);

  return (
    <div className="fixed inset-0 z-[1300] bg-black/60 flex items-end sm:items-center justify-center p-0 sm:p-4"
      role="dialog" aria-modal="true" aria-label="Linha do tempo" onClick={onClose}>
      <div className="bg-white w-full sm:max-w-lg max-h-[90vh] rounded-t-2xl sm:rounded-2xl flex flex-col"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3 p-4 border-b border-gray-100">
          <div className="min-w-0">
            <h2 className="font-semibold text-[#0C3320]">Linha do tempo</h2>
            {titulo && <p className="text-xs text-gray-500 break-words">{titulo}</p>}
          </div>
          <button type="button" onClick={onClose} aria-label="Fechar"
            className="w-9 h-9 rounded-lg hover:bg-gray-100 flex items-center justify-center shrink-0">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="overflow-y-auto p-4">
          {erro && <p className="text-sm text-red-700">{erro}</p>}
          {!erro && eventos === null && <div className="py-8 flex justify-center"><BrandSpinner label="Carregando…" /></div>}
          {eventos && eventos.length === 0 && <p className="text-sm text-gray-500">Nada registrado ainda.</p>}
          {eventos && eventos.length > 0 && (
            <ol className="relative border-l border-gray-200 ml-3.5">
              {eventos.map((ev, i) => <Evento key={i} ev={ev} />)}
            </ol>
          )}
          <p className="mt-2 text-[11px] text-gray-400">
            Somente leitura. Os códigos SHA-256 permitem conferir que o conteúdo lacrado ou assinado não mudou.
          </p>
        </div>
      </div>
    </div>
  );
}
