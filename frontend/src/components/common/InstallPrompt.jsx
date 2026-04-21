// @module InstallPrompt — banner de instalação PWA para Android e iOS
import React, { useState, useEffect } from 'react';
import { Download, X, Smartphone } from 'lucide-react';

const DISMISS_KEY = 'avalieimob_install_dismissed';
const DISMISS_DAYS = 7;

function isDismissed() {
  try {
    const ts = localStorage.getItem(DISMISS_KEY);
    if (!ts) return false;
    return Date.now() - Number(ts) < DISMISS_DAYS * 86400 * 1000;
  } catch { return false; }
}

function isIOS() {
  return /iphone|ipad|ipod/i.test(navigator.userAgent) && !window.MSStream;
}

function isStandalone() {
  return window.matchMedia('(display-mode: standalone)').matches
    || window.navigator.standalone === true;
}

const InstallPrompt = () => {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [visible, setVisible] = useState(false);
  const [ios, setIos] = useState(false);

  useEffect(() => {
    if (isStandalone() || isDismissed()) return;

    if (isIOS()) {
      setIos(true);
      setVisible(true);
      return;
    }

    const handler = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setVisible(true);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const dismiss = () => {
    setVisible(false);
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
  };

  const install = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') setVisible(false);
    setDeferredPrompt(null);
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 max-w-sm mx-auto">
      <div className="bg-[#0d2b0d] border border-emerald-800 rounded-2xl shadow-2xl p-4 text-white">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-emerald-700 flex items-center justify-center">
              <Smartphone className="w-5 h-5" />
            </div>
            <div>
              <p className="font-semibold text-sm leading-tight">Instalar AvalieImob</p>
              <p className="text-xs text-emerald-300">Acesso offline no campo</p>
            </div>
          </div>
          <button onClick={dismiss}
            className="text-gray-400 hover:text-white p-1 -mt-1 -mr-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        {ios ? (
          <div className="text-xs text-emerald-100 space-y-1">
            <p>Para instalar no iPhone/iPad:</p>
            <p>1. Toque em <strong>Compartilhar</strong> <span>↑</span> no Safari</p>
            <p>2. Selecione <strong>Adicionar à Tela Inicial</strong></p>
          </div>
        ) : (
          <div className="flex gap-2 mt-1">
            <button onClick={dismiss}
              className="flex-1 py-2 rounded-xl border border-emerald-700 text-xs text-emerald-300 hover:bg-emerald-900 transition-colors">
              Agora não
            </button>
            <button onClick={install}
              className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold flex items-center justify-center gap-1 transition-colors">
              <Download className="w-3 h-3" /> Instalar App
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default InstallPrompt;
