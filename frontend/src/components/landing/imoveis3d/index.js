// @module imoveis3d — barrel export dos 9 icones 3D low-poly de tipos de imovel.
// Usado pela cena 2 v2 do Avaliacao3DCanvas e tambem como referencia
// pelo fallback (que usa icones Lucide equivalentes).
export { CasaResidencial } from './CasaResidencial';
export { Apartamento } from './Apartamento';
export { Galpao } from './Galpao';
export { Comercio } from './Comercio';
export { Rural } from './Rural';
export { Terreno } from './Terreno';
export { Fazenda } from './Fazenda';
export { SalaComercial } from './SalaComercial';
export { Equipamento } from './Equipamento';

// Catalogo: ordem canonica usada pelo grid 3x3 da cena 2.
// IMPORTANTE: ao integrar na cena 2 v2, importar daqui pra preservar a ordem.
export const TIPOS_IMOVEIS_META = [
  { key: 'casa',       label: 'Residencial Urbano' },
  { key: 'apto',       label: 'Apartamento' },
  { key: 'galpao',     label: 'Galpão Industrial' },
  { key: 'comercio',   label: 'Comércio e Loja' },
  { key: 'rural',      label: 'Imóvel Rural' },
  { key: 'terreno',    label: 'Terrenos e Lotes' },
  { key: 'fazenda',    label: 'Propriedade Rural' },
  { key: 'sala',       label: 'Sala Comercial' },
  { key: 'equipamento',label: 'Equipamentos / Garantia' },
];
