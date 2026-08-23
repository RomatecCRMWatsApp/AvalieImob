// @module components/dashboard/inferencia/InferenciaWizard — tratamento científico em 5 abas.
//
// Amostra · Especificação · Diagnóstico · Resultado · Valor (MD §10).
// Recálculo por BOTÃO EXPLÍCITO — nunca a cada tecla: estimar é ato do avaliador.
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Sigma, Play, Save, Loader2, Lock, FileText, Download, Plus, Trash2,
  AlertTriangle, CheckCircle2, XCircle, ArrowLeft, Copy,
} from 'lucide-react';
import { BrandSpinner } from '../../brand/BrandSpinner';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { useToast } from '../../../hooks/use-toast';
import { inferenciaAPI } from '../../../lib/api';

const VERDE = '#0C3320';
const DOURADO = '#C9A84C';
const ABAS = ['Amostra', 'Especificação', 'Diagnóstico', 'Resultado', 'Valor'];

const GRAU_CLS = {
  III: 'bg-emerald-600', II: 'bg-amber-500', I: 'bg-orange-500', fora: 'bg-red-600',
};

const num = (v, casas = 2) =>
  v == null || Number.isNaN(Number(v)) ? '—'
    : Number(v).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
const brl = (v) => (v == null ? '—' : Number(v).toLocaleString('pt-BR',
  { style: 'currency', currency: 'BRL' }));
const pct = (v, casas = 2) => (v == null ? '—' : `${num(Number(v) * 100, casas)}%`);
const sig = (v) => (v == null ? '—' : (Number(v) * 100 < 1e-4 ? '< 0,0001%' : `${num(Number(v) * 100, 4)}%`));

const Semaforo = ({ ok, label, detalhe }) => (
  <div className={`rounded-xl border p-3 ${
    ok === null ? 'bg-gray-50 border-gray-200'
      : ok ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
    <div className="flex items-center gap-2">
      {ok === null ? <span className="w-4 h-4 rounded-full bg-gray-300" />
        : ok ? <CheckCircle2 className="w-4 h-4 text-emerald-600" />
             : <XCircle className="w-4 h-4 text-red-600" />}
      <span className="text-xs font-semibold text-gray-800">{label}</span>
    </div>
    {detalhe ? <div className="text-[11px] text-gray-600 mt-1 ml-6">{detalhe}</div> : null}
  </div>
);

const Bloco = ({ titulo, children, acao }) => (
  <div className="bg-white rounded-xl border border-gray-200 p-4">
    <div className="flex items-center justify-between gap-2 mb-3">
      <p className="text-xs font-bold uppercase tracking-wide text-gray-500">{titulo}</p>
      {acao}
    </div>
    {children}
  </div>
);

const InferenciaWizard = () => {
  const { id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();

  const [modelo, setModelo] = useState(null);
  const [opcoes, setOpcoes] = useState(null);
  const [loading, setLoading] = useState(true);
  const [aba, setAba] = useState(0);
  const [ocupado, setOcupado] = useState('');

  const load = useCallback(async () => {
    try {
      const [m, o] = await Promise.all([inferenciaAPI.obter(id), inferenciaAPI.opcoes()]);
      setModelo(m);
      setOpcoes(o);
    } catch (e) {
      toast({ title: 'Erro ao carregar o modelo', description: e.response?.data?.detail,
              variant: 'destructive' });
    } finally { setLoading(false); }
  }, [id, toast]);
  useEffect(() => { load(); }, [load]);

  const travado = modelo?.status === 'homologado';
  const r = modelo?.resultado || null;
  const enq = modelo?.enquadramento || r?.enquadramento || null;

  const erro = (e, titulo) => toast({
    title: titulo, description: e.response?.data?.detail || e.message, variant: 'destructive' });

  const estimar = async () => {
    setOcupado('estimar');
    try {
      const m = await inferenciaAPI.estimar(id);
      setModelo(m);
      const g = m.enquadramento || {};
      toast({
        title: `Modelo estimado — Fundamentação ${g.grau_fundamentacao}, Precisão ${g.grau_precisao}`,
        description: g.bloqueios_grau_iii?.length
          ? `${g.bloqueios_grau_iii.length} restrição(ões) ao Grau III — veja a aba Valor.`
          : 'Sem restrições ao Grau III.',
      });
      setAba(2);
    } catch (e) { erro(e, 'Não foi possível estimar'); }
    finally { setOcupado(''); }
  };

  const salvarEspec = async (espec, extras = {}) => {
    setOcupado('espec');
    try {
      setModelo(await inferenciaAPI.especificacao(id, { especificacao: espec, ...extras }));
      toast({ title: 'Especificação salva — estime novamente para atualizar os números.' });
    } catch (e) { erro(e, 'Erro ao salvar'); }
    finally { setOcupado(''); }
  };

  const alternarDado = async (dado, utilizado, motivo) => {
    if (!utilizado && !motivo) {
      const m = window.prompt(`Motivo do descarte de ${dado.dado_id} (vai para o laudo):`);
      if (!m) return;
      motivo = m;
    }
    setOcupado(`dado-${dado.dado_id}`);
    try {
      setModelo(await inferenciaAPI.amostra(id, {
        itens: [{ dado_id: dado.dado_id, utilizado, motivo_descarte: motivo || null }] }));
    } catch (e) { erro(e, 'Erro ao atualizar a amostra'); }
    finally { setOcupado(''); }
  };

  const importar = async () => {
    setOcupado('importar');
    try {
      const res = await inferenciaAPI.importarAmostras(id, {
        categoria: modelo.tipo_imovel === 'rural' ? 'rural' : 'urbano', limite: 200 });
      setModelo(res.modelo);
      toast({ title: `${res.importados} dados importados do banco de amostras` });
    } catch (e) { erro(e, 'Não foi possível importar'); }
    finally { setOcupado(''); }
  };

  const homologar = async () => {
    const itens = opcoes?.normas?.find((n) => n.valor === modelo.norma)?.params?.checklist_manual || [];
    const marcado = {};
    for (const item of itens) {
      if (!window.confirm(`Confirma: ${item}?`)) {
        toast({ title: 'Homologação cancelada', description: `Pendente: ${item}`,
                variant: 'destructive' });
        return;
      }
      marcado[item] = true;
    }
    setOcupado('homologar');
    try {
      setModelo(await inferenciaAPI.homologar(id, { checklist_manual: marcado }));
      toast({ title: 'Modelo homologado — a partir de agora é imutável.' });
    } catch (e) { erro(e, 'Não foi possível homologar'); }
    finally { setOcupado(''); }
  };

  const novaVersao = async () => {
    try {
      const m = await inferenciaAPI.novaVersao(id);
      toast({ title: `Versão ${m.versao} criada` });
      nav(`/dashboard/inferencia/${m.id}`);
    } catch (e) { erro(e, 'Erro ao versionar'); }
  };

  const baixarPdf = async () => {
    setOcupado('pdf');
    const win = window.open('', '_blank');
    try {
      const blob = await inferenciaAPI.pdf(id);
      const url = URL.createObjectURL(blob);
      if (win) win.location.href = url; else window.open(url, '_blank');
    } catch (e) { if (win) win.close(); erro(e, 'Erro ao gerar o laudo'); }
    finally { setOcupado(''); }
  };

  if (loading) return <BrandSpinner label="Carregando modelo..." />;
  if (!modelo) return null;

  return (
    <div className="space-y-5">
      {/* Cabeçalho */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <button onClick={() => nav('/dashboard/inferencia')}
                  className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1 mb-1">
            <ArrowLeft className="w-3.5 h-3.5" /> Modelos
          </button>
          <h1 className="font-display text-2xl font-bold flex items-center gap-2" style={{ color: VERDE }}>
            <Sigma className="w-6 h-6" style={{ color: DOURADO }} /> {modelo.nome}
            {travado && <Lock className="w-4 h-4 text-emerald-600" />}
          </h1>
          <p className="text-xs text-gray-500">
            {modelo.tipo_imovel === 'rural' ? 'Rural' : 'Urbano'} · NBR {modelo.norma} ·
            versão {modelo.versao} · {modelo.status}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {!travado && (
            <Button onClick={estimar} disabled={!!ocupado} style={{ background: VERDE }}
                    className="text-white">
              {ocupado === 'estimar' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                     : <Play className="w-4 h-4 mr-2" />}
              Estimar modelo
            </Button>
          )}
          {r && (
            <Button variant="outline" onClick={baixarPdf} disabled={!!ocupado}>
              <FileText className="w-4 h-4 mr-2" /> Laudo
            </Button>
          )}
          {travado && (
            <Button variant="outline" onClick={novaVersao}>
              <Copy className="w-4 h-4 mr-2" /> Nova versão
            </Button>
          )}
        </div>
      </div>

      {travado && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <strong>Modelo homologado.</strong> Está congelado porque o laudo assinado
          referencia estes números. Para alterar, gere uma nova versão — a anterior
          é preservada.
        </div>
      )}

      {/* Abas */}
      <div className="flex flex-wrap gap-1 border-b border-gray-200">
        {ABAS.map((t, i) => (
          <button key={t} onClick={() => setAba(i)}
                  className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition ${
                    aba === i ? 'border-current' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
                  style={aba === i ? { color: VERDE, borderColor: DOURADO } : undefined}>
            {t}
          </button>
        ))}
      </div>

      {aba === 0 && <AbaAmostra {...{ modelo, travado, ocupado, importar, alternarDado }} />}
      {aba === 1 && <AbaEspecificacao {...{ modelo, opcoes, travado, ocupado, salvarEspec }} />}
      {aba === 2 && <AbaDiagnostico {...{ r, travado, alternarDado, modelo }} />}
      {aba === 3 && <AbaResultado {...{ r }} />}
      {aba === 4 && <AbaValor {...{ r, enq, modelo, travado, ocupado, homologar }} />}
    </div>
  );
};

// ── 1. Amostra ───────────────────────────────────────────────────────────────
const AbaAmostra = ({ modelo, travado, ocupado, importar, alternarDado }) => {
  const linhas = modelo.amostra || [];
  const campos = Object.keys(linhas[0]?.variaveis || {});
  const usados = linhas.filter((l) => l.utilizado !== false).length;

  return (
    <Bloco titulo={`Amostra de mercado — ${usados} utilizados de ${linhas.length}`}
           acao={!travado && (
             <Button size="sm" variant="outline" onClick={importar} disabled={!!ocupado}>
               {ocupado === 'importar' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                       : <Plus className="w-4 h-4 mr-2" />}
               Importar do banco de amostras
             </Button>)}>
      {linhas.length === 0 ? (
        <p className="text-sm text-gray-400 py-6 text-center">
          Nenhum dado ainda. Importe do banco de amostras de mercado para começar.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="text-left px-3 py-2">Dado</th>
                {campos.map((c) => <th key={c} className="text-right px-3 py-2">{c}</th>)}
                <th className="text-left px-3 py-2">Situação</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {linhas.map((l) => {
                const off = l.utilizado === false;
                return (
                  <tr key={l.dado_id} className={`border-t border-gray-100 ${off ? 'opacity-55' : ''}`}>
                    <td className="px-3 py-2 font-medium text-gray-800">{l.dado_id}</td>
                    {campos.map((c) => (
                      <td key={c} className="px-3 py-2 text-right font-mono text-gray-700">
                        {num(l.variaveis?.[c], 2)}
                      </td>
                    ))}
                    <td className="px-3 py-2 text-gray-600">
                      {off ? <span className="text-amber-700">descartado — {l.motivo_descarte}</span>
                           : 'utilizado'}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {!travado && (
                        <Button size="sm" variant="outline"
                                disabled={ocupado === `dado-${l.dado_id}`}
                                onClick={() => alternarDado(l, off, off ? null : undefined)}>
                          {off ? 'Reincluir' : 'Descartar'}
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-[11px] text-gray-400 mt-3">
        O motivo do descarte é obrigatório e vai impresso no laudo, na seção de saneamento
        da amostra.
      </p>
    </Bloco>
  );
};

// ── 2. Especificação ─────────────────────────────────────────────────────────
const AbaEspecificacao = ({ modelo, opcoes, travado, ocupado, salvarEspec }) => {
  const [esp, setEsp] = useState(() => ({
    dependente: modelo.especificacao?.dependente || { campo: 'vu', transformacao: 'identidade' },
    regressores: modelo.especificacao?.regressores || [],
    intercepto: modelo.especificacao?.intercepto !== false,
  }));
  const [aval, setAval] = useState(modelo.avaliando || {});
  const [areaTotal, setAreaTotal] = useState(modelo.area_total_avaliando || '');

  const campos = useMemo(
    () => Object.keys(modelo.amostra?.[0]?.variaveis || {}), [modelo.amostra]);
  const transf = opcoes?.transformacoes || [];

  const setReg = (i, patch) => setEsp((e) => ({
    ...e, regressores: e.regressores.map((r, j) => (j === i ? { ...r, ...patch } : r)) }));
  const addReg = () => setEsp((e) => ({
    ...e,
    regressores: [...e.regressores,
                  { campo: campos[0] || '', transformacao: 'identidade',
                    tipo: 'quantitativa', rotulo: '' }] }));
  const delReg = (i) => setEsp((e) => ({
    ...e, regressores: e.regressores.filter((_, j) => j !== i) }));

  return (
    <div className="space-y-4">
      <Bloco titulo="Variável dependente">
        <div className="flex flex-wrap gap-3">
          <div className="min-w-[200px]">
            <label className="block text-xs text-gray-600 mb-1">Campo</label>
            <select disabled={travado} className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                    value={esp.dependente.campo}
                    onChange={(e) => setEsp((s) => ({ ...s, dependente: { ...s.dependente, campo: e.target.value } }))}>
              {(campos.length ? campos : ['vu']).map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="min-w-[240px]">
            <label className="block text-xs text-gray-600 mb-1">Transformação</label>
            <select disabled={travado} className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                    value={esp.dependente.transformacao}
                    onChange={(e) => setEsp((s) => ({ ...s, dependente: { ...s.dependente, transformacao: e.target.value } }))}>
              {transf.map((t) => <option key={t.valor} value={t.valor}>{t.rotulo}</option>)}
            </select>
          </div>
          <label className="flex items-end gap-2 text-sm text-gray-700 pb-2">
            <input type="checkbox" disabled={travado} checked={esp.intercepto}
                   onChange={(e) => setEsp((s) => ({ ...s, intercepto: e.target.checked }))} />
            Com intercepto
          </label>
        </div>
      </Bloco>

      <Bloco titulo={`Regressores (k = ${esp.regressores.length})`}
             acao={!travado && (
               <Button size="sm" variant="outline" onClick={addReg}>
                 <Plus className="w-4 h-4 mr-1.5" /> Adicionar
               </Button>)}>
        {esp.regressores.length === 0 && (
          <p className="text-sm text-gray-400 py-3">Nenhum regressor. Adicione ao menos um.</p>
        )}
        <div className="space-y-2">
          {esp.regressores.map((r, i) => (
            <div key={i} className="flex flex-wrap items-end gap-2 border border-gray-100 rounded-lg p-2">
              <div className="min-w-[150px] flex-1">
                <label className="block text-[11px] text-gray-500 mb-1">Campo</label>
                <select disabled={travado} className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-lg"
                        value={r.campo} onChange={(e) => setReg(i, { campo: e.target.value })}>
                  {(campos.length ? campos : [r.campo]).map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="min-w-[170px]">
                <label className="block text-[11px] text-gray-500 mb-1">Transformação</label>
                <select disabled={travado} className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-lg"
                        value={r.transformacao}
                        onChange={(e) => setReg(i, { transformacao: e.target.value })}>
                  {transf.map((t) => <option key={t.valor} value={t.valor}>{t.rotulo}</option>)}
                </select>
              </div>
              <div className="min-w-[150px]">
                <label className="block text-[11px] text-gray-500 mb-1">Tipo</label>
                <select disabled={travado} className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-lg"
                        value={r.tipo} onChange={(e) => setReg(i, { tipo: e.target.value })}>
                  {(opcoes?.tipos_variavel || []).map((t) =>
                    <option key={t.valor} value={t.valor}>{t.rotulo}</option>)}
                </select>
              </div>
              <div className="min-w-[110px]">
                <label className="block text-[11px] text-gray-500 mb-1">Rótulo</label>
                <Input disabled={travado} value={r.rotulo || ''} placeholder="AREA"
                       onChange={(e) => setReg(i, { rotulo: e.target.value })} />
              </div>
              {!travado && (
                <Button size="sm" variant="outline" className="text-red-600" onClick={() => delReg(i)}>
                  <Trash2 className="w-4 h-4" />
                </Button>
              )}
            </div>
          ))}
        </div>
      </Bloco>

      <Bloco titulo="Imóvel avaliando">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {esp.regressores.map((r) => (
            <div key={r.campo}>
              <label className="block text-xs text-gray-600 mb-1">{r.rotulo || r.campo}</label>
              <Input disabled={travado} type="number" value={aval[r.campo] ?? ''}
                     onChange={(e) => setAval((a) => ({ ...a, [r.campo]: e.target.value === '' ? '' : Number(e.target.value) }))} />
            </div>
          ))}
          <div>
            <label className="block text-xs text-gray-600 mb-1">Área total (p/ valor total)</label>
            <Input disabled={travado} type="number" value={areaTotal}
                   onChange={(e) => setAreaTotal(e.target.value)} />
          </div>
        </div>
      </Bloco>

      {!travado && (
        <Button onClick={() => salvarEspec(esp, {
          avaliando: aval,
          area_total_avaliando: areaTotal === '' ? null : Number(areaTotal),
        })} disabled={!!ocupado} style={{ background: VERDE }} className="text-white">
          {ocupado === 'espec' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                               : <Save className="w-4 h-4 mr-2" />}
          Salvar especificação
        </Button>
      )}
    </div>
  );
};

// ── 3. Diagnóstico ───────────────────────────────────────────────────────────
const AbaDiagnostico = ({ r, travado, alternarDado, modelo }) => {
  if (!r) return <Bloco titulo="Diagnóstico"><p className="text-sm text-gray-400">
    Estime o modelo para ver os pressupostos.</p></Bloco>;
  const d = r.diagnostico || {};
  const corr = d.correlacao || {};
  const nomes = Object.keys(corr);

  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <Semaforo ok={d.normalidade_ks?.atende} label="Normalidade — KS (Lilliefors)"
                  detalhe={`p = ${num(d.normalidade_ks?.p_valor, 4)}`} />
        <Semaforo ok={d.normalidade_jb?.atende} label="Normalidade — Jarque-Bera"
                  detalhe={`p = ${num(d.normalidade_jb?.p_valor, 4)}`} />
        <Semaforo ok={d.homocedasticidade_bp?.atende} label="Homocedasticidade — Breusch-Pagan"
                  detalhe={`p = ${num(d.homocedasticidade_bp?.p_valor, 4)}`} />
        <Semaforo ok={d.homocedasticidade_white?.atende} label="Homocedasticidade — White"
                  detalhe={`p = ${num(d.homocedasticidade_white?.p_valor, 4)}`} />
        <Semaforo ok={d.durbin_watson?.atende} label="Não-autocorrelação — Durbin-Watson"
                  detalhe={`DW = ${num(d.durbin_watson?.estatistica, 4)} (faixa 1,5–2,5)`} />
        <Semaforo ok={d.vif_ok} label="Multicolinearidade — VIF"
                  detalhe={(d.vif || []).map((v) => `${v.nome} ${num(v.vif, 2)}`).join(' · ') || '—'} />
      </div>

      <Bloco titulo="Aderência dos resíduos padronizados">
        <table className="w-full text-xs">
          <thead className="text-gray-500 uppercase">
            <tr><th className="text-left py-1">Faixa</th>
                <th className="text-right py-1">Observado</th>
                <th className="text-right py-1">Teórico</th></tr>
          </thead>
          <tbody>
            {Object.entries(d.aderencia_residuos || {}).map(([faixa, v]) => (
              <tr key={faixa} className="border-t border-gray-100">
                <td className="py-1.5">±{faixa.replace('.', ',')}σ</td>
                <td className="py-1.5 text-right font-mono">{pct(v.observado, 1)}</td>
                <td className="py-1.5 text-right font-mono text-gray-500">{pct(v.teorico, 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Bloco>

      {nomes.length > 1 && (
        <Bloco titulo="Matriz de correlação">
          <div className="overflow-x-auto">
            <table className="text-xs">
              <thead>
                <tr><th /> {nomes.map((n) => <th key={n} className="px-2 py-1 text-gray-500">{n}</th>)}</tr>
              </thead>
              <tbody>
                {nomes.map((a) => (
                  <tr key={a}>
                    <td className="px-2 py-1 font-medium text-gray-700">{a}</td>
                    {nomes.map((b) => {
                      const v = Number(corr[a]?.[b] ?? 0);
                      const forte = Math.abs(v) >= 0.8 && a !== b;
                      const alpha = Math.min(0.85, Math.abs(v));
                      return (
                        <td key={b} className="px-2 py-1 text-center font-mono"
                            style={{ background: a === b ? '#F3F4F6'
                                       : `rgba(${forte ? '220,38,38' : '12,51,32'},${alpha * 0.22})`,
                                     color: forte ? '#B91C1C' : '#111' }}>
                          {num(v, 2)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(d.pares_correlacionados || []).length > 0 && (
            <p className="text-[11px] text-red-600 mt-2">
              <AlertTriangle className="w-3 h-3 inline mr-1" />
              Correlação forte (|r| ≥ 0,80): {d.pares_correlacionados.map((p) =>
                `${p.a} × ${p.b} = ${num(p.r, 2)}`).join(' · ')}
            </p>
          )}
        </Bloco>
      )}

      <Bloco titulo={`Pontos discrepantes (|resíduo| > 2σ) — ${(d.outliers || []).length}`}>
        {(d.outliers || []).length === 0 ? (
          <p className="text-sm text-gray-400">Nenhum ponto fora de ±2σ.</p>
        ) : (
          <table className="w-full text-xs">
            <thead className="text-gray-500 uppercase">
              <tr><th className="text-left py-1">Dado</th>
                  <th className="text-right py-1">Resíduo padronizado</th>
                  <th className="py-1" /></tr>
            </thead>
            <tbody>
              {d.outliers.map((o) => {
                const dado = (modelo.amostra || []).find((a) => a.dado_id === o.id);
                return (
                  <tr key={o.id} className="border-t border-gray-100">
                    <td className="py-1.5 font-medium">{o.id}</td>
                    <td className="py-1.5 text-right font-mono">{num(o.residuo_padronizado, 3)}</td>
                    <td className="py-1.5 text-right">
                      {!travado && dado && (
                        <Button size="sm" variant="outline"
                                onClick={() => alternarDado(dado, false, undefined)}>
                          Descartar
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Bloco>

      {Object.keys(modelo.graficos || {}).length > 0 && (
        <Bloco titulo="Gráficos de diagnóstico">
          <div className="grid sm:grid-cols-2 gap-3">
            {Object.entries(modelo.graficos).map(([k, g]) => (
              <figure key={k}>
                <img alt={g.titulo || k} className="w-full rounded-lg border border-gray-100"
                     src={g.url || (g.b64 ? `data:image/png;base64,${g.b64}` : '')} />
                <figcaption className="text-[11px] text-gray-500 mt-1">{g.titulo || k}</figcaption>
              </figure>
            ))}
          </div>
        </Bloco>
      )}
    </div>
  );
};

// ── 4. Resultado ─────────────────────────────────────────────────────────────
const AbaResultado = ({ r }) => {
  if (!r) return <Bloco titulo="Resultado"><p className="text-sm text-gray-400">
    Estime o modelo para ver os coeficientes.</p></Bloco>;
  return (
    <div className="space-y-4">
      <Bloco titulo="Regressores">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="text-left px-3 py-2">Regressor</th>
                <th className="text-right px-3 py-2">Coeficiente</th>
                <th className="text-right px-3 py-2">Erro-padrão</th>
                <th className="text-right px-3 py-2">t</th>
                <th className="text-right px-3 py-2">Significância</th>
              </tr>
            </thead>
            <tbody>
              {(r.regressores || []).map((g) => (
                <tr key={g.nome} className="border-t border-gray-100">
                  <td className="px-3 py-2 font-medium text-gray-800">{g.nome}</td>
                  <td className="px-3 py-2 text-right font-mono">{num(g.coeficiente, 6)}</td>
                  <td className="px-3 py-2 text-right font-mono">{num(g.erro_padrao, 6)}</td>
                  <td className="px-3 py-2 text-right font-mono">{num(g.t, 4)}</td>
                  <td className={`px-3 py-2 text-right font-mono ${
                    !g.eh_intercepto && g.significancia > 0.10 ? 'text-red-600 font-semibold' : ''}`}>
                    {sig(g.significancia)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Bloco>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[['n', r.n], ['k', r.k], ['Graus de liberdade', r.graus_liberdade],
          ['R²', num(r.r2, 4)], ['R² ajustado', num(r.r2_ajustado, 4)],
          ['Erro-padrão', num(r.erro_padrao_estimativa, 6)],
          ['F', num(r.f, 3)], ['Significância de F', sig(r.signif_f)]].map(([k, v]) => (
          <div key={k} className="bg-white rounded-xl border border-gray-200 p-3">
            <div className="text-[11px] text-gray-500 uppercase tracking-wide">{k}</div>
            <div className="text-lg font-bold" style={{ color: VERDE }}>{v}</div>
          </div>
        ))}
      </div>

      <Bloco titulo="Equação estimada">
        <code className="block text-xs bg-gray-50 rounded-lg p-3 font-mono text-gray-800 break-all">
          {r.equacao}
        </code>
      </Bloco>
    </div>
  );
};

// ── 5. Valor ─────────────────────────────────────────────────────────────────
const AbaValor = ({ r, enq, modelo, travado, ocupado, homologar }) => {
  if (!r) return <Bloco titulo="Valor"><p className="text-sm text-gray-400">
    Estime o modelo para ver o valor no ponto.</p></Bloco>;
  const p = r.predicao || {};
  const tot = p.total || {};

  return (
    <div className="space-y-4">
      <div className="rounded-xl border-2 p-5 text-center" style={{ borderColor: DOURADO }}>
        <div className="text-xs uppercase tracking-widest text-gray-500">Valor unitário estimado</div>
        <div className="text-3xl font-bold my-1" style={{ color: VERDE }}>
          {brl(p.valor_central)}<span className="text-base font-normal text-gray-500">/m²</span>
        </div>
        <div className="text-sm text-gray-600">
          IP 80%: {brl(p.ip80?.inferior)} a {brl(p.ip80?.superior)}
          {' '}· amplitude {pct(p.amplitude_ip80)}
        </div>
        {tot.valor_central ? (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <div className="text-xs uppercase tracking-widest text-gray-500">Valor total</div>
            <div className="text-2xl font-bold" style={{ color: VERDE }}>{brl(tot.valor_central)}</div>
            <div className="text-xs text-gray-500">
              IP 80%: {brl(tot.ip80?.inferior)} a {brl(tot.ip80?.superior)}
            </div>
          </div>
        ) : null}
      </div>

      <Bloco titulo="Faixas">
        <table className="w-full text-xs">
          <tbody>
            {[['Intervalo de predição (IP) 80%', p.ip80],
              ['Intervalo de confiança (IC) 80% da média', p.ic80],
              ['Campo de arbítrio (±15%)', p.campo_arbitrio]].map(([rot, f]) => (
              <tr key={rot} className="border-t border-gray-100">
                <td className="py-2 text-gray-700">{rot}</td>
                <td className="py-2 text-right font-mono">{brl(f?.inferior)}</td>
                <td className="py-2 text-right font-mono">{brl(f?.superior)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {p.observacao_destransformacao && (
          <p className="text-[11px] text-gray-500 mt-2 italic">{p.observacao_destransformacao}</p>
        )}
      </Bloco>

      {enq && (
        <Bloco titulo={`Enquadramento — NBR ${modelo.norma}`}>
          <div className="flex flex-wrap gap-2 mb-3">
            <span className={`text-xs font-bold text-white px-3 py-1 rounded ${GRAU_CLS[enq.grau_fundamentacao] || 'bg-gray-400'}`}>
              Fundamentação: Grau {enq.grau_fundamentacao}
            </span>
            <span className={`text-xs font-bold text-white px-3 py-1 rounded ${GRAU_CLS[enq.grau_precisao] || 'bg-gray-400'}`}>
              Precisão: Grau {enq.grau_precisao}
            </span>
          </div>
          <table className="w-full text-xs">
            <thead className="text-gray-500 uppercase">
              <tr><th className="text-left py-1">Item</th><th className="text-left py-1">Grau</th>
                  <th className="text-left py-1">Apuração</th></tr>
            </thead>
            <tbody>
              {(enq.itens || []).map((i) => (
                <tr key={i.item} className="border-t border-gray-100">
                  <td className="py-1.5 pr-3">{i.item}</td>
                  <td className="py-1.5 pr-3 font-semibold">{i.grau}</td>
                  <td className="py-1.5 text-gray-600">{i.detalhe}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {(enq.bloqueios_grau_iii || []).length > 0 ? (
            <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p className="text-xs font-bold text-amber-800 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" /> O que impede o Grau III
              </p>
              <ul className="mt-1.5 space-y-1">
                {enq.bloqueios_grau_iii.map((b) => (
                  <li key={b} className="text-[11px] text-amber-900">• {b}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="mt-3 text-xs text-emerald-700 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> Sem restrições ao Grau III.
            </p>
          )}

          {(r.extrapolacoes || []).length > 0 && (
            <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-[11px] text-red-800">
              <strong>Extrapolação:</strong>{' '}
              {r.extrapolacoes.map((e) =>
                `${e.campo} = ${num(e.valor)} fora do intervalo amostral [${num(e.min)}; ${num(e.max)}]`
              ).join(' · ')}
            </div>
          )}
        </Bloco>
      )}

      {!travado && (
        <div className="flex flex-wrap gap-2">
          <Button onClick={homologar} disabled={!!ocupado} style={{ background: VERDE }}
                  className="text-white">
            {ocupado === 'homologar' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                     : <Lock className="w-4 h-4 mr-2" />}
            Homologar modelo
          </Button>
          <span className="text-[11px] text-gray-500 self-center">
            Ao homologar, o modelo é congelado — o laudo assinado referencia estes números.
          </span>
        </div>
      )}
    </div>
  );
};

export default InferenciaWizard;
