// @module serviceWorkerRegistration — registra o service worker do AvalieImob

const SW_URL = `${process.env.PUBLIC_URL}/service-worker.js`;

export function register() {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register(SW_URL)
        .then((registration) => {
          registration.onupdatefound = () => {
            const installing = registration.installing;
            if (!installing) return;
            installing.onstatechange = () => {
              if (installing.state === 'installed' && navigator.serviceWorker.controller) {
                console.info('[SW] Nova versão disponível. Recarregue para atualizar.');
              }
            };
          };

          // Request Background Sync permission
          if ('SyncManager' in window) {
            registration.sync.register('avalieimob-sync-tvi').catch(() => {});
          }
        })
        .catch((err) => {
          console.warn('[SW] Falha ao registrar:', err);
        });

      // Listen for SW messages
      navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data?.type === 'SYNC_PENDING') {
          window.dispatchEvent(new CustomEvent('avalieimob:sync-pending'));
        }
      });
    });
  }
}

export function unregister() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => registration.unregister())
      .catch(() => {});
  }
}
