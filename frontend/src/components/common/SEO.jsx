// @module components/common/SEO — meta tags dinâmicas por página
// Plano SEO v1.0 — Maio/2026. Usar em cada página principal pra garantir
// title/description/OG/canonical únicos por rota (importante pra Google
// indexar diferentes páginas com snippets distintos).
//
// Uso:
//   <SEO
//     title="Planos e Preços"
//     description="Conheça os planos do AvalieImob..."
//     url="https://www.romatecavalieimob.com.br/planos"
//     image="https://www.romatecavalieimob.com.br/brand/banner-planos.png"
//   />
import React from 'react';
import { Helmet } from 'react-helmet-async';

const BASE_URL = 'https://www.romatecavalieimob.com.br';
const DEFAULT_IMAGE = `${BASE_URL}/brand/banner.png`;
const DEFAULT_TITLE = 'AvalieImob — Software de PTAM e Avaliação Imobiliária Online | NBR 14.653';
const DEFAULT_DESC = 'Sistema online de avaliação imobiliária. PTAM, Laudo Técnico, TVI, Avaliação de Garantias e Rural. Conforme NBR 14.653. Teste grátis.';

export default function SEO({
  title,
  description,
  url,
  image,
  type = 'website',
  noindex = false,
  keywords,
  schemaType,
  schemaData,
}) {
  const fullTitle = title ? `${title} | AvalieImob` : DEFAULT_TITLE;
  const desc = description || DEFAULT_DESC;
  const fullUrl = url || BASE_URL;
  const fullImage = image || DEFAULT_IMAGE;

  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={desc} />
      {keywords && <meta name="keywords" content={keywords} />}
      {noindex && <meta name="robots" content="noindex,follow" />}

      <link rel="canonical" href={fullUrl} />

      <meta property="og:type" content={type} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={desc} />
      <meta property="og:url" content={fullUrl} />
      <meta property="og:image" content={fullImage} />
      <meta property="og:locale" content="pt_BR" />
      <meta property="og:site_name" content="AvalieImob" />

      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:url" content={fullUrl} />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={desc} />
      <meta name="twitter:image" content={fullImage} />

      <link rel="alternate" hrefLang="pt-BR" href={fullUrl} />
      <link rel="alternate" hrefLang="x-default" href={fullUrl} />

      {schemaData && (
        <script type="application/ld+json">
          {JSON.stringify({ '@context': 'https://schema.org', '@type': schemaType || 'WebPage', ...schemaData })}
        </script>
      )}
    </Helmet>
  );
}
