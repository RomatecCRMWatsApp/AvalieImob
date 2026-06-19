// Painel admin dos leads da Calculadora pública ("Quanto vale meu imóvel?").
// Rota: /dashboard/admin/leads (admin/owner/ceo). Lista + filtro + busca +
// paginação + troca de status inline + WhatsApp 1-clique + cards de resumo.
import React, { useCallback, useEffect, useState } from 'react';
import { adminAPI } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { BrandSpinner } from '../../components/brand/BrandSpinner';

const VERDE = '#0C3320';
const DOURADO = '#C9A84C';

const STATUS = {
  novo: { label: 'Novo', cor: '#2563eb', bg: '#eff6ff' },
  em_contato: { label: 'Em contato', cor: '#b45309', bg: '#fffbeb' },
  convertido: { label: 'Convertido', cor: '#15803d', bg: '#f0fdf4' },
  descartado: { label: 'Descartado', cor: '#6b7280', bg: '#f9fafb' },
};

const brl = (n) => n == null ? '—' :
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(n);

const dataFmt = (iso) =>
  iso ? new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—';

const LIMIT = 20;

export default function LeadsAdmin() {
  const { toast } = useToast();
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filtroStatus, setFiltroStatus] = useState('');
  const [busca, setBusca] = useState('');
  const [loading, setLoading] = useState(true);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, limit: LIMIT };
      if (filtroStatus) params.status = filtroStatus;
      if (busca.trim()) params.q = busca.trim();
      const [lista, st] = await Promise.all([adminAPI.listLeads(params), adminAPI.leadsStats()]);
      setLeads(lista.items || []);
      setTotal(lista.total || 0);
      setStats(st);
    } catch (e) {
      toast({ title: 'Erro ao carregar leads', description: e.response?.data?.detail, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [page, filtroStatus, busca, toast]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { carregar(); }, [page, filtroStatus]);

  async function mudarStatus(id, status) {
    try {
      await adminAPI.atualizarLead(id, { status });
      carregar();
    } catch (e) {
      toast({ title: 'Erro ao atualizar', description: e.response?.data?.detail, variant: 'destructive' });
    }
  }

  async function excluir(id) {
    if (!window.confirm('Excluir este lead permanentemente?')) return;
    try {
      await adminAPI.excluirLead(id);
      carregar();
    } catch (e) {
      toast({ title: 'Erro ao excluir', description: e.response?.data?.detail, variant: 'destructive' });
    }
  }

  const totalPaginas = Math.max(1, Math.ceil(total / LIMIT));

  const Card = ({ titulo, valor, cor }) => (
    <div className="rounded-xl bg-white p-4 shadow-sm border border-gray-100">
      <p className="text-xs text-gray-500">{titulo}</p>
      <p className="mt-1 text-2xl font-bold" style={{ color: cor || VERDE }}>{valor}</p>
    </div>
  );

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 font-display" style={{ color: VERDE }}>
        Leads · Calculadora de Avaliação
      </h1>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
          <Card titulo="Total" valor={stats.total} />
          <Card titulo="Novos" valor={stats.novos} cor={STATUS.novo.cor} />
          <Card titulo="Em contato" valor={stats.em_contato} cor={STATUS.em_contato.cor} />
          <Card titulo="Convertidos" valor={stats.convertidos} cor={STATUS.convertido.cor} />
          <Card titulo="Últimos 30 dias" valor={stats.ultimos_30_dias} />
          <Card titulo="Conversão" valor={`${stats.taxa_conversao}%`} cor={DOURADO} />
        </div>
      )}

      <div className="flex flex-col md:flex-row gap-3 mb-4">
        <select className="rounded-lg border border-gray-300 px-3 py-2 bg-white text-sm"
          value={filtroStatus} onChange={(e) => { setPage(1); setFiltroStatus(e.target.value); }}>
          <option value="">Todos os status</option>
          {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <input className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
          placeholder="Buscar por nome, WhatsApp ou e-mail..." value={busca}
          onChange={(e) => setBusca(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { setPage(1); carregar(); } }} />
        <button onClick={() => { setPage(1); carregar(); }}
          className="rounded-lg px-5 py-2 font-semibold text-white text-sm" style={{ backgroundColor: VERDE }}>
          Buscar
        </button>
      </div>

      {loading ? (
        <div className="py-20 flex justify-center"><BrandSpinner label="Carregando leads…" /></div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl bg-white shadow-sm border border-gray-100">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="px-4 py-3">Lead</th>
                  <th className="px-4 py-3">Imóvel</th>
                  <th className="px-4 py-3">Estimativa</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Data</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {leads.length === 0 ? (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Nenhum lead encontrado.</td></tr>
                ) : leads.map((l) => (
                  <tr key={l.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-800">{l.nome}</p>
                      <a href={`https://wa.me/${l.whatsapp}`} target="_blank" rel="noreferrer"
                        className="text-green-700 hover:underline">📱 {l.whatsapp}</a>
                      {l.email && <p className="text-xs text-gray-400">{l.email}</p>}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {l.imovel?.tipo} · {l.imovel?.area}m²<br />
                      <span className="text-xs">{l.imovel?.cidade}/{l.imovel?.uf}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-700">
                      {brl(l.estimativa?.valor_min)} – {brl(l.estimativa?.valor_max)}
                    </td>
                    <td className="px-4 py-3">
                      <select value={l.status} onChange={(e) => mudarStatus(l.id, e.target.value)}
                        className="rounded-md px-2 py-1 text-xs font-semibold border-0 cursor-pointer"
                        style={{ color: STATUS[l.status]?.cor, backgroundColor: STATUS[l.status]?.bg }}>
                        {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                      </select>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{dataFmt(l.criado_em)}</td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => excluir(l.id)} className="text-gray-300 hover:text-red-500" title="Excluir">✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between mt-4 text-sm text-gray-600">
            <span>{total} lead(s)</span>
            <div className="flex items-center gap-2">
              <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}
                className="rounded-lg border px-3 py-1.5 disabled:opacity-40">Anterior</button>
              <span>{page} / {totalPaginas}</span>
              <button disabled={page >= totalPaginas} onClick={() => setPage((p) => p + 1)}
                className="rounded-lg border px-3 py-1.5 disabled:opacity-40">Próxima</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
