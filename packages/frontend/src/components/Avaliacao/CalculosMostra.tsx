import React, { useState } from "react";
import { trpc } from "../../lib/trpc";
import { Button } from "../UI/Button";
import { useNotification } from "../../contexts/NotificationContext";
import { BarChart3, TrendingUp, AlertTriangle } from "lucide-react";

interface CalculosMostraProps {
  avaliacaoId: string;
  metodologia: "comparativo" | "evolutivo" | "misto";
}

const fmt = (n: number) =>
  n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const pct = (n: number) => `${n.toFixed(2)}%`;

export function CalculosMostra({ avaliacaoId, metodologia }: CalculosMostraProps) {
  const { success, error: notify } = useNotification();
  const utils = trpc.useUtils();

  const [areaImpactada, setAreaImpactada] = useState("1000");
  const [valorTerreno, setValorTerreno] = useState("");
  const [valorBenfeitorias, setValorBenfeitorias] = useState("0");
  const [depreciacao, setDepreciacao] = useState("0");
  const [fatorLocalizacao, setFatorLocalizacao] = useState("1.0");

  const calculos = trpc.calculo.listarPorAvaliacao.useQuery({ avaliacao_id: avaliacaoId });

  const comparativoMutation = trpc.calculo.calcularComparativo.useMutation({
    onSuccess: () => {
      success("Cálculo comparativo realizado!");
      void utils.calculo.listarPorAvaliacao.invalidate({ avaliacao_id: avaliacaoId });
    },
    onError: (err) => notify(err.message),
  });

  const evolutivoMutation = trpc.calculo.calcularEvolutivo.useMutation({
    onSuccess: () => {
      success("Cálculo evolutivo realizado!");
      void utils.calculo.listarPorAvaliacao.invalidate({ avaliacao_id: avaliacaoId });
    },
    onError: (err) => notify(err.message),
  });

  const handleComparativo = () => {
    comparativoMutation.mutate({
      avaliacao_id: avaliacaoId,
      area_impactada: parseFloat(areaImpactada) || 1000,
      usar_unitarios: true,
    });
  };

  const handleEvolutivo = () => {
    evolutivoMutation.mutate({
      avaliacao_id: avaliacaoId,
      valor_terreno: parseFloat(valorTerreno) || 0,
      valor_benfeitorias: parseFloat(valorBenfeitorias) || 0,
      depreciacao_percentual: parseFloat(depreciacao) || 0,
      fator_localizacao: parseFloat(fatorLocalizacao) || 1.0,
    });
  };

  return (
    <div className="space-y-4">
      {/* Comparativo */}
      {(metodologia === "comparativo" || metodologia === "misto") && (
        <div className="bg-gray-800/40 border border-gray-700/40 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-green-400" />
            <h4 className="text-sm font-semibold text-white">Método Comparativo</h4>
          </div>
          <p className="text-xs text-gray-500 mb-3">
            Requer mínimo de 3 amostras cadastradas com valor R$/m².
          </p>
          <div className="flex items-end gap-3">
            <div className="flex-1 space-y-1">
              <label className="block text-xs font-medium text-gray-400">Área Impactada (m²)</label>
              <input
                type="number"
                value={areaImpactada}
                onChange={(e) => setAreaImpactada(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-600 transition-colors"
              />
            </div>
            <Button
              onClick={handleComparativo}
              loading={comparativoMutation.isPending}
              size="sm"
            >
              Calcular
            </Button>
          </div>
        </div>
      )}

      {/* Evolutivo */}
      {(metodologia === "evolutivo" || metodologia === "misto") && (
        <div className="bg-gray-800/40 border border-gray-700/40 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-blue-400" />
            <h4 className="text-sm font-semibold text-white">Método Evolutivo</h4>
          </div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            {[
              { label: "Valor Terreno (R$)", val: valorTerreno, set: setValorTerreno },
              { label: "Benfeitorias (R$)", val: valorBenfeitorias, set: setValorBenfeitorias },
              { label: "Depreciação (%)", val: depreciacao, set: setDepreciacao },
              { label: "Fator Localização", val: fatorLocalizacao, set: setFatorLocalizacao },
            ].map((f) => (
              <div key={f.label} className="space-y-1">
                <label className="block text-xs font-medium text-gray-400">{f.label}</label>
                <input
                  type="number"
                  value={f.val}
                  onChange={(e) => f.set(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-600 transition-colors"
                />
              </div>
            ))}
          </div>
          <Button onClick={handleEvolutivo} loading={evolutivoMutation.isPending} size="sm">
            Calcular Evolutivo
          </Button>
        </div>
      )}

      {/* Results */}
      {calculos.data && calculos.data.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            Resultados ({calculos.data.length})
          </p>
          {calculos.data.map((c) => (
            <div key={c.id} className="bg-green-900/10 border border-green-700/30 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs bg-green-700/20 text-green-400 px-2 py-0.5 rounded-md capitalize">
                  {c.tipo}
                </span>
                <p className="text-xl font-bold text-green-400">{fmt(c.valor_total)}</p>
              </div>
              {c.tipo === "comparativo" && c.valor_unitario && (
                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div>
                    <p className="text-gray-500">Unitário</p>
                    <p className="text-white font-medium">{fmt(c.valor_unitario)}/m²</p>
                  </div>
                  {c.desvio_padrao && (
                    <div>
                      <p className="text-gray-500">Desvio Padrão</p>
                      <p className="text-white font-medium">{fmt(c.desvio_padrao)}</p>
                    </div>
                  )}
                  {c.coeficiente_variacao && (
                    <div>
                      <p className="text-gray-500">CV</p>
                      <p
                        className={`font-medium ${
                          parseFloat(c.coeficiente_variacao) <= 30
                            ? "text-green-400"
                            : parseFloat(c.coeficiente_variacao) <= 40
                              ? "text-yellow-400"
                              : "text-red-400"
                        }`}
                      >
                        {pct(parseFloat(c.coeficiente_variacao))}
                        {parseFloat(c.coeficiente_variacao) > 40 && (
                          <AlertTriangle className="inline w-3 h-3 ml-1" />
                        )}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
