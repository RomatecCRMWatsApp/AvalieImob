// @module components/common/CookieConsent — Banner e painel de preferências de cookies.
// Só aparece quando o build tem rastreador OPCIONAL configurado (GA4/Clarity). Sem
// escolha, nada opcional é carregado (ver public/rastreio-consentido.js). Botões com o
// mesmo peso visual (sem indução); opções desmarcadas por padrão; reabre pelo link
// "Preferências de cookies" (evento EVENTO_ABRIR).
import React, { useEffect, useState } from 'react';
import {
  EVENTO_ABRIR, lerConsentimento, rastreadoresConfigurados, salvarConsentimento,
} from '../../lib/consentimentoCookies';

const BTN = 'px-4 py-2 rounded-lg text-sm font-semibold border border-emerald-900 text-emerald-950 bg-white hover:bg-emerald-50';

export default function CookieConsent() {
  const cfg = rastreadoresConfigurados();
  const temOpcional = cfg.analytics || cfg.replay;
  const [aberto, setAberto] = useState(() => temOpcional && !lerConsentimento());
  const [config, setConfig] = useState(false);
  const atual = lerConsentimento() || {};
  const [sel, setSel] = useState({ analytics: !!atual.analytics, replay: !!atual.replay });

  useEffect(() => {
    const abrir = () => { setAberto(true); setConfig(true); };
    window.addEventListener(EVENTO_ABRIR, abrir);
    return () => window.removeEventListener(EVENTO_ABRIR, abrir);
  }, []);

  if (!temOpcional || !aberto) return null;

  const salvar = (escolha) => {
    const { precisaRecarregar } = salvarConsentimento(escolha);
    setAberto(false);
    setConfig(false);
    if (precisaRecarregar) window.location.reload();
  };

  return (
    <div role="dialog" aria-modal="false" aria-labelledby="cookie-titulo"
      className="fixed bottom-0 inset-x-0 z-[1400] p-3 sm:p-4">
      <div className="max-w-3xl mx-auto bg-white border border-emerald-900/20 shadow-xl rounded-xl p-4 text-sm text-gray-800">
        <h2 id="cookie-titulo" className="font-semibold text-emerald-950 mb-1">Cookies e medição de uso</h2>
        <p className="mb-3">
          Usamos armazenamento necessário para o site funcionar (login, preferências). Com sua
          permissão, também usamos ferramentas opcionais de estatística{cfg.replay ? ' e de gravação de sessão' : ''}.
          {' '}<a href="/privacidade" className="underline">Saiba mais</a>.
        </p>
        {config && (
          <div className="space-y-2 mb-3">
            <label className="flex gap-2 items-start">
              <input type="checkbox" checked disabled aria-label="Necessários (sempre ativos)" />
              <span><b>Necessários</b> — sempre ativos (sessão, segurança, preferências).</span>
            </label>
            {cfg.analytics && (
              <label className="flex gap-2 items-start">
                <input type="checkbox" checked={sel.analytics}
                  onChange={(e) => setSel((s) => ({ ...s, analytics: e.target.checked }))} />
                <span><b>Estatística</b> — Google Analytics: páginas visitadas e origem do acesso.</span>
              </label>
            )}
            {cfg.replay && (
              <label className="flex gap-2 items-start">
                <input type="checkbox" checked={sel.replay}
                  onChange={(e) => setSel((s) => ({ ...s, replay: e.target.checked }))} />
                <span><b>Gravação de sessão</b> — Microsoft Clarity: cliques, rolagem e mapas de calor.</span>
              </label>
            )}
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          <button type="button" className={BTN} onClick={() => salvar({ analytics: false, replay: false })}>
            Rejeitar opcionais
          </button>
          <button type="button" className={BTN} onClick={() => salvar({ analytics: cfg.analytics, replay: cfg.replay })}>
            Aceitar opcionais
          </button>
          {config ? (
            <button type="button" className={BTN} onClick={() => salvar(sel)}>Salvar escolha</button>
          ) : (
            <button type="button" className={BTN} onClick={() => setConfig(true)}>Configurar</button>
          )}
        </div>
      </div>
    </div>
  );
}
