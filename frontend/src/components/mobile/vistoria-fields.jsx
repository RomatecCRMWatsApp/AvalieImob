// @module vistoria-fields — seções de campos do MobileVistoriaForm
import React, { useState } from 'react';
import { MapPin, Loader2 } from 'lucide-react';

const F = 'w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 min-h-[48px] transition-colors';
const L = 'block text-xs font-semibold text-gray-600 mb-1 mt-3 uppercase tracking-wide';

export const VistoriaFields = ({ section, form, set, PhotoCapture, Signature }) => {
  const [gpsLoading, setGpsLoading] = useState(false);

  const getGPS = () => {
    if (!navigator.geolocation) return;
    setGpsLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        set('lat', pos.coords.latitude.toFixed(6));
        set('lng', pos.coords.longitude.toFixed(6));
        setGpsLoading(false);
      },
      () => setGpsLoading(false),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  if (section === 0) return (
    <div className="space-y-1">
      <label className={L}>Solicitante</label>
      <input className={F} value={form.solicitante}
        onChange={(e) => set('solicitante', e.target.value)} placeholder="Nome do solicitante" />
      <label className={L}>Locatário / Vistoriado</label>
      <input className={F} value={form.locatario}
        onChange={(e) => set('locatario', e.target.value)} placeholder="Nome do locatário" />
    </div>
  );

  if (section === 1) return (
    <div className="space-y-1">
      <label className={L}>Endereço do Imóvel</label>
      <input className={F} value={form.imovel_endereco}
        onChange={(e) => set('imovel_endereco', e.target.value)}
        placeholder="Rua, número, bairro, cidade" />
      <label className={L}>Coordenadas GPS</label>
      <div className="flex gap-2 mt-1">
        <input className={`${F} flex-1`} value={form.lat}
          onChange={(e) => set('lat', e.target.value)} placeholder="Latitude" />
        <input className={`${F} flex-1`} value={form.lng}
          onChange={(e) => set('lng', e.target.value)} placeholder="Longitude" />
        <button type="button" onClick={getGPS} disabled={gpsLoading}
          className="flex items-center justify-center min-w-[48px] min-h-[48px] rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 active:scale-95 transition-all disabled:opacity-60">
          {gpsLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <MapPin className="w-5 h-5" />}
        </button>
      </div>
    </div>
  );

  if (section === 2) return (
    <div className="space-y-1">
      <label className={L}>Tipo de Imóvel</label>
      <select className={F} value={form.tipo_imovel} onChange={(e) => set('tipo_imovel', e.target.value)}>
        <option value="">Selecione</option>
        {['Apartamento', 'Casa', 'Sala Comercial', 'Galpão', 'Terreno'].map((t) => (
          <option key={t}>{t}</option>
        ))}
      </select>
      <label className={L}>Área Total (m²)</label>
      <input className={F} type="number" value={form.area_total}
        onChange={(e) => set('area_total', e.target.value)} placeholder="Ex: 80" />
      <div className="flex gap-3">
        <div className="flex-1">
          <label className={L}>Quartos</label>
          <input className={F} type="number" value={form.num_quartos}
            onChange={(e) => set('num_quartos', e.target.value)} placeholder="0" />
        </div>
        <div className="flex-1">
          <label className={L}>Banheiros</label>
          <input className={F} type="number" value={form.num_banheiros}
            onChange={(e) => set('num_banheiros', e.target.value)} placeholder="0" />
        </div>
      </div>
      <label className={L}>Estado de Conservação</label>
      <select className={F} value={form.estado_conservacao}
        onChange={(e) => set('estado_conservacao', e.target.value)}>
        <option value="">Selecione</option>
        {['Ótimo', 'Bom', 'Regular', 'Ruim', 'Péssimo'].map((s) => <option key={s}>{s}</option>)}
      </select>
      <label className={L}>Observações</label>
      <textarea className={`${F} min-h-[80px] resize-none`}
        value={form.observacoes}
        onChange={(e) => set('observacoes', e.target.value)}
        placeholder="Anotações gerais..." />
    </div>
  );

  if (section === 3) return (
    <div>
      <label className={L}>Fotografias do Imóvel</label>
      <div className="mt-2">{PhotoCapture}</div>
    </div>
  );

  if (section === 4) return (
    <div>
      <label className={L}>Assinatura do Vistoriador</label>
      <div className="mt-2">{Signature}</div>
    </div>
  );

  return null;
};
