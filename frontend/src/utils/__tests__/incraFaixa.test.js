import { getFaixaMatch, faixaContemMedia } from '../incraFaixa';

const faixas = [
  { faixa: 'A', vr_min: 5000, vr_max: 10000, vr_medio: 7500 },
  { faixa: 'B', vr_min: 10001, vr_max: 20000, vr_medio: 15000 },
];

describe('incraFaixa.getFaixaMatch', () => {
  it('dentro da faixa A', () => expect(getFaixaMatch(faixas, 8000)).toBe(0));
  it('dentro da faixa B', () => expect(getFaixaMatch(faixas, 15000)).toBe(1));
  it('acima de tudo → mais próximo de B', () => expect(getFaixaMatch(faixas, 25000)).toBe(1));
  it('abaixo de tudo → mais próximo de A', () => expect(getFaixaMatch(faixas, 1000)).toBe(0));
  it('limite exato vr_min', () => expect(getFaixaMatch(faixas, 5000)).toBe(0));
  it('limite exato vr_max', () => expect(getFaixaMatch(faixas, 10000)).toBe(0));
  it('lista vazia → 0', () => expect(getFaixaMatch([], 9999)).toBe(0));
  it('média inválida → 0 (mais próximo da primeira)', () => expect(getFaixaMatch(faixas, undefined)).toBe(0));
});

describe('incraFaixa.faixaContemMedia', () => {
  it('dentro', () => expect(faixaContemMedia(faixas, 0, 8000)).toBe(true));
  it('fora', () => expect(faixaContemMedia(faixas, 0, 25000)).toBe(false));
  it('índice inválido', () => expect(faixaContemMedia(faixas, 9, 8000)).toBe(false));
});
