import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, X, Loader2,
  FileCheck2, ClipboardCheck, Shield, Beef, Home, Users, Building2,
} from 'lucide-react';
import { useGlobalSearch } from '../../hooks/useGlobalSearch';

/* ── Icone por tipo ─────────────────────────────────────────────────── */
const TIPO_ICON = {
  ptam: FileCheck2,
  tvi: ClipboardCheck,
  garantia: Shield,
  semovente: Beef,
  locacao: Home,
  cliente: Users,
  imovel: Building2,
};

/* ── Label do grupo ─────────────────────────────────────────────────── */
const TIPO_LABEL = {
  ptam: 'PTAM',
  tvi: 'TVI',
  garantia: 'GARANTIAS',
  semovente: 'SEMOVENTES',
  locacao: 'LOCACOES',
  cliente: 'CLIENTES',
  imovel: 'IMOVEIS',
};

/* ── Cor do badge de status ─────────────────────────────────────────── */
function badgeColor(status) {
  if (!status) return '';
  const s = status.toLowerCase();
  if (s === 'emitido') return 'bg-emerald-100 text-emerald-700';
  if (s === 'lacrado') return 'bg-blue-100 text-blue-700';
  return 'bg-gray-100 text-gray-600';
}

/* ── Highlight case-insensitive ─────────────────────────────────────── */
function highlight(text, term) {
  if (!term || !text) return text;
  const parts = text.split(new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
  return parts.map((p, i) =>
    p.toLowerCase() === term.toLowerCase()
      ? <strong key={i} className="font-semibold">{p}</strong>
      : p
  );
}

/* ── Agrupa resultados por tipo, preservando ordem ─────────────────── */
function groupByTipo(results) {
  const order = [];
  const map = {};
  for (const item of results) {
    if (!map[item.tipo]) {
      map[item.tipo] = [];
      order.push(item.tipo);
    }
    map[item.tipo].push(item);
  }
  return order.map(tipo => ({ tipo, items: map[tipo] }));
}

/* ── Componente principal ────────────────────────────────────────────── */
export default function GlobalSearch() {
  const navigate = useNavigate();
  const { query, setQuery, results, loading, open, setOpen, clear } = useGlobalSearch();
  const inputRef = useRef(null);
  const containerRef = useRef(null);
  const [selectedIdx, setSelectedIdx] = useState(-1);

  /* Ctrl+K / Cmd+K foca o input */
  useEffect(() => {
    function onKeyDown(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, []);

  /* Fechar ao clicar fora */
  useEffect(() => {
    function onMouseDown(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [setOpen]);

  /* Resetar indice selecionado quando resultados mudam */
  useEffect(() => {
    setSelectedIdx(-1);
  }, [results]);

  /* Navegar pelo teclado dentro do dropdown */
  function onKeyDownInput(e) {
    if (e.key === 'Escape') {
      clear();
      inputRef.current?.blur();
      return;
    }
    if (!open || results.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIdx(idx => Math.min(idx + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIdx(idx => Math.max(idx - 1, -1));
    } else if (e.key === 'Enter' && selectedIdx >= 0) {
      e.preventDefault();
      navigate(results[selectedIdx].rota);
      clear();
    }
  }

  const groups = groupByTipo(results);

  /* Indice absoluto para controle de teclado */
  let absoluteIdx = 0;

  return (
    <div ref={containerRef} className="relative flex-1 max-w-md">
      {/* Input */}
      <div className="relative">
        {loading
          ? <Loader2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-emerald-500 animate-spin pointer-events-none" />
          : <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        }
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={e => { setQuery(e.target.value); if (e.target.value.trim().length >= 2) setOpen(true); }}
          onFocus={() => { if (results.length > 0) setOpen(true); }}
          onKeyDown={onKeyDownInput}
          placeholder="Buscar laudos, clientes, imoveis... (Ctrl+K)"
          className="w-full pl-9 pr-8 py-2 rounded-xl text-sm bg-gray-100 border border-transparent
                     focus:outline-none focus:border-emerald-300 focus:bg-white transition-all placeholder-gray-400"
        />
        {query && (
          <button
            onClick={clear}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full hover:bg-gray-200 flex items-center justify-center transition-colors"
            tabIndex={-1}
          >
            <X className="w-3 h-3 text-gray-500" />
          </button>
        )}
      </div>

      {/* Dropdown */}
      {open && query.trim().length >= 2 && (
        <div className="absolute left-0 right-0 mt-2 bg-white rounded-lg shadow-xl border border-gray-200 z-50 max-h-[480px] overflow-y-auto flex flex-col">

          {/* Header */}
          <div className="px-3 py-2 border-b border-gray-100 text-xs text-gray-500 flex-shrink-0">
            Resultados para{' '}
            <span className="font-medium text-gray-700">"{query}"</span>
            {' '}· {results.length} encontrado{results.length !== 1 ? 's' : ''}
          </div>

          {/* Resultados agrupados */}
          {results.length > 0 ? (
            <div className="flex-1 overflow-y-auto">
              {groups.map(({ tipo, items }) => (
                <div key={tipo}>
                  {/* Label do grupo */}
                  <div className="px-3 py-1 text-[10px] font-bold tracking-widest text-gray-400 uppercase bg-gray-50 border-b border-gray-100">
                    {TIPO_LABEL[tipo] || tipo.toUpperCase()}
                  </div>

                  {items.map(item => {
                    const Icon = TIPO_ICON[item.tipo] || FileCheck2;
                    const isSelected = absoluteIdx === selectedIdx;
                    const currentIdx = absoluteIdx;
                    absoluteIdx++;

                    return (
                      <button
                        key={`${item.tipo}-${item.id}-${currentIdx}`}
                        onClick={() => { navigate(item.rota); clear(); }}
                        onMouseEnter={() => setSelectedIdx(currentIdx)}
                        className={`w-full text-left px-3 py-2.5 flex items-start gap-3 transition-colors border-b border-gray-50 last:border-0 ${
                          isSelected ? 'bg-emerald-700 text-white' : 'hover:bg-emerald-50 text-gray-800'
                        }`}
                      >
                        <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isSelected ? 'text-white' : 'text-emerald-600'}`} />
                        <div className="flex-1 min-w-0">
                          <div className={`text-sm font-medium truncate ${isSelected ? 'text-white' : 'text-gray-800'}`}>
                            {highlight(item.titulo, query)}
                          </div>
                          {item.subtitulo && (
                            <div className={`text-xs truncate mt-0.5 ${isSelected ? 'text-emerald-100' : 'text-gray-500'}`}>
                              {highlight(item.subtitulo, query)}
                            </div>
                          )}
                        </div>
                        <div className="flex flex-col items-end gap-1 flex-shrink-0">
                          {item.valor && (
                            <span className={`text-xs font-semibold ${isSelected ? 'text-emerald-200' : 'text-emerald-700'}`}>
                              {item.valor}
                            </span>
                          )}
                          {item.status && (
                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${isSelected ? 'bg-white/20 text-white' : badgeColor(item.status)}`}>
                              {item.status}
                            </span>
                          )}
                          {item.updated_at && (
                            <span className={`text-[10px] ${isSelected ? 'text-emerald-200' : 'text-gray-400'}`}>
                              {item.updated_at}
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          ) : (
            /* Estado vazio */
            <div className="px-4 py-6 text-center text-sm text-gray-500">
              Nenhum resultado para{' '}
              <span className="font-medium">"{query}"</span>.
              <br />
              <span className="text-xs text-gray-400 mt-1 block">
                Tente buscar por endereco, nome do cliente ou numero do laudo.
              </span>
            </div>
          )}

          {/* Footer fixo */}
          <div className="px-3 py-2 border-t border-gray-100 text-[10px] text-gray-400 flex gap-3 flex-shrink-0 bg-gray-50">
            <span>↑↓ navegar</span>
            <span>Enter selecionar</span>
            <span>Esc fechar</span>
          </div>
        </div>
      )}
    </div>
  );
}
