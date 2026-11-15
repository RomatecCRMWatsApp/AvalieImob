// @module shell/AvatarPerfil — foto do perfil (Meu Currículo → foto_perfil) no
// cabeçalho e no menu. Busca o perfil uma vez por sessão; sem foto, ou se a
// imagem falhar, mostra as iniciais.
import React, { useEffect, useState } from 'react';
import { perfilAPI, API_BASE } from '../../lib/api';

export const EVENTO_PERFIL = 'avalie:perfil-atualizado';

const fotoSrc = (v) => {
  if (!v) return null;
  const s = String(v);
  if (/^(https?:|data:)/i.test(s) || s.startsWith('/')) return s;
  return `${API_BASE}/upload/image/${s}`;
};

let cache = null; // Promise<string|null>
const carregar = (forcar) => {
  if (!cache || forcar) {
    cache = perfilAPI.get().then((p) => fotoSrc(p?.foto_perfil)).catch(() => null);
  }
  return cache;
};

export function useFotoPerfil() {
  const [src, setSrc] = useState(null);
  useEffect(() => {
    let vivo = true;
    carregar(false).then((s) => { if (vivo) setSrc(s); });
    const atualizar = () => carregar(true).then((s) => { if (vivo) setSrc(s); });
    window.addEventListener(EVENTO_PERFIL, atualizar);
    return () => { vivo = false; window.removeEventListener(EVENTO_PERFIL, atualizar); };
  }, []);
  return src;
}

export default function AvatarPerfil({ iniciais = 'U', size = 34, bg = 'var(--av-brand)', color = 'var(--av-gold)' }) {
  const src = useFotoPerfil();
  const [erro, setErro] = useState(false);
  useEffect(() => { setErro(false); }, [src]);
  const base = {
    width: size, height: size, borderRadius: 999, flexShrink: 0, overflow: 'hidden',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  };
  if (src && !erro) {
    return (
      <span aria-hidden="true" style={{ ...base, background: bg }}>
        <img src={src} alt="" onError={() => setErro(true)}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      </span>
    );
  }
  return (
    <span aria-hidden="true" style={{ ...base, background: bg, color, fontSize: Math.round(size * 0.36), fontWeight: 700 }}>
      {iniciais}
    </span>
  );
}
