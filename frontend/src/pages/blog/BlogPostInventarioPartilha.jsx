// Conteúdo em data/blog/avaliacao-imovel-inventario-partilha.json — fonte ÚNICA: o site renderiza este arquivo e o
// servidor (services/seo_html) entrega o mesmo texto no HTML inicial para os buscadores.
import React from 'react';
import BlogPostTemplate from '../BlogPostTemplate';
import { getRelatedPosts } from '../../data/blogPosts';
import artigo from '../../data/blog/avaliacao-imovel-inventario-partilha.json';

export default function BlogPostInventarioPartilha() {
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
