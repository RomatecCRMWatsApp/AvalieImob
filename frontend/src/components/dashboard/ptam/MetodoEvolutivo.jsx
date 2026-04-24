// @module ptam/MetodoEvolutivo – Método Evolutivo NBR 14.653-2:2011 com CUB automático SINDUSCON
import React, { useState, useEffect, useCallback } from 'react';
import { Building2, MapPin, Calculator, TrendingUp, RefreshCw, AlertTriangle, CheckCircle, Info } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const UFS = [
  'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG',
  'PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'
];

const fmtBRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const fmtNum = (v, dec = 2) =>
  Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec });

// ── Card visual ───────────────────────────────────────────────────────────────
const Card = ({ title, icon: Icon, iconColor = 'text-emerald-600', children }) => (
  <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
    <div className="flex items-center gap-3 px-4 py-3 bg-gray-50 border-b border-gray-200">
      <Icon className={`w-5 h-5 ${iconColor}`} />
      <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
    </div>
    <div className="p-4">{children}</div>
  </div>
);

// ── Input numérico ────────────────────────────────────────────────────────────
const NumInput = ({ label, value, onChange, placeholder, suffix, hint }) => (
  <div>
    <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
    <div className="relative">
      <input
        type="number"
        step="0.01"
        min="0"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        placeholder={placeholder}
        className="w-full h-9 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 pr-12"
      />
      {suffix && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 pointer-events-none">
          {suffix}
        </span>
      )}
    </div>
    {hint && <p className="mt-1 text-xs text-gray-400">{hint}</p>}
  </div>
);

// ── Componente principal ──────────────────────────────────────────────────────
const MetodoEvolutivo = ({ form, setForm }) => {
  // Estado UF e tipos CUB
  const [uf, setUf] = useState(form.property_state || form.uf || 'SP');
  const [cubData, setCubData] = useState(null);
  const [cubLoading, setCubLoading] = useState(false);
  const [cubError, setCubError] = useState('');

  // Campos do método evolutivo
  const [tipoCub, setTipoCub] = useState(form.metodo_evolutivo_tipo_cub || 'R1-N');
  const [cubManual, setCubManual] = useState(false);
  const [cubManualVal, setCubManualVal] = useState(form.metodo_evolutivo_valor_cub || 0);
  const [area, setArea] = useState(form.metodo_evolutivo_area_construida || 0);
  const [fatorAdequacao, setFatorAdequacao] = useState(form.metodo_evolutivo_fator_adequacao || 1.0);
  const [depreciacao, setDepreciacao] = useState(form.metodo_evolutivo_fator_obsolescencia || 0);
  const [benfeitoriaExtra, setBenfeitoriaExtra] = useState(form.metodo_evolutivo_benfeitoria_extra || 0);
  const [valorTerreno, setValorTerreno] = useState(form.metodo_evolutivo_valor_terreno || 0);
  const [areaTerreno, setAreaTerreno] = useState(form.property_area_sqm || form.area_total_ha * 10000 || 0);

  // Buscar CUB ao montar ou trocar UF
  const buscarCub = useCallback(async (estado) => {
    setCubLoading(true);
    setCubError('');
    try {
      const resp = await fetch(`${API_BASE}/cub?estado=${estado}`);
      const data = await resp.json();
      if (data.ok) {
        setCubData(data);
      } else {
        setCubError('Erro ao buscar CUB. Usando referência nacional.');
      }
    } catch {
      setCubError('Sem conexão com servidor. Usando referência nacional.');
    } finally {
      setCubLoading(false);
    }
  }, []);

  useEffect(() => {
    buscarCub(uf);
  }, [uf, buscarCub]);

  // Valor CUB efetivo
  const cubValorEfetivo = cubManual
    ? cubManualVal
    : (cubData?.valores?.[tipoCub] || 0);

  // Cálculo ao vivo
  const fatDep = Math.max(0, Math.min(80, depreciacao)) / 100;
  const fatAdq = Math.max(0.1, fatorAdequacao);
  const custoReproducao = cubValorEfetivo * area * fatAdq;
  const depreciacaoValor = custoReproducao * fatDep;
  const valorBenfeitoria = custoReproducao - depreciacaoValor;
  const valorTotal = valorTerreno + valorBenfeitoria + benfeitoriaExtra;
  const valorPorM2Terreno = areaTerreno > 0 ? valorTerreno / areaTerreno : 0;

  const resultado = {
    tipo_cub: tipoCub,
    cub_valor: cubValorEfetivo,
    area_construida: area,
    fator_adequacao: fatAdq,
    fator_obsolescencia_pct: depreciacao,
    custo_reproducao: custoReproducao,
    depreciacao_valor: depreciacaoValor,
    valor_benfeitoria: valorBenfeitoria,
    valor_terreno: valorTerreno,
    benfeitoria_extra: benfeitoriaExtra,
    valor_total: valorTotal,
    fonte_cub: cubManual ? 'Manual (informado pelo usuário)' : (cubData?.fonte || 'Referência nacional'),
    base_legal: 'NBR 14.653-2:2011, item 8.2.1.2',
    formula: `VT = ${fmtBRL(valorTerreno)} + [CUB(${fmtBRL(cubValorEfetivo)}) × ${fmtNum(area)}m² × Fa(${fatAdq.toFixed(2)}) × (1−${depreciacao.toFixed(1)}%)] + BE(${fmtBRL(benfeitoriaExtra)})`,
  };

  const handleUsarNoLaudo = () => {
    setForm((f) => ({
      ...f,
      metodo_evolutivo_tipo_cub: tipoCub,
      metodo_evolutivo_valor_cub: cubValorEfetivo,
      metodo_evolutivo_fonte_cub: resultado.fonte_cub,
      metodo_evolutivo_area_construida: area,
      metodo_evolutivo_fator_obsolescencia: depreciacao,
      metodo_evolutivo_fator_adequacao: fatAdq,
      metodo_evolutivo_valor_terreno: valorTerreno,
      metodo_evolutivo_benfeitoria_extra: benfeitoriaExtra,
      metodo_evolutivo_resultado: resultado,
      resultado_valor_total: valorTotal,
      total_indemnity: valorTotal,
    }));
  };

  return (
    <div className="space-y-5">
      <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-start gap-2">
        <Info className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-emerald-700">
          <strong>Método Evolutivo – NBR 14.653-2:2011, item 8.2.1.2.</strong>{' '}
          O valor do imóvel é obtido somando o valor do terreno ao custo de reprodução das benfeitorias,
          com aplicação de fator de adequação e depreciação física/funcional.
        </p>
      </div>

      {/* Card 1 – CUB do Mês */}
      <Card title="CUB do Mês (SINDUSCON)" icon={TrendingUp}>
        <div className="space-y-4">
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Estado (UF)</label>
              <select
                value={uf}
                onChange={(e) => setUf(e.target.value)}
                className="w-full h-9 rounded-lg border border-gray-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>
            <button
              type="button"
              onClick={() => buscarCub(uf)}
              disabled={cubLoading}
              className="flex items-center gap-1.5 px-4 h-9 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${cubLoading ? 'animate-spin' : ''}`} />
              {cubLoading ? 'Buscando...' : 'Buscar'}
            </button>
          </div>

          {cubError && (
            <div className="flex items-center gap-2 p-2 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              <span className="text-xs text-amber-700">{cubError}</span>
            </div>
          )}

          {cubData && (
            <div className="flex items-center gap-2 p-2 rounded-lg bg-emerald-50 border border-emerald-200">
              <CheckCircle className="w-4 h-4 text-emerald-600" />
              <span className="text-xs text-emerald-700">
                {cubData.fonte}
                {cubData.is_fallback && (
                  <span className="ml-2 px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-xs font-medium">
                    Referência nacional (SP)
                  </span>
                )}
              </span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Tipo CUB</label>
              <select
                value={tipoCub}
                onChange={(e) => setTipoCub(e.target.value)}
                disabled={cubManual}
                className="w-full h-9 rounded-lg border border-gray-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-gray-100"
              >
                {cubData
                  ? Object.keys(cubData.valores).map((k) => (
                      <option key={k} value={k}>{k} – {fmtBRL(cubData.valores[k])}/m²</option>
                    ))
                  : <option value="R1-N">R1-N (carregando...)</option>
                }
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Valor CUB (R$/m²)
              </label>
              {cubManual ? (
                <input
                  type="number"
                  step="0.01"
                  value={cubManualVal}
                  onChange={(e) => setCubManualVal(parseFloat(e.target.value) || 0)}
                  className="w-full h-9 rounded-lg border border-emerald-400 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              ) : (
                <div className="flex items-center h-9 px-3 bg-gray-50 rounded-lg border border-gray-200 text-sm font-semibold text-emerald-800">
                  {cubValorEfetivo > 0 ? fmtBRL(cubValorEfetivo) : '—'}
                </div>
              )}
            </div>
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={cubManual}
              onChange={(e) => setCubManual(e.target.checked)}
              className="rounded border-gray-300 text-emerald-600"
            />
            <span className="text-xs text-gray-600">Informar CUB manualmente</span>
          </label>
        </div>
      </Card>

      {/* Card 2 – Dados da Edificação */}
      <Card title="Dados da Edificação" icon={Building2}>
        <div className="grid grid-cols-2 gap-4">
          <NumInput
            label="Área Construída (m²)"
            value={area}
            onChange={setArea}
            placeholder="Ex: 150"
            suffix="m²"
          />
          <NumInput
            label="Fator de Adequação"
            value={fatorAdequacao}
            onChange={setFatorAdequacao}
            placeholder="1.00"
            hint="Padrão 1,00 (sem ajuste)"
          />
        </div>

        <div className="mt-4">
          <label className="flex items-center justify-between text-xs font-medium text-gray-600 mb-2">
            <span>Depreciação / Obsolescência</span>
            <span className="font-bold text-gray-800">{depreciacao.toFixed(1)}%</span>
          </label>
          <input
            type="range"
            min="0"
            max="80"
            step="0.5"
            value={depreciacao}
            onChange={(e) => setDepreciacao(parseFloat(e.target.value))}
            className="w-full accent-emerald-600"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>0% – Novo</span>
            <span>40% – Regular</span>
            <span>80% – Ruína</span>
          </div>
        </div>

        <div className="mt-4">
          <NumInput
            label="Benfeitorias Extras (R$)"
            value={benfeitoriaExtra}
            onChange={setBenfeitoriaExtra}
            placeholder="0,00"
            suffix="R$"
            hint="Piscina, poço artesiano, galpão, etc."
          />
        </div>
      </Card>

      {/* Card 3 – Valor do Terreno */}
      <Card title="Valor do Terreno" icon={MapPin} iconColor="text-blue-600">
        <div className="grid grid-cols-2 gap-4">
          <NumInput
            label="Valor de Mercado (R$)"
            value={valorTerreno}
            onChange={setValorTerreno}
            placeholder="0,00"
            suffix="R$"
          />
          <NumInput
            label="Área do Terreno (m²)"
            value={areaTerreno}
            onChange={setAreaTerreno}
            placeholder="0"
            suffix="m²"
          />
        </div>
        {valorPorM2Terreno > 0 && (
          <div className="mt-3 p-2 bg-blue-50 border border-blue-100 rounded-lg flex items-center justify-between">
            <span className="text-xs text-blue-700">Valor unitário do terreno</span>
            <span className="text-sm font-bold text-blue-900">{fmtBRL(valorPorM2Terreno)}/m²</span>
          </div>
        )}
      </Card>

      {/* Card 4 – Resultado */}
      <Card title="Resultado – Método Evolutivo" icon={Calculator} iconColor="text-purple-600">
        <div className="space-y-4">
          {/* Fórmula */}
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
            <p className="text-xs text-gray-500 mb-1 font-medium">Fórmula NBR 14.653-2, item 8.2.1.2</p>
            <p className="text-xs text-gray-700 font-mono break-all">
              VT = VTe + [CUB × Área × Fa × (1 − Fd%)] + BE
            </p>
          </div>

          {/* Detalhamento */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-xs text-gray-500">Custo de Reprodução</div>
              <div className="font-semibold text-gray-800">{fmtBRL(custoReproducao)}</div>
            </div>
            <div className="p-3 bg-red-50 rounded-lg">
              <div className="text-xs text-red-600">(-) Depreciação ({depreciacao.toFixed(1)}%)</div>
              <div className="font-semibold text-red-700">− {fmtBRL(depreciacaoValor)}</div>
            </div>
            <div className="p-3 bg-emerald-50 rounded-lg">
              <div className="text-xs text-emerald-600">Valor das Benfeitorias</div>
              <div className="font-semibold text-emerald-800">{fmtBRL(valorBenfeitoria)}</div>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg">
              <div className="text-xs text-blue-600">Valor do Terreno</div>
              <div className="font-semibold text-blue-800">{fmtBRL(valorTerreno)}</div>
            </div>
          </div>

          {/* Total */}
          {valorTotal > 0 && (
            <div className="p-4 bg-gradient-to-r from-emerald-800 to-emerald-700 rounded-xl">
              <div className="text-xs text-emerald-200 mb-1 uppercase tracking-wider">Valor Total do Imóvel</div>
              <div className="text-3xl font-bold text-white tabular-nums">{fmtBRL(valorTotal)}</div>
              <div className="text-xs text-emerald-300 mt-1">
                Terreno + Benfeitorias + Extras | {resultado.fonte_cub}
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={handleUsarNoLaudo}
            disabled={valorTotal <= 0}
            className="w-full py-3 bg-emerald-700 hover:bg-emerald-800 active:scale-95 text-white text-sm font-semibold rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Usar este valor no laudo
          </button>

          {form.metodo_evolutivo_resultado && (
            <div className="flex items-center gap-2 p-2 bg-emerald-50 border border-emerald-200 rounded-lg">
              <CheckCircle className="w-4 h-4 text-emerald-600" />
              <span className="text-xs text-emerald-700">
                Resultado aplicado ao laudo – {fmtBRL(form.metodo_evolutivo_resultado.valor_total)}
              </span>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

export default MetodoEvolutivo;
