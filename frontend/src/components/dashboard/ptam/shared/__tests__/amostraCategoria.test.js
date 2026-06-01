import {
  amostraCategoria,
  isRuralImovel,
  valorUnitario,
  unidadeValorLabel,
  conversoesArea,
} from '../amostraCategoria';

describe('amostraCategoria — mapeamento property_type → categoria', () => {
  it('casa/apartamento → casa_apto', () => {
    expect(amostraCategoria('casa')).toBe('casa_apto');
    expect(amostraCategoria('apartamento')).toBe('casa_apto');
  });
  it('terreno → terreno_urbano', () => expect(amostraCategoria('terreno')).toBe('terreno_urbano'));
  it('comercial/industrial → galpao_comercial', () => {
    expect(amostraCategoria('comercial')).toBe('galpao_comercial');
    expect(amostraCategoria('industrial')).toBe('galpao_comercial');
  });
  it('terreno_rural → terreno_rural', () => expect(amostraCategoria('terreno_rural')).toBe('terreno_rural'));
  it('rural/fazenda/sitio/chacara → fazenda_sitio', () => {
    ['rural', 'fazenda', 'sitio', 'chacara'].forEach((t) =>
      expect(amostraCategoria(t)).toBe('fazenda_sitio'));
  });
  it('desconhecido → outros', () => {
    expect(amostraCategoria('outros')).toBe('outros');
    expect(amostraCategoria('')).toBe('outros');
    expect(amostraCategoria(undefined)).toBe('outros');
  });
});

describe('isRuralImovel', () => {
  it('rurais retornam true', () => {
    ['rural', 'fazenda', 'sitio', 'chacara', 'terreno_rural'].forEach((t) =>
      expect(isRuralImovel(t)).toBe(true));
  });
  it('urbanos retornam false', () => {
    ['casa', 'apartamento', 'terreno', 'comercial', 'industrial'].forEach((t) =>
      expect(isRuralImovel(t)).toBe(false));
  });
});

describe('valorUnitario — R$/m² (urbano) vs R$/ha (rural)', () => {
  it('urbano: R$/m² = valor / area_m2', () => expect(valorUnitario(200, 100000, false)).toBe(500));
  it('rural: R$/ha = valor / (m2/10000)', () => expect(valorUnitario(50000, 200000, true)).toBe(40000));
  it('retorna 0 quando área ou valor inválidos', () => {
    expect(valorUnitario(0, 100000, false)).toBe(0);
    expect(valorUnitario(200, 0, false)).toBe(0);
  });
  it('rótulo de unidade', () => {
    expect(unidadeValorLabel(true)).toBe('R$/ha');
    expect(unidadeValorLabel(false)).toBe('R$/m²');
  });
});

describe('conversoesArea — ha e alqueire mineiro', () => {
  it('50.000 m² = 5 ha', () => expect(conversoesArea(50000).ha).toBe('5,0000'));
  it('50.000 m² = 1,0331 alq (48.400 m²/alq)', () => expect(conversoesArea(50000).alq).toBe('1,0331'));
  it('área 0 → travessão', () => {
    expect(conversoesArea(0).ha).toBe('—');
    expect(conversoesArea(0).alq).toBe('—');
  });
});
