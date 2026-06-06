import {
  toM2, fromM2, fmtBR, M2_PER_HA, M2_PER_ALQ,
  formatHa, formatRsHa, formatRsM2, formatAreaRural, formatBRL,
} from '../areaConversao';

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

  // \s em JS casa espaço insecável (U+00A0) e fino (U+202F) que o Intl insere antes do número.
  const norm = (s) => s.replace(/\s/g, ' ');

  describe('apresentação rural (ha 4 casas / R$/ha 2 casas)', () => {
    // 4 casas decimais = ares (2ª/3ª) e centiares (3ª/4ª) — nomenclatura agronômica.
    it('formatHa: 294.315 m² → 29,4315 ha', () => {
      expect(formatHa(294315)).toBe('29,4315 ha');
    });
    it('formatHa: 10.000 m² → 1,0000 ha', () => {
      expect(formatHa(10000)).toBe('1,0000 ha');
    });
    it('formatHa: 48.400 m² → 4,8400 ha', () => {
      expect(formatHa(48400)).toBe('4,8400 ha');
    });
    it('formatHa: 484.000 m² → 48,4000 ha', () => {
      expect(formatHa(484000)).toBe('48,4000 ha');
    });
    it('formatHa: decimais customizados (2)', () => {
      expect(formatHa(48400, 2)).toBe('4,84 ha');
    });
    it('formatHa: entrada inválida → 0,0000 ha', () => {
      expect(formatHa(undefined)).toBe('0,0000 ha');
    });

    it('formatRsHa: R$/m² 2 → R$ 20.000,00/ha (2 casas, ×10.000)', () => {
      expect(norm(formatRsHa(2))).toBe('R$ 20.000,00/ha');
    });
    it('formatRsHa: R$/m² 0,5 → R$ 5.000,00/ha', () => {
      expect(norm(formatRsHa(0.5))).toBe('R$ 5.000,00/ha');
    });

    it('formatRsM2: 12,34 → R$ 12,34/m²', () => {
      expect(norm(formatRsM2(12.34))).toBe('R$ 12,34/m²');
    });

    it('formatAreaRural: 294.315 m² → "29,4315 ha  (294.315 m²)"', () => {
      expect(formatAreaRural(294315)).toBe('29,4315 ha  (294.315 m²)');
    });
    it('formatAreaRural: 484.000 m² → "48,4000 ha  (484.000 m²)"', () => {
      expect(formatAreaRural(484000)).toBe('48,4000 ha  (484.000 m²)');
    });
    it('formatAreaRural: 132.114 m²', () => {
      expect(formatAreaRural(132114)).toBe('13,2114 ha  (132.114 m²)');
    });

    it('formatBRL: 1234567.89 → R$ 1.234.567,89', () => {
      expect(norm(formatBRL(1234567.89))).toBe('R$ 1.234.567,89');
    });

    it('coerência: valorTotal independe da unidade (R$/m²×m² = R$/ha×ha)', () => {
      const areaM2 = 484000;
      const vrM2 = 3.5;
      const totalM2 = vrM2 * areaM2;
      const totalHa = (vrM2 * M2_PER_HA) * (areaM2 / M2_PER_HA);
      expect(totalHa).toBeCloseTo(totalM2, 6);
    });
  });
});
