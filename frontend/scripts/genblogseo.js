// Prebuild: junta os artigos de src/data/blog/*.json em public/blog-seo.json.
// O backend (services/seo_html) lê esse arquivo no build para entregar o MESMO texto
// do artigo no HTML inicial (título, H1, seções e links), antes do JavaScript.
const fs = require('fs');
const path = require('path');

const dir = path.join(__dirname, '..', 'src', 'data', 'blog');
const out = path.join(__dirname, '..', 'public', 'blog-seo.json');
const artigos = {};
for (const f of fs.readdirSync(dir).filter((n) => n.endsWith('.json')).sort()) {
  const a = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
  if (!a.slug || a.slug + '.json' !== f) throw new Error(`slug divergente do nome do arquivo: ${f}`);
  artigos[a.slug] = a;
}
fs.writeFileSync(out, JSON.stringify(artigos));
console.log(`[genblogseo] ${Object.keys(artigos).length} artigo(s) -> public/blog-seo.json`);
