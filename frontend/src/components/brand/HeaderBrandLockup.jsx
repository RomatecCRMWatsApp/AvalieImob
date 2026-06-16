import React, { useEffect, useRef, useState } from 'react';
import { BrandMark } from './BrandMark';

// Header animado: alterna entre 3 lockups do monograma "A" com crossfade.
// O "A" verde é comum aos três → a transição parece o brasão se reconfigurando.
// Pausa no hover; respeita prefers-reduced-motion (fixa no lockup 0);
// mobile (≤640px) encolhe e esconde as taglines.

function useIsMobile(query = '(max-width: 640px)') {
  const [m, setM] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia(query);
    setM(mq.matches);
    const on = (e) => setM(e.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, [query]);
  return m;
}

const WORD = 'font-display font-bold leading-none tracking-tight text-[#0C3320] dark:text-[#EDE6D2]';
const TAG = 'text-[11px] tracking-wider text-neutral-500 dark:text-neutral-400';

function buildLockups(dark, mobile) {
  const s = mobile
    ? { badge: 34, glyph: 32, seal: 36, word: 'text-[18px]', word1: 'text-[20px]' }
    : { badge: 42, glyph: 40, seal: 46, word: 'text-[22px]', word1: 'text-[26px]' };
  return [
    // 0 — selo + assinatura
    () => (
      <div className="flex items-center gap-3">
        <BrandMark size={s.badge} variant="badge" title="AvalieImob" />
        <div>
          <div className={WORD + ' ' + s.word}>AvalieImob</div>
          {!mobile && <div className={'mt-1 ' + TAG}>ROMATEC · PTAM · LAUDOS</div>}
        </div>
      </div>
    ),
    // 1 — monograma como letra ("A" é a inicial)
    () => (
      <div className="flex items-end gap-0.5">
        <BrandMark size={s.glyph} variant={dark ? 'glyphGold' : 'glyph'} title="A" className="-mb-[3px]" />
        <div className="leading-none">
          <div className={WORD + ' ' + s.word1}>valieImob</div>
          {!mobile && <div className={'mt-[5px] ' + TAG}>Avaliação imobiliária · NBR 14.653</div>}
        </div>
      </div>
    ),
    // 2 — brasão / selo de avaliador
    () => (
      <div className="flex items-center gap-3.5">
        <BrandMark size={s.seal} variant="seal" title="AvalieImob" />
        <div className="flex flex-col">
          <div className={WORD + ' ' + s.word}>AvalieImob</div>
          {!mobile && (
            <>
              <div className="my-[5px] h-px w-full bg-[#B8860B]" />
              <div className={TAG}>CNAI 031161 · NBR 14.653 · ICP-Brasil</div>
            </>
          )}
        </div>
      </div>
    ),
  ];
}

export function HeaderBrandLockup({ intervalMs = 3500, dark = false, className }) {
  const [i, setI] = useState(0);
  const [reduced, setReduced] = useState(false);
  const paused = useRef(false);
  const mobile = useIsMobile();
  const lockups = buildLockups(dark, mobile);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReduced(mq.matches);
    const onChange = (e) => setReduced(e.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  useEffect(() => {
    if (reduced) return; // acessibilidade: não anima
    const id = window.setInterval(() => {
      if (!paused.current) setI((p) => (p + 1) % lockups.length);
    }, Math.max(2000, intervalMs));
    return () => window.clearInterval(id);
  }, [reduced, intervalMs, lockups.length]);

  return (
    <div
      // largura reservada p/ os lockups absolutos não sobreporem o menu
      className={'relative h-[60px] sm:h-[78px] w-[170px] sm:w-[290px] ' + (className || '')}
      onMouseEnter={() => { paused.current = true; }}
      onMouseLeave={() => { paused.current = false; }}
      aria-label="AvalieImob"
    >
      {lockups.map((Render, idx) => (
        <div
          key={idx}
          aria-hidden={idx !== i}
          className={
            'absolute left-0 top-0 flex h-full items-center transition-all duration-700 ease-out ' +
            (idx === i
              ? 'opacity-100 translate-y-0'
              : 'opacity-0 translate-y-[7px] pointer-events-none')
          }
        >
          <Render />
        </div>
      ))}
    </div>
  );
}

export default HeaderBrandLockup;
