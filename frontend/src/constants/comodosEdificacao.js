// @module constants/comodosEdificacao — catálogo de cômodos (port da ZAYRA)
// Usado no Programa de Necessidades do Projeto Executivo.

export const CATEGORIAS_LABEL = {
  social: '🛋 Área Social',
  intimo: '🛏 Área Íntima',
  servico: '🍳 Área de Serviço',
  externo: '🌳 Área Externa',
  comercial: '🏪 Área Comercial',
  tecnico: '⚙ Áreas Técnicas',
};

export const ORDEM_CATEGORIAS = ['social', 'intimo', 'servico', 'externo', 'comercial', 'tecnico'];

export const COMODOS_CATALOGO = [
  { codigo: 'sala_estar', nome: 'Sala de Estar', nome_plural: 'Salas de Estar', categoria: 'social', icone: '🛋', ordem_pdf: 10 },
  { codigo: 'sala_jantar', nome: 'Sala de Jantar', nome_plural: 'Salas de Jantar', categoria: 'social', icone: '🍽', ordem_pdf: 11 },
  { codigo: 'sala_tv', nome: 'Sala de TV', nome_plural: 'Salas de TV', categoria: 'social', icone: '📺', ordem_pdf: 12 },
  { codigo: 'sala_integrada', nome: 'Sala Integrada', nome_plural: 'Salas Integradas', categoria: 'social', icone: '🏠', ordem_pdf: 13 },
  { codigo: 'home_office', nome: 'Home Office', nome_plural: 'Home Offices', categoria: 'social', icone: '💻', ordem_pdf: 14 },
  { codigo: 'escritorio', nome: 'Escritório', nome_plural: 'Escritórios', categoria: 'social', icone: '📚', ordem_pdf: 15 },
  { codigo: 'hall_entrada', nome: 'Hall de Entrada', nome_plural: 'Halls de Entrada', categoria: 'social', icone: '🚪', ordem_pdf: 16 },
  { codigo: 'lavabo', nome: 'Lavabo', nome_plural: 'Lavabos', categoria: 'social', icone: '🚻', ordem_pdf: 17 },
  { codigo: 'sala_jogos', nome: 'Sala de Jogos', nome_plural: 'Salas de Jogos', categoria: 'social', icone: '🎮', ordem_pdf: 18 },

  { codigo: 'suite_master', nome: 'Suíte Master', nome_plural: 'Suítes Master', categoria: 'intimo', icone: '👑', ordem_pdf: 20 },
  { codigo: 'suite_closet', nome: 'Suíte com Closet', nome_plural: 'Suítes com Closet', categoria: 'intimo', icone: '🚪', ordem_pdf: 21 },
  { codigo: 'suite_simples', nome: 'Suíte Simples', nome_plural: 'Suítes Simples', categoria: 'intimo', icone: '🛏', ordem_pdf: 22 },
  { codigo: 'quarto_casal', nome: 'Quarto de Casal', nome_plural: 'Quartos de Casal', categoria: 'intimo', icone: '💑', ordem_pdf: 23 },
  { codigo: 'quarto_solteiro', nome: 'Quarto de Solteiro', nome_plural: 'Quartos de Solteiro', categoria: 'intimo', icone: '🧒', ordem_pdf: 24 },
  { codigo: 'quarto', nome: 'Quarto', nome_plural: 'Quartos', categoria: 'intimo', icone: '🛌', ordem_pdf: 25 },
  { codigo: 'quarto_hospede', nome: 'Quarto de Hóspedes', nome_plural: 'Quartos de Hóspedes', categoria: 'intimo', icone: '🛎', ordem_pdf: 26 },
  { codigo: 'closet', nome: 'Closet', nome_plural: 'Closets', categoria: 'intimo', icone: '👔', ordem_pdf: 27 },
  { codigo: 'banheiro_social', nome: 'Banheiro Social', nome_plural: 'Banheiros Sociais', categoria: 'intimo', icone: '🚿', ordem_pdf: 28 },
  { codigo: 'banheiro_suite', nome: 'Banheiro de Suíte', nome_plural: 'Banheiros de Suíte', categoria: 'intimo', icone: '🛁', ordem_pdf: 29 },

  { codigo: 'cozinha', nome: 'Cozinha', nome_plural: 'Cozinhas', categoria: 'servico', icone: '🍳', ordem_pdf: 40 },
  { codigo: 'cozinha_americana', nome: 'Cozinha Americana', nome_plural: 'Cozinhas Americanas', categoria: 'servico', icone: '🥘', ordem_pdf: 41 },
  { codigo: 'cozinha_gourmet', nome: 'Cozinha Gourmet', nome_plural: 'Cozinhas Gourmet', categoria: 'servico', icone: '👨‍🍳', ordem_pdf: 42 },
  { codigo: 'copa', nome: 'Copa', nome_plural: 'Copas', categoria: 'servico', icone: '🥄', ordem_pdf: 43 },
  { codigo: 'area_servico', nome: 'Área de Serviço', nome_plural: 'Áreas de Serviço', categoria: 'servico', icone: '🧺', ordem_pdf: 44 },
  { codigo: 'lavanderia', nome: 'Lavanderia', nome_plural: 'Lavanderias', categoria: 'servico', icone: '🧼', ordem_pdf: 45 },
  { codigo: 'despensa', nome: 'Despensa', nome_plural: 'Despensas', categoria: 'servico', icone: '🥫', ordem_pdf: 46 },
  { codigo: 'dce', nome: 'DCE', nome_plural: 'DCEs', categoria: 'servico', icone: '🧹', ordem_pdf: 47 },

  { codigo: 'varanda', nome: 'Varanda', nome_plural: 'Varandas', categoria: 'externo', icone: '🌅', ordem_pdf: 60 },
  { codigo: 'sacada', nome: 'Sacada', nome_plural: 'Sacadas', categoria: 'externo', icone: '🌇', ordem_pdf: 61 },
  { codigo: 'terraco', nome: 'Terraço', nome_plural: 'Terraços', categoria: 'externo', icone: '🏙', ordem_pdf: 62 },
  { codigo: 'area_gourmet', nome: 'Área Gourmet', nome_plural: 'Áreas Gourmet', categoria: 'externo', icone: '🍖', ordem_pdf: 63 },
  { codigo: 'churrasqueira', nome: 'Churrasqueira', nome_plural: 'Churrasqueiras', categoria: 'externo', icone: '🔥', ordem_pdf: 64 },
  { codigo: 'piscina', nome: 'Piscina', nome_plural: 'Piscinas', categoria: 'externo', icone: '🏊', ordem_pdf: 65 },
  { codigo: 'jardim', nome: 'Jardim', nome_plural: 'Jardins', categoria: 'externo', icone: '🌳', ordem_pdf: 66 },
  { codigo: 'quintal', nome: 'Quintal', nome_plural: 'Quintais', categoria: 'externo', icone: '🌿', ordem_pdf: 67 },
  { codigo: 'garagem', nome: 'Garagem', nome_plural: 'Garagens', categoria: 'externo', icone: '🚗', ordem_pdf: 68 },
  { codigo: 'vaga_coberta', nome: 'Vaga Coberta', nome_plural: 'Vagas Cobertas', categoria: 'externo', icone: '🅿', ordem_pdf: 69 },
  { codigo: 'edicula', nome: 'Edícula', nome_plural: 'Edículas', categoria: 'externo', icone: '🏚', ordem_pdf: 70 },

  { codigo: 'salao_comercial', nome: 'Salão Comercial', nome_plural: 'Salões Comerciais', categoria: 'comercial', icone: '🏪', ordem_pdf: 80 },
  { codigo: 'loja', nome: 'Loja', nome_plural: 'Lojas', categoria: 'comercial', icone: '🛍', ordem_pdf: 81 },
  { codigo: 'recepcao', nome: 'Recepção', nome_plural: 'Recepções', categoria: 'comercial', icone: '🛎', ordem_pdf: 82 },
  { codigo: 'sala_atendimento', nome: 'Sala de Atendimento', nome_plural: 'Salas de Atendimento', categoria: 'comercial', icone: '💼', ordem_pdf: 83 },
  { codigo: 'sala_reuniao', nome: 'Sala de Reunião', nome_plural: 'Salas de Reunião', categoria: 'comercial', icone: '👥', ordem_pdf: 84 },
  { codigo: 'almoxarifado', nome: 'Almoxarifado', nome_plural: 'Almoxarifados', categoria: 'comercial', icone: '📦', ordem_pdf: 85 },
  { codigo: 'deposito', nome: 'Depósito', nome_plural: 'Depósitos', categoria: 'comercial', icone: '🗄', ordem_pdf: 86 },
  { codigo: 'banheiro_pne', nome: 'Banheiro PNE', nome_plural: 'Banheiros PNE', categoria: 'comercial', icone: '♿', ordem_pdf: 87 },

  { codigo: 'casa_maquinas', nome: 'Casa de Máquinas', nome_plural: 'Casas de Máquinas', categoria: 'tecnico', icone: '⚙', ordem_pdf: 90 },
  { codigo: 'reservatorio', nome: 'Reservatório', nome_plural: 'Reservatórios', categoria: 'tecnico', icone: '💧', ordem_pdf: 91 },
  { codigo: 'subsolo', nome: 'Subsolo', nome_plural: 'Subsolos', categoria: 'tecnico', icone: '🕳', ordem_pdf: 92 },
  { codigo: 'circulacao', nome: 'Circulação', nome_plural: 'Circulações', categoria: 'tecnico', icone: '↔', ordem_pdf: 93 },
  { codigo: 'escada', nome: 'Escada', nome_plural: 'Escadas', categoria: 'tecnico', icone: '🪜', ordem_pdf: 94 },
  { codigo: 'mezanino', nome: 'Mezanino', nome_plural: 'Mezaninos', categoria: 'tecnico', icone: '🏗', ordem_pdf: 95 },
];

export function comodosPorCategoria() {
  const out = { social: [], intimo: [], servico: [], externo: [], comercial: [], tecnico: [] };
  COMODOS_CATALOGO.forEach((c) => out[c.categoria].push(c));
  Object.keys(out).forEach((k) => out[k].sort((a, b) => a.ordem_pdf - b.ordem_pdf));
  return out;
}
