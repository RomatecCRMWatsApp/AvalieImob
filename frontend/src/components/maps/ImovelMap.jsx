// @module maps/ImovelMap — Mapa Leaflet do imóvel com geocoding automático via Nominatim
import React, { useEffect, useState, useRef } from 'react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { API_BASE } from '../../lib/api';

// Corrige paths dos ícones padrão do Leaflet no CRA
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const TILE_LAYERS = {
  mapa: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  satelite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
};

const greenIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
});

// Centro do Brasil — usado como fallback quando geocoding falha
const BRAZIL_CENTER = { lat: -15.7801, lng: -47.9292 };
const BRAZIL_ZOOM = 4;

const ImovelMap = ({ endereco, lat, lng, height = 280, onPick }) => {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const tileRef = useRef(null);
  const markerRef = useRef(null);
  const onPickRef = useRef(onPick);
  const [tileMode, setTileMode] = useState('mapa');
  const [coords, setCoords] = useState(null);
  const [loading, setLoading] = useState(false);
  const [geocodeFailed, setGeocodeFailed] = useState(false);

  useEffect(() => { onPickRef.current = onPick; }, [onPick]);

  // Geocodifica via backend quando não há coords diretas
  useEffect(() => {
    setGeocodeFailed(false);
    if (lat && lng) {
      const la = parseFloat(lat);
      const ln = parseFloat(lng);
      // Valida coordenadas dentro do território brasileiro antes de centralizar.
      if (!isNaN(la) && !isNaN(ln) && la >= -33.8 && la <= 5.3 && ln >= -73.9 && ln <= -34.7) {
        setCoords({ lat: la, lng: ln });
        return;
      }
    }
    if (!endereco || endereco.trim().length < 10) {
      // Sem endereço nem coords: se o mapa é interativo (onPick), mostra o Brasil p/ clicar.
      if (onPick) { setCoords(BRAZIL_CENTER); setGeocodeFailed(true); }
      return;
    }
    setLoading(true);
    const params = new URLSearchParams({ endereco });
    fetch(`${API_BASE}/maps/geocode?${params}`)
      .then((r) => {
        if (!r.ok) throw new Error('not_found');
        return r.json();
      })
      .then((d) => {
        setCoords({ lat: d.lat, lng: d.lng });
        setGeocodeFailed(false);
      })
      .catch(() => {
        // Fallback: mostra mapa centrado no Brasil em vez de mensagem de erro
        setCoords(BRAZIL_CENTER);
        setGeocodeFailed(true);
      })
      .finally(() => setLoading(false));
  }, [endereco, lat, lng]);

  // Inicializa ou atualiza mapa quando há coords
  useEffect(() => {
    if (!coords || !mapRef.current) return;
    const interativo = !!onPickRef.current;
    const zoom = geocodeFailed ? (interativo ? 15 : BRAZIL_ZOOM) : 18;
    // marcador aparece quando localizado OU quando é interativo (mostra onde clicou)
    const mostrarMarker = !geocodeFailed || interativo;

    const colocarMarker = () => {
      if (markerRef.current) { markerRef.current.remove(); markerRef.current = null; }
      if (!mostrarMarker) return;
      const mk = L.marker([coords.lat, coords.lng], { icon: greenIcon, draggable: interativo })
        .addTo(mapInstance.current);
      if (endereco && !geocodeFailed) mk.bindPopup(endereco).openPopup();
      if (interativo) {
        mk.on('dragend', (e) => {
          const ll = e.target.getLatLng();
          onPickRef.current(+ll.lat.toFixed(6), +ll.lng.toFixed(6));
        });
      }
      markerRef.current = mk;
    };

    if (!mapInstance.current) {
      mapInstance.current = L.map(mapRef.current, {
        zoomControl: true,
        scrollWheelZoom: false,
      }).setView([coords.lat, coords.lng], zoom);

      tileRef.current = L.tileLayer(TILE_LAYERS.mapa, {
        attribution: '© <a href="https://osm.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(mapInstance.current);

      // clique no mapa marca a localização (modo interativo)
      mapInstance.current.on('click', (e) => {
        if (onPickRef.current) {
          onPickRef.current(+e.latlng.lat.toFixed(6), +e.latlng.lng.toFixed(6));
        }
      });
      colocarMarker();
    } else {
      mapInstance.current.setView([coords.lat, coords.lng], zoom);
      colocarMarker();
    }
    // FIX: o container passa de altura 0 -> height; o Leaflet precisa remedir e
    // re-centralizar, senão o mapa fica em branco ou descentralizado.
    setTimeout(() => {
      if (mapInstance.current) {
        mapInstance.current.invalidateSize();
        mapInstance.current.setView([coords.lat, coords.lng], zoom, { animate: false });
      }
    }, 150);
    return () => {};
  }, [coords, endereco, geocodeFailed]);

  // Troca tile layer ao mudar modo
  useEffect(() => {
    if (!mapInstance.current || !tileRef.current) return;
    tileRef.current.setUrl(TILE_LAYERS[tileMode]);
  }, [tileMode]);

  // Cleanup ao desmontar
  useEffect(() => {
    return () => {
      if (mapInstance.current) { mapInstance.current.remove(); mapInstance.current = null; }
    };
  }, []);

  const showMap = !!coords && !loading;

  return (
    <div className="rounded-xl overflow-hidden border border-gray-200 shadow-sm">
      <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-100">
        <span className="text-xs font-semibold text-gray-600">Localização no Mapa</span>
        <div className="flex gap-1">
          {['mapa', 'satelite'].map((m) => (
            <button key={m} onClick={() => setTileMode(m)}
              className={`text-xs px-2 py-1 rounded font-medium transition ${tileMode === m ? 'bg-emerald-900 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:border-emerald-400'}`}>
              {m === 'mapa' ? 'Mapa' : 'Satélite'}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div style={{ height }} className="flex items-center justify-center bg-gray-50 text-sm text-gray-400">
          Geocodificando endereço...
        </div>
      )}

      {!coords && !loading && (
        <div style={{ height }} className="flex items-center justify-center bg-gray-50 text-sm text-gray-400">
          Preencha o endereço completo (rua, bairro, cidade) para ver o mapa.
        </div>
      )}

      {geocodeFailed && showMap && !onPick && (
        <div className="px-3 py-1.5 bg-amber-50 border-b border-amber-100 text-xs text-amber-700">
          Endereço não localizado automaticamente — mapa centralizado no Brasil.
          Informe rua, bairro e cidade para melhor precisão.
        </div>
      )}
      {onPick && showMap && (
        <div className="px-3 py-1.5 bg-emerald-50 border-b border-emerald-100 text-xs text-emerald-800">
          📍 Clique no mapa (ou arraste o marcador) para marcar a localização exata — as coordenadas são preenchidas automaticamente.
        </div>
      )}

      <div ref={mapRef} style={{ height: showMap ? height : 0 }} />
    </div>
  );
};

export default ImovelMap;
