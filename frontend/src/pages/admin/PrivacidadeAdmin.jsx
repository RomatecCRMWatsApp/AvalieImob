// @module pages/admin/PrivacidadeAdmin — pedidos de titulares (LGPD art. 18).
// O sistema registra e acompanha; quem decide e executa é o responsável, com trilha.
// Nada aqui apaga dados automaticamente.
import React, { useCallback, useEffect, useState } from 'react';
import { privacidadeAPI } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { BrandSpinner } from '../../components/brand/BrandSpinner';

const VERDE = '#0C3320';
const ROTULO = {
  recebida: 'Recebido', verificando_identidade: 'Verificando identidade', em_analise: 'Em análise',
  atendida: 'Atendido', indeferida: 'Indeferido',
};
const comoUTC = (s) => (s && !/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? `${s}Z` : s);
const data = (s) => (s ? new Date(comoUTC(s)).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—');

function Pedido({ p, onSalvar }) {
  const [status, setStatus] = useState(p.status);
  const [nota, setNota] = useState('');
  const [resp, setResp] = useState(p.responsavel || '');
  const vencido = p.prazo_referencia && !p.concluida_em && new Date(comoUTC(p.prazo_referencia)) < new Date();
  return (
    <li className="border border-gray-200 rounded-lg p-4 bg-white">
      <div className="flex flex-wrap justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold" style={{ color: VERDE }}>{p.protocolo} · {p.tipo_label}</p>
          <p className="text-sm text-gray-700 break-words">{p.nome} · {p.email}{p.telefone ? ` · ${p.telefone}` : ''} · {p.relacao}</p>
          <p className="text-xs text-gray-500">
            {p.origem === 'conta' ? 'Pedido feito dentro da conta (login verificado)' : 'Pedido público — confirmar identidade antes de entregar ou apagar dados'}
          </p>
        </div>
        <div className="text-right text-xs text-gray-600">
          <p>Recebido {data(p.recebida_em)}</p>
          <p className={vencido ? 'text-red-700 font-semibold' : ''}>Prazo de referência {data(p.prazo_referencia)}</p>
        </div>
      </div>
      <p className="mt-2 text-sm text-gray-800 whitespace-pre-wrap break-words">{p.descricao}</p>
      {(p.historico || []).length > 0 && (
        <ul className="mt-2 text-xs text-gray-500 space-y-0.5">
          {p.historico.map((h, i) => <li key={i}>{data(h.em)} · {ROTULO[h.status] || h.status}{h.nota ? ` — ${h.nota}` : ''}</li>)}
        </ul>
      )}
      <div className="mt-3 grid sm:grid-cols-3 gap-2">
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="border border-gray-300 rounded-md px-2 min-h-[40px] text-sm">
          {Object.entries(ROTULO).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <input value={resp} onChange={(e) => setResp(e.target.value)} placeholder="Responsável" className="border border-gray-300 rounded-md px-2 min-h-[40px] text-sm" />
        <input value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Nota (o que foi feito)" className="border border-gray-300 rounded-md px-2 min-h-[40px] text-sm" />
      </div>
      <button type="button" onClick={() => onSalvar(p.protocolo, { status, nota, responsavel: resp })}
              className="mt-2 px-4 py-2 rounded-md text-white text-sm font-semibold" style={{ background: VERDE }}>Salvar</button>
    </li>
  );
}

export default function PrivacidadeAdmin() {
  const { toast } = useToast();
  const [filtro, setFiltro] = useState('');
  const [itens, setItens] = useState(null);

  const carregar = useCallback(() => {
    privacidadeAPI.adminListar(filtro || undefined)
      .then((r) => setItens(r.solicitacoes || []))
      .catch(() => { setItens([]); toast({ title: 'Não foi possível carregar os pedidos', variant: 'destructive' }); });
  }, [filtro, toast]);
  useEffect(() => { carregar(); }, [carregar]);

  const salvar = async (protocolo, dados) => {
    try {
      await privacidadeAPI.adminAtualizar(protocolo, dados);
      toast({ title: 'Pedido atualizado' });
      carregar();
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e?.response?.data?.detail || '', variant: 'destructive' });
    }
  };

  return (
    <div className="space-y-4 pr-9 sm:pr-12">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: VERDE }}>Pedidos de privacidade</h1>
        <p className="text-sm text-gray-600">Pedidos de titulares (LGPD art. 18), com e sem conta. Os prazos de referência são configuráveis e precisam ser validados pelo jurídico.</p>
      </div>
      <select value={filtro} onChange={(e) => setFiltro(e.target.value)} className="border border-gray-300 rounded-md px-2 min-h-[40px] text-sm">
        <option value="">Todos</option>
        {Object.entries(ROTULO).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
      {itens === null ? <div className="py-10 flex justify-center"><BrandSpinner label="Carregando…" /></div>
        : itens.length === 0 ? <p className="text-gray-500">Nenhum pedido.</p>
          : <ul className="space-y-3">{itens.map((p) => <Pedido key={p.protocolo} p={p} onSalvar={salvar} />)}</ul>}
    </div>
  );
}
