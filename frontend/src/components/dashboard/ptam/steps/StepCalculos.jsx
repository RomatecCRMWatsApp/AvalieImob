// @module ptam/steps/StepCalculos — Step 8: Cálculos e Tratamento Estatístico (NBR 14653-2)
import React, { useEffect, useState, useMemo } from 'react';
import { Textarea } from '../../../ui/textarea';
import { SectionHeader, AiButton } from '../shared/primitives';
import { computeStatsNBR } from '../ptamHelpers';
import { AlertTriangle, CheckCircle, Info } from 'lucide-react';
import MetodoEvolutivo from '../MetodoEvolutivo';

const fmtBRL = (v) =>
  Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const fmtNum = (v, dec = 2) =>
  Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec });

// Cores para coeficiente de variação
const getCVColor = (cv) => {
  if (cv <= 10) return { text: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', label: 'Excelente' };
  if (cv <= 20) return { text: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Bom' };
  if (cv <= 30) return { text: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200', label: 'Regular' };
  return { text: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', label: 'Crítico' };
};

// Cores para graus
const getGrauColor = (grau) => {
  switch (grau) {
    case 'III': return { bg: 'bg-emerald-600', text: 'text-white', label: 'Máximo' };
    case 'II': return { bg: 'bg-blue-500', text: 'text-white', label: 'Intermediário' };
    case 'I': return { bg: 'bg-amber-500', text: 'text-white', label: 'Mínimo' };
    default: return { bg: 'bg-red-500', text: 'text-white', label: 'Insuficiente' };
  }
};

export const StepCalculos = ({ form, setForm, onAi, aiLoading }) => {
  const samples = form.market_samples || [];
  const stats = useMemo(() => computeStatsNBR(samples), [samples]);
  const cvColors = getCVColor(stats.coef_variacao);
  const fundColors = getGrauColor(stats.grau_fundamentacao);
  const precColors = getGrauColor(stats.grau_precisao === 'fora' ? null : stats.grau_precisao);

  // Detecta se metodologia inclui evolutivo
  const isEvolutivo = (form.methodology || '').toLowerCase().includes('evolutivo');
  const [activeTab, setActiveTab] = useState(isEvolutivo ? 'evolutivo' : 'comparativo');

  // Estado local para área a considerar
  const [areaInput, setAreaInput] = useState(form.imovel_area_a_considerar || '');

  // Sincronizar estatísticas no form sempre que samples mudar
  useEffect(() => {
    if (samples.length > 0) {
      setForm((f) => ({
        ...f,
        calc_media: stats.media_final,
        calc_mediana: stats.mediana,
        calc_desvio_padrao: stats.desvio_padrao,
        calc_coef_variacao: stats.coef_variacao,
        calc_media_ponderada: stats.media_final,
        calc_n_validas: stats.n_validas,
        calc_media_inicial: stats.media_inicial,
        calc_limite_inf_saneamento: stats.limite_inf_saneamento,
        calc_limite_sup_saneamento: stats.limite_sup_saneamento,
        calc_limite_inf_ptam: stats.limite_inf_ptam,
        calc_limite_sup_ptam: stats.limite_sup_ptam,
        fundamentacao_grau: stats.grau_fundamentacao,
        precisao_grau: stats.grau_precisao,
      }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [samples.length, stats.media_final, stats.n_validas]);

  // Calcular valor total
  const valorUnitario = stats.media_final;
  const areaConsiderar = Number(areaInput) || 0;
  const valorTotal = valorUnitario > 0 && areaConsiderar > 0 
    ? parseFloat((valorUnitario * areaConsiderar).toFixed(2))
    : 0;

  const handleUsarValor = () => {
    setForm((f) => ({
      ...f,
      imovel_area_a_considerar: areaConsiderar,
      resultado_valor_unitario: valorUnitario,
      resultado_valor_total: valorTotal,
      resultado_intervalo_inf: stats.limite_inf_ptam,
      resultado_intervalo_sup: stats.limite_sup_ptam,
      total_indemnity: valorTotal,
    }));
  };

  // Verificar se há amostras
  if (stats.n_total === 0) {
    return (
      <div className="space-y-4">
        <SectionHeader
          title="8. Cálculos e Tratamento Estatístico"
          subtitle="Estatísticas calculadas automaticamente com base nas amostras coletadas."
        />
        {isEvolutivo && (
          <>
            <div className="flex gap-1 p-1 bg-gray-100 rounded-lg w-fit">
              <button
                type="button"
                onClick={() => setActiveTab('comparativo')}
                className={`px-4 py-1.5 rounded-md text-xs font-medium transition-colors ${activeTab === 'comparativo' ? 'bg-white shadow-sm text-gray-800' : 'text-gray-500 hover:text-gray-700'}`}
              >
                Comparativo
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('evolutivo')}
                className={`px-4 py-1.5 rounded-md text-xs font-medium transition-colors ${activeTab === 'evolutivo' ? 'bg-emerald-600 text-white shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
              >
                Evolutivo (CUB)
              </button>
            </div>
            {activeTab === 'evolutivo' && (
              <MetodoEvolutivo form={form} setForm={setForm} />
            )}
          </>
        )}
        {(!isEvolutivo || activeTab === 'comparativo') && (
          <div className="p-6 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm">
            <div className="flex items-center gap-2">
              <Info className="w-5 h-5" />
              <span>Nenhuma amostra com área e valor informados. Volte ao passo 6 e preencha as amostras.</span>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="8. Cálculos e Tratamento Estatístico"
        subtitle="Análise estatística completa conforme NBR 14653-2"
      />

      {/* Tabs: Comparativo / Evolutivo */}
      {isEvolutivo && (
        <div className="flex gap-1 p-1 bg-gray-100 rounded-lg w-fit">
          <button
            type="button"
            onClick={() => setActiveTab('comparativo')}
            className={`px-4 py-1.5 rounded-md text-xs font-medium transition-colors ${activeTab === 'comparativo' ? 'bg-white shadow-sm text-gray-800' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Comparativo
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('evolutivo')}
            className={`px-4 py-1.5 rounded-md text-xs font-medium transition-colors ${activeTab === 'evolutivo' ? 'bg-emerald-600 text-white shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Evolutivo (CUB)
          </button>
        </div>
      )}

      {/* Aba Evolutivo */}
      {isEvolutivo && activeTab === 'evolutivo' && (
        <MetodoEvolutivo form={form} setForm={setForm} />
      )}

      {/* Conteúdo Comparativo */}
      {(!isEvolutivo || activeTab === 'comparativo') && (<>

      {/* Bloco A — Saneamento */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700">A. Saneamento das Amostras</h3>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-xs text-gray-500 mb-1">Média Inicial</div>
              <div className="text-lg font-semibold text-gray-800">{fmtBRL(stats.media_inicial)}/m²</div>
            </div>
            <div className="text-center p-3 bg-red-50 rounded-lg border border-red-100">
              <div className="text-xs text-red-600 mb-1">Limite Inferior (-10%)</div>
              <div className="text-lg font-semibold text-red-700">{fmtBRL(stats.limite_inf_saneamento)}/m²</div>
            </div>
            <div className="text-center p-3 bg-red-50 rounded-lg border border-red-100">
              <div className="text-xs text-red-600 mb-1">Limite Superior (+10%)</div>
              <div className="text-lg font-semibold text-red-700">{fmtBRL(stats.limite_sup_saneamento)}/m²</div>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-4">
              <div>
                <span className="text-sm text-gray-600">Total de amostras: </span>
                <span className="text-sm font-semibold text-gray-800">{stats.n_total}</span>
              </div>
              <div className="w-px h-4 bg-gray-300" />
              <div>
                <span className="text-sm text-gray-600">Válidas após saneamento: </span>
                <span className={`text-sm font-semibold ${stats.n_validas >= 3 ? 'text-emerald-600' : 'text-red-600'}`}>
                  {stats.n_validas}
                </span>
              </div>
              <div className="w-px h-4 bg-gray-300" />
              <div>
                <span className="text-sm text-gray-600">Eliminadas: </span>
                <span className={`text-sm font-semibold ${stats.indices_saneadas.length > 0 ? 'text-red-600' : 'text-gray-600'}`}>
                  {stats.indices_saneadas.length}
                </span>
              </div>
            </div>
          </div>

          {stats.n_validas < 3 && (
            <div className="mt-3 flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              <span className="text-sm text-red-700 font-medium">
                Insuficiente — mínimo 3 amostras válidas para PTAM conforme NBR 14653-2
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Bloco B — Estatísticas Finais */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700">B. Estatísticas Finais (pós-saneamento)</h3>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-emerald-50 rounded-lg border border-emerald-100">
              <div className="text-xs text-emerald-600 mb-1 uppercase tracking-wider">Amostras Válidas</div>
              <div className="text-2xl font-bold text-emerald-800">{stats.n_validas}</div>
              <div className="text-xs text-emerald-600 mt-1">de {stats.n_total} inseridas</div>
            </div>

            <div className="text-center p-4 bg-emerald-50 rounded-lg border border-emerald-100">
              <div className="text-xs text-emerald-600 mb-1 uppercase tracking-wider">Média Final</div>
              <div className="text-2xl font-bold text-emerald-800">{fmtBRL(stats.media_final)}/m²</div>
              <div className="text-xs text-emerald-600 mt-1">Valor adotado base</div>
            </div>

            <div className="text-center p-4 bg-blue-50 rounded-lg border border-blue-100">
              <div className="text-xs text-blue-600 mb-1 uppercase tracking-wider">Mediana</div>
              <div className="text-2xl font-bold text-blue-800">{fmtBRL(stats.mediana)}/m²</div>
            </div>

            <div className="text-center p-4 bg-gray-50 rounded-lg border border-gray-100">
              <div className="text-xs text-gray-500 mb-1 uppercase tracking-wider">Desvio Padrão</div>
              <div className="text-xl font-bold text-gray-800">{fmtBRL(stats.desvio_padrao)}</div>
              <div className="text-xs text-gray-400 mt-1">amostral (n-1)</div>
            </div>

            <div className={`text-center p-4 rounded-lg border ${cvColors.bg} ${cvColors.border}`}>
              <div className={`text-xs mb-1 uppercase tracking-wider ${cvColors.text}`}>Coef. Variação</div>
              <div className={`text-2xl font-bold ${cvColors.text}`}>{stats.coef_variacao.toFixed(2)}%</div>
              <div className={`text-xs mt-1 ${cvColors.text}`}>{cvColors.label}</div>
            </div>

            <div className="text-center p-4 bg-gray-50 rounded-lg border border-gray-100">
              <div className="text-xs text-gray-500 mb-1 uppercase tracking-wider">Intervalo PTAM</div>
              <div className="text-sm font-bold text-gray-800">±5% da média</div>
              <div className="text-xs text-gray-400 mt-1">{fmtBRL(stats.limite_inf_ptam)} a {fmtBRL(stats.limite_sup_ptam)}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Bloco C — Intervalo de Valores PTAM */}
      <div className="bg-emerald-900 rounded-xl overflow-hidden">
        <div className="px-6 py-4">
          <h3 className="text-sm font-semibold text-emerald-100 mb-4">C. Intervalo de Valores do PTAM (±5%)</h3>
          
          <div className="grid grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-xs text-emerald-300 mb-1">Limite Inferior</div>
              <div className="text-xl font-bold text-white">{fmtBRL(stats.limite_inf_ptam)}/m²</div>
              <div className="text-xs text-emerald-400 mt-1">-5%</div>
            </div>

            <div className="text-center bg-emerald-800 rounded-lg py-3">
              <div className="text-xs text-emerald-200 mb-1">Valor Adotado</div>
              <div className="text-2xl font-bold text-white">{fmtBRL(stats.media_final)}/m²</div>
              <div className="text-xs text-emerald-300 mt-1">Média final pós-saneamento</div>
            </div>

            <div className="text-center">
              <div className="text-xs text-emerald-300 mb-1">Limite Superior</div>
              <div className="text-xl font-bold text-white">{fmtBRL(stats.limite_sup_ptam)}/m²</div>
              <div className="text-xs text-emerald-400 mt-1">+5%</div>
            </div>
          </div>
        </div>
      </div>

      {/* Bloco D — Graus de Fundamentação e Precisão */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700">D. Graus de Fundamentação e Precisão (NBR 14653-2)</h3>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-2 gap-6">
            {/* Grau de Fundamentação */}
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold ${fundColors.bg} ${fundColors.text}`}>
                  {stats.grau_fundamentacao === 'insuficiente' ? '!' : stats.grau_fundamentacao}
                </div>
                <div>
                  <div className="text-sm text-gray-500">Grau de Fundamentação</div>
                  <div className="text-lg font-semibold text-gray-800">{fundColors.label}</div>
                </div>
              </div>
              <p className="text-sm text-gray-600">{stats.texto_grau_fundamentacao}</p>
              
              {stats.grau_fundamentacao === 'insuficiente' && (
                <div className="flex items-center gap-2 p-2 bg-red-50 border border-red-200 rounded-lg">
                  <AlertTriangle className="w-4 h-4 text-red-500" />
                  <span className="text-xs text-red-700">Adicione mais amostras para atingir o grau mínimo</span>
                </div>
              )}
            </div>

            {/* Grau de Precisão */}
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold ${precColors.bg} ${precColors.text}`}>
                  {stats.grau_precisao === 'fora' ? '!' : stats.grau_precisao}
                </div>
                <div>
                  <div className="text-sm text-gray-500">Grau de Precisão</div>
                  <div className="text-lg font-semibold text-gray-800">{precColors.label}</div>
                </div>
              </div>
              <p className="text-sm text-gray-600">{stats.texto_grau_precisao}</p>
              
              {stats.grau_precisao === 'fora' && (
                <div className="flex items-center gap-2 p-2 bg-red-50 border border-red-200 rounded-lg">
                  <AlertTriangle className="w-4 h-4 text-red-500" />
                  <span className="text-xs text-red-700">CV > 30% — laudo sem validade técnica. Revisar amostras.</span>
                </div>
              )}
              {stats.grau_precisao === 'III' && (
                <div className="flex items-center gap-2 p-2 bg-emerald-50 border border-emerald-200 rounded-lg">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span className="text-xs text-emerald-700">Precisão máxima conforme NBR 14653-2</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Bloco E — Área e Valor Final */}
      <div className="bg-white rounded-xl border-2 border-emerald-400 overflow-hidden">
        <div className="bg-emerald-700 px-4 py-3">
          <h3 className="text-sm font-semibold text-white">E. Área e Valor Final do Imóvel</h3>
        </div>
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Área a considerar (m²)
              </label>
              <input
                type="number"
                step="0.01"
                className="w-full h-10 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                value={areaInput}
                onChange={(e) => setAreaInput(e.target.value)}
                placeholder="Ex: 250,00"
              />
              <p className="mt-1 text-xs text-gray-400">
                Área efetiva utilizada para o cálculo do valor total
              </p>
            </div>

            <div className="flex items-end">
              <div className="w-full p-4 bg-emerald-50 rounded-lg border border-emerald-200">
                <div className="text-xs text-emerald-600 mb-1">Cálculo Automático</div>
                <div className="text-sm text-gray-700">
                  {valorUnitario > 0 && areaConsiderar > 0 ? (
                    <span>
                      <span className="font-semibold text-emerald-800">{fmtBRL(valorUnitario)}/m²</span>
                      {' × '}
                      <span className="font-semibold text-emerald-800">{fmtNum(areaConsiderar)} m²</span>
                      {' = '}
                      <span className="font-bold text-emerald-900 text-lg">{fmtBRL(valorTotal)}</span>
                    </span>
                  ) : (
                    <span className="text-gray-400 italic">Preencha a área para calcular o valor total</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {valorTotal > 0 && (
            <div className="flex items-center justify-between p-4 bg-emerald-100 rounded-lg border border-emerald-300">
              <div>
                <div className="text-xs text-emerald-700 uppercase tracking-wide mb-1 font-medium">
                  Valor Total do Imóvel
                </div>
                <div className="text-3xl font-bold text-emerald-900 tabular-nums">
                  {fmtBRL(valorTotal)}
                </div>
                <div className="text-xs text-emerald-600 mt-1">
                  {fmtBRL(valorUnitario)}/m² × {fmtNum(areaConsiderar)} m²
                </div>
              </div>
              
              <button
                type="button"
                onClick={handleUsarValor}
                className="bg-emerald-700 hover:bg-emerald-800 active:scale-95 text-white text-sm font-semibold px-6 py-3 rounded-xl shadow-sm transition-all"
              >
                Usar estes valores no resultado
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Campos adicionais */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700">Observações Adicionais</h3>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Fatores de Homogeneização aplicados
            </label>
            <Textarea
              value={form.calc_fatores_homogeneizacao || ''}
              onChange={(e) => setForm({ ...form, calc_fatores_homogeneizacao: e.target.value })}
              rows={3}
              placeholder="Descreva os fatores aplicados: localização, área, padrão construtivo, etc."
            />
            <div className="mt-1 flex justify-end">
              <AiButton
                onClick={() => onAi('calc_fatores_homogeneizacao')}
                loading={aiLoading === 'calc_fatores_homogeneizacao'}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Observações sobre os cálculos
            </label>
            <Textarea
              value={form.calc_observacoes || ''}
              onChange={(e) => setForm({ ...form, calc_observacoes: e.target.value })}
              rows={3}
              placeholder="Outliers descartados, ajustes realizados, limitações dos dados..."
            />
            <div className="mt-1 flex justify-end">
              <AiButton
                onClick={() => onAi('calc_observacoes')}
                loading={aiLoading === 'calc_observacoes'}
              />
            </div>
          </div>
        </div>
      </div>
      </>)}
    </div>
  );
};
