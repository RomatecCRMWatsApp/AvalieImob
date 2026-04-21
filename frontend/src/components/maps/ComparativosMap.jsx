// @module maps/ComparativosMap — Mapa Leaflet com imóvel avaliado + amostras numeradas e raio 500m
import React, { useEffect, useRef, useState } from 'react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const greenIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
});

const makeNumberedIcon = (n) =>
  L.divIcon({
    html: `<div style="width:24px;height:24px;border-radius:50%;background:#1e3a5f;color:#fff;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;border:2px solid #fff;box-shadow:0 1px 4px #0004">${n}</div>`,
    className: '',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -14],
  });

const fmt = (v) => v > 0 ? `R$ ${Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}` : '—';

const ComparativosMap = ({ ptamId, imovelCoords, imovelAddress, samples = [], height = 340 }) => {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!ptamId) return;
    setLoading(true);
    const token = localStorage.getItem('romatec_token');
    const base = process.env.REACT_APP_BACKEND_URL || '';
    fetch(`${base}/api/maps/comparativos/${ptamId}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.ok ? r.json() : null)
      .then((d) => setData(d))
      .catch(() => null)
      .finally(() => setLoading(false));
  }, [ptamId]);

  const imovel = data?.imovel || { coords: imovelCoords, address: imovelAddress };
  const pts = data?.samples || samples;

  useEffect(() => {
    if (!mapRef.current) return;
    const center = imovel?.coords;
    if (!center) return;

    if (mapInstance.current) { mapInstance.current.remove(); mapInstance.current = null; }

    const map = L.map(mapRef.current, { zoomControl: true, scrollWheelZoom: false }).setView(
      [center.lat, center.lng], 15
    );
    mapInstance.current = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap', maxZoom: 19,
    }).addTo(map);

    L.circle([center.lat, center.lng], {
      radius: 500, color: '#064e3b', fillColor: '#064e3b', fillOpacity: 0.07, weight: 1.5,
    }).addTo(map);

    L.marker([center.lat, center.lng], { icon: greenIcon })
      .addTo(map)
      .bindPopup(`<strong>Imóvel avaliado</strong><br>${imovel.address || ''}`)
      .openPopup();

    pts.forEach((s) => {
      if (!s.coords) return;
      const distM = map.distance([center.lat, center.lng], [s.coords.lat, s.coords.lng]);
      L.marker([s.coords.lat, s.coords.lng], { icon: makeNumberedIcon(s.idx) })
        .addTo(map)
        .bindPopup(
          `<strong>Amostra ${s.idx}</strong><br>${s.address}<br>` +
          `<span style="color:#065f46;font-weight:600">${fmt(s.value_per_sqm)}/m²</span><br>` +
          `Distância: ${Math.round(distM)} m`
        );
    });
  }, [data, imovel, pts]);

  useEffect(() => () => { if (mapInstance.current) { mapInstance.current.remove(); mapInstance.current = null; } }, []);

  if (loading) return (
    <div style={{ height }} className="rounded-xl border border-gray-200 bg-gray-50 flex items-center justify-center text-sm text-gray-400">
      Carregando mapa de comparativos...
    </div>
  );

  if (!imovel?.coords) return (
    <div style={{ height }} className="rounded-xl border border-gray-200 bg-gray-50 flex items-center justify-center text-sm text-gray-400 px-4 text-center">
      Preencha o endereço do imóvel para visualizar o mapa de comparativos.
    </div>
  );

  return (
    <div className="rounded-xl overflow-hidden border border-gray-200 shadow-sm">
      <div className="px-3 py-2 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-600">Mapa de Comparativos</span>
        <span className="text-xs text-gray-400">{pts.filter(s => s.coords).length} amostra(s) no mapa · raio 500 m</span>
      </div>
      <div ref={mapRef} style={{ height }} />
    </div>
  );
};

export default ComparativosMap;
