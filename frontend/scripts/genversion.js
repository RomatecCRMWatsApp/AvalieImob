// Gera frontend/src/version.js com a data/hora do build (roda no prebuild).
const fs = require('fs');
const path = require('path');
const now = new Date();
const br = new Date(now.getTime() - 3 * 60 * 60 * 1000); // UTC-3 (Brasil)
const p = (n) => String(n).padStart(2, '0');
const version = 'v1.0 Â· ' + p(br.getUTCDate()) + '/' + p(br.getUTCMonth() + 1)
  + ' ' + p(br.getUTCHours()) + ':' + p(br.getUTCMinutes());
fs.writeFileSync(
  path.join(__dirname, '..', 'src', 'version.js'),
  '// Gerado automaticamente no build (prebuild). NAO editar manualmente.\n'
  + "export const APP_VERSION = '" + version + "';\n",
  'utf8'
);
console.log('[genversion] APP_VERSION =', version);