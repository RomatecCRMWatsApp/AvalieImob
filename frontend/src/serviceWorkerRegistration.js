// @module serviceWorkerRegistration â€” registra o SW e forca auto-atualizacao.
// Garante que novas versoes cheguem sem limpar cache (inclusive PWA no iOS).

const SW_URL = `${process.env.PUBLIC_URL}/service-worker.js`;

export function register() {
  if (!('serviceWorker' in navigator)) return;

  const hadController = !!navigator.serviceWorker.controller;
  let refreshing = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (refreshing || !hadController) return;
    refreshing = true;
    window.location.reload();
  });

  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register(SW_URL)
      .then((registration) => {
        registration.update().catch(() => {});
        document.addEventListener('visibilitychange', () => {
          if (document.visibilityState === 'visible') {
            registration.update().catch(() => {});
          }
        });

        registration.onupdatefound = () => {
          const installing = registration.installing;
          if (!installing) return;
          installing.onstatechange = () => {
            if (installing.state === 'installed' && navigator.serviceWorker.controller) {
              console.info('[SW] Nova versao instalada â€” recarregando...');
            }
          };
        };

        if ('SyncManager' in window) {
          registration.sync.register('avalieimob-sync-tvi').catch(() => {});
        }
      })
      .catch((err) => {
        console.warn('[SW] Falha ao registrar:', err);
      });

    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data?.type === 'SYNC_PENDING') {
        window.dispatchEvent(new CustomEvent('avalieimob:sync-pending'));
      }
    });
  });
}

export function unregister() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => registration.unregister())
      .catch(() => {});
  }
}