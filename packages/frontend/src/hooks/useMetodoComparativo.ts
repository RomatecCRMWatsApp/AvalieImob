import { useState, useMemo } from "react";

interface Amostra {
  id: string;
  descricao: string;
  valor_unitario_m2: number;
  area_m2: number;
}

interface ResultadoComparativo {
  media: number;
  desvio_padrao: number;
  coeficiente_variacao: number;
  intervalo_minimo: number;
  intervalo_maximo: number;
  margem_erro: number;
  valor_total: number;
  amostra_tamanho: number;
  valido: boolean;
  mensagem: string;
}

export function useMetodoComparativo(
  amostras: Amostra[],
  area_impactada: number
): ResultadoComparativo {
  // Filtrar apenas amostras com valor_unitario_m2
  const valoresUnitarios = useMemo(() => {
    return amostras
      .map((a) => a.valor_unitario_m2)
      .filter((v) => v > 0 && !isNaN(v));
  }, [amostras]);

  // Validar mínimo de 3 amostras
  const temAmostrasValidas = useMemo(() => {
    return valoresUnitarios.length >= 3;
  }, [valoresUnitarios]);

  // Calcular estatísticas
  const resultado = useMemo(() => {
    if (!temAmostrasValidas) {
      return {
        media: 0,
        desvio_padrao: 0,
        coeficiente_variacao: 0,
        intervalo_minimo: 0,
        intervalo_maximo: 0,
        margem_erro: 0,
        valor_total: 0,
        amostra_tamanho: 0,
        valido: false,
        mensagem: `Mínimo de 3 amostras necessário. Você tem ${valoresUnitarios.length}.`,
      };
    }

    // MÉDIA
    const media = valoresUnitarios.reduce((a, b) => a + b, 0) / valoresUnitarios.length;

    // DESVIO PADRÃO
    const variancia =
      valoresUnitarios.reduce((sum, val) => sum + Math.pow(val - media, 2), 0) /
      (valoresUnitarios.length - 1);
    const desvio_padrao = Math.sqrt(variancia);

    // COEFICIENTE DE VARIAÇÃO (CV)
    const coeficiente_variacao = (desvio_padrao / media) * 100;

    // INTERVALO DE CONFIANÇA 95% (z = 1.96)
    const erro_margem = 1.96 * (desvio_padrao / Math.sqrt(valoresUnitarios.length));
    const intervalo_minimo = media - erro_margem;
    const intervalo_maximo = media + erro_margem;
    const margem_erro = (erro_margem / media) * 100;

    // VALOR TOTAL INDENIZATÓRIO
    const valor_total = media * area_impactada;

    // Validar se CV está dentro dos limites ABNT NBR 14.653
    // CV ≤ 30% = Ótimo
    // CV ≤ 40% = Bom
    // CV > 40% = Deve revisar amostras
    let valido = true;
    let mensagem = "✓ Cálculo válido";

    if (coeficiente_variacao > 40) {
      valido = false;
      mensagem = `⚠️ CV muito alto (${coeficiente_variacao.toFixed(2)}%). Revise as amostras.`;
    } else if (coeficiente_variacao > 30) {
      mensagem = `⚠️ CV elevado (${coeficiente_variacao.toFixed(2)}%). Considere mais amostras.`;
    }

    return {
      media,
      desvio_padrao,
      coeficiente_variacao,
      intervalo_minimo,
      intervalo_maximo,
      margem_erro,
      valor_total,
      amostra_tamanho: valoresUnitarios.length,
      valido,
      mensagem,
    };
  }, [valoresUnitarios, area_impactada, temAmostrasValidas]);

  return resultado;
}

export function formatarMoeda(valor: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(valor);
}

export function formatarPorcentagem(valor: number, casas: number = 2): string {
  return `${valor.toFixed(casas)}%`;
}
