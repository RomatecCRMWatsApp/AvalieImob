// @module pages/ServicoTemplate — template SEO-otimizado pra páginas de serviço
// Plano SEO v1.0 — capturar tráfego orgânico de palavras-chave técnicas
// (PTAM, NBR 14.653, avaliação rural, etc).
//
// Cada página tem ~1.500 palavras únicas, schema.org Service, FAQ específica,
// CTAs claros e links internos. Dark/clean conforme branding RomaTec.
import React from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';

const BASE = 'https://www.romatecavalieimob.com.br';

export default function ServicoTemplate({
  slug,
  titulo,
  subtitulo,
  meta,
  hero,
  intro,
  beneficios = [],
  comoFunciona = [],
  publicoAlvo = [],
  faq = [],
  ctaTitulo,
  ctaTexto,
  palavrasChave,
}) {
  const url = `${BASE}/servicos/${slug}`;
  const ogImage = `${BASE}/brand/banner.png`;

  const serviceSchema = {
    '@context': 'https://schema.org',
    '@type': 'Service',
    name: titulo,
    description: meta,
    url,
    provider: {
      '@type': 'Organization',
      name: 'RomaTec Consultoria Total',
      url: BASE,
    },
    areaServed: { '@type': 'Country', name: 'Brasil' },
    serviceType: titulo,
  };

  const faqSchema = faq.length > 0 ? {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faq.map(f => ({
      '@type': 'Question',
      name: f.q,
      acceptedAnswer: { '@type': 'Answer', text: f.a },
    })),
  } : null;

  return (
    <>
      <Helmet>
        <title>{titulo} | AvalieImob - RomaTec</title>
        <meta name="description" content={meta} />
        {palavrasChave && <meta name="keywords" content={palavrasChave} />}
        <link rel="canonical" href={url} />
        <meta property="og:type" content="article" />
        <meta property="og:title" content={titulo} />
        <meta property="og:description" content={meta} />
        <meta property="og:url" content={url} />
        <meta property="og:image" content={ogImage} />
        <meta property="og:locale" content="pt_BR" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={titulo} />
        <meta name="twitter:description" content={meta} />
        <meta name="twitter:image" content={ogImage} />
        <link rel="alternate" hrefLang="pt-BR" href={url} />
        <script type="application/ld+json">{JSON.stringify(serviceSchema)}</script>
        {faqSchema && <script type="application/ld+json">{JSON.stringify(faqSchema)}</script>}
      </Helmet>

      <main style={styles.main}>
        {/* HEADER */}
        <header style={styles.header}>
          <Link to="/" style={styles.logoLink}>
            <strong>AvalieImob</strong>
          </Link>
          <nav style={styles.nav}>
            <Link to="/" style={styles.navLink}>Início</Link>
            <Link to="/planos" style={styles.navLink}>Planos</Link>
            <Link to="/sobre" style={styles.navLink}>Sobre</Link>
            <Link to="/cadastro" style={styles.navCTA}>Teste Grátis</Link>
          </nav>
        </header>

        {/* HERO */}
        <section style={styles.hero}>
          <div style={styles.container}>
            <h1 style={styles.h1}>{titulo}</h1>
            <p style={styles.subtitulo}>{subtitulo}</p>
            <p style={styles.heroText}>{hero}</p>
            <div style={styles.ctaRow}>
              <Link to="/cadastro" style={styles.ctaPrimary}>Começar grátis →</Link>
              <Link to="/planos" style={styles.ctaSecondary}>Ver planos</Link>
            </div>
          </div>
        </section>

        {/* INTRO */}
        <section style={styles.section}>
          <div style={styles.container}>
            <div style={{ maxWidth: 760, margin: '0 auto' }}>
              {intro.map((p, i) => <p key={i} style={styles.paragrafo}>{p}</p>)}
            </div>
          </div>
        </section>

        {/* BENEFÍCIOS */}
        {beneficios.length > 0 && (
          <section style={{ ...styles.section, background: '#f5f7f5' }}>
            <div style={styles.container}>
              <h2 style={styles.h2}>Por que escolher o AvalieImob para {titulo.toLowerCase()}?</h2>
              <div style={styles.grid}>
                {beneficios.map((b, i) => (
                  <div key={i} style={styles.card}>
                    <div style={styles.cardIcon}>✓</div>
                    <h3 style={styles.cardTitulo}>{b.titulo}</h3>
                    <p style={styles.cardTexto}>{b.descricao}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* COMO FUNCIONA */}
        {comoFunciona.length > 0 && (
          <section style={styles.section}>
            <div style={styles.container}>
              <h2 style={styles.h2}>Como funciona</h2>
              <ol style={styles.passos}>
                {comoFunciona.map((p, i) => (
                  <li key={i} style={styles.passo}>
                    <span style={styles.passoNum}>{i + 1}</span>
                    <div>
                      <h3 style={styles.passoTitulo}>{p.titulo}</h3>
                      <p style={styles.passoTexto}>{p.descricao}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </section>
        )}

        {/* PÚBLICO-ALVO */}
        {publicoAlvo.length > 0 && (
          <section style={{ ...styles.section, background: '#0d4f3c', color: '#fff' }}>
            <div style={styles.container}>
              <h2 style={{ ...styles.h2, color: '#fff' }}>Para quem é este serviço</h2>
              <ul style={styles.publico}>
                {publicoAlvo.map((p, i) => <li key={i} style={styles.publicoItem}>▸ {p}</li>)}
              </ul>
            </div>
          </section>
        )}

        {/* FAQ */}
        {faq.length > 0 && (
          <section style={styles.section}>
            <div style={styles.container}>
              <h2 style={styles.h2}>Perguntas frequentes</h2>
              <div style={{ maxWidth: 800, margin: '0 auto' }}>
                {faq.map((f, i) => (
                  <details key={i} style={styles.faq}>
                    <summary style={styles.faqQ}>{f.q}</summary>
                    <p style={styles.faqA}>{f.a}</p>
                  </details>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* CTA FINAL */}
        <section style={{ ...styles.section, background: '#c9a84c', color: '#1a1916', textAlign: 'center' }}>
          <div style={styles.container}>
            <h2 style={{ ...styles.h2, color: '#1a1916' }}>{ctaTitulo}</h2>
            <p style={{ fontSize: 18, marginBottom: 24, maxWidth: 700, margin: '0 auto 24px' }}>{ctaTexto}</p>
            <Link to="/cadastro" style={{ ...styles.ctaPrimary, background: '#0d4f3c', color: '#fff' }}>
              Comece agora grátis →
            </Link>
          </div>
        </section>

        {/* LINKS INTERNOS — outros serviços */}
        <section style={styles.section}>
          <div style={styles.container}>
            <h3 style={{ ...styles.h2, fontSize: 22, marginBottom: 16 }}>Outros serviços do AvalieImob</h3>
            <div style={styles.linksInternos}>
              {SERVICOS_LINKS.filter(s => s.slug !== slug).map(s => (
                <Link key={s.slug} to={`/servicos/${s.slug}`} style={styles.linkInterno}>
                  → {s.titulo}
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* FOOTER */}
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

export const SERVICOS_LINKS = [
  { slug: 'ptam', titulo: 'PTAM — Parecer Técnico de Avaliação Mercadológica' },
  { slug: 'laudo-tecnico', titulo: 'Laudo Técnico de Avaliação' },
  { slug: 'avaliacao-rural', titulo: 'Avaliação de Imóveis Rurais' },
  { slug: 'avaliacao-garantia', titulo: 'Avaliação de Garantias Bancárias' },
  { slug: 'avaliacao-urbana', titulo: 'Avaliação de Imóveis Urbanos' },
];

const styles = {
  main: { fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif', color: '#1a1916', lineHeight: 1.6 },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 32px', borderBottom: '1px solid #e5e7eb', background: '#fff', position: 'sticky', top: 0, zIndex: 10 },
  logoLink: { color: '#0d4f3c', fontSize: 22, textDecoration: 'none' },
  nav: { display: 'flex', gap: 20, alignItems: 'center' },
  navLink: { color: '#4b5563', textDecoration: 'none', fontSize: 14 },
  navCTA: { background: '#0d4f3c', color: '#fff', padding: '8px 16px', borderRadius: 6, textDecoration: 'none', fontSize: 14, fontWeight: 600 },
  hero: { padding: '60px 32px 40px', background: 'linear-gradient(135deg, #0d4f3c 0%, #1a6b52 100%)', color: '#fff' },
  container: { maxWidth: 1100, margin: '0 auto' },
  h1: { fontSize: 'clamp(28px, 5vw, 44px)', fontWeight: 800, marginBottom: 12, letterSpacing: '-0.02em' },
  subtitulo: { fontSize: 'clamp(16px, 2.5vw, 20px)', opacity: 0.9, marginBottom: 20, maxWidth: 800 },
  heroText: { fontSize: 16, opacity: 0.85, marginBottom: 32, maxWidth: 800 },
  ctaRow: { display: 'flex', gap: 12, flexWrap: 'wrap' },
  ctaPrimary: { background: '#c9a84c', color: '#1a1916', padding: '14px 28px', borderRadius: 8, fontWeight: 700, textDecoration: 'none', display: 'inline-block', fontSize: 16 },
  ctaSecondary: { background: 'rgba(255,255,255,0.15)', color: '#fff', padding: '14px 28px', borderRadius: 8, textDecoration: 'none', display: 'inline-block', fontSize: 16, border: '1px solid rgba(255,255,255,0.3)' },
  section: { padding: '60px 32px' },
  paragrafo: { fontSize: 17, marginBottom: 20, color: '#374151' },
  h2: { fontSize: 'clamp(24px, 4vw, 34px)', fontWeight: 700, marginBottom: 32, textAlign: 'center', color: '#0d4f3c' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 },
  card: { background: '#fff', padding: 24, borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.08)', border: '1px solid #e5e7eb' },
  cardIcon: { width: 36, height: 36, borderRadius: '50%', background: '#0d4f3c', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, marginBottom: 12 },
  cardTitulo: { fontSize: 17, fontWeight: 700, marginBottom: 8, color: '#0d4f3c' },
  cardTexto: { fontSize: 14, color: '#4b5563' },
  passos: { listStyle: 'none', padding: 0, maxWidth: 800, margin: '0 auto' },
  passo: { display: 'flex', gap: 20, marginBottom: 28 },
  passoNum: { flexShrink: 0, width: 44, height: 44, borderRadius: '50%', background: '#0d4f3c', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 18 },
  passoTitulo: { fontSize: 18, fontWeight: 700, marginBottom: 6, color: '#0d4f3c' },
  passoTexto: { fontSize: 15, color: '#4b5563' },
  publico: { listStyle: 'none', padding: 0, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 },
  publicoItem: { fontSize: 16, padding: '12px 0' },
  faq: { borderBottom: '1px solid #e5e7eb', padding: '16px 0' },
  faqQ: { fontSize: 17, fontWeight: 600, cursor: 'pointer', color: '#0d4f3c' },
  faqA: { fontSize: 15, color: '#4b5563', marginTop: 12, paddingLeft: 4 },
  linksInternos: { display: 'flex', flexWrap: 'wrap', gap: 12, justifyContent: 'center' },
  linkInterno: { padding: '8px 16px', background: '#f5f7f5', borderRadius: 6, textDecoration: 'none', color: '#0d4f3c', fontSize: 14, border: '1px solid #d1d5db' },
  footer: { padding: '32px', textAlign: 'center', background: '#1a1916', color: '#fff', fontSize: 13 },
};
