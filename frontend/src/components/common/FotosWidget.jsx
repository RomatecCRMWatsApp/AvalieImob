import React, { useState, useRef, useCallback, useEffect } from 'react';
import { X, Camera, Loader2, RefreshCw, Trash2, Eye, Download, MapPin, MessageCircle, Send, CloudUpload, Wifi, WifiOff } from 'lucide-react';
import { useToast } from '../../hooks/use-toast';
import { galeriaAPI, brandingAPI, API_BASE } from '../../lib/api';
import { latLonToUTM } from '../../utils/latLonToUTM';
import './FotosWidget.css';

const fotoUrl = (id) => `${API_BASE}/upload/image/${id}`;

// ── Fila offline (IndexedDB) — fotos capturadas sem rede ficam pendentes. ──
const IDB_NAME = 'avalieimob_galeria';
const IDB_STORE = 'pendentes';
function _idb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(IDB_STORE)) db.createObjectStore(IDB_STORE, { keyPath: 'id' });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function idbAdd(item) {
  const db = await _idb();
  return new Promise((res, rej) => {
    const tx = db.transaction(IDB_STORE, 'readwrite');
    tx.objectStore(IDB_STORE).put(item);
    tx.oncomplete = () => res(); tx.onerror = () => rej(tx.error);
  });
}
async function idbAll() {
  const db = await _idb();
  return new Promise((res, rej) => {
    const r = db.transaction(IDB_STORE, 'readonly').objectStore(IDB_STORE).getAll();
    r.onsuccess = () => res(r.result || []); r.onerror = () => rej(r.error);
  });
}
async function idbDel(id) {
  const db = await _idb();
  return new Promise((res, rej) => {
    const tx = db.transaction(IDB_STORE, 'readwrite');
    tx.objectStore(IDB_STORE).delete(id);
    tx.oncomplete = () => res(); tx.onerror = () => rej(tx.error);
  });
}

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
  const [online, setOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);
  const [pendentes, setPendentes] = useState(0);
  const [sincronizando, setSincronizando] = useState(false);
  const fileRef = useRef(null);

  const atualizarPendentes = useCallback(async () => {
    try { setPendentes((await idbAll()).length); } catch { /* idb indisponível */ }
  }, []);

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener('online', on);
    window.addEventListener('offline', off);
    atualizarPendentes();
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off); };
  }, [atualizarPendentes]);

  const sincronizar = useCallback(async () => {
    const itens = await idbAll();
    if (!itens.length) { toast({ title: 'Nenhuma foto pendente' }); return; }
    setSincronizando(true);
    let ok = 0;
    for (const it of itens) {
      try { await galeriaAPI.salvar(it.blob, it.meta); await idbDel(it.id); ok += 1; }
      catch { /* mantém na fila */ }
    }
    await atualizarPendentes();
    setSincronizando(false);
    toast({ title: `${ok} foto(s) sincronizada(s)` });
    // recarrega a lista após sincronizar
    try { const d = await galeriaAPI.listar({ limit: 200 }); setFotos(d.fotos || []); } catch { /* ignore */ }
  }, [toast, atualizarPendentes]);

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
        const src = (!b.use_default && b.logo_url) ? b.logo_url : `${window.location.origin}/icon-192.png`;
        try {
          const resp = await fetch(src, { mode: 'cors' });
          if (resp.ok) {
            const url = URL.createObjectURL(await resp.blob());
            logoImg = await loadImg(url);
          }
        } catch { /* sem CORS na logo custom → segue só com o nome */ }
      }
    } catch { /* branding indisponível → padrão */ }
    if (!logoImg) {
      try {
        const resp = await fetch(`${window.location.origin}/icon-192.png`, { mode: 'cors' });
        if (resp.ok) logoImg = await loadImg(URL.createObjectURL(await resp.blob()));
      } catch { /* segue só com o nome */ }
    }
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
      const meta = {
        latitude: gps?.lat ?? '', longitude: gps?.lon ?? '', altitude: gps?.alt ?? '',
        utm: utmLabel, endereco, data_hora: dataHora,
      };
      try {
        await galeriaAPI.salvar(blob, meta);
        toast({ title: 'Foto salva na galeria' + (gps ? ' com GPS' : ' (sem GPS)') });
        await carregar();
      } catch (upErr) {
        // Sem rede / falha de upload → guarda na fila offline (IndexedDB).
        await idbAdd({ id: `p_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`, blob, meta, criado: dataHora });
        await atualizarPendentes();
        toast({ title: 'Sem conexão — foto salva offline', description: 'Use “Sincronizar pendentes” quando tiver rede.' });
      }
    } catch (err) {
      toast({ title: 'Erro ao processar foto', description: err.response?.data?.detail || String(err), variant: 'destructive' });
    } finally {
      setCapturando(false);
      setStatusMsg('');
    }
  };

  const enviarWA = async (f) => {
    const phone = window.prompt('WhatsApp do destinatário (DDI+DDD, só dígitos):', '55');
    if (!phone) return;
    try {
      await galeriaAPI.enviarWhatsApp(f.id, phone.replace(/\D/g, ''));
      toast({ title: 'Foto enviada via WhatsApp' });
    } catch (e) {
      toast({ title: 'Erro ao enviar', description: e.response?.data?.detail, variant: 'destructive' });
    }
  };

  const enviarTG = async (f) => {
    const chat = window.prompt('Chat ID do Telegram (deixe vazio p/ o padrão):', '');
    if (chat === null) return;
    try {
      await galeriaAPI.enviarTelegram(f.id, chat.trim());
      toast({ title: 'Foto enviada via Telegram' });
    } catch (e) {
      toast({ title: 'Erro ao enviar', description: e.response?.data?.detail, variant: 'destructive' });
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
              {pendentes > 0 && (
                <button onClick={sincronizar} disabled={sincronizando || !online}
                  className="flex items-center gap-2 border border-amber-300 bg-amber-50 text-amber-800 px-3 py-2 rounded-lg text-sm font-semibold disabled:opacity-50">
                  {sincronizando ? <Loader2 className="w-4 h-4 animate-spin" /> : <CloudUpload className="w-4 h-4" />}
                  Sincronizar pendentes ({pendentes})
                </button>
              )}
              <span className={`ml-auto flex items-center gap-1 text-xs font-medium ${online ? 'text-emerald-600' : 'text-gray-400'}`}>
                {online ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
                {online ? 'Online' : 'Offline'}
              </span>
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
                        <button onClick={() => setViewUrl(fotoUrl(f.id))} title="Ver" className="flex-1 py-1.5 flex items-center justify-center text-gray-600 hover:bg-gray-50"><Eye className="w-3.5 h-3.5" /></button>
                        <button onClick={() => enviarWA(f)} title="Enviar por WhatsApp" className="flex-1 py-1.5 flex items-center justify-center text-green-600 hover:bg-green-50"><MessageCircle className="w-3.5 h-3.5" /></button>
                        <button onClick={() => enviarTG(f)} title="Enviar por Telegram" className="flex-1 py-1.5 flex items-center justify-center text-sky-600 hover:bg-sky-50"><Send className="w-3.5 h-3.5" /></button>
                        <a href={fotoUrl(f.id)} download={`foto_${f.numero}.jpg`} title="Baixar" className="flex-1 py-1.5 flex items-center justify-center text-gray-600 hover:bg-gray-50"><Download className="w-3.5 h-3.5" /></a>
                        <button onClick={() => excluir(f)} title="Excluir" className="flex-1 py-1.5 flex items-center justify-center text-red-600 hover:bg-red-50"><Trash2 className="w-3.5 h-3.5" /></button>
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
          <button onClick={(e) => { e.stopPropagation(); setViewUrl(null); }} title="Fechar"
            className="absolute top-4 right-4 z-10 w-10 h-10 rounded-full bg-white/15 hover:bg-white/35 text-white flex items-center justify-center">
            <X className="w-6 h-6" />
          </button>
          <img onClick={(e) => e.stopPropagation()} src={viewUrl} alt="Foto" className="max-w-full max-h-[88vh] object-contain rounded shadow-2xl" />
          <button onClick={(e) => { e.stopPropagation(); setViewUrl(null); }}
            className="absolute bottom-5 left-1/2 -translate-x-1/2 z-10 px-5 py-2 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold flex items-center gap-1.5 shadow-lg">
            <X className="w-4 h-4" /> Fechar
          </button>
        </div>
      )}
    </>
  );
}
