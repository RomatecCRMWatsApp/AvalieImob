/* Carregador de rastreadores OPCIONAIS condicionado ao consentimento (LGPD / Guia ANPD).
 * Google Analytics 4 e Microsoft Clarity só são carregados se:
 *   1) o ID estiver configurado no build (window.__AVALIE_GA_ID / __AVALIE_CLARITY_ID);
 *   2) o visitante tiver ACEITADO a categoria correspondente
 *      (localStorage "avalie_consentimento_cookies": {analytics, replay}).
 * Antes da escolha, nada é carregado, nenhum cookie desses fornecedores é gravado e
 * nenhuma requisição sai para eles. Chamado no carregamento e de novo após o aceite.
 */
(function (w, d) {
  var CHAVE = 'avalie_consentimento_cookies';
  function ler() {
    try { return JSON.parse(w.localStorage.getItem(CHAVE) || 'null'); } catch (e) { return null; }
  }
  function valido(id, placeholder) { return !!id && id.indexOf('%REACT_APP_') !== 0 && id !== placeholder; }
  function carregarGA(id) {
    if (w.__avalieGA) return; w.__avalieGA = true;
    var s = d.createElement('script'); s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + id;
    d.head.appendChild(s);
    w.dataLayer = w.dataLayer || [];
    w.gtag = function () { w.dataLayer.push(arguments); };
    w.gtag('js', new Date());
    w.gtag('config', id, { anonymize_ip: true });
  }
  function carregarClarity(id) {
    if (w.__avalieClarity) return; w.__avalieClarity = true;
    w.clarity = w.clarity || function () { (w.clarity.q = w.clarity.q || []).push(arguments); };
    var t = d.createElement('script'); t.async = true; t.src = 'https://www.clarity.ms/tag/' + id;
    d.head.appendChild(t);
  }
  w.__avalieRastreio = function () {
    var c = ler();
    if (!c) return { carregados: [] };
    var out = [];
    if (c.analytics === true && valido(w.__AVALIE_GA_ID)) { carregarGA(w.__AVALIE_GA_ID); out.push('ga'); }
    if (c.replay === true && valido(w.__AVALIE_CLARITY_ID)) { carregarClarity(w.__AVALIE_CLARITY_ID); out.push('clarity'); }
    return { carregados: out };
  };
  w.__avalieRastreio();
})(window, document);
