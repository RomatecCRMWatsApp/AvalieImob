import React from "react";
import { BarChart3 } from "lucide-react";
import { CalculoComparativoPage } from "./CalculoComparativoPage";

export function Calculos() {
  return (
    <div className="space-y-4 max-w-5xl">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-orange-700/20 rounded-xl flex items-center justify-center">
          <BarChart3 className="w-5 h-5 text-orange-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Cálculos</h1>
          <p className="text-gray-500 text-xs">Método Comparativo Direto · ABNT NBR 14.653</p>
        </div>
      </div>

      <CalculoComparativoPage />
    </div>
  );
}
