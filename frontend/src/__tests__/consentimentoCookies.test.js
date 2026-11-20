// Rastreadores opcionais: nada antes da escolha; rejeição não carrega; revogação apaga
// cookies e pede recarga. Roda o carregador REAL de public/rastreio-consentido.js.
import fs from 'fs';
import path from 'path';
import {
  CHAVE, lerConsentimento, rastreadoresConfigurados, salvarConsentimento,
} from '../lib/consentimentoCookies';

const LOADER = fs.readFileSync(path.join(__dirname, '../../public/rastreio-consentido.js'), 'utf8');

function scriptsExternos() {
  return Array.from(document.querySelectorAll('script[src]')).map((s) => s.src);
}

function rodarLoader() {
  // eslint-disable-next-line no-new-func
  new Function(LOADER)();
}

beforeEach(() => {
  document.head.innerHTML = '';
  window.localStorage.clear();
  delete window.__avalieGA; delete window.__avalieClarity; delete window.gtag; delete window.clarity;
  window.__AVALIE_GA_ID = 'G-TESTE123';
  window.__AVALIE_CLARITY_ID = 'clarityteste';
});

test('sem escolha: nenhum script de rastreio é carregado', () => {
  rodarLoader();
  expect(scriptsExternos()).toEqual([]);
  expect(window.gtag).toBeUndefined();
});

test('rejeitar opcionais: continua sem carregar nada', () => {
  rodarLoader();
  salvarConsentimento({ analytics: false, replay: false });
  expect(scriptsExternos()).toEqual([]);
  expect(lerConsentimento()).toMatchObject({ analytics: false, replay: false });
});

test('aceitar só estatística carrega GA e não o Clarity', () => {
  rodarLoader();
  salvarConsentimento({ analytics: true, replay: false });
  const srcs = scriptsExternos();
  expect(srcs.some((s) => s.includes('googletagmanager.com'))).toBe(true);
  expect(srcs.some((s) => s.includes('clarity.ms'))).toBe(false);
});

test('consentimento já gravado é respeitado no carregamento seguinte', () => {
  window.localStorage.setItem(CHAVE, JSON.stringify({ versao: 'x', analytics: false, replay: true }));
  rodarLoader();
  const srcs = scriptsExternos();
  expect(srcs.some((s) => s.includes('clarity.ms'))).toBe(true);
  expect(srcs.some((s) => s.includes('googletagmanager'))).toBe(false);
});

test('ID não configurado no build (placeholder) nunca carrega', () => {
  window.__AVALIE_GA_ID = '%REACT_APP_GA_MEASUREMENT_ID%';
  window.localStorage.setItem(CHAVE, JSON.stringify({ versao: 'x', analytics: true, replay: false }));
  rodarLoader();
  expect(scriptsExternos()).toEqual([]);
});

test('revogação apaga cookies opcionais e pede recarga', () => {
  rodarLoader();
  salvarConsentimento({ analytics: true, replay: true });
  document.cookie = '_ga=GA1.1.123; path=/';
  document.cookie = '_clck=abc; path=/';
  document.cookie = 'tema=dark; path=/';
  const r = salvarConsentimento({ analytics: false, replay: false });
  expect(r.precisaRecarregar).toBe(true);
  expect(document.cookie).not.toMatch(/_ga=|_clck=/);
  expect(document.cookie).toMatch(/tema=dark/);
});

test('rastreadoresConfigurados ignora placeholders e vazios', () => {
  expect(rastreadoresConfigurados({})).toEqual({ analytics: false, replay: false });
  expect(rastreadoresConfigurados({ REACT_APP_GA_MEASUREMENT_ID: '%REACT_APP_GA_MEASUREMENT_ID%' }).analytics).toBe(false);
  expect(rastreadoresConfigurados({ REACT_APP_CLARITY_PROJECT_ID: 'abc' }).replay).toBe(true);
});
