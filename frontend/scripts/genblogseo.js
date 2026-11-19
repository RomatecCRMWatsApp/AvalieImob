// Prebuild: junta src/data/blog/*.json em public/blog-seo.json e src/data/servicos/*.json
// em public/servicos-seo.json. O backend (services/seo_html) lê esses arquivos no build para
// entregar o MESMO texto da página no HTML inicial (título, H1, seções e links), antes do
// JavaScript. No container só existe frontend/build — por isso o texto precisa ir junto.
const fs = require('fs');
const path = require('path');

function juntar(pasta, saida, rotulo) {
  const dir = path.join(__dirname, '..', 'src', 'data', pasta);
  const itens = {};
  for (const f of fs.readdirSync(dir).filter((n) => n.endsWith('.json')).sort()) {
    const a = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    if (!a.slug || a.slug + '.json' !== f) throw new Error(`slug divergente do nome do arquivo: ${pasta}/${f}`);
    itens[a.slug] = a;
  }
  fs.writeFileSync(path.join(__dirname, '..', 'public', saida), JSON.stringify(itens));
  console.log(`[genblogseo] ${Object.keys(itens).length} ${rotulo} -> public/${saida}`);
}

juntar('blog', 'blog-seo.json', 'artigo(s)');
juntar('servicos', 'servicos-seo.json', 'página(s) de serviço');
