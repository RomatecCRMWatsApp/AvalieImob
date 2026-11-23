// @module receita-rtc/SimuladorCbsIbsModal — estimativa de CBS/IBS sobre os honorários do recibo,
// pelas calculadoras oficiais da Receita Federal. A conta configura regime e códigos (sem padrão);
// a data da operação é sempre informada pelo usuário (nunca "hoje" automático).
import React, { useEffect, useState } from 'react';
import { X, Calculator, Loader2, AlertTriangle, Info, Settings2, History, CheckCircle2 } from 'lucide-react';
import { Button } from '../../ui/button';
import { receitaRtcAPI } from '../../../lib/api';
import { fmtDataHora } from '../../../utils/datasServidor';

const UFS = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR',
  'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO'];
const ROTULO_FALTA = {
  regime: 'regime tributário', uf: 'UF', codigo_municipio: 'município de prestação', nbs: 'NBS do serviço',
  cst: 'CST', cClassTrib: 'cClassTrib', confirmado_com_contador: 'confirmação com o contador',
  'simples.cAtivSN': 'atividade do Simples', 'simples.pIBSSN': 'alíquota efetiva do IBS no Simples',
  'simples.pCBSSN': 'alíquota efetiva da CBS no Simples',
};
const ORIGEM = { CALCULADORA: 'Calculadora da Receita', TABELA_INTERNA: 'Tabela interna (informada manualmente)' };
const TRIBUTO = { CBS: 'CBS', IBS_UF: 'IBS estadual', IBS_MUN: 'IBS municipal' };
const SITUACAO = {
  calculado: { txt: 'Calculado', cls: 'text-emerald-700' },
  calculado_com_erros: { txt: 'Calculado em parte', cls: 'text-amber-700' },
  nao_calculado: { txt: 'Não calculado', cls: 'text-red-700' },
};

const brl = (s) => (s == null || s === '' ? '—'
  : 'R$ ' + Number(s).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const pct = (s) => (s == null || s === '' ? '—' : `${String(s).replace('.', ',')}%`);
const dataBr = (iso) => (iso ? iso.split('-').reverse().join('/') : '—');
const msgErro = (e, padrao) => {
  const d = e?.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (d?.mensagem) return d.mensagem;
  return padrao;
};

function Campo({ rotulo, dica, children }) {
  return (
    <label className="block text-sm min-w-0">
      <span className="font-medium text-gray-800">{rotulo}</span>
      {dica && <span className="block text-xs text-gray-500 mt-0.5">{dica}</span>}
      <div className="mt-1">{children}</div>
    </label>
  );
}

const inputCls = 'w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm min-h-[44px] focus:outline-none focus:ring-2 focus:ring-emerald-600';

function ConfigConta({ inicial, onSalvo }) {
  const [f, setF] = useState(() => ({
    regime: '', uf: '', codigo_municipio: '', nome_municipio: '', nbs: '', cst: '', cClassTrib: '',
    descricao_classificacao: '', confirmado_com_contador: false,
    ...(inicial || {}),
    simples: { crt: '1', cAtivSN: '', pIBSSN: '', pCBSSN: '', ...((inicial || {}).simples || {}) },
  }));
  const [municipios, setMunicipios] = useState([]);
  const [ajuda, setAjuda] = useState(null);
  const [buscando, setBuscando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const setSn = (k, v) => setF((x) => ({ ...x, simples: { ...x.simples, [k]: v } }));

  useEffect(() => {
    if (!f.uf) { setMunicipios([]); return; }
    receitaRtcAPI.municipios(f.uf).then((d) => setMunicipios(d.municipios || [])).catch(() => setMunicipios([]));
  }, [f.uf]);

  const consultarNbs = async () => {
    setErro(''); setAjuda(null); setBuscando(true);
    try { setAjuda(await receitaRtcAPI.classificacoes(f.nbs)); }
    catch (e) { setErro(msgErro(e, 'Não foi possível consultar o NBS.')); }
    finally { setBuscando(false); }
  };

  const salvar = async () => {
    setErro(''); setSalvando(true);
    try { onSalvo(await receitaRtcAPI.salvarConfig(f)); }
    catch (e) { setErro(msgErro(e, 'Não foi possível salvar.')); }
    finally { setSalvando(false); }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        Informe os dados da <strong>sua</strong> empresa ou atividade. Não há valor padrão: confirme cada código com o seu contador.
      </p>
      <div className="grid sm:grid-cols-2 gap-3">
        <Campo rotulo="Regime tributário">
          <select className={inputCls} value={f.regime || ''} onChange={(e) => set('regime', e.target.value)}>
            <option value="">Selecione…</option>
            <option value="REGULAR">Regime regular (Lucro Presumido ou Real)</option>
            <option value="SIMPLES">Simples Nacional</option>
          </select>
        </Campo>
        <Campo rotulo="UF de prestação">
          <select className={inputCls} value={f.uf || ''} onChange={(e) => { set('uf', e.target.value); set('codigo_municipio', ''); }}>
            <option value="">Selecione…</option>
            {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </Campo>
        <Campo rotulo="Município de prestação">
          <select className={inputCls} value={f.codigo_municipio || ''} disabled={!municipios.length}
            onChange={(e) => {
              const m = municipios.find((x) => x.codigo === e.target.value);
              set('codigo_municipio', e.target.value); set('nome_municipio', m?.nome || '');
            }}>
            <option value="">{f.uf ? 'Selecione…' : 'Escolha a UF primeiro'}</option>
            {municipios.map((m) => <option key={m.codigo} value={m.codigo}>{m.nome}</option>)}
          </select>
        </Campo>
        <Campo rotulo="NBS do serviço" dica="9 dígitos (Nomenclatura Brasileira de Serviços).">
          <div className="flex gap-2">
            <input className={inputCls} inputMode="numeric" value={f.nbs || ''} onChange={(e) => set('nbs', e.target.value)} />
            <Button type="button" variant="outline" className="min-h-[44px] shrink-0" onClick={consultarNbs}
              disabled={buscando || (f.nbs || '').replace(/\D/g, '').length !== 9}>
              {buscando ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Consultar'}
            </Button>
          </div>
        </Campo>
      </div>

      {ajuda && (
        <div className="rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm">
          <div className="font-medium text-sky-900">{ajuda.descricao || 'NBS não encontrado na tabela oficial.'}</div>
          {ajuda.opcoes?.length > 0 && (
            <>
              <div className="text-xs text-sky-800 mt-2">Classificações que a tabela oficial associa a esse NBS (escolha com o seu contador):</div>
              <ul className="mt-1 space-y-1">
                {ajuda.opcoes.map((o) => (
                  <li key={`${o.cst}-${o.cClassTrib}`}>
                    <button type="button" className="text-left text-sky-900 underline underline-offset-2"
                      onClick={() => { set('cst', o.cst); set('cClassTrib', o.cClassTrib); set('descricao_classificacao', o.descricao || ''); }}>
                      CST {o.cst} · cClassTrib {o.cClassTrib} — {o.descricao}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-3">
        {f.regime !== 'SIMPLES' && (
          <Campo rotulo="CST" dica="3 dígitos.">
            <input className={inputCls} inputMode="numeric" value={f.cst || ''} onChange={(e) => set('cst', e.target.value)} />
          </Campo>
        )}
        <Campo rotulo="cClassTrib" dica="6 dígitos.">
          <input className={inputCls} inputMode="numeric" value={f.cClassTrib || ''} onChange={(e) => set('cClassTrib', e.target.value)} />
        </Campo>
      </div>

      {f.regime === 'SIMPLES' && (
        <div className="rounded-lg border border-gray-200 p-3 space-y-3">
          <div className="text-sm font-medium text-gray-800">Dados do Simples Nacional</div>
          <p className="text-xs text-gray-500">
            A calculadora do Simples só calcula serviço a partir de 2027. As alíquotas efetivas dependem da sua faixa de faturamento: peça ao contador. MEI não é calculado.
          </p>
          <div className="grid sm:grid-cols-2 gap-3">
            <Campo rotulo="Situação">
              <select className={inputCls} value={f.simples.crt} onChange={(e) => setSn('crt', e.target.value)}>
                <option value="1">Simples Nacional</option>
                <option value="2">Simples Nacional, excesso de sublimite</option>
              </select>
            </Campo>
            <Campo rotulo="Código da atividade (cAtivSN)" dica="2 dígitos, ex.: 07 a 14 para serviços.">
              <input className={inputCls} inputMode="numeric" value={f.simples.cAtivSN} onChange={(e) => setSn('cAtivSN', e.target.value)} />
            </Campo>
            <Campo rotulo="Alíquota efetiva do IBS (%)">
              <input className={inputCls} inputMode="decimal" value={f.simples.pIBSSN} onChange={(e) => setSn('pIBSSN', e.target.value)} />
            </Campo>
            <Campo rotulo="Alíquota efetiva da CBS (%)">
              <input className={inputCls} inputMode="decimal" value={f.simples.pCBSSN} onChange={(e) => setSn('pCBSSN', e.target.value)} />
            </Campo>
          </div>
        </div>
      )}

      <label className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
        <input type="checkbox" className="mt-1 h-5 w-5 shrink-0 accent-emerald-700" checked={!!f.confirmado_com_contador}
          onChange={(e) => set('confirmado_com_contador', e.target.checked)} />
        <span>Confirmei o regime e os códigos acima com o meu contador. Sem essa confirmação o simulador fica desativado.</span>
      </label>

      {erro && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{erro}</div>}
      <div className="flex justify-end">
        <Button onClick={salvar} disabled={salvando} className="min-h-[44px] bg-emerald-800 hover:bg-emerald-900 text-white">
          {salvando ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}Salvar dados tributários
        </Button>
      </div>
    </div>
  );
}

function Resultado({ s }) {
  const sit = SITUACAO[s.situacao] || SITUACAO.nao_calculado;
  const item = s.itens?.[0] || {};
  const regular = s.regime === 'REGULAR';
  const erros = [...(s.erros_gerais || []), ...((s.itens || []).flatMap((i) => i.erros || []))];
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className={`text-sm font-semibold ${sit.cls}`}>{sit.txt}</span>
        <span className="text-xs text-gray-500">Data da operação {dataBr(s.data_operacao)} · versão {s.versao_calculadora?.versao_app || '—'}</span>
      </div>
      {s.avisos?.filter((a) => a.startsWith('Estimativa com alíquota')).map((a) => (
        <div key={a} className="flex gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" /> {a}
        </div>
      ))}
      {erros.length > 0 && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 space-y-2">
          {erros.map((e, i) => (
            <div key={i}>
              <div className="font-medium">{e.titulo || e.codigo}</div>
              <div className="text-xs">{e.descricao || e.detalhe}</div>
              {e.codigo && <div className="text-[11px] text-red-600 mt-0.5">Código {e.codigo}</div>}
            </div>
          ))}
        </div>
      )}
      {s.situacao !== 'nao_calculado' && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[320px]">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b">
                <th className="py-2 pr-3 font-medium">Tributo</th>
                <th className="py-2 pr-3 font-medium text-right">Alíquota</th>
                {regular && <th className="py-2 pr-3 font-medium text-right">Efetiva</th>}
                <th className="py-2 font-medium text-right">Valor</th>
              </tr>
            </thead>
            <tbody>
              {regular ? (
                [['CBS', item.cbs], ['IBS estadual', item.ibs_uf], ['IBS municipal', item.ibs_mun]].map(([nome, t]) => (
                  <tr key={nome} className="border-b border-gray-100">
                    <td className="py-2 pr-3 text-gray-900">{nome}{t?.reducao && Number(t.reducao) > 0 ? <span className="block text-[11px] text-gray-500">redução de {pct(t.reducao)}</span> : null}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{pct(t?.aliquota)}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{pct(t?.aliquota_efetiva)}</td>
                    <td className="py-2 text-right tabular-nums">{brl(t?.valor)}</td>
                  </tr>
                ))
              ) : (
                [['CBS', item.cbs?.aliquota, item.cbs?.valor], ['IBS', item.ibs_aliquota, item.ibs]].map(([nome, a, v]) => (
                  <tr key={nome} className="border-b border-gray-100">
                    <td className="py-2 pr-3 text-gray-900">{nome}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{pct(a)}</td>
                    <td className="py-2 text-right tabular-nums">{brl(v)}</td>
                  </tr>
                ))
              )}
              <tr>
                <td className="py-2 pr-3 font-semibold">Base de cálculo</td>
                <td colSpan={regular ? 3 : 2} className="py-2 text-right font-semibold tabular-nums">{brl(s.totais?.base_calculo)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
      {s.aliquotas && (
        <details className="text-xs text-gray-600">
          <summary className="cursor-pointer">De onde vieram as alíquotas</summary>
          <ul className="mt-1 space-y-0.5">
            {Object.entries(s.aliquotas).map(([k, a]) => (
              <li key={k}>{TRIBUTO[k]}: {ORIGEM[a.origem]}{a.aliquota ? ` (${pct(a.aliquota)})` : ''}{a.fonte ? ` — ${a.fonte}` : ''}</li>
            ))}
          </ul>
        </details>
      )}
      {item.memoria && (
        <details className="text-xs text-gray-600">
          <summary className="cursor-pointer">Memória de cálculo oficial</summary>
          <ul className="mt-1 space-y-1">{Object.values(item.memoria).map((m, i) => <li key={i}>{m}</li>)}</ul>
        </details>
      )}
    </div>
  );
}

export default function SimuladorCbsIbsModal({ recibo, onClose }) {
  const [disp, setDisp] = useState(null);
  const [editando, setEditando] = useState(false);
  const [data, setData] = useState('');
  const [simulando, setSimulando] = useState(false);
  const [erro, setErro] = useState('');
  const [resultado, setResultado] = useState(null);
  const [historico, setHistorico] = useState([]);

  const carregar = () => receitaRtcAPI.disponivel().then((d) => { setDisp(d); setEditando(d.ativo && !d.configurado); })
    .catch(() => setDisp({ ativo: false }));
  const carregarHistorico = () => receitaRtcAPI.simulacoes('recibo', recibo.id)
    .then((d) => setHistorico(d.simulacoes || [])).catch(() => setHistorico([]));

  useEffect(() => { carregar(); carregarHistorico(); }, [recibo.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const simular = async () => {
    setErro(''); setResultado(null);
    if (!data) { setErro('Informe a data da operação (data do fato gerador).'); return; }
    setSimulando(true);
    try {
      setResultado(await receitaRtcAPI.simular({ origem_tipo: 'recibo', origem_id: recibo.id, data_operacao: data }));
      carregarHistorico();
    } catch (e) {
      setErro(msgErro(e, 'Não foi possível simular agora.'));
    } finally { setSimulando(false); }
  };

  const cfg = disp?.config;
  return (
    <div className="fixed inset-0 z-[1300] bg-black/60 flex items-end sm:items-center justify-center" role="dialog" aria-modal="true" aria-labelledby="rtc-titulo">
      <div className="bg-white w-full sm:max-w-2xl max-h-[92dvh] overflow-y-auto rounded-t-2xl sm:rounded-2xl shadow-xl">
        <div className="sticky top-0 bg-white border-b px-4 sm:px-5 py-3 flex items-center justify-between gap-3">
          <h2 id="rtc-titulo" className="font-semibold text-gray-900 flex items-center gap-2 min-w-0">
            <Calculator className="w-5 h-5 text-emerald-800 shrink-0" />
            <span className="truncate">CBS/IBS sobre os honorários</span>
          </h2>
          <button onClick={onClose} className="p-2 -m-2 rounded-lg hover:bg-gray-100 min-h-[44px] min-w-[44px] flex items-center justify-center" aria-label="Fechar">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 sm:p-5 space-y-4">
          <div className="flex gap-2 rounded-lg bg-gray-50 border border-gray-200 p-3 text-xs text-gray-700">
            <Info className="w-4 h-4 shrink-0 mt-0.5 text-gray-500" />
            <span>Estimativa baseada nas calculadoras oficiais da Receita Federal. Não substitui o sistema emissor nem a validação do contador.</span>
          </div>

          <div className="text-sm text-gray-700">
            <span className="font-medium">{recibo.numero || 'Recibo'}</span> · {recibo.destinatario_nome || '—'} · <span className="font-semibold">{brl(recibo.valor)}</span>
          </div>

          {!disp && <div className="py-6 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-gray-400" /></div>}
          {disp && !disp.ativo && <div className="text-sm text-gray-600">O simulador não está disponível no momento.</div>}

          {disp?.ativo && editando && (
            <ConfigConta inicial={cfg} onSalvo={(r) => { setDisp((d) => ({ ...d, config: r.config, configurado: !r.faltantes.length, faltantes: r.faltantes })); if (!r.faltantes.length) setEditando(false); }} />
          )}

          {disp?.ativo && !editando && !disp.configurado && (
            <div className="text-sm text-amber-800">Falta configurar: {disp.faltantes.map((k) => ROTULO_FALTA[k] || k).join(', ')}.</div>
          )}

          {disp?.ativo && !editando && disp.configurado && (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-gray-200 p-3 text-xs text-gray-600">
                <span className="min-w-0">
                  {cfg.regime === 'SIMPLES' ? 'Simples Nacional' : 'Regime regular'} · {cfg.nome_municipio || cfg.codigo_municipio}/{cfg.uf} · NBS {cfg.nbs}
                  {cfg.regime !== 'SIMPLES' && <> · CST {cfg.cst}</>} · cClassTrib {cfg.cClassTrib}
                </span>
                <button type="button" onClick={() => setEditando(true)} className="inline-flex items-center gap-1 text-emerald-800 font-medium min-h-[44px]">
                  <Settings2 className="w-4 h-4" /> Alterar
                </button>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-end gap-3">
                <Campo rotulo="Data da operação" dica="Data do fato gerador da operação (confirme com o seu contador). Não é preenchida sozinha.">
                  <input type="date" className={inputCls} value={data} onChange={(e) => setData(e.target.value)} />
                </Campo>
                <Button onClick={simular} disabled={simulando} className="min-h-[44px] bg-emerald-800 hover:bg-emerald-900 text-white shrink-0">
                  {simulando ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Calculator className="w-4 h-4 mr-2" />}Simular
                </Button>
              </div>
            </>
          )}

          {erro && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{erro}</div>}
          {resultado && <Resultado s={resultado} />}

          {historico.length > 0 && (
            <details className="text-sm" open={!resultado}>
              <summary className="cursor-pointer font-medium text-gray-800 flex items-center gap-2">
                <History className="w-4 h-4" /> Simulações salvas ({historico.length})
              </summary>
              <ul className="mt-2 divide-y divide-gray-100">
                {historico.map((h) => (
                  <li key={h.id} className="py-2">
                    <button type="button" className="w-full text-left flex flex-wrap items-baseline justify-between gap-x-3 min-h-[44px]" onClick={() => setResultado(h)}>
                      <span className="text-gray-900">{fmtDataHora(h.criado_em)} · operação {dataBr(h.data_operacao)}</span>
                      <span className="text-gray-600 text-xs flex items-center gap-1">
                        {h.situacao === 'calculado' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
                        CBS {brl(h.totais?.cbs)} · IBS {brl(h.totais?.ibs)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}
