// @hook useNovidades — carrega novidades UMA vez por sessão + ações (visto/dispensar/cta).
import { useState, useEffect, useCallback, useRef } from 'react';
import { novidadesAPI } from '../lib/api';

export function useNovidades() {
  const [pendentes, setPendentes] = useState([]);
  const [historico, setHistorico] = useState([]);
  const carregado = useRef(false);

  const carregar = useCallback(async () => {
    try {
      const [p, h] = await Promise.all([novidadesAPI.pendentes(), novidadesAPI.historico()]);
      setPendentes(Array.isArray(p) ? p : []);
      setHistorico(Array.isArray(h) ? h : []);
    } catch { /* silencioso — não pode atrapalhar o carregamento do dashboard */ }
  }, []);

  useEffect(() => {
    if (carregado.current) return;   // uma vez por sessão (não a cada navegação)
    carregado.current = true;
    carregar();
  }, [carregar]);

  const visualizar = useCallback((id) => { novidadesAPI.visualizada(id).catch(() => {}); }, []);

  const dispensar = useCallback((id) => {
    novidadesAPI.dispensar(id).catch(() => {});
    setPendentes((s) => s.filter((n) => n.id !== id));
    setHistorico((s) => s.map((n) => (n.id === id ? { ...n, lida: true, dispensada: true } : n)));
  }, []);

  const clicarCta = useCallback((id) => { novidadesAPI.cta(id).catch(() => {}); dispensar(id); }, [dispensar]);

  return { pendentes, historico, count: pendentes.length, visualizar, dispensar, clicarCta, recarregar: carregar };
}

export default useNovidades;
