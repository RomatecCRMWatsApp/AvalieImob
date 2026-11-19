// Conteúdo em data/servicos/ptam.json — fonte ÚNICA: a página renderiza este arquivo e o
// servidor (services/seo_html) entrega o mesmo texto no HTML inicial para os buscadores.
import React from 'react';
import ServicoTemplate from './ServicoTemplate';
import servico from '../data/servicos/ptam.json';

export default function ServicoPTAM() {
  return <ServicoTemplate {...servico} />;
}
