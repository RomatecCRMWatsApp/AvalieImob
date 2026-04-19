import React, { useState } from "react";
import { trpc } from "../lib/trpc";
import {
  useMetodoComparativo,
  formatarMoeda,
  formatarPorcentagem,
} from "../hooks/useMetodoComparativo";
import {
  Plus,
  Trash2,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  BarChart3,
} from "lucide-react";

interface Amostra {
  id: string;
  descricao: string;
  valor_unitario_m2: number;
  area_m2: number;
  fonte: string;
}

export function CalculoComparativoPage() {
  const [avaliacao_id] = useState(
    new URLSearchParams(window.location.search).get("avaliacao_id") || ""
  );
  const [area_impactada, setArea_impactada] = useState(5000);
  const [amostras, setAmostras] = useState<Amostra[]>([
    {
      id: "1",
      descricao: "Terreno urbano próximo - Valor: R$ 150.000",
      valor_unitario_m2: 300,
      area_m2: 500,
      fonte: "CRECI",
    },
    {
      id: "2",
      descricao: "Propriedade comercial zona industrial",
      valor_unitario_m2: 350,
      area_m2: 800,
      fonte: "Imobiliária",
    },
    {
      id: "3",
      descricao: "Lote comercial BR-222",
      valor_unitario_m2: 280,
      area_m2: 1000,
      fonte: "Oferta Pública",
    },
  ]);

  const [novaAmostra, setNovaAmostra] = useState({
    descricao: "",
    valor_unitario_m2: 0,
    area_m2: 0,
    fonte: "",
  });

  const resultado = useMetodoComparativo(amostras, area_impactada);

  const handleAdicionarAmostra = () => {
    if (
      novaAmostra.descricao &&
      novaAmostra.valor_unitario_m2 > 0
    ) {
      setAmostras([
        ...amostras,
        {
          id: Date.now().toString(),
          ...novaAmostra,
        },
      ]);
      setNovaAmostra({
        descricao: "",
        valor_unitario_m2: 0,
        area_m2: 0,
        fonte: "",
      });
    }
  };

  const handleRemoverAmostra = (id: string) => {
    setAmostras(amostras.filter((a) => a.id !== id));
  };

  const calcularMutation = trpc.calculo.calcularComparativo.useMutation({
    onSuccess: (data) => {
      alert(
        `✓ Cálculo realizado com sucesso!\nValor Total: ${formatarMoeda(data.valor_total)}`
      );
    },
    onError: (error) => {
      alert(`Erro: ${error.message}`);
    },
  });

  const handleSalvarCalculo = () => {
    if (!avaliacao_id) {
      alert("Carregue uma avaliação primeiro");
      return;
    }
    calcularMutation.mutate({
      avaliacao_id,
      area_impactada,
      usar_unitarios: true,
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-gray-900 to-green-900 border border-green-700/30 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-2">
          <BarChart3 className="w-6 h-6 text-green-400" />
          <h1 className="text-2xl font-bold">Método Comparativo</h1>
        </div>
        <p className="text-gray-400">
          ABNT NBR 14.653 - Cálculo baseado em análise estatística de amostras
        </p>
      </div>

      {/* Área Impactada */}
      <div className="bg-gray-900 border border-gray-700/30 rounded-lg p-6">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Área Impactada (m²)
        </label>
        <input
          type="number"
          value={area_impactada}
          onChange={(e) => setArea_impactada(Number(e.target.value))}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
        />
        <p className="text-gray-500 text-sm mt-2">
          Área que será impactada pela servidão ou avaliação
        </p>
      </div>

      {/* Tabela de Amostras */}
      <div className="bg-gray-900 border border-gray-700/30 rounded-lg p-6">
        <h2 className="text-lg font-bold mb-4">Amostras de Mercado</h2>

        {/* Tabela */}
        <div className="overflow-x-auto mb-6">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-green-700/30">
                <th className="text-left py-3 px-4 text-gray-400">Descrição</th>
                <th className="text-right py-3 px-4 text-gray-400">R$/m²</th>
                <th className="text-right py-3 px-4 text-gray-400">Área (m²)</th>
                <th className="text-left py-3 px-4 text-gray-400">Fonte</th>
                <th className="text-center py-3 px-4 text-gray-400">Ação</th>
              </tr>
            </thead>
            <tbody>
              {amostras.map((amostra) => (
                <tr key={amostra.id} className="border-b border-gray-700/20 hover:bg-gray-800/50">
                  <td className="py-3 px-4">{amostra.descricao}</td>
                  <td className="text-right py-3 px-4 text-green-400 font-mono">
                    {formatarMoeda(amostra.valor_unitario_m2)}
                  </td>
                  <td className="text-right py-3 px-4 font-mono">
                    {amostra.area_m2.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-gray-400 text-xs">
                    {amostra.fonte}
                  </td>
                  <td className="text-center py-3 px-4">
                    <button
                      onClick={() => handleRemoverAmostra(amostra.id)}
                      className="p-1 hover:bg-red-600/20 rounded transition text-red-400"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Adicionar Nova Amostra */}
        <div className="bg-gray-800/50 rounded-lg p-4 space-y-3">
          <h3 className="font-semibold text-sm text-gray-300">
            Adicionar Nova Amostra
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Descrição da amostra"
              value={novaAmostra.descricao}
              onChange={(e) =>
                setNovaAmostra({ ...novaAmostra, descricao: e.target.value })
              }
              className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
            />
            <input
              type="number"
              placeholder="Valor R$/m²"
              value={novaAmostra.valor_unitario_m2}
              onChange={(e) =>
                setNovaAmostra({
                  ...novaAmostra,
                  valor_unitario_m2: Number(e.target.value),
                })
              }
              className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
            />
            <input
              type="text"
              placeholder="Fonte (CRECI, Imob, etc)"
              value={novaAmostra.fonte}
              onChange={(e) =>
                setNovaAmostra({ ...novaAmostra, fonte: e.target.value })
              }
              className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
            />
            <button
              onClick={handleAdicionarAmostra}
              className="bg-green-600 hover:bg-green-700 text-white rounded px-4 py-2 flex items-center justify-center gap-2 text-sm font-medium transition"
            >
              <Plus className="w-4 h-4" />
              Adicionar
            </button>
          </div>
        </div>
      </div>

      {/* Resultados */}
      <div className="bg-gray-900 border border-gray-700/30 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-6">
          {resultado.valido ? (
            <CheckCircle className="w-6 h-6 text-green-400" />
          ) : (
            <AlertCircle className="w-6 h-6 text-yellow-400" />
          )}
          <h2 className="text-lg font-bold">Resultados</h2>
        </div>

        {/* Mensagem de validação */}
        <div
          className={`mb-6 p-3 rounded-lg text-sm ${
            resultado.valido
              ? "bg-green-500/10 border border-green-500/30 text-green-300"
              : "bg-yellow-500/10 border border-yellow-500/30 text-yellow-300"
          }`}
        >
          {resultado.mensagem}
        </div>

        {resultado.valido && (
          <>
            {/* Grid de Resultados */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
              {[
                {
                  label: "Valor Unitário Médio",
                  valor: formatarMoeda(resultado.media),
                  destaque: true,
                },
                {
                  label: "Desvio Padrão",
                  valor: formatarMoeda(resultado.desvio_padrao),
                },
                {
                  label: "Coef. Variação (CV)",
                  valor: formatarPorcentagem(resultado.coeficiente_variacao),
                },
                {
                  label: "Intervalo Mínimo",
                  valor: formatarMoeda(resultado.intervalo_minimo),
                },
                {
                  label: "Intervalo Máximo",
                  valor: formatarMoeda(resultado.intervalo_maximo),
                },
                {
                  label: "Margem de Erro",
                  valor: formatarPorcentagem(resultado.margem_erro),
                },
              ].map((item, idx) => (
                <div
                  key={idx}
                  className={`p-4 rounded-lg ${
                    item.destaque
                      ? "bg-gradient-to-br from-green-600/20 to-green-700/20 border border-green-500/30"
                      : "bg-gray-800/50 border border-gray-700/30"
                  }`}
                >
                  <p className="text-gray-400 text-sm mb-1">{item.label}</p>
                  <p
                    className={`text-xl font-bold ${
                      item.destaque
                        ? "text-green-400"
                        : "text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-yellow-400"
                    }`}
                  >
                    {item.valor}
                  </p>
                </div>
              ))}
            </div>

            {/* Valor Total Indenizatório */}
            <div className="bg-gradient-to-r from-green-600/30 to-green-700/30 border border-green-500/30 rounded-lg p-6 mb-6">
              <p className="text-gray-400 text-sm mb-2">
                Valor Total Indenizatório
              </p>
              <p className="text-4xl font-bold text-green-400">
                {formatarMoeda(resultado.valor_total)}
              </p>
              <p className="text-gray-400 text-xs mt-2">
                {area_impactada.toLocaleString()} m² × {formatarMoeda(resultado.media)}
              </p>
            </div>

            {/* Info Técnica */}
            <div className="bg-gray-800/50 rounded-lg p-4 text-sm text-gray-400">
              <p className="font-semibold text-white mb-2">Informações Técnicas:</p>
              <ul className="space-y-1">
                <li>✓ Amostras analisadas: {resultado.amostra_tamanho}</li>
                <li>✓ Intervalo de confiança: 95% (z = 1.96)</li>
                <li>✓ Norma aplicada: ABNT NBR 14.653</li>
                <li>
                  {resultado.coeficiente_variacao <= 30
                    ? "✓ CV ≤ 30% - Cálculo ÓTIMO"
                    : resultado.coeficiente_variacao <= 40
                    ? "⚠️ CV ≤ 40% - Cálculo BOM"
                    : "❌ CV > 40% - Revisar amostras"}
                </li>
              </ul>
            </div>

            {/* Salvar */}
            <button
              onClick={handleSalvarCalculo}
              disabled={calcularMutation.isPending}
              className="w-full mt-6 bg-gradient-to-r from-green-600 to-green-500 hover:from-green-700 hover:to-green-600 text-white font-semibold py-3 rounded-lg transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <TrendingUp className="w-5 h-5" />
              {calcularMutation.isPending
                ? "Salvando..."
                : "Salvar Cálculo e Gerar PTAM"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
