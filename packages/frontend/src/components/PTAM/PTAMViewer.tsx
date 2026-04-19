import React from "react";
import { FileText, Download, Calendar, Hash } from "lucide-react";

interface PTAMViewerProps {
  ptam: {
    ptam_emitidos: {
      id: string;
      numero_ptam: string;
      url_docx: string | null;
      data_emissao: Date | null;
    };
    avaliacoes: {
      titulo: string;
      metodologia: string | null;
    };
  };
}

export function PTAMViewer({ ptam }: PTAMViewerProps) {
  const { ptam_emitidos: p, avaliacoes: av } = ptam;

  return (
    <div className="bg-gray-800/50 border border-gray-700/40 rounded-xl p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-green-700/20 rounded-lg flex items-center justify-center flex-shrink-0">
            <FileText className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">{av.titulo}</p>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <Hash className="w-3 h-3" />
                {p.numero_ptam}
              </span>
              {p.data_emissao && (
                <span className="flex items-center gap-1 text-xs text-gray-500">
                  <Calendar className="w-3 h-3" />
                  {new Date(p.data_emissao).toLocaleDateString("pt-BR")}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs bg-green-700/20 text-green-400 px-2 py-0.5 rounded-md">
            Emitido
          </span>
          {p.url_docx && (
            <a
              href={p.url_docx}
              download
              className="p-1.5 hover:bg-green-700/20 rounded-lg text-green-400 transition"
              title="Download DOCX"
            >
              <Download className="w-4 h-4" />
            </a>
          )}
        </div>
      </div>

      {av.metodologia && (
        <p className="text-xs text-gray-500 capitalize">
          Metodologia: {av.metodologia}
        </p>
      )}
    </div>
  );
}
