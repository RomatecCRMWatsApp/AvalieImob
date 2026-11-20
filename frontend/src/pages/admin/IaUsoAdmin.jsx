// @module IaUsoAdmin — uso da IA por provedor/modelo/origem (só metadados, sem o texto).
import React, { useEffect, useState } from 'react';
import { Cpu, CheckCircle2, XCircle } from 'lucide-react';
import { adminAPI } from '../../lib/api';
import { BrandSpinner } from '../../components/brand/BrandSpinner';
import { fmtDataHora } from '../../utils/datasServidor';

const NOME = { groq: 'Groq', gemini: 'Gemini', claude: 'Claude', openai: 'OpenAI' };
const RESULTADO = { ok: 'respondeu', vazio: 'resposta vazia', timeout: 'tempo esgotado', nao_configurado: 'sem chave' };
const rotRes = (r) => RESULTADO[r] || (r?.startsWith('erro:') ? `erro (${r.slice(5)})` : r);
const ms = (v) => (v == null ? '—' : v >= 1000 ? `${(v / 1000).toFixed(1).replace('.', ',')} s` : `${v} ms`);
const ORIGEM = { atendimento_site: 'Atendimento do site', contratos: 'Contratos', instagram: 'Instagram' };
const rotOrigem = (o) => ORIGEM[o] || (o?.startsWith('chat:') ? `Roma_IA (${o.slice(5)})` : o);

function Card({ titulo, valor, sub }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-3 min-w-0">
      <div className="text-xs text-gray-500">{titulo}</div>
      <div className="text-xl font-bold text-gray-900 mt-0.5">{valor}</div>
      {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
    </div>
  );
}

export default function IaUsoAdmin() {
  const [dias, setDias] = useState(7);
  const [d, setD] = useState(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    setD(null); setErro('');
    adminAPI.iaUso(dias).then(setD).catch((e) => setErro(e?.response?.data?.detail || 'Não foi possível carregar.'));
  }, [dias]);

  const r = d?.resumo;
  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="font-display text-[30px] font-bold leading-tight text-[#C9A84C] flex items-center gap-2">
            <Cpu className="w-7 h-7" /> Uso da IA
          </h1>
          <p className="text-sm text-[#5B7466] dark:text-[#9FB5A6] mt-1">
            Qual provedor e modelo respondeu cada pedido, quanto tempo levou e onde houve falha.
            O texto das conversas não é guardado aqui.
          </p>
        </div>
        <select value={dias} onChange={(e) => setDias(Number(e.target.value))} aria-label="Período"
          className="rounded-xl border border-gray-300 bg-white px-3 py-2.5 text-sm min-h-[44px]">
          {[1, 7, 30, 90].map((n) => <option key={n} value={n}>Últimos {n} dia{n > 1 ? 's' : ''}</option>)}
        </select>
      </div>

      {erro && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{erro}</div>}
      {!d && !erro && <div className="py-10 flex justify-center"><BrandSpinner label="Carregando…" /></div>}

      {d && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <Card titulo="Pedidos" valor={r.chamadas} sub={`${r.sem_resposta} sem resposta`} />
            <Card titulo="Respondidos" valor={r.taxa_sucesso == null ? '—' : `${String(r.taxa_sucesso).replace('.', ',')}%`} />
            <Card titulo="Tempo médio" valor={ms(r.ms_medio)} sub={`95% abaixo de ${ms(r.ms_p95)}`} />
            <Card titulo="Precisaram de reserva" valor={r.com_reserva} sub="o 1º provedor falhou" />
          </div>

          <section className="rounded-2xl border border-gray-200 bg-white p-4">
            <h2 className="text-sm font-semibold text-gray-800">Provedores (na ordem da cascata)</h2>
            <ul className="mt-2 divide-y divide-gray-100">
              {['groq', 'gemini', 'claude', 'openai'].map((p) => {
                const st = r.provedores.find((x) => x.provedor === p);
                const falhas = st ? Object.entries(st.falhas) : [];
                return (
                  <li key={p} className="py-2.5 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="flex items-center gap-1.5 font-medium text-gray-900 min-w-[90px]">
                      {d.configurados[p]
                        ? <CheckCircle2 className="w-4 h-4 text-emerald-600" aria-label="chave configurada" />
                        : <XCircle className="w-4 h-4 text-gray-400" aria-label="sem chave" />}
                      {NOME[p]}
                    </span>
                    <span className="text-xs text-gray-500 break-all">{d.modelos[p]}</span>
                    <span className="text-sm text-gray-700">
                      {st ? `${st.respondeu}/${st.tentativas} respondidas · ${ms(st.ms_medio)}` : (d.configurados[p] ? 'sem uso no período' : 'sem chave')}
                    </span>
                    {falhas.length > 0 && (
                      <span className="text-xs text-amber-700">
                        {falhas.map(([k, v]) => `${v} ${rotRes(k)}`).join(' · ')}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white p-4">
            <h2 className="text-sm font-semibold text-gray-800">Onde a IA foi usada</h2>
            {r.origens.length === 0 ? <p className="text-sm text-gray-500 mt-2">Nenhum uso no período.</p> : (
              <ul className="mt-2 divide-y divide-gray-100">
                {r.origens.map((o) => (
                  <li key={o.origem} className="py-2 flex justify-between gap-3 text-sm">
                    <span className="text-gray-800 break-words min-w-0">{rotOrigem(o.origem)}</span>
                    <span className="text-gray-600 shrink-0">{o.chamadas}{o.falhas ? ` · ${o.falhas} sem resposta` : ''}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white p-4">
            <h2 className="text-sm font-semibold text-gray-800">Últimos pedidos</h2>
            {d.recentes.length === 0 ? <p className="text-sm text-gray-500 mt-2">Nenhum pedido registrado.</p> : (
              <ul className="mt-2 divide-y divide-gray-100">
                {d.recentes.map((x) => (
                  <li key={x.id} className="py-2 text-sm">
                    <div className="flex flex-wrap items-baseline gap-x-3">
                      <span className="text-gray-900">{fmtDataHora(x.ts)}</span>
                      <span className="text-gray-600">{rotOrigem(x.origem)}</span>
                      <span className={x.sucesso ? 'text-emerald-700' : 'text-red-700'}>
                        {x.sucesso ? `${NOME[x.provedor] || x.provedor} · ${ms(x.ms_total)}` : 'sem resposta'}
                      </span>
                    </div>
                    {(x.tentativas || []).length > 1 && (
                      <div className="text-xs text-gray-500 mt-0.5 break-words">
                        {(x.tentativas || []).map((t) => `${NOME[t.provedor] || t.provedor}: ${rotRes(t.resultado)} (${ms(t.ms)})`).join(' → ')}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
          <p className="text-xs text-gray-500">
            Os registros guardam só provedor, modelo, tempo, resultado e o tamanho do texto, e somem sozinhos após {d.retencao_dias} dias.
          </p>
        </>
      )}
    </div>
  );
}
