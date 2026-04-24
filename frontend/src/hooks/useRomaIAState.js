import { useState, useCallback, useRef } from 'react';

export function useRomaIAState() {
  const [state, setState] = useState('idle');
  const timerRef = useRef(null);

  const setThinking = useCallback(() => {
    clearTimeout(timerRef.current);
    setState('thinking');
  }, []);

  const setTyping = useCallback(() => {
    clearTimeout(timerRef.current);
    setState('typing');
  }, []);

  const setSpeaking = useCallback(() => {
    clearTimeout(timerRef.current);
    setState('speaking');
    timerRef.current = setTimeout(() => setState('idle'), 2500);
  }, []);

  const setIdle = useCallback(() => {
    clearTimeout(timerRef.current);
    setState('idle');
  }, []);

  return { state, setThinking, setTyping, setSpeaking, setIdle };
}
