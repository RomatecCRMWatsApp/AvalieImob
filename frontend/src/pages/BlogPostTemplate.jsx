// @module pages/BlogPostTemplate — template SEO-otimizado para artigos do blog
// Plano SEO v1.0 — capturar trafego de cauda longa em palavras-chave tecnicas
// (NBR 14.653, PTAM passo a passo, VLF, etc).
//
// Cada artigo: ~2.000 palavras unicas, schema.org Article, breadcrumbs,
// links internos para servicos relacionados, CTA pro cadastro.
import React from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';

const BASE = 'https://www.romatecavalieimob.com.br';

export default function BlogPostTemplate({
  slug,
  titulo,
  subtitulo,
  meta,
  palavrasChave,
  dataPublicacao,
  dataAtualizacao,
  autor = 'José Romário Pinto Bezerra',
  tempoLeitura = '8 min',
  categoria = 'Avaliação Imobiliária',
  resumo,
  conteudo,
  servicosRelacionados = [],
  postsRelacionados = [],
}) {
  const url = `${BASE}/blog/${slug}`;
  const ogImage = `${BASE}/brand/banner.png`;

  const articleSchema = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: titulo,
    description: meta,
    image: ogImage,
    datePublished: dataPublicacao,
    dateModified: dataAtualizacao || dataPublicacao,
    author: {
      '@type': 'Person',
      name: autor,
      jobTitle: 'CEO RomaTec — Técnico em Agrimensura CFTMA 12-091-853-69',
    },
    publisher: {
      '@type': 'Organization',
      name: 'RomaTec Consultoria Total',
      logo: {
        '@type': 'ImageObject',
        url: `${BASE}/brand/icone.png`,
      },
    },
    mainEntityOfPage: { '@type': 'WebPage', '@id': url },
    articleSection: categoria,
    inLanguage: 'pt-BR',
  };

  const breadcrumbSchema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Início', item: BASE },
      { '@type': 'ListItem', position: 2, name: 'Blog', item: `${BASE}/blog` },
      { '@type': 'ListItem', position: 3, name: titulo, item: url },
    ],
  };

  return (
    <>
      <Helmet>
        <title>{titulo} | Blog AvalieImob</title>
        <meta name="description" content={meta} />
        {palavrasChave && <meta name="keywords" content={palavrasChave} />}
        <meta name="author" content={autor} />
        <link rel="canonical" href={url} />
        <meta property="og:type" content="article" />
        <meta property="og:title" content={titulo} />
        <meta property="og:description" content={meta} />
        <meta property="og:url" content={url} />
        <meta property="og:image" content={ogImage} />
        <meta property="og:locale" content="pt_BR" />
        <meta property="article:published_time" content={dataPublicacao} />
        <meta property="article:modified_time" content={dataAtualizacao || dataPublicacao} />
        <meta property="article:author" content={autor} />
        <meta property="article:section" content={categoria} />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={titulo} />
        <meta name="twitter:description" content={meta} />
        <meta name="twitter:image" content={ogImage} />
        <link rel="alternate" hrefLang="pt-BR" href={url} />
        <script type="application/ld+json">{JSON.stringify(articleSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(breadcrumbSchema)}</script>
      </Helmet>

      <main style={styles.main}>
        <header style={styles.header}>
          <Link to="/" style={styles.logoLink}>
            <strong>AvalieImob</strong>
          </Link>
          <nav style={styles.nav}>
            <Link to="/" style={styles.navLink}>Início</Link>
            <Link to="/blog" style={styles.navLink}>Blog</Link>
            <Link to="/planos" style={styles.navLink}>Planos</Link>
            <Link to="/cadastro" style={styles.navCTA}>Teste Grátis</Link>
          </nav>
        </header>

        <article>
          <section style={styles.heroArtigo}>
            <div style={styles.containerArtigo}>
              <nav style={styles.breadcrumb} aria-label="breadcrumb">
                <Link to="/" style={styles.breadcrumbLink}>Início</Link>
                <span style={styles.breadcrumbSep}>›</span>
                <Link to="/blog" style={styles.breadcrumbLink}>Blog</Link>
                <span style={styles.breadcrumbSep}>›</span>
                <span style={styles.breadcrumbAtivo}>{categoria}</span>
              </nav>

              <span style={styles.categoria}>{categoria}</span>
              <h1 style={styles.h1Artigo}>{titulo}</h1>
              {subtitulo && <p style={styles.subtituloArtigo}>{subtitulo}</p>}

              <div style={styles.meta}>
                <span>Por <strong>{autor}</strong></span>
                <span style={styles.metaSep}>·</span>
                <time dateTime={dataPublicacao}>
                  {new Date(dataPublicacao).toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' })}
                </time>
                <span style={styles.metaSep}>·</span>
                <span>{tempoLeitura} de leitura</span>
              </div>
            </div>
          </section>

          <section style={styles.section}>
            <div style={styles.containerArtigo}>
              {resumo && (
                <div style={styles.resumo}>
                  <strong style={{ color: '#0d4f3c' }}>Resumo executivo:</strong> {resumo}
                </div>
              )}
              <div style={styles.conteudo}>
                {conteudo.map((bloco, i) => renderBloco(bloco, i))}
              </div>
            </div>
          </section>

          <section style={{ ...styles.section, background: '#c9a84c', color: '#1a1916', textAlign: 'center', padding: '50px 32px' }}>
            <div style={styles.container}>
              <h2 style={{ fontSize: 28, fontWeight: 700, marginBottom: 12, color: '#1a1916' }}>
                Pronto para emitir laudos profissionais?
              </h2>
              <p style={{ fontSize: 17, marginBottom: 20, maxWidth: 600, margin: '0 auto 20px' }}>
                Teste o AvalieImob 7 dias grátis. Sem cartão de crédito. Sistema completo conforme NBR 14.653.
              </p>
              <Link to="/cadastro" style={{ ...styles.ctaPrimary, background: '#0d4f3c', color: '#fff' }}>
                Começar grátis →
              </Link>
            </div>
          </section>

          {servicosRelacionados.length > 0 && (
            <section style={styles.section}>
              <div style={styles.containerArtigo}>
                <h3 style={styles.h3Sec}>Serviços relacionados</h3>
                <div style={styles.linksInternos}>
                  {servicosRelacionados.map(s => (
                    <Link key={s.slug} to={`/servicos/${s.slug}`} style={styles.linkInterno}>
                      → {s.titulo}
                    </Link>
                  ))}
                </div>
              </div>
            </section>
          )}

          {postsRelacionados.length > 0 && (
            <section style={{ ...styles.section, background: '#f5f7f5' }}>
              <div style={styles.containerArtigo}>
                <h3 style={styles.h3Sec}>Continue lendo</h3>
                <div style={styles.postsRelGrid}>
                  {postsRelacionados.map(p => (
                    <Link key={p.slug} to={`/blog/${p.slug}`} style={styles.postRelCard}>
                      <span style={styles.postRelCat}>{p.categoria || 'Artigo'}</span>
                      <h4 style={styles.postRelTitulo}>{p.titulo}</h4>
                      <p style={styles.postRelMeta}>{p.tempoLeitura} de leitura</p>
                    </Link>
                  ))}
                </div>
              </div>
            </section>
          )}
        </article>

        <footer style={styles.footer}>
          <p>© 2026 RomaTec Consultoria Total · J R P Bezerra LTDA · CNPJ 17.261.987/0001-09</p>
          <p style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>
            Açailândia/MA · CEP 65.930-000 · Conformidade ABNT NBR 14.653
          </p>
        </footer>
      </main>
    </>
  );
}

function renderBloco(bloco, i) {
  if (bloco.h2) return <h2 key={i} style={styles.h2Artigo}>{bloco.h2}</h2>;
  if (bloco.h3) return <h3 key={i} style={styles.h3Artigo}>{bloco.h3}</h3>;
  if (bloco.p) return <p key={i} style={styles.p}>{bloco.p}</p>;
  if (bloco.lista) return (
    <ul key={i} style={styles.lista}>
      {bloco.lista.map((item, j) => <li key={j} style={styles.listaItem}>{item}</li>)}
    </ul>
  );
  if (bloco.listaOrd) return (
    <ol key={i} style={styles.lista}>
      {bloco.listaOrd.map((item, j) => <li key={j} style={styles.listaItem}>{item}</li>)}
    </ol>
  );
  if (bloco.callout) return (
    <div key={i} style={styles.callout}>
      {bloco.calloutTitulo && <strong style={{ color: '#0d4f3c', display: 'block', marginBottom: 8 }}>{bloco.calloutTitulo}</strong>}
      {bloco.callout}
    </div>
  );
  if (bloco.cta) return (
    <div key={i} style={styles.ctaInline}>
      <p style={{ marginBottom: 12 }}>{bloco.cta}</p>
      <Link to={bloco.ctaLink || '/cadastro'} style={styles.ctaPrimary}>
        {bloco.ctaTexto || 'Começar grátis →'}
      </Link>
    </div>
  );
  return null;
}

const styles = {
  main: { fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif', color: '#1a1916', lineHeight: 1.7 },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 32px', borderBottom: '1px solid #e5e7eb', background: '#fff', position: 'sticky', top: 0, zIndex: 10 },
  logoLink: { color: '#0d4f3c', fontSize: 22, textDecoration: 'none' },
  nav: { display: 'flex', gap: 20, alignItems: 'center' },
  navLink: { color: '#4b5563', textDecoration: 'none', fontSize: 14 },
  navCTA: { background: '#0d4f3c', color: '#fff', padding: '8px 16px', borderRadius: 6, textDecoration: 'none', fontSize: 14, fontWeight: 600 },

  heroArtigo: { padding: '40px 32px 30px', background: 'linear-gradient(135deg, #0d4f3c 0%, #1a6b52 100%)', color: '#fff' },
  container: { maxWidth: 1100, margin: '0 auto' },
  containerArtigo: { maxWidth: 760, margin: '0 auto' },
  breadcrumb: { fontSize: 13, marginBottom: 18, opacity: 0.85 },
  breadcrumbLink: { color: '#fff', textDecoration: 'none', borderBottom: '1px solid rgba(255,255,255,0.4)' },
  breadcrumbSep: { margin: '0 8px', opacity: 0.6 },
  breadcrumbAtivo: { opacity: 0.7 },
  categoria: { display: 'inline-block', background: 'rgba(201,168,76,0.25)', color: '#ffd97a', padding: '4px 12px', borderRadius: 4, fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 14 },
  h1Artigo: { fontSize: 'clamp(28px, 4.5vw, 40px)', fontWeight: 800, marginBottom: 12, letterSpacing: '-0.02em', lineHeight: 1.2 },
  subtituloArtigo: { fontSize: 'clamp(16px, 2vw, 19px)', opacity: 0.92, marginBottom: 24, lineHeight: 1.5 },
  meta: { fontSize: 14, opacity: 0.85, display: 'flex', gap: 8, flexWrap: 'wrap' },
  metaSep: { opacity: 0.5 },

  section: { padding: '50px 32px' },
  resumo: { padding: '18px 22px', background: '#f5f7f5', borderLeft: '4px solid #0d4f3c', borderRadius: 4, marginBottom: 28, fontSize: 15, color: '#374151' },
  conteudo: { fontSize: 17, color: '#1f2937' },
  h2Artigo: { fontSize: 'clamp(22px, 3.5vw, 30px)', fontWeight: 700, color: '#0d4f3c', marginTop: 38, marginBottom: 14, letterSpacing: '-0.01em' },
  h3Artigo: { fontSize: 'clamp(18px, 2.5vw, 22px)', fontWeight: 700, color: '#1a6b52', marginTop: 28, marginBottom: 10 },
  p: { marginBottom: 18, color: '#374151' },
  lista: { marginBottom: 18, paddingLeft: 22 },
  listaItem: { marginBottom: 8, color: '#374151' },
  callout: { padding: '18px 22px', background: '#fff7e0', borderLeft: '4px solid #c9a84c', borderRadius: 4, margin: '24px 0', fontSize: 15, color: '#374151' },
  ctaInline: { padding: '24px', background: '#0d4f3c', color: '#fff', borderRadius: 8, textAlign: 'center', margin: '24px 0' },
  ctaPrimary: { background: '#c9a84c', color: '#1a1916', padding: '12px 24px', borderRadius: 8, fontWeight: 700, textDecoration: 'none', display: 'inline-block', fontSize: 15 },

  h3Sec: { fontSize: 22, fontWeight: 700, marginBottom: 18, color: '#0d4f3c', textAlign: 'center' },
  linksInternos: { display: 'flex', flexWrap: 'wrap', gap: 12, justifyContent: 'center' },
  linkInterno: { padding: '8px 16px', background: '#f5f7f5', borderRadius: 6, textDecoration: 'none', color: '#0d4f3c', fontSize: 14, border: '1px solid #d1d5db' },

  postsRelGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 },
  postRelCard: { display: 'block', padding: 20, background: '#fff', borderRadius: 8, textDecoration: 'none', color: '#1a1916', border: '1px solid #e5e7eb' },
  postRelCat: { display: 'inline-block', fontSize: 11, color: '#0d4f3c', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 },
  postRelTitulo: { fontSize: 16, fontWeight: 700, marginBottom: 8, color: '#0d4f3c', lineHeight: 1.35 },
  postRelMeta: { fontSize: 13, color: '#6b7280' },

  footer: { padding: '32px', textAlign: 'center', background: '#1a1916', color: '#fff', fontSize: 13 },
};
