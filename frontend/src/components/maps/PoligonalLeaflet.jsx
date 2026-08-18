// @module maps/PoligonalLeaflet — Preview da poligonal SIG-RI sobre imagem de
// satélite (Leaflet + ESRI World Imagery). Recebe um GeoJSON FeatureCollection
// em SIRGAS 2000 (EPSG:4674, lon/lat) — o mesmo do endpoint /geojson.
//
// COBERTURA DO SATÉLITE (bug "Map data not yet available"): o ESRI World Imagery
// NÃO tem imagem em todo zoom em qualquer lugar — no interior do Brasil (ex.:
// Açailândia/MA) a cobertura para em z17. Pedir z18+ devolve um tile CINZA de
// placeholder ("Map data not yet available") — era o que aparecia ao dar
// fitBounds num lote pequeno (sobe pra z19). A correção descobre em runtime o
// maior zoom COM imagem pela API `tilemap` do próprio ESRI (CORS liberado) e o
// aplica em `maxNativeZoom` — aí o Leaflet AMPLIA o melhor tile existente em vez
// de baixar o cinza. Camada "Mapa" (OSM) como alternativa: tem z19 em todo o
// Brasil e mostra as ruas confrontantes.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

const SAT = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const SAT_TILEMAP = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tilemap';
const OSM = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const ATTR_SAT = 'Tiles © Esri — World Imagery';
const ATTR_OSM = '© <a href="https://osm.org/copyright">OpenStreetMap</a>';

const ZOOM_MAX = 20;          // teto do serviço
const ZOOM_MIN_PROBE = 14;    // abaixo disso a cobertura é global, não vale sondar
const ZOOM_FALLBACK = 17;     // sem resposta da sondagem: cobertura típica do interior
const GOLD = '#C9A227';
const GREEN = '#0C3320';

// lon/lat -> índice do tile (Web Mercator / esquema XYZ)
function tileDeLonLat(lon, lat, z) {
  const n = 2 ** z;
  const rad = (lat * Math.PI) / 180;
  return {
    x: Math.floor(((lon + 180) / 360) * n),
    y: Math.floor(((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) * n),
  };
}

// Cache por região (chave = tile z12) p/ não resondar a cada render
const _cacheZoom = new Map();

// Maior zoom com IMAGEM REAL no ponto. null = sondagem indisponível (rede/CORS).
async function descobrirZoomSatelite(lon, lat) {
  const t12 = tileDeLonLat(lon, lat, 12);
  const chave = `${t12.x}/${t12.y}`;
  if (_cacheZoom.has(chave)) return _cacheZoom.get(chave);

  const zooms = [];
  for (let z = ZOOM_MAX; z >= ZOOM_MIN_PROBE; z--) zooms.push(z);
  const respostas = await Promise.all(
    zooms.map(async (z) => {
      const { x, y } = tileDeLonLat(lon, lat, z);
      try {
        const r = await fetch(`${SAT_TILEMAP}/${z}/${y}/${x}/1/1`, { cache: 'force-cache' });
        if (!r.ok) return null;
        const j = await r.json();
        return Array.isArray(j.data) && j.data[0] === 1 ? z : 0;
      } catch (e) {
        return null; // sondagem falhou (offline/bloqueio) — não é "sem cobertura"
      }
    })
  );
  const zOk = respostas.filter((z) => typeof z === 'number' && z > 0);
  const sondou = respostas.some((z) => z !== null);
  const resultado = zOk.length ? Math.max(...zOk) : (sondou ? ZOOM_MIN_PROBE : null);
  _cacheZoom.set(chave, resultado);
  return resultado;
}

export default function PoligonalLeaflet({ geojson, height = 300 }) {
  const ref = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const tileRef = useRef(null);
  const [camada, setCamada] = useState('satelite');
  const [zoomSat, setZoomSat] = useState(null);   // maior zoom com imagem
  const [zoomAtual, setZoomAtual] = useState(null);

  const aneis = useCallback(() => {
    const feats = (geojson && geojson.features) || [];
    return feats
      .map((f) => (f && f.geometry && f.geometry.coordinates && f.geometry.coordinates[0]) || [])
      .map((coords) => coords
        .map(([lon, lat]) => [lat, lon])
        .filter(([la, ln]) => Number.isFinite(la) && Number.isFinite(ln)))
      .filter((ll) => ll.length >= 3);
  }, [geojson]);

  // Inicializa o mapa uma vez
  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    const map = L.map(ref.current, { zoomControl: true, scrollWheelZoom: false })
      .setView([-15.78, -47.93], 4);
    mapRef.current = map;
    tileRef.current = L.tileLayer(SAT, {
      attribution: ATTR_SAT,
      maxZoom: ZOOM_MAX,
      maxNativeZoom: ZOOM_FALLBACK, // conservador até a sondagem responder
    }).addTo(map);
    map.on('zoomend', () => setZoomAtual(map.getZoom()));
    setTimeout(() => mapRef.current && mapRef.current.invalidateSize(), 120);
  }, []);

  // Troca a camada base (satélite <-> mapa) / aplica a cobertura sondada
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (tileRef.current) tileRef.current.remove();
    tileRef.current = camada === 'satelite'
      ? L.tileLayer(SAT, {
          attribution: ATTR_SAT,
          maxZoom: ZOOM_MAX,
          maxNativeZoom: zoomSat || ZOOM_FALLBACK,
        })
      : L.tileLayer(OSM, { attribution: ATTR_OSM, maxZoom: 19 });
    tileRef.current.addTo(map);
    if (layerRef.current) layerRef.current.bringToFront();
  }, [camada, zoomSat]);

  // Redesenha a poligonal quando o GeoJSON muda
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (layerRef.current) { layerRef.current.remove(); layerRef.current = null; }
    const listaAneis = aneis();
    const grp = L.featureGroup().addTo(map);
    layerRef.current = grp;
    listaAneis.forEach((latlngs) => {
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
    if (listaAneis.length) {
      try {
        map.fitBounds(grp.getBounds(), { padding: [24, 24], maxZoom: 19 });
        setZoomAtual(map.getZoom());
        // Sonda a cobertura real do satélite no centro do imóvel
        const c = grp.getBounds().getCenter();
        descobrirZoomSatelite(c.lng, c.lat).then((z) => { if (z) setZoomSat(z); });
      } catch (e) { /* bounds vazio */ }
    }
    setTimeout(() => map.invalidateSize(), 120);
  }, [geojson, aneis]);

  // Cleanup
  useEffect(() => () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } }, []);

  const vazio = aneis().length === 0;
  // Só avisa quando o satélite está de fato sendo ampliado além da imagem existente
  const ampliado = camada === 'satelite' && zoomSat && zoomAtual && zoomAtual > zoomSat;
  const btn = (ativo) => `px-2 py-1 text-[11px] font-medium rounded ${ativo ? 'bg-white shadow text-gray-900' : 'text-white/90 hover:bg-white/20'}`;

  return (
    <div className="rounded-lg overflow-hidden border border-gray-200 relative">
      <div ref={ref} style={{ height }} />

      {/* Alternador de camada */}
      <div className="absolute top-2 right-2 z-[500] flex gap-0.5 rounded bg-black/55 p-0.5 backdrop-blur-sm">
        <button type="button" onClick={() => setCamada('satelite')} className={btn(camada === 'satelite')}>Satélite</button>
        <button type="button" onClick={() => setCamada('mapa')} className={btn(camada === 'mapa')}>Mapa</button>
      </div>

      {/* Cobertura do satélite insuficiente para o zoom atual */}
      {ampliado && !vazio && (
        <div className="absolute bottom-2 left-2 z-[500] max-w-[85%] rounded bg-amber-500/90 px-2 py-1 text-[10px] leading-tight text-white">
          Satélite desta região só tem imagem até o zoom {zoomSat} — a vista está ampliada (menos nítida).
          Use <strong>Mapa</strong> para ver as ruas confrontantes.
        </div>
      )}

      {vazio && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/30 text-white text-xs text-center px-4 pointer-events-none">
          Informe Latitude/Longitude ou coordenadas UTM dos vértices e clique em "Atualizar satélite".
        </div>
      )}
    </div>
  );
}
