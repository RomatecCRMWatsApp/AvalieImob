// @hook useScrollProgress — retorna progresso 0→1 de uma section conforme
// ela atravessa o viewport. Usado pela secao 3D (Avaliacao3D) pra amarrar
// transformacoes Three.js ao scroll do usuario.
//
// Uso:
//   const ref = useRef(null);
//   const progress = useScrollProgress(ref);
//   // progress vai de 0 (topo da section ainda abaixo do viewport)
//   // ate 1 (base da section ja saiu pelo topo).
//
// Implementacao via requestAnimationFrame + IntersectionObserver pra
// evitar listener de scroll global (menos peso na main thread).
import { useEffect, useState } from 'react';

export function useScrollProgress(ref) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!ref?.current) return undefined;
    const el = ref.current;
    let rafId = null;
    let visible = false;

    const compute = () => {
      const rect = el.getBoundingClientRect();
      const winH = window.innerHeight || document.documentElement.clientHeight;
      // Section atravessa o viewport: comeca quando topo entra,
      // termina quando base sai. Total de pixels percorridos = altura
      // da section + altura do viewport. Mapeamos linearmente em 0..1.
      const total = rect.height + winH;
      const traveled = winH - rect.top;
      const p = Math.max(0, Math.min(1, traveled / total));
      setProgress(p);
    };

    const tick = () => {
      compute();
      if (visible) rafId = requestAnimationFrame(tick);
    };

    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        visible = entry.isIntersecting;
        if (visible && rafId === null) {
          rafId = requestAnimationFrame(tick);
        } else if (!visible && rafId !== null) {
          cancelAnimationFrame(rafId);
          rafId = null;
        }
      });
    }, { threshold: 0, rootMargin: '0px' });

    io.observe(el);
    compute();

    return () => {
      io.disconnect();
      if (rafId !== null) cancelAnimationFrame(rafId);
    };
  }, [ref]);

  return progress;
}
