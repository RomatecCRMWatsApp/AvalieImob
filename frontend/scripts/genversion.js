// Gera frontend/src/version.js no prebuild.
// Numero de build (incremental) + SHA + data/hora.
//
// IMPORTANTE: no build do Docker/Railway o .git NAO existe (.dockerignore exclui **/.git),
// entao 'git rev-list' falha la. Por isso a fonte primaria do numero e o arquivo
// committed frontend/build-number.txt — incrementado pelo DEPLOY.bat (onde o git existe).
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

// 1) build-number.txt (commitado, funciona sem git)  2) git count  3) version.js anterior
let build;
try {
  const raw = fs.readFileSync(path.join(__dirname, '..', 'build-number.txt'), 'utf8').trim();
  const n = parseInt(raw, 10);
  if (Number.isFinite(n) && n > 0) build = n;
} catch (e) { /* sem arquivo */ }

if (build === undefined) {
  const g = parseInt(git('rev-list --count HEAD', ''), 10);
  if (Number.isFinite(g) && g > 0) build = g;
}

if (build === undefined) {
  try {
    const prev = fs.readFileSync(path.join(__dirname, '..', 'src', 'version.js'), 'utf8');
    const m = prev.match(/BUILD_NUMBER\s*=\s*(\d+)/);
    build = m ? parseInt(m[1], 10) : 1;   // sem +1 (nao infla a cada build sem git)
  } catch (e) {
    build = 1;
  }
}

const sha = git('rev-parse --short HEAD', 'local');

// Horario do build em UTC-3 (Brasil)
const now = new Date();
const br = new Date(now.getTime() - 3 * 60 * 60 * 1000);
const p = (n) => String(n).padStart(2, '0');
const data = p(br.getUTCDate()) + '/' + p(br.getUTCMonth() + 1) + '/' + br.getUTCFullYear();
const hora = p(br.getUTCHours()) + ':' + p(br.getUTCMinutes());

const MAJOR = 1;
const MINOR = 4;
const version = 'v' + MAJOR + '.' + MINOR + '.' + build;     // ex.: v1.0.339
const dataHora = data + ' ' + hora;                           // ex.: 30/05/2026 12:07
const label = version + ' - ' + dataHora;

const out =
  '// Gerado automaticamente no build (prebuild). NAO editar manualmente.\n' +
  'export const APP_VERSION = ' + JSON.stringify(version) + ';\n' +
  'export const BUILD_NUMBER = ' + build + ';\n' +
  'export const BUILD_SHA = ' + JSON.stringify(sha) + ';\n' +
  'export const BUILD_DATE = ' + JSON.stringify(dataHora) + ';\n' +
  'export const APP_BUILD_LABEL = ' + JSON.stringify(label) + ';\n';

fs.writeFileSync(path.join(__dirname, '..', 'src', 'version.js'), out, 'utf8');

// Publica também um version.json estático (servido em /version.json) para o
// front detectar atualização: compara o build publicado com o build carregado.
try {
  fs.writeFileSync(
    path.join(__dirname, '..', 'public', 'version.json'),
    JSON.stringify({ build: build, version: version, date: dataHora }) + '\n',
    'utf8'
  );
} catch (e) { /* pasta public ausente em alguns contextos — ignora */ }

console.log('[genversion] ' + label + ' (' + sha + ')');
