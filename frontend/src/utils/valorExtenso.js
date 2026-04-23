/**
 * @module utils/valorExtenso
 * Converte valor numérico para extenso em português brasileiro
 * Suporta até 999.999.999,99
 */

const UNIDADES = [
  '', 'um', 'dois', 'três', 'quatro', 'cinco', 'seis', 'sete', 'oito', 'nove',
  'dez', 'onze', 'doze', 'treze', 'quatorze', 'quinze', 'dezesseis', 'dezessete',
  'dezoito', 'dezenove'
];

const DEZENAS = [
  '', '', 'vinte', 'trinta', 'quarenta', 'cinquenta', 'sessenta', 'setenta',
  'oitenta', 'noventa'
];

const CENTENAS = [
  '', 'cento', 'duzentos', 'trezentos', 'quatrocentos', 'quinhentos',
  'seiscentos', 'setecentos', 'oitocentos', 'novecentos'
];

const MILHAR_SINGULAR = ['', 'mil', 'milhão', 'bilhão'];
const MILHAR_PLURAL = ['', 'mil', 'milhões', 'bilhões'];

/**
 * Converte um número de 0-999 para extenso
 */
function extensoCentena(num) {
  if (num === 0) return '';
  if (num === 100) return 'cem';
  if (num < 20) return UNIDADES[num];
  
  const centena = Math.floor(num / 100);
  const resto = num % 100;
  
  if (centena === 0) {
    const dezena = Math.floor(resto / 10);
    const unidade = resto % 10;
    if (unidade === 0) return DEZENAS[dezena];
    return `${DEZENAS[dezena]} e ${UNIDADES[unidade]}`;
  }
  
  if (resto === 0) return CENTENAS[centena];
  
  const dezena = Math.floor(resto / 10);
  const unidade = resto % 10;
  
  if (resto < 20) {
    return `${CENTENAS[centena]} e ${UNIDADES[resto]}`;
  }
  
  if (unidade === 0) {
    return `${CENTENAS[centena]} e ${DEZENAS[dezena]}`;
  }
  
  return `${CENTENAS[centena]} e ${DEZENAS[dezena]} e ${UNIDADES[unidade]}`;
}

/**
 * Divide o número em grupos de 3 dígitos
 */
function dividirEmGrupos(num) {
  const grupos = [];
  while (num > 0) {
    grupos.push(num % 1000);
    num = Math.floor(num / 1000);
  }
  return grupos.length === 0 ? [0] : grupos;
}

/**
 * Converte valor numérico para extenso
 * @param {number} valor - Valor a converter (ex: 285000.50)
 * @param {string} moeda - 'reais' ou outra moeda
 * @returns {string} Valor por extenso
 */
export function valorExtenso(valor, moeda = 'reais') {
  if (valor === null || valor === undefined || isNaN(valor)) return '';
  
  const valorAbsoluto = Math.abs(valor);
  const parteInteira = Math.floor(valorAbsoluto);
  const centavos = Math.round((valorAbsoluto - parteInteira) * 100);
  
  if (parteInteira === 0 && centavos === 0) return `zero ${moeda}`;
  
  const grupos = dividirEmGrupos(parteInteira);
  const partes = [];
  
  for (let i = grupos.length - 1; i >= 0; i--) {
    const valorGrupo = grupos[i];
    if (valorGrupo === 0) continue;
    
    const extenso = extensoCentena(valorGrupo);
    const escala = valorGrupo === 1 ? MILHAR_SINGULAR[i] : MILHAR_PLURAL[i];
    
    if (i === 0) {
      partes.push(extenso);
    } else if (valorGrupo === 1 && i === 1) {
      // "mil" não leva "um" antes
      partes.push(escala);
    } else {
      partes.push(`${extenso} ${escala}`);
    }
  }
  
  let resultado = partes.join(', ');
  
  // Substituir última vírgula por "e" se houver mais de uma parte
  const ultimaVirgula = resultado.lastIndexOf(', ');
  if (ultimaVirgula !== -1 && partes.length > 1) {
    resultado = resultado.substring(0, ultimaVirgula) + ' e ' + resultado.substring(ultimaVirgula + 2);
  }
  
  // Adicionar moeda
  if (parteInteira === 1 && moeda === 'reais') {
    resultado += ' real';
  } else {
    resultado += ` ${moeda}`;
  }
  
  // Adicionar centavos
  if (centavos > 0) {
    const extensoCentavos = extensoCentena(centavos);
    if (centavos === 1) {
      resultado += ` e ${extensoCentavos} centavo`;
    } else {
      resultado += ` e ${extensoCentavos} centavos`;
    }
  }
  
  return resultado;
}

/**
 * Converte valor numérico para extenso simplificado (sem centavos)
 * @param {number} valor - Valor a converter
 * @returns {string} Valor por extenso
 */
export function valorExtensoSimplificado(valor) {
  return valorExtenso(valor, 'reais').replace(/ e .* centavos?/, '');
}

export default valorExtenso;
