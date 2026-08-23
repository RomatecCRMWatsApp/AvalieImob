// @module dashboard/novidades/ReleaseModal — Modal de release (bloqueante) na identidade do sistema.
import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../ui/button';
import MarkdownLite from './MarkdownLite';

// Aviso automático de release (services/release_notes): cada item é uma FERRAMENTA
// atualizada, com selo do tipo. Layout aprovado pelo dono em 23/08/2026 (opção B).
const TIPO_ITEM = {
  novo:     { label: 'Novo',     cls: 'bg-emerald-100 text-emerald-800' },
  melhoria: { label: 'Melhoria', cls: 'bg-sky-100 text-sky-800' },
  correcao: { label: 'Correção', cls: 'bg-amber-100 text-amber-800' },
};

const ItensAtualizados = ({ itens = [] }) => (
  <div>
    {itens.map((i, k) => {
      const t = TIPO_ITEM[i.tipo] || TIPO_ITEM.melhoria;
      return (
        <div key={`${i.modulo}-${k}`}
             className="flex gap-2.5 py-2.5 border-b border-gray-100 last:border-0">
          <span className={`shrink-0 h-fit mt-0.5 text-[9px] font-bold uppercase tracking-wider
                            px-1.5 py-1 rounded text-center min-w-[62px] ${t.cls}`}>
            {t.label}
          </span>
          <span>
            <span className="block text-[12.5px] font-bold" style={{ color: '#0C3320' }}>
              {i.modulo}
            </span>
            {i.texto && (
              <span className="block text-[12px] text-gray-600 leading-snug mt-0.5">{i.texto}</span>
            )}
          </span>
        </div>
      );
    })}
  </div>
);

const TAG = {
  novidade: { label: 'Novidade', cls: 'bg-emerald-100 text-emerald-700' },
  melhoria: { label: 'Melhoria', cls: 'bg-sky-100 text-sky-700' },
  correcao: { label: 'Correção', cls: 'bg-amber-100 text-amber-700' },
  aviso: { label: 'Aviso', cls: 'bg-red-100 text-red-600' },
};

// itens = SÓ as pendentes bloqueantes. Fila com indicador "1 de N".
const ReleaseModal = ({ itens = [], onVisualizar, onDispensar, onCta }) => {
  const nav = useNavigate();
  const [idx, setIdx] = useState(0);
  const [visivel, setVisivel] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setVisivel(true), 800); // não compete com o loading do dashboard
    return () => clearTimeout(t);
  }, []);

  if (!visivel || idx >= itens.length) return null;
  const n = itens[idx];
  const tag = TAG[n.tag] || TAG.novidade;

  const fechar = () => { onVisualizar?.(n.id); setIdx((i) => i + 1); };   // X/overlay = visto (reaparece no próximo login)
  const entendi = () => { onDispensar?.(n.id); setIdx((i) => i + 1); };
  const cta = () => { onCta?.(n.id); if (n.cta_rota) nav(n.cta_rota); setIdx((i) => i + 1); };

  return (
    <div className="fixed inset-0 z-[60] flex items-end sm:items-center justify-center bg-black/50" onClick={fechar}>
      <div onClick={(e) => e.stopPropagation()}
        className="bg-white w-full sm:max-w-lg sm:rounded-2xl rounded-t-2xl max-h-[85vh] overflow-hidden flex flex-col shadow-2xl">
        <div className="px-5 py-4 relative" style={{ background: '#0C3320' }}>
          <div className="h-1 w-14 rounded-full mb-2" style={{ background: '#C9A84C' }} />
          <div className="flex items-center justify-between">
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
              n.automatica ? 'bg-[#C9A84C] text-[#0C3320]' : tag.cls}`}>
              {n.automatica ? 'Sistema atualizado' : tag.label}
              {!n.automatica && n.versao ? ` · v${n.versao}` : ''}
            </span>
            {itens.length > 1 && <span className="text-[11px] text-emerald-200">{idx + 1} de {itens.length}</span>}
          </div>
          <h2 className="font-display text-xl font-bold text-white mt-2 pr-6">{n.titulo}</h2>
          {n.automatica && (n.versao || n.atualizado_em_br) && (
            <div className="text-[10.5px] font-mono tracking-wide" style={{ color: '#9FC9B0' }}>
              {n.versao ? `v${n.versao}` : ''}
              {n.versao && n.atualizado_em_br ? ' · ' : ''}
              {n.atualizado_em_br || ''}
            </div>
          )}
          <button onClick={fechar} className="absolute top-3 right-3 text-white/70 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-5 overflow-y-auto">
          {n.imagem_url && <img src={n.imagem_url} alt="" className="w-full rounded-xl mb-3" />}
          {Array.isArray(n.itens) && n.itens.length
            ? <ItensAtualizados itens={n.itens} />
            : <MarkdownLite text={n.conteudo_md} />}
        </div>
        <div className="border-t border-gray-100 p-4 flex items-center gap-2">
          {n.cta_rota && (
            <Button onClick={cta} className="flex-1 font-bold" style={{ background: 'linear-gradient(135deg,#E0C264,#C9A84C)', color: '#0C3320' }}>
              {n.cta_label || 'Saiba mais'}
            </Button>
          )}
          {n.automatica && !n.cta_rota && (
            <Button variant="outline" className="flex-1"
                    onClick={() => { onVisualizar?.(n.id); nav('/dashboard/novidades'); }}>
              Ver histórico
            </Button>
          )}
          <Button variant="outline" onClick={entendi} className={n.cta_rota || n.automatica ? '' : 'flex-1'}>
            Entendi
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ReleaseModal;
