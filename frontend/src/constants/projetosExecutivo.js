// @module constants/projetosExecutivo — os 7 projetos do Projeto Executivo (port ZAYRA).
// Espelha PROJETOS_DEFAULT do backend (services/pricing/projeto_executivo.py).
export const PROJETOS_EXECUTIVO_DEFAULT = [
  { codigo: 'mapa_situacao', nome: 'Mapa de Situação e Localização', ordem: 1, selecionado: true,
    detalhamento_entrega: 'Prancha contendo planta de situação (quadra/lote), planta de localização do imóvel, orientação magnética (Norte), coordenadas de referência (SIRGAS2000), confrontantes, vias de acesso, recuos, taxa de ocupação e coeficiente de aproveitamento conforme legislação municipal.' },
  { codigo: 'arquitetonico', nome: 'Projeto Arquitetônico', ordem: 2, selecionado: true,
    detalhamento_entrega: 'Plantas baixas de todos os pavimentos com cotas e áreas, planta de cobertura, planta de implantação, cortes longitudinal e transversal (mínimo 2), fachadas (mínimo 2), planta de layout, memorial descritivo e quadro de áreas, em conformidade com as NBR 13531 e NBR 13532.' },
  { codigo: 'hidraulico', nome: 'Projeto Hidráulico (Água Fria)', ordem: 3, selecionado: true,
    detalhamento_entrega: 'Planta baixa hidráulica por pavimento, vistas isométricas dos pontos de consumo, detalhes de barrilete e reservatório, dimensionamento de tubulações, quantitativo de materiais e memorial de cálculo conforme NBR 5626.' },
  { codigo: 'sanitario', nome: 'Projeto Sanitário (Esgoto e Águas Pluviais)', ordem: 4, selecionado: true,
    detalhamento_entrega: 'Planta baixa de esgoto sanitário, planta baixa de águas pluviais, vistas isométricas, detalhes de caixa de inspeção, fossa séptica e sumidouro (quando aplicável), dimensionamento conforme NBR 8160 e NBR 10844, e quantitativo de materiais.' },
  { codigo: 'eletrico', nome: 'Projeto Elétrico', ordem: 5, selecionado: true,
    detalhamento_entrega: 'Planta baixa de pontos elétricos por pavimento, diagrama unifilar, quadro de cargas, dimensionamento de condutores e proteções, detalhe de entrada de energia conforme padrão da concessionária (Equatorial Maranhão), memorial descritivo conforme NBR 5410 e quantitativo de materiais.' },
  { codigo: 'estrutural', nome: 'Projeto Estrutural', ordem: 6, selecionado: true,
    detalhamento_entrega: 'Planta de locação de pilares, planta de formas por pavimento, detalhamento de vigas, lajes, pilares e fundações, memorial de cálculo, especificação de materiais (concreto e aço), em conformidade com NBR 6118 e NBR 6122.' },
  { codigo: 'pci', nome: 'Projeto de Prevenção e Combate a Incêndio (PCI)', ordem: 7, selecionado: false,
    detalhamento_entrega: 'Planta baixa de PCI com rotas de fuga, localização de extintores, hidrantes, iluminação de emergência e sinalização, memorial descritivo conforme Normas Técnicas do CBMMA e NBR 9077, para protocolo junto ao Corpo de Bombeiros Militar do Maranhão.' },
];
