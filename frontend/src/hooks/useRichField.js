// src/hooks/useRichField.js
// AvalieImob — hook para gerenciar campo rico em formulários de laudo
// Converte HTML <-> valor do form, sanitiza na saída, expõe plainText

import { useState, useCallback } from "react";

/**
 * Extrai texto plano de HTML (para preview / busca / IA)
 */
function htmlToPlain(html = "") {
  if (!html) return "";
  return html
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>/gi, "\n")
    .replace(/<\/li>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .trim();
}

/**
 * Sanitiza HTML mantendo apenas tags seguras (bold, italic, etc.)
 */
function sanitize(html = "") {
  const ALLOWED = ["b", "strong", "i", "em", "u", "s", "strike", "ul", "ol", "li", "p", "br", "div", "span"];
  const ALLOWED_ATTRS = ["style"]; // apenas style inline gerado pelo execCommand

  // Parser simples via DOMParser no browser
  if (typeof DOMParser === "undefined") return html;
  const doc = new DOMParser().parseFromString(html, "text/html");

  function clean(node) {
    if (node.nodeType === Node.TEXT_NODE) return;
    if (node.nodeType === Node.ELEMENT_NODE) {
      const tag = node.tagName.toLowerCase();
      if (!ALLOWED.includes(tag)) {
        // substitui pelo conteúdo
        node.replaceWith(...node.childNodes);
        return;
      }
      // remove atributos não permitidos
      [...node.attributes].forEach((attr) => {
        if (!ALLOWED_ATTRS.includes(attr.name)) node.removeAttribute(attr.name);
      });
    }
    [...node.childNodes].forEach(clean);
  }

  [...doc.body.childNodes].forEach(clean);
  return doc.body.innerHTML;
}

/**
 * useRichField(initialValue)
 *
 * Retorna { html, plain, onChange, onBlurHtml, reset }
 *
 * Uso:
 *   const objetivo = useRichField(laudo.objetivo || "");
 *   <RichTextEditor value={objetivo.html} onChange={objetivo.onChange} />
 *   // para salvar: objetivo.html (HTML) ou objetivo.plain (texto puro)
 */
export function useRichField(initialValue = "") {
  const [html, setHtml] = useState(initialValue);

  const onChange = useCallback((newHtml) => {
    setHtml(newHtml);
  }, []);

  // chamado no onBlur — sanitiza antes de persistir
  const onBlurHtml = useCallback((rawHtml) => {
    const clean = sanitize(rawHtml);
    setHtml(clean);
  }, []);

  const reset = useCallback((val = "") => {
    setHtml(val);
  }, []);

  return {
    html,
    plain: htmlToPlain(html),
    onChange,
    onBlurHtml,
    reset,
  };
}

export default useRichField;
