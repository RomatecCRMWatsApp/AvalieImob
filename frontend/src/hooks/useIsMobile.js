// @module useIsMobile — detecta dispositivo móvel por largura, userAgent e PWA standalone
import { useState, useEffect } from 'react';

const MOBILE_BREAKPOINT = 768;

const MOBILE_UA_REGEX = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|mobile|Tablet/i;

function detectMobile() {
  const byWidth = window.innerWidth <= MOBILE_BREAKPOINT;
  const byUA = MOBILE_UA_REGEX.test(navigator.userAgent);
  const byStandalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;
  return byWidth || byUA || byStandalone;
}

export function useIsMobile() {
  const [isMobile, setIsMobile] = useState(detectMobile);

  useEffect(() => {
    function handleResize() {
      setIsMobile(detectMobile());
    }
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return isMobile;
}

export default useIsMobile;
