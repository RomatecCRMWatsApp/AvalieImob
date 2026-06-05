// src/components/dashboard/ptam/PhotoGrid.jsx
// AvalieImob — Galeria de fotos com legenda editável inline por foto
// React 19 | sem dependências externas

import { useState, useRef, useCallback } from "react";
import "./PhotoGrid.css";

// ─── sugestões de legenda rápida ─────────────────────────────────
const SUGESTOES = [
  "Fachada", "Entrada", "Sala de estar", "Sala de jantar",
  "Cozinha", "Área de serviço", "Quarto 1", "Quarto 2", "Quarto 3",
  "Suíte", "Banheiro", "Banheiro social", "Garagem", "Quintal",
  "Área externa", "Corredor", "Vista frontal", "Vista lateral",
  "Vista posterior", "Muro", "Calçada", "Cobertura", "Varanda",
];

// ─── item de foto individual ─────────────────────────────────────
function PhotoItem({ photo, index, onLegendChange, onRemove, onSelect }) {
  const [editando, setEditando]   = useState(false);
  const [legenda,  setLegenda]    = useState(photo.legenda || "");
  const [showSug,  setShowSug]    = useState(false);
  const inputRef = useRef(null);

  const handleFocus = () => {
    setEditando(true);
    setShowSug(true);
  };

  const handleBlur = () => {
    // pequeno delay para permitir clique nas sugestões
    setTimeout(() => {
      setEditando(false);
      setShowSug(false);
    }, 150);
  };

  const handleChange = (val) => {
    setLegenda(val);
    onLegendChange(index, val);
  };

  const handleSugestao = (s) => {
    setLegenda(s);
    onLegendChange(index, s);
    setShowSug(false);
    inputRef.current?.blur();
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" || e.key === "Escape") {
      inputRef.current?.blur();
    }
  };

  const filtradas = legenda
    ? SUGESTOES.filter(s => s.toLowerCase().includes(legenda.toLowerCase()))
    : SUGESTOES;

  return (
    <div className={`pg-item ${photo.selecionada ? "pg-item--sel" : ""}`}>

      {/* ── imagem ── */}
      <div className="pg-img-wrap" onClick={() => onSelect?.(index)}>
        <img src={photo.url} alt={legenda || `Foto ${index + 1}`} className="pg-img" loading="lazy" />

        {/* badge GPS */}
        {photo.gps && (
          <span className="pg-badge-gps">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a7 7 0 0 1 7 7c0 5-7 13-7 13S5 14 5 9a7 7 0 0 1 7-7z"/>
              <circle cx="12" cy="9" r="2.5"/>
            </svg>
            GPS
          </span>
        )}

        {/* overlay de seleção */}
        {photo.selecionada && (
          <div className="pg-sel-overlay">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
              stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
        )}

        {/* botão remover */}
        <button
          type="button"
          className="pg-btn-remove"
          title="Remover foto"
          onClick={e => { e.stopPropagation(); onRemove(index); }}
        >
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="3" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      {/* ── campo de legenda ── */}
      <div className="pg-legend-wrap">
        <div className={`pg-legend-field ${editando ? "pg-legend-field--focus" : ""}`}>
          <svg className="pg-legend-icon" width="11" height="11" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={legenda}
            onChange={e => handleChange(e.target.value)}
            onFocus={handleFocus}
            onBlur={handleBlur}
            onKeyDown={handleKeyDown}
            placeholder={`Legenda da foto ${index + 1}`}
            maxLength={60}
            className="pg-legend-input"
            title="Clique para adicionar legenda"
          />
          {legenda && (
            <button
              type="button"
              className="pg-legend-clear"
              onMouseDown={e => { e.preventDefault(); handleChange(""); }}
              title="Limpar legenda"
            >
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="3" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          )}
        </div>

        {/* ── dropdown de sugestões ── */}
        {showSug && filtradas.length > 0 && (
          <div className="pg-sugestoes">
            {filtradas.slice(0, 8).map(s => (
              <button
                key={s}
                type="button"
                className="pg-sug-item"
                onMouseDown={() => handleSugestao(s)}
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── componente principal ─────────────────────────────────────────
export default function PhotoGrid({
  photos = [],           // [{ url, gps, legenda, selecionada }]
  onChange,              // (photos[]) => void
  onUpload,             // (files) => void
  multiSelect = false,
}) {
  const fileRef = useRef(null);

  const updatePhoto = useCallback((index, patch) => {
    const next = photos.map((p, i) => i === index ? { ...p, ...patch } : p);
    onChange?.(next);
  }, [photos, onChange]);

  const handleLegendChange = useCallback((index, legenda) => {
    updatePhoto(index, { legenda });
  }, [updatePhoto]);

  const handleRemove = useCallback((index) => {
    onChange?.(photos.filter((_, i) => i !== index));
  }, [photos, onChange]);

  const handleSelect = useCallback((index) => {
    if (!multiSelect) return;
    updatePhoto(index, { selecionada: !photos[index].selecionada });
  }, [photos, multiSelect, updatePhoto]);

  const handleFileChange = useCallback((e) => {
    if (onUpload) onUpload(Array.from(e.target.files));
    e.target.value = "";
  }, [onUpload]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files).filter(f =>
      ["image/jpeg","image/png","image/webp"].includes(f.type)
    );
    if (files.length && onUpload) onUpload(files);
  }, [onUpload]);

  // ── legenda em lote ──
  const [batchMode, setBatchMode] = useState(false);

  function aplicarLoteSequencial() {
    const prefixo = window.prompt("Prefixo para legendas sequenciais (ex: Foto):", "Foto");
    if (!prefixo) return;
    const next = photos.map((p, i) => ({ ...p, legenda: `${prefixo} ${i + 1}` }));
    onChange?.(next);
  }

  function limparTodasLegendas() {
    if (!window.confirm("Limpar todas as legendas?")) return;
    onChange?.(photos.map(p => ({ ...p, legenda: "" })));
  }

  return (
    <div className="pg-root">

      {/* ── barra de ações em lote ── */}
      {photos.length > 0 && (
        <div className="pg-batch-bar">
          <span className="pg-batch-count">
            {photos.length} foto{photos.length !== 1 ? "s" : ""}
            {photos.filter(p => p.legenda).length > 0 &&
              ` · ${photos.filter(p => p.legenda).length} com legenda`}
          </span>
          <div className="pg-batch-actions">
            <button type="button" className="pg-batch-btn" onClick={aplicarLoteSequencial}
              title="Numerar fotos automaticamente">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                <path d="M3 12h18M3 6h18M3 18h18"/>
              </svg>
              Numerar automaticamente
            </button>
            <button type="button" className="pg-batch-btn pg-batch-btn--danger"
              onClick={limparTodasLegendas} title="Apagar todas as legendas">
              Limpar legendas
            </button>
          </div>
        </div>
      )}

      {/* ── grid de fotos ── */}
      <div
        className="pg-grid"
        onDragOver={e => e.preventDefault()}
        onDrop={handleDrop}
      >
        {photos.map((photo, i) => (
          <PhotoItem
            key={photo.url + i}
            photo={photo}
            index={i}
            onLegendChange={handleLegendChange}
            onRemove={handleRemove}
            onSelect={handleSelect}
          />
        ))}

        {/* ── card de upload ── */}
        <div className="pg-upload-card" onClick={() => fileRef.current?.click()}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
            stroke="#0B6E4F" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <span>Clique ou arraste mais fotos</span>
          <small>JPG, PNG, WebP — máx 5 MB</small>
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            hidden
            onChange={handleFileChange}
          />
        </div>
      </div>
    </div>
  );
}
