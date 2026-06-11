// @module dashboard/propostas/PropostasList — Catálogo de tipos + propostas existentes.
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Home, Store, Compass, MapPin, TreePine, Scissors, Link2, Ruler, Coins,
  DraftingCompass, Layers, Loader2, Trash2, FileText, ChevronRight,
} from 'lucide-react';
import { useToast } from '../../../hooks/use-toast';
import { propostasAPI } from '../../../lib/api';

const ICONS = { Home, Store, Compass, MapPin, TreePine, Scissors, Link2, Ruler, Coins, DraftingCompass, Layers };

const STATUS = {
  rascunho: 'bg-gray-100 text-gray-700', emitida: 'bg-blue-100 text-blue-800',
  enviada: 'bg-emerald-100 text-emerald-800', aceita: 'bg-purple-100 text-purple-700',
  cancelada: 'bg-red-100 text-red-700',
};

const fmtBRL = (v) => 'R$ ' + Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const PropostasList = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const [tipos, setTipos] = useState([]);
  const [propostas, setPropostas] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [cat, lista] = await Promise.all([propostasAPI.catalogo(), propostasAPI.listar()]);
      setTipos(cat.tipos || []);
      setPropostas(Array.isArray(lista) ? lista : []);
    } catch (e) {
      toast({ title: 'Erro ao carregar propostas', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setLoading(false); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const labelDe = (subtipo) => (tipos.find((t) => t.subtipo === subtipo)?.label) || subtipo;

  const excluir = async (p, e) => {
    e.stopPropagation();
    if (!window.confirm(`Excluir a proposta ${p.numero}?`)) return;
    try { await propostasAPI.excluir(p.id); setPropostas((prev) => prev.filter((x) => x.id !== p.id)); toast({ title: 'Proposta excluída' }); }
    catch { toast({ title: 'Erro ao excluir', variant: 'destructive' }); }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-[34px] font-bold leading-tight text-[#C9A84C]">Propostas de Consultoria</h1>
        <p className="text-sm mt-1 text-[#5B7466] dark:text-[#9FB5A6]">Gere propostas com cálculo automático — mesma lógica da gestão de obras.</p>
      </div>

      {/* Catálogo de tipos */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-[#F2EFE6]">Nova proposta — escolha o tipo</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {tipos.map((t) => {
            const Icon = ICONS[t.icone] || FileText;
            const disp = t.disponivel;
            return (
              <button
                key={t.subtipo} type="button" disabled={!disp}
                onClick={() => disp && nav(`/dashboard/propostas/nova/${t.subtipo}`)}
                aria-label={`Nova proposta: ${t.label}`}
                className={`group relative text-left rounded-2xl p-[18px] border transition-all duration-150
                  ${disp
                    ? 'bg-white border-[rgba(12,51,32,0.12)] hover:-translate-y-0.5 hover:border-[rgba(201,168,76,0.55)] hover:shadow-[0_8px_24px_rgba(12,51,32,0.12)] cursor-pointer dark:bg-[#103B26] dark:border-[rgba(201,168,76,0.14)]'
                    : 'bg-gray-50 border-gray-100 opacity-60 cursor-not-allowed dark:bg-[#0e2c1d]'}`}
              >
                {disp && <ChevronRight className="absolute top-4 right-4 w-4 h-4 text-[#C9A84C] opacity-0 group-hover:opacity-100 transition-opacity" />}
                <div className="flex items-start gap-3">
                  <div className="w-[38px] h-[38px] rounded-xl flex items-center justify-center flex-shrink-0 bg-[rgba(201,168,76,0.16)]">
                    <Icon className="w-[18px] h-[18px] text-[#C9A84C]" />
                  </div>
                  <div className="min-w-0">
                    <div className="font-semibold text-[15px] leading-tight text-[#15301F] dark:text-[#F2EFE6]">{t.label}</div>
                    <div className={`text-[11px] mt-1 font-medium ${disp ? 'text-emerald-600' : 'text-gray-400'}`}>
                      {disp ? '● Disponível' : '○ Em breve'}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Propostas existentes */}
      <div className="space-y-3 pt-2">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-[#F2EFE6]">
          Propostas existentes {propostas.length > 0 && <span className="text-gray-400 font-normal">· {propostas.length}</span>}
        </h2>
        {loading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-7 h-7 animate-spin text-emerald-700" /></div>
        ) : propostas.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-xl border border-dashed border-gray-200 text-gray-400">
            <FileText className="w-10 h-10 mx-auto mb-2 text-gray-300" />
            Nenhuma proposta ainda. Escolha um tipo acima para começar.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {propostas.map((p) => (
              <div key={p.id} onClick={() => nav(`/dashboard/propostas/${p.id}`)}
                className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md transition cursor-pointer">
                <div className="flex items-start justify-between mb-2">
                  <span className="text-xs font-semibold text-amber-700">{p.numero}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${STATUS[p.status] || STATUS.rascunho}`}>{p.status}</span>
                </div>
                <div className="text-sm font-semibold text-gray-900 line-clamp-1">{labelDe(p.subtipo)}</div>
                <div className="text-xs text-gray-500 line-clamp-1">{p.cliente_nome || p.endereco_imovel || '—'}</div>
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                  <span className="font-bold text-emerald-700">{fmtBRL(p.valor_total)}</span>
                  <button title="Excluir" onClick={(e) => excluir(p, e)}
                    className="w-7 h-7 rounded-lg hover:bg-red-50 flex items-center justify-center text-red-500"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PropostasList;
