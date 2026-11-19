// Conteúdo em data/servicos/avaliacao-urbana.json — fonte ÚNICA: a página renderiza este arquivo e o
// servidor (services/seo_html) entrega o mesmo texto no HTML inicial para os buscadores.
import React from 'react';
import ServicoTemplate from './ServicoTemplate';
import servico from '../data/servicos/avaliacao-urbana.json';

export default function ServicoAvaliacaoUrbana() {
  return <ServicoTemplate {...servico} />;
}
