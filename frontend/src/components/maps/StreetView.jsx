// @module maps/StreetView — Embed Google Street View ou fallback link externo
import React from 'react';
import { ExternalLink } from 'lucide-react';

const API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY;

const StreetView = ({ lat, lng, endereco, height = 280 }) => {
  if (!lat || !lng) {
    return (
      <div className="rounded-xl border border-gray-200 bg-gray-50 flex items-center justify-center text-sm text-gray-400"
        style={{ height }}>
        Coordenadas necessárias para Street View.
      </div>
    );
  }

  const mapsUrl = `https://www.google.com/maps?q=${lat},${lng}&layer=c&cbll=${lat},${lng}`;

  if (API_KEY) {
    const src = `https://www.google.com/maps/embed/v1/streetview?key=${API_KEY}&location=${lat},${lng}&heading=0&pitch=0&fov=90`;
    return (
      <div className="rounded-xl overflow-hidden border border-gray-200 shadow-sm">
        <div className="px-3 py-2 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
          <span className="text-xs font-semibold text-gray-600">Street View</span>
          <a href={mapsUrl} target="_blank" rel="noopener noreferrer"
            className="text-xs text-emerald-700 hover:underline flex items-center gap-1">
            <ExternalLink className="w-3 h-3" /> Abrir no Google Maps
          </a>
        </div>
        <iframe title="Street View" src={src} width="100%" height={height} style={{ border: 0 }} loading="lazy" />
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 space-y-3" style={{ minHeight: height / 2 }}>
      <div className="text-xs font-semibold text-gray-600">Street View</div>
      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
        Configure <code className="font-mono">REACT_APP_GOOGLE_MAPS_API_KEY</code> para Street View embutido.
      </p>
      <a href={mapsUrl} target="_blank" rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-700 hover:underline">
        <ExternalLink className="w-4 h-4" />
        Ver no Google Maps Street View
      </a>
    </div>
  );
};

export default StreetView;
