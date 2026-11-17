// @module hooks/usePlanos — planos com preço vindo do servidor (fonte única: backend/services/planos.py).
// Os textos/recursos de cada card continuam em mock.PLANS; daqui só vêm preço e economia.
// Se a rota GET /api/planos falhar, a tela segue com os valores locais (sem quebrar).
import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { PLANS } from '../mock/mock';

const ID_SERVIDOR = { monthly: 'mensal', quarterly: 'trimestral', annual: 'anual' };

let _cache = null; // promise compartilhada: 1 requisição por carregamento da página

function _buscar() {
  if (!_cache) {
    _cache = api.get('/planos').then((r) => r.data).catch(() => null);
  }
  return _cache;
}

export function mesclarPlanos(dados) {
  const lista = dados?.planos;
  if (!Array.isArray(lista)) return PLANS;
  const porId = Object.fromEntries(lista.map((p) => [p.id, p]));
  return PLANS.map((p) => {
    const s = porId[ID_SERVIDOR[p.id]];
    if (!s || typeof s.preco !== 'number') return p;
    return {
      ...p,
      price: s.preco,
      saving: s.economia_pct > 0 ? `Economize ${s.economia_pct}%` : p.saving,
    };
  });
}

export default function usePlanos() {
  const [planos, setPlanos] = useState(PLANS);
  const [testeDias, setTesteDias] = useState(null);
  useEffect(() => {
    let vivo = true;
    _buscar().then((d) => {
      if (!vivo || !d) return;
      setPlanos(mesclarPlanos(d));
      if (Number.isFinite(d.teste_dias)) setTesteDias(d.teste_dias);
    });
    return () => { vivo = false; };
  }, []);
  return { planos, testeDias };
}
