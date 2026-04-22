import { useState, useEffect, useRef, useCallback } from 'react';
import { cndAPI } from '../../../../lib/api';

export function useConsulta(id) {
  const [consulta, setConsulta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const fetch = useCallback(async () => {
    if (!id) return;
    try {
      const data = await cndAPI.getConsulta(id);
      setConsulta(data);
      const status = data.consulta?.status || data.status;
      if (status !== 'processando' && status !== 'pendente') {
        clearInterval(intervalRef.current);
      }
    } catch (err) {
      setError(err?.response?.data?.detail || 'Erro ao buscar consulta');
      clearInterval(intervalRef.current);
    }
  }, [id]);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetch().finally(() => setLoading(false));
    intervalRef.current = setInterval(fetch, 3000);
    return () => clearInterval(intervalRef.current);
  }, [id, fetch]);

  return { consulta, loading, error };
}

export function useHistorico() {
  const [historico, setHistorico] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchHistorico = useCallback(async () => {
    setLoading(true);
    try {
      const data = await cndAPI.getHistorico();
      setHistorico(data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Erro ao buscar histórico');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistorico();
  }, [fetchHistorico]);

  const remove = useCallback(async (id) => {
    await cndAPI.deleteConsulta(id);
    setHistorico(prev => prev.filter(c => c.id !== id));
  }, []);

  return { historico, loading, error, refresh: fetchHistorico, remove };
}
