import { useState, useEffect, useCallback } from 'react';
import { tviAPI } from '../../../../lib/api';

export function useModels() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    tviAPI.listModels()
      .then(data => {
        if (Array.isArray(data)) {
          setModels(data);
        } else if (data.categorias) {
          // Backend returns { categorias: { Cat1: [...], Cat2: [...] }, total: N }
          const flat = Object.values(data.categorias).flat();
          setModels(flat);
        } else {
          setModels(data.models || []);
        }
      })
      .catch(e => setError(e?.message || 'Erro ao carregar modelos'))
      .finally(() => setLoading(false));
  }, []);

  return { models, loading, error };
}

export function useVistorias() {
  const [vistorias, setVistorias] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await tviAPI.list();
      setVistorias(Array.isArray(data) ? data : data.items || []);
    } catch {
      setVistorias([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const remove = useCallback(async (id) => {
    await tviAPI.remove(id);
    setVistorias(prev => prev.filter(v => v.id !== id));
  }, []);

  return { vistorias, loading, reload: load, remove };
}

export function useVistoria(id) {
  const [vistoria, setVistoria] = useState(null);
  const [loading, setLoading] = useState(!!id);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await tviAPI.get(id);
      setVistoria(data);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const save = useCallback(async (fields) => {
    if (!id) return;
    const updated = await tviAPI.update(id, fields);
    setVistoria(updated);
    return updated;
  }, [id]);

  return { vistoria, setVistoria, loading, reload: load, save };
}
