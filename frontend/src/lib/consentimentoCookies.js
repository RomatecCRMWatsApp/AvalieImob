// @module lib/consentimentoCookies — Preferências de cookies/rastreadores OPCIONAIS.
// Fonte da verdade do consentimento no navegador (o carregador em
// public/rastreio-consentido.js lê a MESMA chave). Categorias:
//   analytics → Google Analytics 4 (estatística de audiência)
//   replay    → Microsoft Clarity (mapas de calor e gravação de sessão)
// Necessários (login, preferências, rascunhos, origem do cadastro) não dependem disso.
export const CHAVE = 'avalie_consentimento_cookies';
export const VERSAO = '2026-11-20';
export const EVENTO_ABRIR = 'avalie:preferencias-cookies';

const PLACEHOLDER = /^%REACT_APP_/;

function idValido(id) {
  return !!id && !PLACEHOLDER.test(id);
}

/** Quais rastreadores opcionais este build tem configurados. */
export function rastreadoresConfigurados(env = process.env) {
  return {
    analytics: idValido(env.REACT_APP_GA_MEASUREMENT_ID),
    replay: idValido(env.REACT_APP_CLARITY_PROJECT_ID),
  };
}

export function lerConsentimento(storage = window.localStorage) {
  try {
    const c = JSON.parse(storage.getItem(CHAVE) || 'null');
    return c && c.versao ? c : null;
  } catch (_e) {
    return null;
  }
}

const COOKIES_OPCIONAIS = [/^_ga/, /^_gid$/, /^_gat/, /^_clck$/, /^_clsk$/, /^CLID$/, /^MUID$/];

/** Apaga cookies dos rastreadores opcionais sob o nosso domínio (limite: cookies de
 * terceiros nos domínios do fornecedor não são alcançáveis pelo site). */
export function apagarCookiesOpcionais(doc = document) {
  const nomes = (doc.cookie || '').split(';').map((c) => c.split('=')[0].trim()).filter(Boolean);
  const host = doc.location ? doc.location.hostname : '';
  const dominios = ['', host, `.${host}`, `.${host.split('.').slice(-3).join('.')}`];
  let n = 0;
  nomes.forEach((nome) => {
    if (COOKIES_OPCIONAIS.some((re) => re.test(nome))) {
      dominios.forEach((d) => {
        doc.cookie = `${nome}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/${d ? `; domain=${d}` : ''}`;
      });
      n += 1;
    }
  });
  return n;
}

/**
 * Salva a escolha. Se alguma categoria foi REVOGADA, apaga os cookies opcionais e
 * pede recarga (o script do fornecedor já carregado só sai da página recarregando).
 * Retorna {precisaRecarregar}.
 */
export function salvarConsentimento({ analytics, replay }, { storage = window.localStorage, win = window } = {}) {
  const anterior = lerConsentimento(storage);
  const novo = { versao: VERSAO, analytics: !!analytics, replay: !!replay, em: new Date().toISOString() };
  try { storage.setItem(CHAVE, JSON.stringify(novo)); } catch (_e) { /* modo privado */ }
  const revogou = !!anterior && ((anterior.analytics && !novo.analytics) || (anterior.replay && !novo.replay));
  if (revogou) {
    apagarCookiesOpcionais(win.document);
    return { precisaRecarregar: true, consentimento: novo };
  }
  if (typeof win.__avalieRastreio === 'function') win.__avalieRastreio();
  return { precisaRecarregar: false, consentimento: novo };
}

export function abrirPreferencias(win = window) {
  win.dispatchEvent(new Event(EVENTO_ABRIR));
}
