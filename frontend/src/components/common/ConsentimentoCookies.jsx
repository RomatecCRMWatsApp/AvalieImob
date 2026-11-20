// @module components/common/ConsentimentoCookies — banner de rastreadores opcionais.
// Só aparece quando há rastreador opcional configurado (GA/Clarity) e o visitante ainda
// não escolheu, ou quando ele pede para mudar ("Preferências de cookies").
import React, { useEffect, useState } from 'react';
import {
  EVENTO_ABRIR, aplicarEscolhaSalva, lerEscolha, revogar, salvarEscolha, trackersConfigurados,
} from '../../lib/consentimento';

const VERDE = '#0C3320';

export default function ConsentimentoCookies() {
  const trackers = trackersConfigurados();
  const [aberto, setAberto] = useState(false);
  const [configurar, setConfigurar] = useState(false);
  const [analise, setAnalise] = useState(false);
  const escolhaAtual = lerEscolha();

  useEffect(() => {
    aplicarEscolhaSalva();
    if (trackers.length && !lerEscolha()) setAberto(true);
    const abrir = () => { setAnalise(!!lerEscolha()?.analise); setConfigurar(true); setAberto(true); };
    window.addEventListener(EVENTO_ABRIR, abrir);
    return () => window.removeEventListener(EVENTO_ABRIR, abrir);
  }, [trackers.length]);

  if (!aberto) return null;

  const fechar = (valor) => { salvarEscolha(valor); setAberto(false); setConfigurar(false); };
  const botao = 'px-4 py-2 rounded-md text-sm font-semibold border min-h-[44px]';

  return (
    <div role="dialog" aria-modal="false" aria-labelledby="consent-titulo"
         className="fixed bottom-0 inset-x-0 z-[1400] p-3 sm:p-4">
      <div className="max-w-3xl mx-auto bg-white border border-gray-200 rounded-xl shadow-2xl p-4 sm:p-5 text-sm text-gray-700">
        <h2 id="consent-titulo" className="font-bold text-base mb-1" style={{ color: VERDE }}>Cookies e medição</h2>
        {!trackers.length ? (
          <p>Este site usa apenas armazenamento necessário (login, sessão do atendimento e preferências de tela). Não há rastreadores opcionais ativos.</p>
        ) : (
          <p>
            Usamos armazenamento necessário para o site funcionar. Com a sua permissão, também usamos
            ferramentas de medição ({trackers.map((t) => t.nome).join(' e ')}). Elas só são carregadas se você aceitar.{' '}
            <a href="/privacidade" className="underline">Saiba mais</a>.
          </p>
        )}

        {configurar && trackers.length > 0 && (
          <div className="mt-3 space-y-2 border-t border-gray-100 pt-3">
            <label className="flex items-start gap-3">
              <input type="checkbox" checked disabled className="mt-1" />
              <span><strong>Necessários</strong> — login, segurança e preferências de tela. Sempre ativos.</span>
            </label>
            <label className="flex items-start gap-3 cursor-pointer">
              <input type="checkbox" checked={analise} onChange={(e) => setAnalise(e.target.checked)} className="mt-1" />
              <span><strong>Medição</strong> — {trackers.map((t) => `${t.nome}: ${t.finalidade}`).join('; ')}.</span>
            </label>
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          {trackers.length > 0 && !configurar && (
            <>
              <button type="button" className={botao} style={{ borderColor: VERDE, color: VERDE }} onClick={() => fechar(false)}>Rejeitar opcionais</button>
              <button type="button" className={botao} style={{ borderColor: VERDE, color: VERDE }} onClick={() => fechar(true)}>Aceitar opcionais</button>
              <button type="button" className={`${botao} border-gray-300 text-gray-600`} onClick={() => setConfigurar(true)}>Configurar</button>
            </>
          )}
          {trackers.length > 0 && configurar && (
            <>
              <button type="button" className={botao} style={{ borderColor: VERDE, color: VERDE }} onClick={() => fechar(analise)}>Salvar escolha</button>
              {escolhaAtual && (
                <button type="button" className={`${botao} border-gray-300 text-gray-600`} onClick={revogar}>Apagar minha escolha e cookies de medição</button>
              )}
            </>
          )}
          {!trackers.length && (
            <button type="button" className={botao} style={{ borderColor: VERDE, color: VERDE }} onClick={() => setAberto(false)}>Fechar</button>
          )}
        </div>
      </div>
    </div>
  );
}
