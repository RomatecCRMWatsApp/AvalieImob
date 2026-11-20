// @module lib/consentimento — rastreadores OPCIONAIS só carregam depois da escolha do visitante.
//
// O index.html apenas declara os IDs configurados (window.__AVALIE_TRACKERS__); nenhum
// script de terceiros é baixado antes do "Aceitar". Sem IDs configurados, não há banner
// (o site só usa armazenamento necessário: login, sessão do chat, preferências de tela).
//
// Guia da ANPD sobre cookies: opções desmarcadas por padrão, aceitar e rejeitar com o mesmo
// destaque, revogação tão fácil quanto o aceite. A escolha fica neste navegador
// (localStorage) com versão e data/hora; mudar a VERSAO pede a escolha de novo.

export const CHAVE = 'avalie_consentimento';
export const VERSAO = 1;
export const EVENTO_ABRIR = 'avalie:cookies-abrir';

export function trackersConfigurados() {
  const t = (typeof window !== 'undefined' && window.__AVALIE_TRACKERS__) || {};
  const lista = [];
  if (t.ga) lista.push({ id: 'ga', nome: 'Google Analytics', finalidade: 'medir visitas e páginas mais lidas' });
  if (t.clarity) lista.push({ id: 'clarity', nome: 'Microsoft Clarity', finalidade: 'mapas de calor e gravação anônima de navegação para melhorar o site' });
  return lista;
}

export function lerEscolha() {
  try {
    const e = JSON.parse(localStorage.getItem(CHAVE) || 'null');
    return e && e.versao === VERSAO ? e : null;
  } catch {
    return null;
  }
}

export function salvarEscolha(analise) {
  const escolha = { versao: VERSAO, analise: !!analise, em: new Date().toISOString() };
  try { localStorage.setItem(CHAVE, JSON.stringify(escolha)); } catch { /* navegador sem storage */ }
  if (escolha.analise) carregarOpcionais();
  return escolha;
}

let carregado = false;
export function carregarOpcionais() {
  if (carregado || typeof document === 'undefined') return;
  const t = window.__AVALIE_TRACKERS__ || {};
  if (t.ga) {
    const s = document.createElement('script');
    s.async = true;
    s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(t.ga)}`;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    // eslint-disable-next-line no-inner-declarations
    function gtag() { window.dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag('js', new Date());
    gtag('config', t.ga, { anonymize_ip: true });
  }
  if (t.clarity) {
    /* eslint-disable */
    (function (c, l, a, r, i, tg, y) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      tg = l.createElement(r); tg.async = 1; tg.src = 'https://www.clarity.ms/tag/' + i;
      y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(tg, y);
    })(window, document, 'clarity', 'script', t.clarity);
    /* eslint-enable */
  }
  carregado = true;
}

// Cookies que GA e Clarity gravam no domínio do site (os do domínio deles o navegador não deixa apagar daqui).
const PREFIXOS = ['_ga', '_gid', '_gat', '_clck', '_clsk', 'CLID', 'MUID', 'ANONCHK', 'SM'];

export function revogar() {
  try { localStorage.removeItem(CHAVE); } catch { /* sem storage */ }
  const host = window.location.hostname;
  const dominios = [host, `.${host}`, `.${host.replace(/^www\./, '')}`];
  document.cookie.split(';').map((c) => c.split('=')[0].trim()).forEach((nome) => {
    if (!PREFIXOS.some((p) => nome.startsWith(p))) return;
    dominios.forEach((d) => { document.cookie = `${nome}=; Max-Age=0; path=/; domain=${d}`; });
    document.cookie = `${nome}=; Max-Age=0; path=/`;
  });
  // Script de terceiro já carregado só sai da memória recarregando a página.
  window.location.reload();
}

export function abrirPreferencias() {
  window.dispatchEvent(new Event(EVENTO_ABRIR));
}

// Chamado uma vez ao iniciar o app: respeita a escolha já feita.
export function aplicarEscolhaSalva() {
  const e = lerEscolha();
  if (e && e.analise) carregarOpcionais();
}
