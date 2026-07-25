// @module maps/PoligonalLeaflet — Preview da poligonal SIG-RI sobre imagem de
// satélite (Leaflet + ESRI World Imagery). Recebe um GeoJSON FeatureCollection
// em SIRGAS 2000 (EPSG:4674, lon/lat) — o mesmo do endpoint /geojson.
import React, { useEffect, useRef } from 'react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

const SAT = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const GOLD = '#C9A227';
const GREEN = '#0C3320';

export default function PoligonalLeaflet({ geojson, height = 300 }) {
  const ref = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);

  // Inicializa o mapa uma vez
  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    mapRef.current = L.map(ref.current, { zoomControl: true, scrollWheelZoom: false })
      .setView([-15.78, -47.93], 4);
    L.tileLayer(SAT, { attribution: 'Tiles © Esri — World Imagery', maxZoom: 20 }).addTo(mapRef.current);
    setTimeout(() => mapRef.current && mapRef.current.invalidateSize(), 120);
  }, []);

  // Redesenha a poligonal quando o GeoJSON muda
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (layerRef.current) { layerRef.current.remove(); layerRef.current = null; }
    const feats = (geojson && geojson.features) || [];
    const grp = L.featureGroup().addTo(map);
    layerRef.current = grp;
    let temGeom = false;
    feats.forEach((f) => {
      const coords = (f && f.geometry && f.geometry.coordinates && f.geometry.coordinates[0]) || [];
      const latlngs = coords.map(([lon, lat]) => [lat, lon]).filter(([la, ln]) => !isNaN(la) && !isNaN(ln));
      if (latlngs.length < 3) return;
      temGeom = true;
      L.polygon(latlngs, { color: GOLD, weight: 2, fillColor: GOLD, fillOpacity: 0.18 }).addTo(grp);
      const fechado = latlngs.length > 1
        && latlngs[0][0] === latlngs[latlngs.length - 1][0]
        && latlngs[0][1] === latlngs[latlngs.length - 1][1];
      const n = fechado ? latlngs.length - 1 : latlngs.length;
      for (let i = 0; i < n; i++) {
        L.circleMarker(latlngs[i], { radius: 4, color: GREEN, weight: 2, fillColor: '#fff', fillOpacity: 1 })
          .bindTooltip(`P-${String(i + 1).padStart(2, '0')}`, { direction: 'top' })
          .addTo(grp);
      }
    });
    if (temGeom) {
      try { map.fitBounds(grp.getBounds(), { padding: [24, 24], maxZoom: 19 }); } catch (e) { /* bounds vazio */ }
    }
    setTimeout(() => map.invalidateSize(), 120);
  }, [geojson]);

  // Cleanup
  useEffect(() => () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } }, []);

  const vazio = !((geojson && geojson.features) || []).some(
    (f) => f && f.geometry && f.geometry.coordinates && (f.geometry.coordinates[0] || []).length >= 3);
  return (
    <div className="rounded-lg overflow-hidden border border-gray-200 relative">
      <div ref={ref} style={{ height }} />
      {vazio && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/30 text-white text-xs text-center px-4 pointer-events-none">
          Informe Latitude/Longitude ou coordenadas UTM dos vértices e clique em "Atualizar satélite".
        </div>
      )}
    </div>
  );
}
