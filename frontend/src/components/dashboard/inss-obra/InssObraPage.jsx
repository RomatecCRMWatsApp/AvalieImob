// @module inss-obra/InssObraPage — INSS de obra (aferição direta no SERO).
// Lista de obras + ficha da obra: dados, áreas, VAU, simulação com memória de
// cálculo, prazos, checklist com comprovantes e valor oficial do SERO.
// A simulação NUNCA é o valor oficial: o oficial é o que o SERO apura no e-CAC.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft, Plus, Trash2, Calculator, FileDown, Eye, Upload, ExternalLink, CheckCircle2,
  AlertTriangle, Clock, HardHat,
} from 'lucide-react';
import { inssObraAPI, clientsAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';
const lbl = 'block text-[11px] font-medium text-gray-500 mb-1';
const inp = 'w-full border rounded-lg px-2.5 py-1.5 text-sm bg-white';

const brl = (v) => (v == null || v === '' ? '—'
  : Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }));
const num = (v, c = 2) => (v == null ? '—'
  : Number(v).toLocaleString('pt-BR', { minimumFractionDigits: c, maximumFractionDigits: c }));
const pct = (v) => (v == null ? '—'
  : `${(Number(v) * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`);
const dataBR = (iso) => (iso ? String(iso).slice(0, 10).split('-').reverse().join('/') : '—');

const STATUS = {
  rascunho: ['Rascunho', 'bg-gray-100 text-gray-700'],
  simulada: ['Simulada', 'bg-amber-100 text-amber-800'],
  regularizada: ['Regularizada', 'bg-emerald-100 text-emerald-800'],
};
const SITUACAO = {
  feito: ['Feito', 'text-emerald-700', CheckCircle2],
  em_dia: ['No prazo', 'text-gray-700', Clock],
  proximo: ['Vence em breve', 'text-amber-700', AlertTriangle],
  vencido: ['Vencido', 'text-red-700', AlertTriangle],
};

const abrirBlob = async (promessa, toast) => {
  const win = window.open('', '_blank');
  try {
    const blob = await promessa;
    const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob], { type: 'application/pdf' }));
    if (win) win.location.href = url; else window.location.href = url;
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch {
    if (win) win.close();
    toast({ title: 'Erro ao abrir o arquivo', variant: 'destructive' });
  }
};

const erroMsg = (e, padrao) => {
  const d = e?.response?.data?.detail;
  return typeof d === 'string' ? d : padrao;
};

const nomeParam = (k, rotuloDest) => {
  if (k.startsWith('equivalencia:')) return `percentual de equivalência (${rotuloDest(k.split(':')[1]).toLowerCase()})`;
  return { aliquotas: 'divisão das alíquotas por código de receita', usinado: 'percentual do usinado por UF' }[k] || k;
};

function Field({ label, value, onChange, type = 'text', placeholder, className = '' }) {
  return (
    <div className={className}>
      <label className={lbl}>{label}</label>
      <input className={inp} type={type} value={value ?? ''} placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function Select({ label, value, onChange, opcoes, className = '' }) {
  return (
    <div className={className}>
      {label && <label className={lbl}>{label}</label>}
      <select className={inp} value={value ?? ''} onChange={(e) => onChange(e.target.value)}>
        {opcoes.map((o) => <option key={o.valor} value={o.valor}>{o.rotulo}</option>)}
      </select>
    </div>
  );
}

function Card({ titulo, children, extra }) {
  return (
    <section className="bg-white rounded-xl border p-4 sm:p-5">
      <div className="flex items-center justify-between gap-2 mb-3">
        <h2 className="font-semibold text-[15px]" style={{ color: GREEN }}>{titulo}</h2>
        {extra}
      </div>
      {children}
    </section>
  );
}

// ── Lista ────────────────────────────────────────────────────────────────────
function Lista() {
  const nav = useNavigate();
  const { toast } = useToast();
  const [obras, setObras] = useState(null);

  const carregar = useCallback(async () => {
    try { setObras(await inssObraAPI.listar()); } catch { setObras([]); }
  }, []);
  useEffect(() => { carregar(); }, [carregar]);

  const nova = async () => {
    try {
      const o = await inssObraAPI.criar({ responsavel: 'PF', uf: 'MA' });
      nav(`/dashboard/inss-obra/${o.id}`);
    } catch (e) { toast({ title: erroMsg(e, 'Erro ao criar'), variant: 'destructive' }); }
  };
  const excluir = async (o) => {
    if (!window.confirm(`Excluir a obra ${o.numero}?`)) return;
    await inssObraAPI.excluir(o.id);
    carregar();
  };

  return (
    <div className="p-4 sm:p-6 pr-9 sm:pr-12 max-w-6xl mx-auto space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-bold" style={{ color: GREEN }}>INSS de Obra</h1>
          <p className="text-sm text-gray-500">
            Simule a aferição do SERO, acompanhe os prazos e guarde os comprovantes até a certidão da obra.
          </p>
        </div>
        <button onClick={nova} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-medium"
          style={{ background: GREEN }}>
          <Plus size={16} /> Nova obra
        </button>
      </div>
      {obras === null ? <BrandSpinner label="Carregando" /> : obras.length === 0 ? (
        <div className="bg-white border rounded-xl p-8 text-center text-gray-500">
          <HardHat className="mx-auto mb-2" style={{ color: GOLD }} />
          Nenhuma obra ainda. Clique em <b>Nova obra</b> para simular o INSS de um cliente.
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {obras.map((o) => {
            const [st, cls] = STATUS[o.status] || STATUS.rascunho;
            const tot = o.ultima_simulacao?.resultado?.total;
            return (
              <div key={o.id} className="bg-white border rounded-xl p-4 flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-xs text-gray-500">{o.numero}</div>
                    <div className="font-semibold">{o.cliente_nome || 'Cliente não informado'}</div>
                    <div className="text-xs text-gray-500">{o.municipio || '—'}/{o.uf || '—'} · CNO {o.cno || 'a inscrever'}</div>
                  </div>
                  <span className={`text-[11px] px-2 py-0.5 rounded-full ${cls}`}>{st}</span>
                </div>
                <div className="text-sm">INSS estimado: <b style={{ color: GREEN }}>{tot ? brl(tot) : '—'}</b></div>
                <div className="text-xs text-gray-500">
                  Checklist {o.checklist_progresso?.feitos || 0}/{o.checklist_progresso?.total || 0}
                </div>
                <div className="flex gap-2 mt-1">
                  <button onClick={() => nav(`/dashboard/inss-obra/${o.id}`)}
                    className="flex-1 px-3 py-1.5 rounded-lg text-white text-sm" style={{ background: GREEN }}>Abrir</button>
                  {tot && (
                    <button onClick={() => abrirBlob(inssObraAPI.pdf(o.id), toast)} title="PDF da simulação"
                      className="px-3 py-1.5 rounded-lg border text-sm"><FileDown size={15} /></button>
                  )}
                  <button onClick={() => excluir(o)} title="Excluir" className="px-3 py-1.5 rounded-lg border text-sm text-red-600">
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Ficha da obra ────────────────────────────────────────────────────────────
const AREA_VAZIA = { descricao: '', destinacao: 'residencial_unifamiliar', categoria: 'obra_nova',
  tipo: 'alvenaria', classe: 'principal', area_m2: '' };

function Ficha({ id }) {
  const nav = useNavigate();
  const { toast } = useToast();
  const [obra, setObra] = useState(null);
  const [op, setOp] = useState(null);
  const [clientes, setClientes] = useState([]);
  const [simulando, setSimulando] = useState(false);
  const [salvo, setSalvo] = useState(true);
  const [oficial, setOficial] = useState('');
  const timer = useRef(null);
  const pendente = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const [o, opc] = await Promise.all([inssObraAPI.obter(id), inssObraAPI.opcoes()]);
        setObra(o); setOp(opc);
        setOficial(o.sero_oficial?.total ? num(o.sero_oficial.total) : '');
      } catch { toast({ title: 'Obra não encontrada', variant: 'destructive' }); nav('/dashboard/inss-obra'); }
      try { const c = await clientsAPI.list(); setClientes(Array.isArray(c) ? c : []); } catch { /* opcional */ }
    })();
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const flush = useCallback(async () => {
    if (timer.current) { clearTimeout(timer.current); timer.current = null; }
    const campos = pendente.current;
    if (!campos) return;
    pendente.current = null;
    try {
      const o = await inssObraAPI.atualizar(id, campos);
      setObra((cur) => ({ ...o, ...(pendente.current || {}), areas: cur?.areas ?? o.areas, vau: cur?.vau ?? o.vau }));
      setSalvo(true);
    } catch (e) { toast({ title: erroMsg(e, 'Erro ao salvar'), variant: 'destructive' }); }
  }, [id, toast]);

  useEffect(() => () => { flush(); }, [flush]);

  const set = (campos) => {
    setObra((o) => ({ ...o, ...campos }));
    pendente.current = { ...(pendente.current || {}), ...campos };
    setSalvo(false);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(flush, 1000);
  };

  if (!obra || !op) return <div className="p-6"><BrandSpinner label="Carregando" /></div>;

  const areas = obra.areas || [];
  const setArea = (i, campo, v) => set({ areas: areas.map((a, j) => (j === i ? { ...a, [campo]: v } : a)) });
  const destUsadas = [...new Set(areas.map((a) => a.destinacao))];
  const rotuloDest = (v) => op.destinacoes.find((d) => d.valor === v)?.rotulo || v;

  const selCliente = (cid) => {
    const c = clientes.find((x) => String(x.id) === String(cid));
    if (!c) return;
    set({ cliente_id: c.id, cliente_nome: c.name || c.nome || '', cpf_cnpj: c.doc || c.cpf || c.cnpj || '',
      telefone: c.phone || c.telefone || '' });
  };

  const simularAgora = async () => {
    await flush();
    setSimulando(true);
    try {
      await inssObraAPI.simular(id);
      setObra(await inssObraAPI.obter(id));
      toast({ title: 'Simulação concluída' });
    } catch (e) {
      toast({ title: erroMsg(e, 'Erro ao simular'), variant: 'destructive' });
    } finally { setSimulando(false); }
  };

  const enviar = async (chave, file) => {
    if (!file) return;
    try { setObra(await inssObraAPI.enviarComprovante(id, chave, file)); toast({ title: 'Comprovante salvo' }); }
    catch (e) { toast({ title: erroMsg(e, 'Erro no envio'), variant: 'destructive' }); }
  };
  const remover = async (chave) => {
    if (!window.confirm('Remover este comprovante?')) return;
    setObra(await inssObraAPI.removerComprovante(id, chave));
  };
  const salvarOficial = async () => {
    try {
      setObra(await inssObraAPI.seroOficial(id, { total: oficial }));
      toast({ title: oficial ? 'Valor oficial registrado' : 'Valor oficial removido' });
    } catch (e) { toast({ title: erroMsg(e, 'Valor inválido'), variant: 'destructive' }); }
  };

  const sim = obra.ultima_simulacao?.resultado;
  const [stTxt, stCls] = STATUS[obra.status] || STATUS.rascunho;
  const difOficial = sim && obra.sero_oficial?.total
    ? Number(obra.sero_oficial.total) - Number(sim.total) : null;

  return (
    <div className="p-4 sm:p-6 pr-9 sm:pr-12 max-w-6xl mx-auto space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button onClick={async () => { await flush(); nav('/dashboard/inss-obra'); }} className="p-2 rounded-lg border">
            <ArrowLeft size={16} />
          </button>
          <div>
            <div className="text-xs text-gray-500">{obra.numero} · {salvo ? 'salvo' : 'salvando…'}</div>
            <h1 className="text-xl font-display font-bold" style={{ color: GREEN }}>
              {obra.cliente_nome || 'Nova obra'}
            </h1>
          </div>
          <span className={`text-[11px] px-2 py-0.5 rounded-full ${stCls}`}>{stTxt}</span>
        </div>
      </div>

      <Card titulo="1. Cliente e obra">
        <div className="grid gap-3 sm:grid-cols-4">
          {clientes.length > 0 && (
            <div className="sm:col-span-4">
              <label className={lbl}>Puxar do cadastro de clientes</label>
              <select className={inp} value={obra.cliente_id || ''} onChange={(e) => selCliente(e.target.value)}>
                <option value="">— selecionar —</option>
                {clientes.map((c) => <option key={c.id} value={c.id}>{c.name || c.nome}</option>)}
              </select>
            </div>
          )}
          <Field className="sm:col-span-2" label="Responsável pela obra (nome)" value={obra.cliente_nome}
            onChange={(v) => set({ cliente_nome: v })} />
          <Field label="CPF/CNPJ" value={obra.cpf_cnpj} onChange={(v) => set({ cpf_cnpj: v })} />
          <Select label="Tipo de responsável" value={obra.responsavel || 'PF'} onChange={(v) => set({ responsavel: v })}
            opcoes={[{ valor: 'PF', rotulo: 'Pessoa física' }, { valor: 'PJ', rotulo: 'Pessoa jurídica' }]} />
          <Field className="sm:col-span-2" label="Endereço da obra" value={obra.endereco} onChange={(v) => set({ endereco: v })} />
          <Field label="Município" value={obra.municipio} onChange={(v) => set({ municipio: v })} />
          <Select label="UF" value={obra.uf || 'MA'} onChange={(v) => set({ uf: v })}
            opcoes={op.ufs.map((u) => ({ valor: u, rotulo: u }))} />
          <Field label="CNO (se já inscrita)" value={obra.cno} onChange={(v) => set({ cno: v })} placeholder="00.000.00000/00" />
          <Field label="Alvará nº" value={obra.alvara} onChange={(v) => set({ alvara: v })} />
          <Field label="ART/RRT/TRT nº" value={obra.art_rrt} onChange={(v) => set({ art_rrt: v })} />
          <Field label="Telefone" value={obra.telefone} onChange={(v) => set({ telefone: v })} />
          <Field label="Início da obra" type="date" value={obra.data_inicio} onChange={(v) => set({ data_inicio: v })} />
          <Field label="Fim da obra (habite-se ou conclusão)" type="date" value={obra.data_fim} onChange={(v) => set({ data_fim: v })} />
          <Field label="Data da aferição (vazio = hoje)" type="date" value={obra.data_afericao}
            onChange={(v) => set({ data_afericao: v })} />
          <label className="flex items-center gap-2 text-sm mt-5">
            <input type="checkbox" checked={!!obra.usinado} onChange={(e) => set({ usinado: e.target.checked })} />
            Usou concreto/argamassa usinada ou massa asfáltica
          </label>
        </div>
      </Card>

      <Card titulo="2. Áreas do projeto"
        extra={<button onClick={() => set({ areas: [...areas, { ...AREA_VAZIA }] })}
          className="inline-flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg border"><Plus size={14} /> Área</button>}>
        <p className="text-xs text-gray-500 mb-3">
          Principal = corpo da construção (inclui varanda, terraço, garagem dentro da projeção). Complementar =
          piscina, quadra, garagem fora da projeção. Lance cada categoria (obra nova, acréscimo, reforma, demolição) em linha própria.
        </p>
        {areas.length === 0 && <div className="text-sm text-gray-500">Nenhuma área. Clique em “+ Área”.</div>}
        <div className="space-y-2">
          {areas.map((a, i) => (
            <div key={i} className="flex gap-2 items-end border rounded-lg p-2">
              <div className="flex-1 grid gap-2 sm:grid-cols-12">
                <Field className="sm:col-span-2" label="Descrição" value={a.descricao} placeholder="Casa, piscina…"
                  onChange={(v) => setArea(i, 'descricao', v)} />
                <Select className="sm:col-span-3" label="Destinação" value={a.destinacao} opcoes={op.destinacoes}
                  onChange={(v) => setArea(i, 'destinacao', v)} />
                <Select className="sm:col-span-2" label="Categoria" value={a.categoria} opcoes={op.categorias}
                  onChange={(v) => setArea(i, 'categoria', v)} />
                <Select className="sm:col-span-2" label="Material" value={a.tipo} opcoes={op.tipos}
                  onChange={(v) => setArea(i, 'tipo', v)} />
                <Select className="sm:col-span-2" label="Área" value={a.classe} opcoes={op.classes_area}
                  onChange={(v) => setArea(i, 'classe', v)} />
                <Field className="sm:col-span-1" label="m²" value={a.area_m2} onChange={(v) => setArea(i, 'area_m2', v)} />
              </div>
              <button onClick={() => set({ areas: areas.filter((_, j) => j !== i) })}
                className="p-2 rounded-lg border text-red-600" title="Remover">
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </div>
      </Card>

      <Card titulo="3. VAU do mês (R$/m²)">
        <p className="text-xs text-gray-500 mb-3">
          O VAU é publicado pela Receita dentro do SERO (e-CAC → SERO → Consultar Tabela VAU). Copie o valor da sua UF
          e destinação no mês da aferição. O sistema não substitui o VAU pelo CUB.
        </p>
        {destUsadas.length === 0 ? <div className="text-sm text-gray-500">Cadastre as áreas primeiro.</div> : (
          <div className="grid gap-3 sm:grid-cols-3">
            {destUsadas.map((d) => (
              <Field key={d} label={`VAU — ${rotuloDest(d)}`} value={(obra.vau || {})[d]}
                onChange={(v) => set({ vau: { ...(obra.vau || {}), [d]: v } })} placeholder="ex.: 2.345,67" />
            ))}
            <Field label="Competência do VAU" value={obra.vau_competencia} placeholder="11/2026"
              onChange={(v) => set({ vau_competencia: v })} />
            <Field className="sm:col-span-2" label="Fonte (onde consultou)" value={obra.vau_fonte}
              placeholder="SERO — Consultar Tabela VAU" onChange={(v) => set({ vau_fonte: v })} />
          </div>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <button onClick={simularAgora} disabled={simulando}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-medium disabled:opacity-60"
            style={{ background: GREEN }}>
            <Calculator size={16} /> {simulando ? 'Calculando…' : 'Simular INSS'}
          </button>
          {sim && (
            <button onClick={() => abrirBlob(inssObraAPI.pdf(id), toast)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border text-sm">
              <FileDown size={16} /> PDF para o cliente
            </button>
          )}
        </div>
      </Card>

      {sim && (
        <Card titulo="4. Resultado da simulação">
          <div className="rounded-lg p-3 mb-3 text-sm bg-red-50 text-red-800 border border-red-200">{sim.aviso}</div>
          <div className="grid gap-3 sm:grid-cols-4 mb-4">
            {[['Custo da obra (COD)', brl(sim.cod_total)], ['Mão de obra (RMT)', brl(sim.rmt_total)],
              ['Base de cálculo', brl(sim.base_calculo)], ['INSS estimado', brl(sim.total)]].map(([k, v], i) => (
              <div key={k} className={`rounded-lg border p-3 ${i === 3 ? 'bg-amber-50 border-amber-300' : ''}`}>
                <div className="text-[11px] text-gray-500">{k}</div>
                <div className="text-lg font-bold" style={{ color: GREEN }}>{v}</div>
              </div>
            ))}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs min-w-[760px]">
              <thead><tr className="text-white" style={{ background: GREEN }}>
                {['Área', 'm²', 'Redução', 'm² cálculo', 'VAU', 'COD', '% M.O.', '% cat.', 'F. social', 'RMT'].map((h) =>
                  <th key={h} className="px-2 py-1.5 text-left font-medium">{h}</th>)}
              </tr></thead>
              <tbody>
                {sim.linhas.map((l) => (
                  <tr key={l.n} className="border-b">
                    <td className="px-2 py-1.5">{l.descricao || rotuloDest(l.destinacao)}<div className="text-gray-500">
                      {op.categorias.find((c) => c.valor === l.categoria)?.rotulo} · {op.classes_area.find((c) => c.valor === l.classe)?.rotulo}</div></td>
                    <td className="px-2">{num(l.area_m2)}</td><td className="px-2">{pct(l.reducao_area)}</td>
                    <td className="px-2">{num(l.area_calculo)}</td><td className="px-2">{num(l.vau)}</td>
                    <td className="px-2">{num(l.cod)}</td><td className="px-2">{pct(l.pct_mao_de_obra)}</td>
                    <td className="px-2">{pct(Number(l.pct_categoria) * Number(l.pct_destinacao))}</td>
                    <td className="px-2">{pct(l.fator_social)}</td><td className="px-2 font-semibold">{num(l.rmt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 mt-4 text-sm">
            <div className="space-y-1">
              <div>Meses da obra: <b>{sim.decadencia.meses_total}</b> · decadentes: <b>{sim.decadencia.meses_decadentes}</b></div>
              <div>RMT não decadente: <b>{brl(sim.rmt_nao_decadente)}</b></div>
              <div>Crédito do usinado: <b>{sim.usinado.aplicado ? brl(sim.usinado.credito) : 'não informado'}</b></div>
            </div>
            <table className="text-xs">
              <tbody>
                {sim.debitos.map((d) => (
                  <tr key={d.codigo} className="border-b"><td className="py-1">{d.codigo_receita ? <span className="text-gray-500">{d.codigo_receita} · </span> : null}{d.nome}</td>
                    <td className="text-right px-2">{pct(d.aliquota)}</td><td className="text-right">{brl(d.valor)}</td></tr>
                ))}
                <tr className="font-bold"><td className="py-1">Total</td><td className="text-right px-2">36,8%</td>
                  <td className="text-right">{brl(sim.total)}</td></tr>
              </tbody>
            </table>
          </div>
          {(sim.alertas || []).length > 0 && (
            <ul className="mt-3 text-xs text-amber-800 bg-amber-50 rounded-lg p-3 list-disc pl-5 space-y-1">
              {sim.alertas.map((a) => <li key={a}>{a}</li>)}
            </ul>
          )}
          {(sim.parametros_a_conferir || []).length > 0 && (
            <p className="mt-2 text-[11px] text-gray-500">
              Parâmetros ainda em conferência com o PDF oficial do Manual: {sim.parametros_a_conferir.map((k) => nomeParam(k, rotuloDest)).join(', ')}.
            </p>
          )}
          {obra.simulacoes_qtd > 1 && (
            <p className="mt-2 text-[11px] text-gray-500">{obra.simulacoes_qtd} simulações guardadas (a mais recente é a exibida).</p>
          )}
        </Card>
      )}

      <Card titulo="5. Prazos">
        {(obra.prazos || []).length === 0 ? (
          <div className="text-sm text-gray-500">Informe a data de início da obra para ver o prazo do CNO.</div>
        ) : (
          <div className="space-y-2">
            {obra.prazos.map((p) => {
              const [txt, cls, Icon] = SITUACAO[p.situacao] || SITUACAO.em_dia;
              return (
                <div key={p.chave} className="flex flex-wrap items-center justify-between gap-2 border rounded-lg p-3 text-sm">
                  <div><b>{p.titulo}</b><div className="text-xs text-gray-500">{p.base}</div></div>
                  <div className={`flex items-center gap-1.5 ${cls}`}><Icon size={15} /> {dataBR(p.prazo)} · {txt}</div>
                </div>
              );
            })}
            <p className="text-[11px] text-gray-500">Feriados municipais e móveis não são considerados — confira no calendário local.</p>
          </div>
        )}
      </Card>

      <Card titulo="6. Checklist e comprovantes"
        extra={<span className="text-xs text-gray-500">{obra.checklist_progresso?.feitos}/{obra.checklist_progresso?.total}</span>}>
        <div className="space-y-2">
          {(obra.checklist_itens || []).map((c) => (
            <div key={c.chave} className="flex flex-wrap items-center justify-between gap-2 border rounded-lg p-3">
              <div className="min-w-0">
                <div className="text-sm font-medium flex items-center gap-1.5">
                  {c.status === 'ok' ? <CheckCircle2 size={15} className="text-emerald-600" /> : <Clock size={15} className="text-gray-400" />}
                  {c.titulo} {c.obrigatorio && <span className="text-[10px] text-gray-400">(necessário)</span>}
                </div>
                <div className="text-xs text-gray-500">{c.status === 'ok' ? `${c.arquivo} · ${dataBR(c.enviado_em)}` : c.dica}</div>
              </div>
              <div className="flex gap-2">
                {c.link && (
                  <a href={c.link} target="_blank" rel="noreferrer" className="px-2.5 py-1.5 rounded-lg border text-xs inline-flex items-center gap-1">
                    <ExternalLink size={13} /> e-CAC
                  </a>
                )}
                {c.status === 'ok' && (
                  <button onClick={() => abrirBlob(inssObraAPI.comprovante(id, c.chave), toast)}
                    className="px-2.5 py-1.5 rounded-lg border text-xs"><Eye size={13} /></button>
                )}
                <label className="px-2.5 py-1.5 rounded-lg border text-xs inline-flex items-center gap-1 cursor-pointer">
                  <Upload size={13} /> {c.status === 'ok' ? 'Trocar' : 'Enviar'}
                  <input type="file" accept=".pdf,image/*,.xml" className="hidden"
                    onChange={(e) => { enviar(c.chave, e.target.files?.[0]); e.target.value = ''; }} />
                </label>
                {c.status === 'ok' && (
                  <button onClick={() => remover(c.chave)} className="px-2.5 py-1.5 rounded-lg border text-xs text-red-600">
                    <Trash2 size={13} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card titulo="7. Valor oficial do SERO">
        <p className="text-xs text-gray-500 mb-3">
          Depois de aferir no e-CAC, informe o total da memória de cálculo do SERO para comparar com a simulação.
        </p>
        <div className="flex flex-wrap items-end gap-2">
          <Field label="Total apurado pelo SERO (R$)" value={oficial} onChange={setOficial} placeholder="ex.: 10.380,15" />
          <button onClick={salvarOficial} className="px-4 py-2 rounded-lg text-white text-sm" style={{ background: GREEN }}>Registrar</button>
        </div>
        {difOficial != null && (
          <p className="mt-3 text-sm">
            Oficial {brl(obra.sero_oficial.total)} × simulado {brl(sim.total)} → diferença{' '}
            <b className={Math.abs(difOficial) < 1 ? 'text-emerald-700' : 'text-amber-700'}>{brl(difOficial)}</b>
            {Math.abs(difOficial) >= 1 && ' — confira o VAU e as áreas informadas.'}
          </p>
        )}
      </Card>
    </div>
  );
}

export default function InssObraPage() {
  const { id } = useParams();
  return id ? <Ficha id={id} /> : <Lista />;
}
