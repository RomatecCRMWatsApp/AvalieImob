// src/components/ui/RichTextEditor.jsx
// AvalieImob — Editor rico inline para campos de laudo
// React 19 | sem dependências externas | contentEditable + toolbar flutuante

import { useRef, useEffect, useState, useCallback } from "react";
import "./RichTextEditor.css";

// ─── ícones SVG inline (sem lib externa) ─────────────────────────
const Icon = ({ d, size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);

const ICONS = {
  bold:        "M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z M6 12h9a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z",
  italic:      "M19 4h-9M14 20H5M15 4 9 20",
  underline:   "M6 3v7a6 6 0 0 0 6 6 6 6 0 0 0 6-6V3M4 21h16",
  strike:      "M16 4H9a4 4 0 0 0-1 7.9M4 12h16M8 20h8",
  alignLeft:   "M21 6H3M15 12H3M17 18H3",
  alignCenter: "M21 6H3M17 12H7M19 18H5",
  alignRight:  "M21 6H3M21 12H9M21 18H11",
  alignJust:   "M21 6H3M21 12H3M21 18H3",
  ul:          "M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01",
  ol:          "M10 6h11M10 12h11M10 18h11M4 6h.01M4 12h.01M4 18h.01",
  clear:       "M12 2 2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5",
  ai:          "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 6v4l3 3",
};

// ─── grupos da toolbar ────────────────────────────────────────────
const TOOLBAR_GROUPS = [
  [
    { cmd: "bold",          icon: "bold",        title: "Negrito (Ctrl+B)" },
    { cmd: "italic",        icon: "italic",      title: "Itálico (Ctrl+I)" },
    { cmd: "underline",     icon: "underline",   title: "Sublinhado (Ctrl+U)" },
    { cmd: "strikeThrough", icon: "strike",      title: "Tachado" },
  ],
  [
    { cmd: "justifyLeft",   icon: "alignLeft",   title: "Alinhar à esquerda" },
    { cmd: "justifyCenter", icon: "alignCenter", title: "Centralizar" },
    { cmd: "justifyRight",  icon: "alignRight",  title: "Alinhar à direita" },
    { cmd: "justifyFull",   icon: "alignJust",   title: "Justificar" },
  ],
  [
    { cmd: "insertUnorderedList", icon: "ul", title: "Lista com marcadores" },
    { cmd: "insertOrderedList",   icon: "ol", title: "Lista numerada" },
  ],
  [
    { cmd: "removeFormat", icon: "clear", title: "Limpar formatação" },
  ],
];

// ─── componente principal ─────────────────────────────────────────
export default function RichTextEditor({
  value = "",
  onChange,
  onBlurHtml,
  placeholder = "Clique para editar…",
  minHeight = 120,
  label,
  hint,
  disabled = false,
  showAiButton = true,
  onAiImprove,
  className = "",
}) {
  const editorRef  = useRef(null);
  const [focused,  setFocused]  = useState(false);
  const [activeCmd, setActiveCmd] = useState({});
  const isInitRef  = useRef(false);

  // ── inicializa / re-sincroniza conteúdo sem sobrescrever cursor ──
  // Re-sincroniza quando o valor muda EXTERNAMENTE (ex.: botão IA) e o
  // editor não está focado — durante a digitação não sobrescreve.
  useEffect(() => {
    const el = editorRef.current;
    if (!el) return;
    if (!isInitRef.current) {
      el.innerHTML = value || "";
      isInitRef.current = true;
    } else if (!focused && (value || "") !== el.innerHTML) {
      el.innerHTML = value || "";
    }
  }, [value, focused]);

  // ── atualiza estado dos botões ao selecionar ───────────────────
  const updateActiveState = useCallback(() => {
    const cmds = ["bold","italic","underline","strikeThrough",
                  "justifyLeft","justifyCenter","justifyRight","justifyFull",
                  "insertUnorderedList","insertOrderedList"];
    const state = {};
    cmds.forEach(c => {
      try { state[c] = document.queryCommandState(c); } catch { state[c] = false; }
    });
    setActiveCmd(state);
  }, []);

  const handleSelectionChange = useCallback(() => {
    if (focused) updateActiveState();
  }, [focused, updateActiveState]);

  useEffect(() => {
    document.addEventListener("selectionchange", handleSelectionChange);
    return () => document.removeEventListener("selectionchange", handleSelectionChange);
  }, [handleSelectionChange]);

  // ── exec formatação ────────────────────────────────────────────
  const execCmd = useCallback((cmd) => {
    editorRef.current?.focus();
    document.execCommand(cmd, false, null);
    updateActiveState();
    if (onChange) onChange(editorRef.current.innerHTML);
  }, [onChange, updateActiveState]);

  const handleInput = useCallback(() => {
    if (onChange) onChange(editorRef.current.innerHTML);
  }, [onChange]);

  const handleBlur = useCallback(() => {
    setFocused(false);
    if (onBlurHtml) onBlurHtml(editorRef.current.innerHTML);
  }, [onBlurHtml]);

  const handleFocus = useCallback(() => {
    setFocused(true);
    updateActiveState();
  }, [updateActiveState]);

  // ── paste: só texto limpo ──────────────────────────────────────
  const handlePaste = useCallback((e) => {
    e.preventDefault();
    const text = e.clipboardData.getData("text/plain");
    document.execCommand("insertText", false, text);
  }, []);

  const isEmpty = !value || value === "<br>" || value === "<p><br></p>";

  return (
    <div className={`rte-wrapper ${focused ? "rte-focused" : ""} ${disabled ? "rte-disabled" : ""} ${className}`}>

      {label && <label className="rte-label">{label}</label>}

      {/* ── toolbar ── */}
      <div className={`rte-toolbar ${focused ? "rte-toolbar--visible" : ""}`}
           onMouseDown={e => e.preventDefault()}>

        {TOOLBAR_GROUPS.map((group, gi) => (
          <span key={gi} className="rte-toolbar-group">
            {group.map(btn => (
              <button
                key={btn.cmd}
                type="button"
                title={btn.title}
                className={`rte-btn ${activeCmd[btn.cmd] ? "rte-btn--active" : ""}`}
                onMouseDown={e => { e.preventDefault(); execCmd(btn.cmd); }}
              >
                <Icon d={ICONS[btn.icon]} />
              </button>
            ))}
          </span>
        ))}

        {showAiButton && onAiImprove && (
          <>
            <span className="rte-toolbar-sep" />
            <button
              type="button"
              title="Aperfeiçoar com IA"
              className="rte-btn rte-btn--ai"
              onMouseDown={e => { e.preventDefault(); onAiImprove(editorRef.current.innerHTML); }}
            >
              <Icon d={ICONS.ai} size={13} />
              <span>IA</span>
            </button>
          </>
        )}
      </div>

      {/* ── área editável ── */}
      <div className="rte-editor-wrap">
        {isEmpty && !focused && (
          <span className="rte-placeholder">{placeholder}</span>
        )}
        <div
          ref={editorRef}
          contentEditable={!disabled}
          suppressContentEditableWarning
          className="rte-editor"
          style={{ minHeight }}
          onInput={handleInput}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onPaste={handlePaste}
          spellCheck={false}
        />
      </div>

      {hint && <p className="rte-hint">{hint}</p>}
    </div>
  );
}
