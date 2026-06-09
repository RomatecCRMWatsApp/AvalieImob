import React, { useState, useRef, useCallback } from 'react';
import { X, Camera, Loader2, RefreshCw, Trash2, Eye, Download, MapPin } from 'lucide-react';
import { useToast } from '../../hooks/use-toast';
import { galeriaAPI, brandingAPI, API_BASE } from '../../lib/api';
import { latLonToUTM } from '../../utils/latLonToUTM';
import './FotosWidget.css';

const fotoUrl = (id) => `${API_BASE}/upload/image/${id}`;

function loadImg(src, crossOrigin = false) {
  return new Promise((resolve, reject) => {
    const i = new Image();
    if (crossOrigin) i.crossOrigin = 'anonymous';
    i.onload = () => resolve(i);
    i.onerror = reject;
    i.src = src;
  });
}

// Geolocalização (lat, lon, alt) com timeout.
function obterGPS() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lon: p.coords.longitude, alt: p.coords.altitude }),
      () => resolve(null),
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 10000 },
    );
  });
}

// Endereço reverso via OpenStreetMap (Nominatim).
async function geocodeReverso(lat, lon) {
  try {
    const r = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&accept-language=pt-BR&zoom=18`,
      { headers: { Accept: 'application/json' } },
    );
    const d = await r.json();
    return d.display_name || '';
  } catch {
    return '';
  }
}

export default function FotosWidget() {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [fotos, setFotos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [capturando, setCapturando] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [viewUrl, setViewUrl] = useState(null);
  const fileRef = useRef(null);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const d = await galeriaAPI.listar({ limit: 200 });
      setFotos(d.fotos || []);
    } catch (e) {
      toast({ title: 'Erro ao carregar galeria', description: e.response?.data?.detail, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const abrir = () => { setOpen(true); carregar(); };

  // Carrega a logo do overlay: branding do usuário (white-label) ou padrão AvalieImob.
  async function carregarLogoEnome() {
    let logoImg = null;
    let nome = 'Romatec Consultoria Total';
    try {
      const b = await brandingAPI.get();
      if (b) {
        nome = (!b.use_default && (b.stamp_name || b.footer_line1)) || b.stamp_name || nome;
        const src = (!b.use_default && b.logo_url) ? b.logo_url : `${window.location.origin}/brand/icone.png`;
        try {
          const resp = await fetch(src, { mode: 'cors' });
          if (resp.ok) {
            const url = URL.createObjectURL(await resp.blob());
            logoImg = await loadImg(url);
          }
        } catch { /* sem CORS na logo custom → segue só com o nome */ }
      }
    } catch { /* branding indisponível → padrão */ }
    return { logoImg, nome };
  }

  // Desenha o overlay técnico (GPS/UTM/endereço/data/logo) na foto.
  async function gerarOverlay(file, info, logoImg, nome) {
    const url = URL.createObjectURL(file);
    const img = await loadImg(url);
    URL.revokeObjectURL(url);

    const maxW = 1600;
    let w = img.width, h = img.height;
    if (w > maxW) { h = Math.round((h * maxW) / w); w = maxW; }
    const canvas = document.createElement('canvas');
    canvas.width = w; canvas.height = h;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0, w, h);

    const linhas = [];
    if (info.lat != null) {
      linhas.push(`GPS: ${info.lat.toFixed(6)}, ${info.lon.toFixed(6)}` + (info.alt != null ? ` · alt ${Math.round(info.alt)}m` : ''));
    }
    if (info.utm) linhas.push(info.utm);
    if (info.endereco) linhas.push(info.endereco);
    linhas.push(`Data: ${info.dataHora}`);
    linhas.push(nome);

    const pad = Math.round(w * 0.015);
    const fs = Math.max(12, Math.round(w * 0.0165));
    const lh = Math.round(fs * 1.4);
    const barH = lh * linhas.length + pad * 2;

    ctx.fillStyle = 'rgba(0,0,0,0.55)';
    ctx.fillRect(0, h - barH, w, barH);
    ctx.fillStyle = '#ffffff';
    ctx.font = `${fs}px Arial, sans-serif`;
    ctx.textBaseline = 'top';
    let y = h - barH + pad;
    const maxTextW = logoImg ? w - pad * 2 - w * 0.16 : w - pad * 2;
    for (const ln of linhas) {
      let s = ln;
      while (s && ctx.measureText(s).width > maxTextW) s = s.slice(0, -1);
      ctx.fillText(s, pad, y);
      y += lh;
    }
    if (logoImg) {
      const lw = Math.round(w * 0.13);
      const lh2 = Math.round((logoImg.height / logoImg.width) * lw);
      try { ctx.drawImage(logoImg, w - lw - pad, h - barH + (barH - lh2) / 2, lw, lh2); } catch { /* taint */ }
    }
    return await new Promise((res) => canvas.toBlob(res, 'image/jpeg', 0.9));
  }

  const onArquivo = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setCapturando(true);
    try {
      setStatusMsg('Obtendo localização...');
      const gps = await obterGPS();
      let endereco = '';
      let utmLabel = '';
      if (gps) {
        setStatusMsg('Buscando endereço...');
        endereco = await geocodeReverso(gps.lat, gps.lon);
        try { utmLabel = latLonToUTM(gps.lat, gps.lon).label; } catch { utmLabel = ''; }
      }
      setStatusMsg('Aplicando carimbo...');
      const { logoImg, nome } = await carregarLogoEnome();
      const dataHora = new Date().toLocaleString('pt-BR');
      const blob = await gerarOverlay(
        file,
        { lat: gps?.lat, lon: gps?.lon, alt: gps?.alt, utm: utmLabel, endereco, dataHora },
        logoImg, nome,
      );
      setStatusMsg('Salvando...');
      await galeriaAPI.salvar(blob, {
        latitude: gps?.lat ?? '', longitude: gps?.lon ?? '', altitude: gps?.alt ?? '',
        utm: utmLabel, endereco, data_hora: dataHora,
      });
      toast({ title: 'Foto salva na galeria' + (gps ? ' com GPS' : ' (sem GPS)') });
      await carregar();
    } catch (err) {
      toast({ title: 'Erro ao salvar foto', description: err.response?.data?.detail || String(err), variant: 'destructive' });
    } finally {
      setCapturando(false);
      setStatusMsg('');
    }
  };

  const excluir = async (f) => {
    if (!window.confirm(`Excluir a foto #${f.numero}?`)) return;
    try {
      await galeriaAPI.remover(f.id);
      setFotos((prev) => prev.filter((x) => x.id !== f.id));
    } catch (e) {
      toast({ title: 'Erro ao excluir', description: e.response?.data?.detail, variant: 'destructive' });
    }
  };

  return (
    <>
      <button className="fotos-fab" onClick={abrir} title="Galeria de Fotos" aria-label="Abrir galeria de fotos">
        <span className="fotos-fab-icon">📷</span>
        <span className="fotos-fab-label">Fotos</span>
      </button>

      {open && (
        <div className="fixed inset-0 z-[1100] bg-black/60 flex items-end sm:items-center justify-center p-0 sm:p-4">
          <div className="bg-white w-full max-w-3xl h-[92vh] sm:h-[88vh] rounded-t-2xl sm:rounded-2xl flex flex-col overflow-hidden">
            {/* Header */}
            <div className="bg-emerald-900 text-white px-4 py-3 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <Camera className="w-5 h-5" />
                <div>
                  <h3 className="font-bold text-sm">Galeria de Fotos</h3>
                  <p className="text-[11px] text-emerald-200">Foto com carimbo GPS + UTM + endereço, reutilizável nos laudos.</p>
                </div>
              </div>
              <button onClick={() => setOpen(false)} className="text-emerald-200 hover:text-white"><X className="w-5 h-5" /></button>
            </div>

            {/* Ações */}
            <div className="px-4 py-3 border-b flex flex-wrap gap-2 shrink-0">
              <button
                onClick={() => fileRef.current?.click()}
                disabled={capturando}
                className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-semibold"
              >
                {capturando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Camera className="w-4 h-4" />}
                {capturando ? (statusMsg || 'Processando...') : 'Tirar Foto'}
              </button>
              <button onClick={carregar} disabled={loading} className="flex items-center gap-2 border px-3 py-2 rounded-lg text-sm">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />} Recarregar
              </button>
              <input ref={fileRef} type="file" accept="image/*" capture="environment" hidden onChange={onArquivo} />
            </div>

            {/* Grid */}
            <div className="flex-1 overflow-y-auto p-3 bg-gray-50">
              {loading && <div className="flex justify-center py-10"><Loader2 className="w-8 h-8 text-emerald-700 animate-spin" /></div>}
              {!loading && fotos.length === 0 && (
                <div className="text-center py-12 text-gray-400">
                  <Camera className="w-10 h-10 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">Nenhuma foto ainda. Toque em “Tirar Foto”.</p>
                </div>
              )}
              {!loading && fotos.length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {fotos.map((f) => (
                    <div key={f.id} className="bg-white rounded-xl border overflow-hidden flex flex-col">
                      <img src={fotoUrl(f.id)} alt={`Foto ${f.numero}`} className="w-full aspect-square object-cover" loading="lazy" />
                      <div className="p-2 text-[11px] text-gray-600 flex-1">
                        <p className="font-bold text-gray-800">Foto #{f.numero}</p>
                        {f.endereco && <p className="flex items-start gap-1 mt-0.5"><MapPin className="w-3 h-3 mt-0.5 text-emerald-600 shrink-0" />{f.endereco}</p>}
                        {f.data_hora && <p className="text-gray-400 mt-0.5">{f.data_hora}</p>}
                      </div>
                      <div className="flex border-t divide-x text-xs">
                        <button onClick={() => setViewUrl(fotoUrl(f.id))} className="flex-1 py-1.5 flex items-center justify-center gap-1 text-gray-600 hover:bg-gray-50"><Eye className="w-3.5 h-3.5" /></button>
                        <a href={fotoUrl(f.id)} download={`foto_${f.numero}.jpg`} className="flex-1 py-1.5 flex items-center justify-center gap-1 text-gray-600 hover:bg-gray-50"><Download className="w-3.5 h-3.5" /></a>
                        <button onClick={() => excluir(f)} className="flex-1 py-1.5 flex items-center justify-center gap-1 text-red-600 hover:bg-red-50"><Trash2 className="w-3.5 h-3.5" /></button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {viewUrl && (
        <div onClick={() => setViewUrl(null)} className="fixed inset-0 z-[1200] bg-black/85 flex items-center justify-center p-4">
          <img src={viewUrl} alt="Foto" className="max-w-full max-h-[92vh] object-contain rounded shadow-2xl" />
        </div>
      )}
    </>
  );
}
