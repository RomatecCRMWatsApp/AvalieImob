// @component Avaliacao3D — wrapper inteligente da secao 3D.
// Decide em runtime entre o canvas pesado (Avaliacao3DCanvas, lazy-loaded)
// e o fallback estatico (Avaliacao3DFallback) baseado em:
//   - prefers-reduced-motion (acessibilidade)
//   - largura de tela < 768px (mobile)
//   - usuario clicou "Pular animacao"
//
// Lazy-loading garante que mobile e usuarios reduced-motion NAO baixam
// three/r3f/drei/gsap (~600KB), so quem efetivamente vai ver a animacao.
import React, { Suspense, lazy, useEffect, useState } from 'react';
import Avaliacao3DFallback from './Avaliacao3DFallback';

const Avaliacao3DCanvas = lazy(() => import('./Avaliacao3DCanvas'));

function shouldUseFallback() {
  if (typeof window === 'undefined') return true; // SSR safe
  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  const isMobile = window.innerWidth < 768;
  return Boolean(reducedMotion || isMobile);
}

export default function Avaliacao3D() {
  const [useFallback, setUseFallback] = useState(true); // default seguro
  const [skipped, setSkipped] = useState(false);

  useEffect(() => {
    setUseFallback(shouldUseFallback());

    // Re-avalia em resize (rotacao tablet, redimensionamento desktop)
    let resizeTimer = null;
    const onResize = () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => setUseFallback(shouldUseFallback()), 250);
    };
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      clearTimeout(resizeTimer);
    };
  }, []);

  if (useFallback || skipped) {
    return <Avaliacao3DFallback />;
  }

  return (
    <Suspense fallback={<Avaliacao3DFallback />}>
      <Avaliacao3DCanvas onSkip={() => setSkipped(true)} />
    </Suspense>
  );
}
