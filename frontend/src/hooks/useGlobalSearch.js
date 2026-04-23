import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../lib/api';

export function useGlobalSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    if (query.trim().length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    timerRef.current = setTimeout(async () => {
      try {
        const res = await api.get('/search', { params: { q: query.trim(), limit: 20 } });
        setResults(res.data.results || []);
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query]);

  const clear = useCallback(() => {
    setQuery('');
    setResults([]);
    setOpen(false);
    setLoading(false);
  }, []);

  return { query, setQuery, results, loading, open, setOpen, clear };
}
