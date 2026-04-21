// @module maps/MapaPrintable — Mapa estático 800x400 para exportação PDF via canvas capture
import React, { useEffect, useRef } from 'react';
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

const MapaPrintable = ({ lat, lng, endereco, width = 800, height = 400 }) => {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);

  useEffect(() => {
    if (!mapRef.current || !lat || !lng) return;
    if (mapInstance.current) { mapInstance.current.remove(); mapInstance.current = null; }

    const map = L.map(mapRef.current, {
      zoomControl: false, scrollWheelZoom: false,
      attributionControl: false, dragging: false, doubleClickZoom: false,
    }).setView([parseFloat(lat), parseFloat(lng)], 16);
    mapInstance.current = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
    L.marker([parseFloat(lat), parseFloat(lng)], { icon: greenIcon })
      .addTo(map)
      .bindPopup(endereco || 'Imóvel')
      .openPopup();

    return () => { if (mapInstance.current) { mapInstance.current.remove(); mapInstance.current = null; } };
  }, [lat, lng, endereco]);

  if (!lat || !lng) return null;

  return (
    <div
      ref={mapRef}
      style={{ width, height, maxWidth: '100%' }}
      className="rounded-lg border border-gray-200 overflow-hidden print:shadow-none"
    />
  );
};

export default MapaPrintable;
