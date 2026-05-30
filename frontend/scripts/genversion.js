// Gera frontend/src/version.js no prebuild:
// numero de build incremental (quantas versoes / em qual esta) + SHA + data/hora.
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function git(cmd, fallback) {
  try {
    return execSync('git ' + cmd, { cwd: __dirname, stdio: ['ignore', 'pipe', 'ignore'] })
      .toString().trim();
  } catch (e) {
    return fallback;
  }
}

// Numero de build = total de commits no historico (monotonico e crescente).
// Diz exatamente quantas versoes ja sairam e em qual o sistema esta.
let build = parseInt(git('rev-list --count HEAD', ''), 10);
if (!Number.isFinite(build) || build <= 0) {
  // Fallback (sem git): incrementa a partir do version.js anterior.
  try {
    const prev = fs.readFileSync(path.join(__dirname, '..', 'src', 'version.js'), 'utf8');
    const m = prev.match(/BUILD_NUMBER\s*=\s*(\d+)/);
    build = m ? parseInt(m[1], 10) + 1 : 1;
  } catch (e) {
    build = 1;
  }
}

const sha = git('rev-parse --short HEAD', 'local');

// Horario do build em UTC-3 (Brasil).
const now = new Date();
const br = new Date(now.getTime() - 3 * 60 * 60 * 1000);
const p = (n) => String(n).padStart(2, '0');
const data = p(br.getUTCDate()) + '/' + p(br.getUTCMonth() + 1) + '/' + br.getUTCFullYear();
const hora = p(br.getUTCHours()) + ':' + p(br.getUTCMinutes());

const MAJOR = 1;
const MINOR = 0;
const version = 'v' + MAJOR + '.' + MINOR + '.' + build;          // ex.: v1.0.137
const dataHora = data + ' ' + hora;                                // ex.: 30/05/2026 09:30
const label = version + ' - ' + dataHora;                          // ex.: v1.0.137 - 30/05/2026 09:30

const out =
  '// Gerado automaticamente no build (prebuild). NAO editar manualmente.\n' +
  'export const APP_VERSION = ' + JSON.stringify(version) + ';\n' +
  'export const BUILD_NUMBER = ' + build + ';\n' +
  'export const BUILD_SHA = ' + JSON.stringify(sha) + ';\n' +
  'export const BUILD_DATE = ' + JSON.stringify(dataHora) + ';\n' +
  'export const APP_BUILD_LABEL = ' + JSON.stringify(label) + ';\n';

fs.writeFileSync(path.join(__dirname, '..', 'src', 'version.js'), out, 'utf8');
console.log('[genversion] ' + label + ' (' + sha + ')');
