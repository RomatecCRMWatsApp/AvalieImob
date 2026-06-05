// @module ui/RichField — Wrapper do RichTextEditor ligado a um campo do form.
// Converte texto puro (legado/IA) em HTML básico para o editor exibir corretamente,
// e grava HTML de volta no form. Reutilizável em todos os campos de texto longo.
import React from 'react';
import RichTextEditor from './RichTextEditor';

const HTML_RE = /<(b|i|u|p|div|ul|ol|br|span|strong|em)\b/i;

/** Texto puro -> HTML básico (preserva quebras). Se já for HTML, retorna como veio. */
export function paraEditorHtml(v) {
  if (!v) return '';
  const s = String(v);
  if (HTML_RE.test(s)) return s;
  const esc = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return s.split('\n').map((l) => (l.trim() ? `<div>${esc(l)}</div>` : '<div><br></div>')).join('');
}

export default function RichField({
  form,
  setForm,
  field,
  placeholder = 'Clique para editar…',
  minHeight = 100,
  disabled = false,
}) {
  return (
    <RichTextEditor
      value={paraEditorHtml(form?.[field])}
      onChange={(html) => setForm({ ...form, [field]: html })}
      onBlurHtml={(html) => setForm({ ...form, [field]: html })}
      placeholder={placeholder}
      minHeight={minHeight}
      disabled={disabled}
      showAiButton={false}
    />
  );
}
