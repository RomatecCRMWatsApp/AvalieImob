import React from "react";
import { PTAMList } from "../components/PTAM/PTAMList";
import { FileText } from "lucide-react";

export function PTAMs() {
  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-green-700/20 rounded-xl flex items-center justify-center">
          <FileText className="w-5 h-5 text-green-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">PTAMs</h1>
          <p className="text-gray-500 text-xs">Pareceres técnicos emitidos</p>
        </div>
      </div>

      <PTAMList />
    </div>
  );
}
