import React from 'react';
import { FileDown, Download, MessageCircle, Mail, Loader2 } from 'lucide-react';

const ExportBar = ({ vistoria, loading = {}, onPdf, onDocx, onWhatsApp, onEmail }) => {
  const id = vistoria?.id;

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <button
        type="button"
        onClick={() => onPdf && onPdf(id)}
        disabled={loading[`${id}_pdf`]}
        title="Exportar PDF"
        className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium
                   bg-emerald-900 text-white hover:bg-emerald-800 disabled:opacity-50 transition"
      >
        {loading[`${id}_pdf`]
          ? <Loader2 className="w-4 h-4 animate-spin" />
          : <FileDown className="w-4 h-4" />}
        PDF
      </button>

      <button
        type="button"
        onClick={() => onDocx && onDocx(id)}
        disabled={loading[`${id}_docx`]}
        title="Exportar DOCX"
        className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium
                   border border-gray-200 text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition"
      >
        {loading[`${id}_docx`]
          ? <Loader2 className="w-4 h-4 animate-spin" />
          : <Download className="w-4 h-4" />}
        DOCX
      </button>

      <button
        type="button"
        onClick={() => onWhatsApp && onWhatsApp(vistoria)}
        title="Compartilhar via WhatsApp"
        className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium
                   border border-gray-200 text-gray-700 hover:bg-green-50 hover:border-green-300 hover:text-green-700 transition"
      >
        <MessageCircle className="w-4 h-4" />
        WhatsApp
      </button>

      <button
        type="button"
        onClick={() => onEmail && onEmail(vistoria)}
        title="Compartilhar por Email"
        className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium
                   border border-gray-200 text-gray-700 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition"
      >
        <Mail className="w-4 h-4" />
        Email
      </button>
    </div>
  );
};

export default ExportBar;
