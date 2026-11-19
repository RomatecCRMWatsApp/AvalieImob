// @module pages/admin/BlogMetricasAdmin — funil por artigo do blog.
//
// Leituras e cliques são contados de forma anônima (artigo + posição do botão, por dia).
// Cadastros vêm da página de entrada gravada no cadastro (v1.4.1545). Assinatura = plano
// pago ativo no sistema, não clique em "assinar".
import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { BrandSpinner } from '../../components/brand/BrandSpinner';
import { useToast } from '../../hooks/use-toast';
import { adminAPI } from '../../lib/api';
import { BLOG_POSTS } from '../../data/blogPosts';

const VERDE = '#0C3320';
const DOURADO = '#C9A84C';
const PERIODOS = [
  { dias: 7, label: '7 dias' },
  { dias: 30, label: '30 dias' },
  { dias: 90, label: '90 dias' },
  { dias: 3650, label: 'Tudo' },
];
const TITULO = Object.fromEntries(BLOG_POSTS.map((p) => [p.slug, p.titulo]));

function Card({ rotulo, valor, dica }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 min-w-0">
      <div className="text-xs uppercase tracking-wide text-gray-500">{rotulo}</div>
      <div className="text-2xl font-bold tabular-nums mt-1" style={{ color: VERDE }}>{valor}</div>
      {dica && <div className="text-xs text-gray-500 mt-1">{dica}</div>}
    </div>
  );
}

export default function BlogMetricasAdmin() {
  const { toast } = useToast();
  const [dias, setDias] = useState(30);
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(await adminAPI.blogMetricas({ dias }));
    } catch (e) {
      toast({ title: 'Não foi possível carregar as métricas do blog', description: e?.response?.data?.detail || 'Tente de novo.', variant: 'destructive' });
    } finally {
      setCarregando(false);
    }
  }, [dias, toast]);

  useEffect(() => { carregar(); }, [carregar]);

  const t = dados?.totais || {};
  const posicoes = dados?.posicoes || {};

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <div className="inline-flex flex-wrap p-1 rounded-lg bg-gray-100 border border-gray-200">
          {PERIODOS.map((p) => (
            <button key={p.dias} type="button" onClick={() => setDias(p.dias)}
                    className={`px-3 py-1.5 rounded-md text-sm ${dias === p.dias ? 'bg-white shadow-sm font-semibold' : 'text-gray-500'}`}
                    style={dias === p.dias ? { color: VERDE } : undefined}>
              {p.label}
            </button>
          ))}
        </div>
        <button type="button" onClick={carregar}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-gray-200 text-sm text-gray-600 hover:bg-gray-50">
          <RefreshCw className="w-4 h-4" /> Atualizar
        </button>
      </div>

      {carregando && !dados ? (
        <div className="py-16 flex justify-center"><BrandSpinner label="Carregando…" /></div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Card rotulo="Leituras" valor={t.leituras ?? 0} dica="1 por artigo por sessão" />
            <Card rotulo="Cliques nos botões" valor={t.cliques ?? 0} dica={`${t.taxa_clique ?? 0}% das leituras`} />
            <Card rotulo="Cadastros" valor={t.cadastros ?? 0} dica="que entraram por um artigo" />
            <Card rotulo="Em teste" valor={t.em_teste ?? 0} />
            <Card rotulo="Assinantes" valor={t.assinantes ?? 0} dica="plano pago ativo" />
          </div>

          <div className="rounded-xl border border-gray-200 bg-white overflow-x-auto">
            <table className="w-full text-sm min-w-[720px]">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-gray-200">
                  <th className="px-4 py-3">Artigo</th>
                  <th className="px-3 py-3 text-right">Leituras</th>
                  <th className="px-3 py-3 text-right">Cliques</th>
                  <th className="px-3 py-3">Onde clicaram</th>
                  <th className="px-3 py-3 text-right">Cadastros</th>
                  <th className="px-3 py-3 text-right">Teste</th>
                  <th className="px-3 py-3 text-right">Assin.</th>
                </tr>
              </thead>
              <tbody>
                {(dados?.artigos || []).length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-10 text-center text-gray-500">
                    Ainda não há leituras nem cadastros vindos do blog neste período. A contagem de leituras e cliques começou em 19/11/2026.
                  </td></tr>
                )}
                {(dados?.artigos || []).map((a) => (
                  <tr key={a.slug} className="border-b border-gray-100 last:border-0 align-top">
                    <td className="px-4 py-3 min-w-0">
                      <a href={`/blog/${a.slug}`} target="_blank" rel="noreferrer"
                         className="font-medium hover:underline" style={{ color: VERDE }}>
                        {TITULO[a.slug] || a.slug}
                      </a>
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums">{a.leituras}</td>
                    <td className="px-3 py-3 text-right tabular-nums">
                      {a.cliques}
                      {a.leituras > 0 && <div className="text-xs text-gray-500">{a.taxa_clique}%</div>}
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(a.cliques_por_posicao || {}).sort((x, y) => y[1] - x[1]).map(([pos, n]) => (
                          <span key={pos} className="px-2 py-0.5 rounded-full text-xs border"
                                style={{ borderColor: DOURADO, color: VERDE }}>
                            {posicoes[pos] || pos}: {n}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums font-semibold">{a.cadastros}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{a.em_teste}</td>
                    <td className="px-3 py-3 text-right tabular-nums">{a.assinantes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-500">
            Contagem anônima: só o artigo, a posição do botão e o dia. Cadastro conta para o artigo em que a visita começou. Assinante é quem tem plano pago ativo no sistema.
          </p>
        </>
      )}
    </div>
  );
}
