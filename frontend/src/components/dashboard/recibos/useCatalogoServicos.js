// @module recibos/useCatalogoServicos — Hook que consome /api/recibos/catalogo
//
// Retorna o catálogo cascata (categorias → serviços) e helpers de lookup.
// Cada serviço carrega { value, label, tipo, descricao } para auto-preencher
// o formulário de recibo.
import { useState, useEffect, useCallback, useMemo } from 'react';
import { recibosAPI } from '../../../lib/api';

export function useCatalogoServicos() {
  const [categorias, setCategorias] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let vivo = true;
    recibosAPI.catalogo()
      .then((d) => { if (vivo) setCategorias(d.categorias || []); })
      .catch(() => { if (vivo) setCategorias([]); })
      .finally(() => { if (vivo) setLoading(false); });
    return () => { vivo = false; };
  }, []);

  const servicosDe = useCallback(
    (catValue) => categorias.find((c) => c.value === catValue)?.servicos || [],
    [categorias],
  );

  const buscarServico = useCallback(
    (catValue, servValue) => servicosDe(catValue).find((s) => s.value === servValue) || null,
    [servicosDe],
  );

  return useMemo(
    () => ({ categorias, loading, servicosDe, buscarServico }),
    [categorias, loading, servicosDe, buscarServico],
  );
}

export default useCatalogoServicos;
