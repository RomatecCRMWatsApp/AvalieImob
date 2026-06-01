import { toM2, fromM2, fmtBR, M2_PER_HA, M2_PER_ALQ } from '../areaConversao';

describe('areaConversao', () => {
  it('1 alqueire mineiro = 48.400 m²', () => expect(toM2(1, 'alq')).toBe(48400));
  it('1 hectare = 10.000 m²', () => expect(toM2(1, 'ha')).toBe(10000));
  it('1 alqueire mineiro = 4,84 ha', () => expect(M2_PER_ALQ / M2_PER_HA).toBe(4.84));
  it('48.400 m² → 1 alq', () => expect(fromM2(48400, 'alq')).toBe(1));
  it('10.000 m² → 1 ha', () => expect(fromM2(10000, 'ha')).toBe(1));
  it('toM2 m² → identidade', () => expect(toM2(500, 'm2')).toBe(500));
  it('fromM2 m² → identidade', () => expect(fromM2(500, 'm2')).toBe(500));

  it('round-trip preserva valor (ha)', () => {
    expect(fromM2(toM2(2.5, 'ha'), 'ha')).toBe(2.5);
  });
  it('round-trip preserva valor (alq)', () => {
    expect(fromM2(toM2(3.7, 'alq'), 'alq')).toBeCloseTo(3.7, 10);
  });

  it('entradas inválidas viram 0', () => {
    expect(toM2(NaN, 'ha')).toBe(0);
    expect(fromM2(undefined, 'alq')).toBe(0);
  });

  it('fmtBR formata pt-BR com casas fixas', () => {
    expect(fmtBR(48400, 2)).toBe('48.400,00');
    expect(fmtBR(1, 6)).toBe('1,000000');
  });
});
