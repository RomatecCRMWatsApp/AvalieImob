// Conteúdo em data/blog/diferenca-ptam-laudo-avaliacao-imobiliaria.json — fonte ÚNICA: o site renderiza este arquivo e o
// servidor (services/seo_html) entrega o mesmo texto no HTML inicial para os buscadores.
import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getRelatedPosts } from '../../data/blogPosts';
import artigo from '../../data/blog/diferenca-ptam-laudo-avaliacao-imobiliaria.json';

export default function BlogPostPtamLaudo() {
  return (
    <BlogPostTemplate
      slug={artigo.slug}
      titulo={artigo.titulo}
      subtitulo={artigo.subtitulo}
      meta={artigo.meta}
      palavrasChave={artigo.palavrasChave}
      dataPublicacao={artigo.dataPublicacao}
      dataAtualizacao={artigo.dataAtualizacao}
      tempoLeitura={artigo.tempoLeitura}
      categoria={artigo.categoria}
      resumo={artigo.resumo}
      conteudo={artigo.conteudo}
      servicosRelacionados={artigo.servicosRelacionados}
      postsRelacionados={getRelatedPosts(artigo.slug)}
    />
  );
}
