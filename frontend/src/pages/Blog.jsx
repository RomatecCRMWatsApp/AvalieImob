// @module pages/Blog — indice do blog. Lista todos os artigos da BLOG_POSTS.
// SEO: Schema.org Blog + ItemList; canonical; OG/Twitter; sitemap referencia /blog.
import React from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { BLOG_POSTS } from '../data/blogPosts';

const BASE = 'https://www.romatecavalieimob.com.br';

export default function Blog() {
  const url = `${BASE}/blog`;
  const ogImage = `${BASE}/brand/banner.png`;

  const blogSchema = {
    '@context': 'https://schema.org',
    '@type': 'Blog',
    name: 'Blog AvalieImob',
    description: 'Artigos técnicos sobre PTAM, NBR 14.653, avaliação imobiliária urbana e rural, garantias bancárias e mercado.',
    url,
    publisher: {
      '@type': 'Organization',
      name: 'RomaTec Consultoria Total',
      logo: { '@type': 'ImageObject', url: `${BASE}/brand/icone.png` },
    },
    blogPost: BLOG_POSTS.map(p => ({
      '@type': 'BlogPosting',
      headline: p.titulo,
      description: p.meta,
      url: `${BASE}/blog/${p.slug}`,
      datePublished: p.dataPublicacao,
      dateModified: p.dataAtualizacao || p.dataPublicacao,
    })),
  };

  return (
    <>
      <Helmet>
        <title>Blog AvalieImob — Artigos sobre PTAM, NBR 14.653 e Avaliação Imobiliária</title>
        <meta name="description" content="Artigos técnicos sobre PTAM, Laudo Técnico, NBR 14.653, avaliação rural e urbana, garantias bancárias e mercado imobiliário. Conteúdo escrito por engenheiro avaliador." />
        <meta name="keywords" content="blog avaliação imobiliária, artigos PTAM, NBR 14.653, blog avaliador imobiliário, conteúdo técnico avaliação" />
        <link rel="canonical" href={url} />
        <meta property="og:type" content="website" />
        <meta property="og:title" content="Blog AvalieImob — PTAM, NBR 14.653 e Avaliação Imobiliária" />
        <meta property="og:description" content="Artigos técnicos para avaliadores, corretores, engenheiros e arquitetos." />
        <meta property="og:url" content={url} />
        <meta property="og:image" content={ogImage} />
        <meta property="og:locale" content="pt_BR" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Blog AvalieImob" />
        <meta name="twitter:description" content="Conteúdo técnico sobre avaliação imobiliária." />
        <meta name="twitter:image" content={ogImage} />
        <link rel="alternate" hrefLang="pt-BR" href={url} />
        <script type="application/ld+json">{JSON.stringify(blogSchema)}</script>
      </Helmet>

      <main style={styles.main}>
        <header style={styles.header}>
          <Link to="/" style={styles.logoLink}><strong>AvalieImob</strong></Link>
          <nav style={styles.nav}>
            <Link to="/" style={styles.navLink}>Início</Link>
            <Link to="/blog" style={styles.navLink}>Blog</Link>
            <Link to="/planos" style={styles.navLink}>Planos</Link>
            <Link to="/cadastro" style={styles.navCTA}>Teste Grátis</Link>
          </nav>
        </header>

        <section style={styles.hero}>
          <div style={styles.container}>
            <span style={styles.tagHero}>Blog Técnico</span>
            <h1 style={styles.h1}>Conhecimento técnico para avaliadores imobiliários</h1>
            <p style={styles.subtitulo}>
              Artigos práticos sobre PTAM, NBR 14.653, avaliação urbana e rural, garantias bancárias e mercado.
              Conteúdo escrito por engenheiro avaliador com 10+ anos de experiência.
            </p>
          </div>
        </section>

        <section style={styles.section}>
          <div style={styles.container}>
            <div style={styles.grid}>
              {BLOG_POSTS.map(post => (
                <Link key={post.slug} to={`/blog/${post.slug}`} style={styles.card}>
                  <span style={styles.cat}>{post.categoria}</span>
                  <h2 style={styles.cardTitulo}>{post.titulo}</h2>
                  <p style={styles.cardResumo}>{post.meta}</p>
                  <div style={styles.cardMeta}>
                    <time dateTime={post.dataPublicacao}>
                      {new Date(post.dataPublicacao).toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' })}
                    </time>
                    <span style={styles.metaSep}>·</span>
                    <span>{post.tempoLeitura}</span>
                  </div>
                  <span style={styles.lerMais}>Ler artigo →</span>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section style={{ ...styles.section, background: '#c9a84c', color: '#1a1916', textAlign: 'center', padding: '50px 32px' }}>
          <div style={styles.container}>
            <h2 style={{ fontSize: 28, fontWeight: 700, marginBottom: 12, color: '#1a1916' }}>
              Quer emitir laudos profissionais conforme NBR 14.653?
            </h2>
            <p style={{ fontSize: 17, marginBottom: 20, maxWidth: 600, margin: '0 auto 20px' }}>
              Teste o AvalieImob 7 dias grátis. Sem cartão de crédito.
            </p>
            <Link to="/cadastro" style={{ ...styles.ctaPrimary, background: '#0d4f3c', color: '#fff' }}>
              Começar grátis →
            </Link>
          </div>
        </section>

        <footer style={styles.footer}>
          <p>© 2026 RomaTec Consultoria Total · J R P Bezerra LTDA · CNPJ 17.261.987/0001-09</p>
          <p style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>Açailândia/MA · CEP 65.930-000</p>
        </footer>
      </main>
    </>
  );
}

const styles = {
  main: { fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif', color: '#1a1916', lineHeight: 1.6, background: '#fff' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 32px', borderBottom: '1px solid #e5e7eb', background: '#fff', position: 'sticky', top: 0, zIndex: 10 },
  logoLink: { color: '#0d4f3c', fontSize: 22, textDecoration: 'none' },
  nav: { display: 'flex', gap: 20, alignItems: 'center' },
  navLink: { color: '#4b5563', textDecoration: 'none', fontSize: 14 },
  navCTA: { background: '#0d4f3c', color: '#fff', padding: '8px 16px', borderRadius: 6, textDecoration: 'none', fontSize: 14, fontWeight: 600 },

  hero: { padding: '60px 32px 40px', background: 'linear-gradient(135deg, #0d4f3c 0%, #1a6b52 100%)', color: '#fff', textAlign: 'center' },
  container: { maxWidth: 1100, margin: '0 auto' },
  tagHero: { display: 'inline-block', background: 'rgba(201,168,76,0.25)', color: '#ffd97a', padding: '4px 14px', borderRadius: 4, fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 14 },
  h1: { fontSize: 'clamp(28px, 4.5vw, 42px)', fontWeight: 800, marginBottom: 16, letterSpacing: '-0.02em' },
  subtitulo: { fontSize: 'clamp(15px, 2vw, 18px)', opacity: 0.92, maxWidth: 700, margin: '0 auto', lineHeight: 1.5 },

  section: { padding: '50px 32px' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24 },
  card: { display: 'block', padding: 24, background: '#fff', borderRadius: 10, textDecoration: 'none', color: '#1a1916', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0,0,0,0.04)', transition: 'transform 0.15s, box-shadow 0.15s' },
  cat: { display: 'inline-block', fontSize: 11, color: '#0d4f3c', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12, padding: '3px 10px', background: '#f5f7f5', borderRadius: 3 },
  cardTitulo: { fontSize: 20, fontWeight: 700, color: '#0d4f3c', marginBottom: 10, lineHeight: 1.3 },
  cardResumo: { fontSize: 14, color: '#4b5563', marginBottom: 14, lineHeight: 1.5 },
  cardMeta: { fontSize: 13, color: '#6b7280', marginBottom: 14 },
  metaSep: { margin: '0 6px', opacity: 0.6 },
  lerMais: { fontSize: 14, fontWeight: 600, color: '#0d4f3c' },

  ctaPrimary: { background: '#c9a84c', color: '#1a1916', padding: '14px 28px', borderRadius: 8, fontWeight: 700, textDecoration: 'none', display: 'inline-block', fontSize: 16 },

  footer: { padding: '32px', textAlign: 'center', background: '#1a1916', color: '#fff', fontSize: 13 },
};
