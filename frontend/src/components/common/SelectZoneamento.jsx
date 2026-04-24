// @module common/SelectZoneamento — Select de Zoneamento dinâmico com zonas do usuário via API
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { ChevronDown, Search, Plus, Settings, Loader2 } from 'lucide-react';
import { zonasAPI } from '../../lib/api';
import { ModalNovaZona } from './ModalNovaZona';
import { ModalGerenciarZonas } from './ModalGerenciarZonas';

// Fallback hardcoded se a API falhar
const ZONAS_FALLBACK = [
  { id: 'f_ZR1',  codigo: 'ZR1',  nome: 'Zona Residencial 1',                municipio: '' },
  { id: 'f_ZR2',  codigo: 'ZR2',  nome: 'Zona Residencial 2',                municipio: '' },
  { id: 'f_ZR3',  codigo: 'ZR3',  nome: 'Zona Residencial 3',                municipio: '' },
  { id: 'f_ZC',   codigo: 'ZC',   nome: 'Zona Comercial',                    municipio: '' },
  { id: 'f_ZCI',  codigo: 'ZCI',  nome: 'Zona Comercial e Industrial',       municipio: '' },
  { id: 'f_ZI',   codigo: 'ZI',   nome: 'Zona Industrial',                   municipio: '' },
  { id: 'f_ZEI',  codigo: 'ZEI',  nome: 'Zona de Expansão Industrial',       municipio: '' },
  { id: 'f_ZRu',  codigo: 'ZRu',  nome: 'Zona Rural',                        municipio: '' },
  { id: 'f_ZEIS', codigo: 'ZEIS', nome: 'Zona Especial de Interesse Social',  municipio: '' },
  { id: 'f_ZPA',  codigo: 'ZPA',  nome: 'Zona de Proteção Ambiental',        municipio: '' },
  { id: 'f_ZM',   codigo: 'ZM',   nome: 'Zona Mista',                        municipio: '' },
  { id: 'f_ZCB',  codigo: 'ZCB',  nome: 'Zona de Centralidade de Bairro',    municipio: '' },
];

function agruparPorMunicipio(zonas) {
  const grupos = {};
  zonas.forEach((z) => {
    const key = z.municipio || '';
    if (!grupos[key]) grupos[key] = [];
    grupos[key].push(z);
  });
  return grupos;
}

export function SelectZoneamento({ value, onChange, municipio, placeholder }) {
  const [zonas, setZonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [busca, setBusca] = useState('');
  const [showNovaZona, setShowNovaZona] = useState(false);
  const [showGerenciar, setShowGerenciar] = useState(false);
  const dropdownRef = useRef(null);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const data = await zonasAPI.listar();
      setZonas(Array.isArray(data) ? data : ZONAS_FALLBACK);
    } catch {
      setZonas(ZONAS_FALLBACK);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  // Fechar ao clicar fora
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
        setBusca('');
      }
    };
    if (open) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Filtrar por municipio prop e busca
  const zonasFiltradas = zonas.filter((z) => {
    const matchMunicipio = !municipio || !z.municipio || z.municipio.toLowerCase() === municipio.toLowerCase();
    const matchBusca = !busca
      || z.codigo.toLowerCase().includes(busca.toLowerCase())
      || z.nome.toLowerCase().includes(busca.toLowerCase());
    return matchMunicipio && matchBusca;
  });

  const grupos = agruparPorMunicipio(zonasFiltradas);
  const municipioKeys = Object.keys(grupos).sort();

  const selected = zonas.find((z) => z.codigo === value || z.id === value);
  const displayLabel = selected ? `${selected.codigo} — ${selected.nome}` : '';

  const handleSelect = (zona) => {
    onChange(zona.codigo);
    setOpen(false);
    setBusca('');
  };

  return (
    <>
      <div className="relative" ref={dropdownRef}>
        {/* Trigger */}
        <button
          type="button"
          onClick={() => { setOpen((o) => !o); setBusca(''); }}
          className="flex items-center justify-between w-full max-w-xs border border-gray-300 rounded-md px-3 py-2 bg-white text-sm text-left hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {loading ? (
            <span className="flex items-center gap-2 text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin" /> Carregando...
            </span>
          ) : (
            <span className={displayLabel ? 'text-gray-900' : 'text-gray-400'}>
              {displayLabel || placeholder || 'Selecione o zoneamento...'}
            </span>
          )}
          <ChevronDown className="h-4 w-4 text-gray-400 ml-2 shrink-0" />
        </button>

        {/* Dropdown */}
        {open && (
          <div className="absolute z-50 mt-1 w-80 max-w-sm bg-white border border-gray-200 rounded-lg shadow-lg">
            {/* Busca */}
            <div className="p-2 border-b border-gray-100">
              <div className="flex items-center gap-2 px-2 py-1.5 border border-gray-200 rounded-md">
                <Search className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                <input
                  autoFocus
                  type="text"
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                  placeholder="Buscar zona..."
                  className="text-sm flex-1 outline-none bg-transparent"
                />
              </div>
            </div>

            {/* Lista */}
            <div className="max-h-56 overflow-y-auto py-1">
              {zonasFiltradas.length === 0 ? (
                <div className="px-4 py-3 text-sm text-gray-400 text-center">Nenhuma zona encontrada</div>
              ) : (
                municipioKeys.map((mun) => (
                  <div key={mun}>
                    {mun && (
                      <div className="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wide bg-gray-50">
                        {mun}
                      </div>
                    )}
                    {grupos[mun].map((zona) => (
                      <button
                        key={zona.id}
                        type="button"
                        onClick={() => handleSelect(zona)}
                        className={`w-full text-left px-3 py-2 text-sm hover:bg-blue-50 flex items-center gap-2 ${
                          value === zona.codigo ? 'bg-blue-50 text-blue-700' : 'text-gray-800'
                        }`}
                      >
                        <span className="font-semibold text-xs w-12 shrink-0">{zona.codigo}</span>
                        <span className="truncate">{zona.nome}</span>
                      </button>
                    ))}
                  </div>
                ))
              )}
            </div>

            {/* Ações */}
            <div className="border-t border-gray-100 p-1.5 space-y-0.5">
              <button
                type="button"
                onClick={() => { setOpen(false); setShowNovaZona(true); }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-md"
              >
                <Plus className="h-4 w-4" />
                Cadastrar nova zona
              </button>
              <button
                type="button"
                onClick={() => { setOpen(false); setShowGerenciar(true); }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-md"
              >
                <Settings className="h-4 w-4" />
                Gerenciar minhas zonas
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal Nova Zona */}
      {showNovaZona && (
        <ModalNovaZona
          open={showNovaZona}
          onClose={() => setShowNovaZona(false)}
          municipioInicial={municipio || ''}
          onSucesso={(novaZona) => {
            setShowNovaZona(false);
            carregar();
            if (novaZona) onChange(novaZona.codigo);
          }}
        />
      )}

      {/* Modal Gerenciar Zonas */}
      {showGerenciar && (
        <ModalGerenciarZonas
          open={showGerenciar}
          onClose={() => { setShowGerenciar(false); carregar(); }}
        />
      )}
    </>
  );
}

export default SelectZoneamento;
