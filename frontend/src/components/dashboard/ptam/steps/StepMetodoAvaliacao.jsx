// @module ptam/steps/StepMetodoAvaliacao — Step 8c: Métodos de Depreciação e Valorização (Ross-Heidecke, Linha Reta, Fatores, Rural, Renda)
import React, { useState } from 'react';
import { Input } from '../../../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../ui/select';
import { Field, SectionHeader } from '../shared/primitives';

const fmtBRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

// ── Ross-Heidecke ──────────────────────────────────────────────────────────────
const ESTADOS_RH = [
  { value: 'A', label: 'A — Novo',                ke: 1.00 },
  { value: 'B', label: 'B — Bom',                 ke: 0.85 },
  { value: 'C', label: 'C — Regular',             ke: 0.65 },
  { value: 'D', label: 'D — Precário',             ke: 0.50 },
  { value: 'E', label: 'E — Ruim',                ke: 0.35 },
  { value: 'F', label: 'F — Péssimo',             ke: 0.20 },
  { value: 'G', label: 'G — Sem Valor Comercial',  ke: 0.10 },
  { value: 'H', label: 'H — Demolição',            ke: 0.05 },
];

function calcRH(p) {
  const ke = (ESTADOS_RH.find((e) => e.value === (p.estado || 'C')) || ESTADOS_RH[2]).ke;
  const idRatio = Math.min(Number(p.idade_atual || 0) / Math.max(Number(p.vida_util || 60), 1), 1);
  const kd = idRatio * idRatio * (1 - ke) + idRatio * ke;
  return { kd, depPct: kd * 100, valDep: Number(p.valor_novo || 0) * kd, valResidual: Number(p.valor_novo || 0) * (1 - kd) };
}

const FormRossHeidecke = ({ params, setParams, onCalc }) => {
  const r = calcRH(params);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field label="Valor de Novo (R$)"><Input type="number" step="0.01" value={params.valor_novo || ''} onChange={(e) => setParams({ ...params, valor_novo: Number(e.target.value) })} placeholder="R$ 0,00" /></Field>
        <Field label="Idade Atual (anos)"><Input type="number" min="0" value={params.idade_atual || ''} onChange={(e) => setParams({ ...params, idade_atual: Number(e.target.value) })} placeholder="0" /></Field>
        <Field label="Vida Útil (padrão 60 anos)"><Input type="number" min="1" value={params.vida_util || 60} onChange={(e) => setParams({ ...params, vida_util: Number(e.target.value) })} /></Field>
        <Field label="Estado de Conservação (A–H)">
          <Select value={params.estado || 'C'} onValueChange={(v) => setParams({ ...params, estado: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{ESTADOS_RH.map((e) => <SelectItem key={e.value} value={e.value}>{e.label}</SelectItem>)}</SelectContent>
          </Select>
        </Field>
      </div>
      {Number(params.valor_novo) > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-center">
            <div className="text-xs text-amber-700 uppercase tracking-wider mb-1">Coeficiente Kd</div>
            <div className="text-xl font-bold text-amber-800">{r.kd.toFixed(4)}</div>
            <div className="text-xs text-gray-500">{r.depPct.toFixed(2)}% depreciado</div>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center">
            <div className="text-xs text-red-600 uppercase tracking-wider mb-1">Depreciação</div>
            <div className="text-xl font-bold text-red-700">{fmtBRL(r.valDep)}</div>
          </div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center">
            <div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">Valor Residual</div>
            <div className="text-xl font-bold text-emerald-800">{fmtBRL(r.valResidual)}</div>
          </div>
        </div>
      )}
      <button type="button" onClick={() => onCalc({ depPct: r.depPct, valDep: r.valDep, valBenfeitoria: r.valResidual, valTotal: r.valResidual })} className="w-full py-2 bg-emerald-900 hover:bg-emerald-800 text-white rounded-lg text-sm font-semibold">Aplicar Ross-Heidecke ao Laudo</button>
    </div>
  );
};

// ── Linha Reta ─────────────────────────────────────────────────────────────────
function calcLR(p) {
  const vn = Number(p.valor_novo || 0);
  const resid = vn * (Number(p.residual_pct ?? 20) / 100);
  const depAnual = (vn - resid) / Math.max(Number(p.vida_util ?? 40), 1);
  const depAcum = depAnual * Math.min(Number(p.idade_atual || 0), Number(p.vida_util ?? 40));
  return { depAnual, depAcum, valAtual: Math.max(vn - depAcum, resid) };
}

const FormLinhaReta = ({ params, setParams, onCalc }) => {
  const r = calcLR(params);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field label="Valor de Novo (R$)"><Input type="number" step="0.01" value={params.valor_novo || ''} onChange={(e) => setParams({ ...params, valor_novo: Number(e.target.value) })} placeholder="R$ 0,00" /></Field>
        <Field label="Valor Residual (%)"><Input type="number" min="0" max="100" step="0.1" value={params.residual_pct ?? 20} onChange={(e) => setParams({ ...params, residual_pct: Number(e.target.value) })} /></Field>
        <Field label="Vida Útil (padrão 40 anos)"><Input type="number" min="1" value={params.vida_util ?? 40} onChange={(e) => setParams({ ...params, vida_util: Number(e.target.value) })} /></Field>
        <Field label="Idade Atual (anos)"><Input type="number" min="0" value={params.idade_atual || ''} onChange={(e) => setParams({ ...params, idade_atual: Number(e.target.value) })} placeholder="0" /></Field>
      </div>
      {Number(params.valor_novo) > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center"><div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Dep. Anual</div><div className="text-lg font-bold text-gray-800">{fmtBRL(r.depAnual)}</div></div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center"><div className="text-xs text-red-600 uppercase tracking-wider mb-1">Dep. Acumulada</div><div className="text-lg font-bold text-red-700">{fmtBRL(r.depAcum)}</div></div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center"><div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">Valor Atual</div><div className="text-lg font-bold text-emerald-800">{fmtBRL(r.valAtual)}</div></div>
        </div>
      )}
      <button type="button" onClick={() => onCalc({ depPct: Number(params.valor_novo) > 0 ? (r.depAcum / Number(params.valor_novo)) * 100 : 0, valDep: r.depAcum, valBenfeitoria: r.valAtual, valTotal: r.valAtual })} className="w-full py-2 bg-emerald-900 hover:bg-emerald-800 text-white rounded-lg text-sm font-semibold">Aplicar Linha Reta ao Laudo</button>
    </div>
  );
};

// ── Fatores de Terreno ─────────────────────────────────────────────────────────
const FATOR_LOC = [{ value: '1.10', label: 'Esquina (+10%)' }, { value: '1.00', label: 'Meio de Quadra (referência)' }, { value: '0.85', label: 'Fundos (-15%)' }];
const FATOR_TOPO = [{ value: '1.00', label: 'Plano' }, { value: '0.95', label: 'Aclive suave (-5%)' }, { value: '0.90', label: 'Declive suave (-10%)' }, { value: '0.80', label: 'Acentuado (-20%)' }, { value: '0.70', label: 'Irregular (-30%)' }];
const FATOR_INFRA = [{ value: '1.00', label: 'Infraestrutura completa' }, { value: '0.90', label: 'Parcial (-10%)' }, { value: '0.75', label: 'Básica apenas (-25%)' }];

function fatorTestada(m) { const v = Number(m || 0); if (v <= 0) return 1; if (v < 8) return 0.90; if (v <= 15) return 1.00; return 1.05; }

function calcFT(p) {
  const ft = fatorTestada(p.testada_m);
  const vuAdj = Number(p.valor_unitario || 0) * Number(p.f_loc || 1) * Number(p.f_topo || 1) * ft * Number(p.f_infra || 1);
  return { ft, vuAdj, valTotal: vuAdj * Number(p.area_terreno || 0) };
}

const FormFatoresTerreno = ({ params, setParams, onCalc }) => {
  const r = calcFT(params);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field label="Valor Unitário de Referência (R$/m²)"><Input type="number" step="0.01" value={params.valor_unitario || ''} onChange={(e) => setParams({ ...params, valor_unitario: Number(e.target.value) })} placeholder="R$/m² da ponderância" /></Field>
        <Field label="Área do Terreno (m²)"><Input type="number" step="0.01" value={params.area_terreno || ''} onChange={(e) => setParams({ ...params, area_terreno: Number(e.target.value) })} placeholder="m²" /></Field>
        <Field label="Fator Localização">
          <Select value={params.f_loc || '1.00'} onValueChange={(v) => setParams({ ...params, f_loc: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{FATOR_LOC.map((f) => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}</SelectContent></Select>
        </Field>
        <Field label="Fator Topografia">
          <Select value={params.f_topo || '1.00'} onValueChange={(v) => setParams({ ...params, f_topo: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{FATOR_TOPO.map((f) => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}</SelectContent></Select>
        </Field>
        <Field label="Testada (metros)"><Input type="number" step="0.1" value={params.testada_m || ''} onChange={(e) => setParams({ ...params, testada_m: Number(e.target.value) })} placeholder="metros" /></Field>
        <Field label="Fator Infraestrutura">
          <Select value={params.f_infra || '1.00'} onValueChange={(v) => setParams({ ...params, f_infra: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{FATOR_INFRA.map((f) => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}</SelectContent></Select>
        </Field>
      </div>
      {Number(params.valor_unitario) > 0 && Number(params.area_terreno) > 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
          <div className="grid grid-cols-4 gap-2 text-center text-sm mb-3">
            <div><div className="text-xs text-gray-400">Localização</div><div className="font-bold">{Number(params.f_loc || 1).toFixed(2)}</div></div>
            <div><div className="text-xs text-gray-400">Topografia</div><div className="font-bold">{Number(params.f_topo || 1).toFixed(2)}</div></div>
            <div><div className="text-xs text-gray-400">Testada</div><div className="font-bold">{r.ft.toFixed(2)}</div></div>
            <div><div className="text-xs text-gray-400">Infraestrutura</div><div className="font-bold">{Number(params.f_infra || 1).toFixed(2)}</div></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white border border-gray-200 rounded-lg p-3 text-center"><div className="text-xs text-gray-500 mb-1">VU Ajustado (R$/m²)</div><div className="text-lg font-bold text-gray-800">{fmtBRL(r.vuAdj)}</div></div>
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center"><div className="text-xs text-emerald-700 mb-1">Valor Total do Terreno</div><div className="text-lg font-bold text-emerald-800">{fmtBRL(r.valTotal)}</div></div>
          </div>
        </div>
      )}
      <button type="button" onClick={() => onCalc({ valTerreno: r.valTotal, valTotal: r.valTotal })} className="w-full py-2 bg-emerald-900 hover:bg-emerald-800 text-white rounded-lg text-sm font-semibold">Aplicar Fatores de Terreno ao Laudo</button>
    </div>
  );
};

// ── NBR Rural ─────────────────────────────────────────────────────────────────
const CLASSES_USO = [
  { value: '1.00', label: 'Classe I — Aptidão Boa (1,00)' },
  { value: '0.90', label: 'Classe II — Aptidão Regular (0,90)' },
  { value: '0.75', label: 'Classe III — Aptidão Restrita (0,75)' },
  { value: '0.60', label: 'Classe IV — Aptidão Marginal (0,60)' },
  { value: '0.40', label: 'Classe V–VII — Sem Aptidão Agrícola (0,40)' },
];

function calcRural(p) {
  const valTerra = Number(p.vtn_hectare || 0) * Number(p.area_ha || 0) * Number(p.classe_uso || 1);
  return { valTerra, valTotal: valTerra + Number(p.benfeitorias_rurais || 0) + Number(p.cultura_permanente || 0) + Number(p.cultura_temporaria || 0) };
}

const FormNbrRural = ({ params, setParams, onCalc }) => {
  const r = calcRural(params);
  return (
    <div className="space-y-4">
      <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-800">Conforme ABNT NBR 14653-3 e IN INCRA. VTN = valor de mercado do hectare sem benfeitorias.</div>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Área Total (ha)"><Input type="number" step="0.0001" value={params.area_ha || ''} onChange={(e) => setParams({ ...params, area_ha: Number(e.target.value) })} placeholder="0,0000" /></Field>
        <Field label="VTN — Valor por Hectare (R$/ha)"><Input type="number" step="0.01" value={params.vtn_hectare || ''} onChange={(e) => setParams({ ...params, vtn_hectare: Number(e.target.value) })} placeholder="R$/ha" /></Field>
        <Field label="Classe de Uso / CUF (NBR 14653-3)" full>
          <Select value={params.classe_uso || '1.00'} onValueChange={(v) => setParams({ ...params, classe_uso: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{CLASSES_USO.map((c) => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}</SelectContent></Select>
        </Field>
        <Field label="Benfeitorias Rurais (R$)"><Input type="number" step="0.01" value={params.benfeitorias_rurais || ''} onChange={(e) => setParams({ ...params, benfeitorias_rurais: Number(e.target.value) })} placeholder="R$ 0,00" /></Field>
        <Field label="Cultura Permanente (R$)"><Input type="number" step="0.01" value={params.cultura_permanente || ''} onChange={(e) => setParams({ ...params, cultura_permanente: Number(e.target.value) })} placeholder="R$ 0,00" /></Field>
        <Field label="Cultura Temporária (R$)"><Input type="number" step="0.01" value={params.cultura_temporaria || ''} onChange={(e) => setParams({ ...params, cultura_temporaria: Number(e.target.value) })} placeholder="R$ 0,00" /></Field>
      </div>
      {Number(params.area_ha) > 0 && Number(params.vtn_hectare) > 0 && (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center"><div className="text-xs text-green-700 uppercase tracking-wider mb-1">Valor da Terra Nua</div><div className="text-lg font-bold text-green-800">{fmtBRL(r.valTerra)}</div><div className="text-xs text-gray-500">VTN × {Number(params.area_ha)} ha × CUF {Number(params.classe_uso || 1).toFixed(2)}</div></div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center"><div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">Valor Total Rural</div><div className="text-lg font-bold text-emerald-800">{fmtBRL(r.valTotal)}</div><div className="text-xs text-gray-500">Terra + Benfeitorias + Culturas</div></div>
        </div>
      )}
      <button type="button" onClick={() => onCalc({ valTerreno: r.valTerra, valTotal: r.valTotal })} className="w-full py-2 bg-emerald-900 hover:bg-emerald-800 text-white rounded-lg text-sm font-semibold">Aplicar NBR Rural ao Laudo</button>
    </div>
  );
};

// ── Método da Renda ────────────────────────────────────────────────────────────
function calcRenda(p) {
  const rendaAnual = Number(p.renda_mensal || 0) * 12;
  const taxa = Number(p.taxa_cap || 8) / 100;
  let val = 0;
  if (p.tipo === 'prazo') {
    const n = Number(p.prazo_anos || 0) * 12;
    const tm = taxa / 12;
    val = tm > 0 && n > 0 ? Number(p.renda_mensal || 0) * ((1 - Math.pow(1 + tm, -n)) / tm) : Number(p.renda_mensal || 0) * n;
  } else {
    val = taxa > 0 ? rendaAnual / taxa : 0;
  }
  return { rendaAnual, valCapitalizado: val };
}

const FormRenda = ({ params, setParams, onCalc }) => {
  const r = calcRenda(params);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field label="Renda Mensal (R$)"><Input type="number" step="0.01" value={params.renda_mensal || ''} onChange={(e) => setParams({ ...params, renda_mensal: Number(e.target.value) })} placeholder="R$ 0,00" /></Field>
        <Field label="Taxa de Capitalização (%, padrão 8%)"><Input type="number" step="0.01" min="0.01" value={params.taxa_cap ?? 8} onChange={(e) => setParams({ ...params, taxa_cap: Number(e.target.value) })} /></Field>
        <Field label="Tipo de Cálculo">
          <Select value={params.tipo || 'perpetuidade'} onValueChange={(v) => setParams({ ...params, tipo: v })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="perpetuidade">Perpetuidade (Renda / Taxa)</SelectItem><SelectItem value="prazo">Prazo determinado (VPL)</SelectItem></SelectContent></Select>
        </Field>
        {params.tipo === 'prazo' && <Field label="Prazo (anos)"><Input type="number" min="1" value={params.prazo_anos || ''} onChange={(e) => setParams({ ...params, prazo_anos: Number(e.target.value) })} placeholder="anos" /></Field>}
      </div>
      {Number(params.renda_mensal) > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center"><div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Renda Anual</div><div className="text-lg font-bold text-gray-800">{fmtBRL(r.rendaAnual)}</div></div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center"><div className="text-xs text-blue-600 uppercase tracking-wider mb-1">Taxa a.a.</div><div className="text-lg font-bold text-blue-700">{Number(params.taxa_cap || 8).toFixed(2)}%</div></div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center"><div className="text-xs text-emerald-700 uppercase tracking-wider mb-1">Valor Capitalizado</div><div className="text-lg font-bold text-emerald-800">{fmtBRL(r.valCapitalizado)}</div></div>
        </div>
      )}
      <button type="button" onClick={() => onCalc({ valTotal: r.valCapitalizado })} className="w-full py-2 bg-emerald-900 hover:bg-emerald-800 text-white rounded-lg text-sm font-semibold">Aplicar Método da Renda ao Laudo</button>
    </div>
  );
};

// ── Orquestrador ───────────────────────────────────────────────────────────────
const METODOS_AVAL = [
  { value: 'ross_heidecke',   label: 'Ross-Heidecke',       desc: 'Casa/Apto com idade', icon: '🏠' },
  { value: 'linha_reta',      label: 'Linha Reta',           desc: 'Galpão/Construção',   icon: '🏭' },
  { value: 'fatores_terreno', label: 'Fatores Terreno',      desc: 'Terreno urbano',       icon: '🗺️' },
  { value: 'nbr_rural',       label: 'NBR Rural',            desc: 'Rural / INCRA',        icon: '🌾' },
  { value: 'renda',           label: 'Método da Renda',      desc: 'Comercial/Renda',      icon: '💰' },
];

export const StepMetodoAvaliacao = ({ form, setForm }) => {
  const metodo = form.metodo_avaliacao || null;
  const [params, setParams] = useState(form.metodo_params || {});

  const updateParams = (p) => { setParams(p); setForm((f) => ({ ...f, metodo_params: p })); };

  const handleCalc = ({ depPct, valDep, valBenfeitoria, valTerreno, valTotal }) => {
    setForm((f) => ({
      ...f,
      depreciacao_percentual: depPct !== undefined ? depPct : f.depreciacao_percentual,
      valor_depreciacao:      valDep !== undefined ? valDep : f.valor_depreciacao,
      valor_benfeitoria:      valBenfeitoria !== undefined ? valBenfeitoria : f.valor_benfeitoria,
      valor_terreno_calc:     valTerreno !== undefined ? valTerreno : f.valor_terreno_calc,
      valor_total_metodo:     valTotal !== undefined ? valTotal : f.valor_total_metodo,
    }));
  };

  const inserirNoLaudo = () => {
    if (!form.valor_total_metodo) return;
    setForm((f) => ({ ...f, resultado_valor_total: f.valor_total_metodo, total_indemnity: f.valor_total_metodo }));
  };

  const selectMetodo = (v) => {
    setParams({});
    setForm((f) => ({ ...f, metodo_avaliacao: v, metodo_params: {}, depreciacao_percentual: null, valor_depreciacao: null, valor_benfeitoria: null, valor_terreno_calc: null, valor_total_metodo: null }));
  };

  const hasResult = form.valor_total_metodo != null && form.valor_total_metodo > 0;

  return (
    <div>
      <SectionHeader
        title="8c. Método de Avaliação — Depreciação e Valorização"
        subtitle="Selecione o método conforme o tipo de imóvel. Cálculos automáticos no frontend."
      />

      <div className="grid grid-cols-5 gap-3 mb-6">
        {METODOS_AVAL.map((m) => (
          <button key={m.value} type="button" onClick={() => selectMetodo(m.value)}
            className={`flex flex-col items-center justify-center gap-1.5 rounded-xl border-2 px-2 py-3 text-center transition-all ${metodo === m.value ? 'border-emerald-600 bg-emerald-50 shadow-md' : 'border-gray-200 bg-white hover:border-emerald-300 hover:bg-emerald-50/50'}`}>
            <span className="text-xl">{m.icon}</span>
            <span className={`text-xs font-bold leading-tight ${metodo === m.value ? 'text-emerald-800' : 'text-gray-700'}`}>{m.label}</span>
            <span className="text-[10px] text-gray-400 leading-tight">{m.desc}</span>
          </button>
        ))}
      </div>

      {metodo && (
        <div className="rounded-xl border-2 border-emerald-200 bg-white p-5 mb-6">
          <div className="text-sm font-semibold text-emerald-800 mb-4">{METODOS_AVAL.find((m) => m.value === metodo)?.label}</div>
          {metodo === 'ross_heidecke'   && <FormRossHeidecke params={params} setParams={updateParams} onCalc={handleCalc} />}
          {metodo === 'linha_reta'      && <FormLinhaReta     params={params} setParams={updateParams} onCalc={handleCalc} />}
          {metodo === 'fatores_terreno' && <FormFatoresTerreno params={params} setParams={updateParams} onCalc={handleCalc} />}
          {metodo === 'nbr_rural'       && <FormNbrRural      params={params} setParams={updateParams} onCalc={handleCalc} />}
          {metodo === 'renda'           && <FormRenda         params={params} setParams={updateParams} onCalc={handleCalc} />}
        </div>
      )}

      {hasResult && (
        <div className="rounded-2xl border-2 border-amber-400 bg-gradient-to-br from-amber-50 to-yellow-50 p-6">
          <div className="text-xs font-bold text-amber-700 uppercase tracking-widest mb-3">Resultado Consolidado — {METODOS_AVAL.find((m) => m.value === metodo)?.label}</div>
          <div className="grid grid-cols-2 gap-3 mb-4">
            {form.valor_terreno_calc > 0 && (
              <div className="bg-white rounded-lg border border-amber-200 p-3"><div className="text-xs text-gray-500 mb-0.5">Valor do Terreno</div><div className="font-bold text-gray-800">{fmtBRL(form.valor_terreno_calc)}</div></div>
            )}
            {form.valor_benfeitoria > 0 && (
              <div className="bg-white rounded-lg border border-amber-200 p-3"><div className="text-xs text-gray-500 mb-0.5">Benfeitorias (depreciado)</div><div className="font-bold text-gray-800">{fmtBRL(form.valor_benfeitoria)}</div></div>
            )}
            {form.depreciacao_percentual > 0 && (
              <div className="bg-white rounded-lg border border-red-200 p-3"><div className="text-xs text-red-500 mb-0.5">Depreciação</div><div className="font-bold text-red-700">{Number(form.depreciacao_percentual).toFixed(2)}% — {fmtBRL(form.valor_depreciacao)}</div></div>
            )}
          </div>
          <div className="bg-amber-400/20 border border-amber-400 rounded-xl p-4 text-center">
            <div className="text-xs text-amber-700 uppercase tracking-wider mb-1">VALOR TOTAL (Terreno + Benfeitorias)</div>
            <div className="text-4xl font-bold text-amber-900">{fmtBRL(form.valor_total_metodo)}</div>
          </div>
          <div className="mt-4 flex justify-end">
            <button type="button" onClick={inserirNoLaudo} className="px-6 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-semibold shadow">Inserir no Laudo</button>
          </div>
        </div>
      )}

      {!metodo && (
        <div className="text-center py-10 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200 text-gray-400 text-sm">
          Selecione um método acima para iniciar o cálculo de depreciação ou valorização.
        </div>
      )}
    </div>
  );
};
