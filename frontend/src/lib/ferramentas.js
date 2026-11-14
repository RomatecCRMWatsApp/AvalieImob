// Ponte entre a área de Ferramentas do painel e os widgets existentes
// (Roma_IA, Galeria de Fotos, Consulta CNPJ/CPF). Os widgets continuam donos do
// próprio estado e dos próprios fluxos; aqui só se pede que abram.
import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export const EVENTO_FERRAMENTA = 'avalie:ferramenta';

export const FERRAMENTAS = {
  ROMA_IA: 'roma-ia',
  FOTOS: 'fotos',
  CONSULTA: 'consulta',
  TEMA: 'tema',
};

export function abrirFerramenta(id) {
  window.dispatchEvent(new CustomEvent(EVENTO_FERRAMENTA, { detail: id }));
}

/** Chama `abrir` quando a área de Ferramentas pede a ferramenta `id`. */
export function useAberturaFerramenta(id, abrir) {
  useEffect(() => {
    const h = (e) => { if (e.detail === id) abrir(); };
    window.addEventListener(EVENTO_FERRAMENTA, h);
    return () => window.removeEventListener(EVENTO_FERRAMENTA, h);
  }, [id, abrir]);
}

/**
 * Dentro do painel (/dashboard) as ferramentas são acessadas pelo botão
 * "Ferramentas" do cabeçalho — as abas flutuantes laterais ficam ocultas.
 * Nas páginas públicas o comportamento antigo continua.
 */
export function useNoPainel() {
  const { pathname } = useLocation();
  return pathname === '/dashboard' || pathname.startsWith('/dashboard/');
}
