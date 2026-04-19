import { z } from "zod";
import { router, protectedProcedure } from "../lib/trpc";
import { v4 as uuid } from "uuid";
import { TRPCError } from "@trpc/server";
import { eq } from "drizzle-orm";
import { calculos, avaliacoes, amostras } from "@avaliemob/db/schema";

// Funções matemáticas para cálculos ABNT NBR 14.653
function calcularMedia(valores: number[]): number {
  return valores.reduce((a, b) => a + b, 0) / valores.length;
}

function calcularDesvio(valores: number[], media: number): number {
  const variancia =
    valores.reduce((sum, val) => sum + Math.pow(val - media, 2), 0) /
    (valores.length - 1);
  return Math.sqrt(variancia);
}

function calcularIntervaloConfianca(
  media: number,
  desvio: number,
  tamanho: number,
  confianca: number = 0.95
) {
  // Usando z-score aproximado para 95% confiança = 1.96
  const erro = confianca === 0.95 ? 1.96 : 1.645;
  const margem = erro * (desvio / Math.sqrt(tamanho));

  return {
    minimo: media - margem,
    maximo: media + margem,
    margem: (margem / media) * 100,
  };
}

function calcularCoeficienteVariacao(desvio: number, media: number): number {
  return (desvio / media) * 100;
}

export const calculoRouter = router({
  calcularComparativo: protectedProcedure
    .input(
      z.object({
        avaliacao_id: z.string(),
        area_impactada: z.number(),
        usar_unitarios: z.boolean().default(true),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      // Verificar avaliação
      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(eq(avaliacoes.id, input.avaliacao_id))
        .limit(1);

      if (
        avaliacao.length === 0 ||
        avaliacao[0].avaliador_id !== ctx.user!.userId
      ) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      // Buscar amostras
      const amostrasList = await db
        .select()
        .from(amostras)
        .where(eq(amostras.avaliacao_id, input.avaliacao_id));

      if (amostrasList.length < 3) {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: "Mínimo de 3 amostras necessário para cálculo",
        });
      }

      // Extrair valores unitários (m2 ou ha)
      const valoresUnitarios = amostrasList
        .map((a) =>
          input.usar_unitarios
            ? parseFloat(a.valor_unitario_m2 || "0")
            : parseFloat(a.valor_unitario_ha || "0")
        )
        .filter((v) => v > 0);

      if (valoresUnitarios.length < 3) {
        throw new TRPCError({
          code: "BAD_REQUEST",
          message: "Dados insuficientes para o cálculo",
        });
      }

      // Cálculos estatísticos
      const media = calcularMedia(valoresUnitarios);
      const desvio = calcularDesvio(valoresUnitarios, media);
      const cv = calcularCoeficienteVariacao(desvio, media);
      const intervalo = calcularIntervaloConfianca(
        media,
        desvio,
        valoresUnitarios.length,
        0.95
      );

      const valorTotal = media * input.area_impactada;

      const calculoId = uuid();

      await db.insert(calculos).values({
        id: calculoId,
        avaliacao_id: input.avaliacao_id,
        tipo: "comparativo",
        area_impactada_m2: input.usar_unitarios
          ? input.area_impactada.toString()
          : null,
        area_impactada_ha: !input.usar_unitarios
          ? input.area_impactada.toString()
          : null,
        valor_unitario: media.toString(),
        valor_total: valorTotal.toString(),
        margem_erro: intervalo.margem.toString(),
        intervalo_minimo: intervalo.minimo.toString(),
        intervalo_maximo: intervalo.maximo.toString(),
        amostra_tamanho: valoresUnitarios.length,
        desvio_padrao: desvio.toString(),
        coeficiente_variacao: cv.toString(),
        dados_json: JSON.stringify({
          amostras: valoresUnitarios,
          media,
          desvio,
          cv,
          intervalo,
          confianca: "95%",
          norma: "ABNT NBR 14.653",
        }),
      });

      return {
        id: calculoId,
        tipo: "comparativo",
        valor_unitario: media,
        valor_total: valorTotal,
        intervalo: {
          minimo: intervalo.minimo,
          maximo: intervalo.maximo,
        },
        margem_erro: intervalo.margem,
        coeficiente_variacao: cv,
        amostra_tamanho: valoresUnitarios.length,
      };
    }),

  calcularEvolutivo: protectedProcedure
    .input(
      z.object({
        avaliacao_id: z.string(),
        valor_terreno: z.number(),
        valor_benfeitorias: z.number().default(0),
        depreciacao_percentual: z.number().default(0),
        fator_localizacao: z.number().default(1.0),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      // Verificar avaliação
      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(eq(avaliacoes.id, input.avaliacao_id))
        .limit(1);

      if (
        avaliacao.length === 0 ||
        avaliacao[0].avaliador_id !== ctx.user!.userId
      ) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      // Cálculo evolutivo: VT = VTerreno + (VBenfeitorias × (1 - Depreciação)) × FatorLocalizacao
      const benfeitoriaDepreciada =
        input.valor_benfeitorias * (1 - input.depreciacao_percentual / 100);
      const valorImovel =
        (input.valor_terreno + benfeitoriaDepreciada) * input.fator_localizacao;

      const calculoId = uuid();

      await db.insert(calculos).values({
        id: calculoId,
        avaliacao_id: input.avaliacao_id,
        tipo: "evolutivo",
        valor_total: valorImovel.toString(),
        dados_json: JSON.stringify({
          valor_terreno: input.valor_terreno,
          valor_benfeitorias: input.valor_benfeitorias,
          depreciacao_percentual: input.depreciacao_percentual,
          benfeitorias_depreciada: benfeitoriaDepreciada,
          fator_localizacao: input.fator_localizacao,
          valor_final: valorImovel,
          norma: "ABNT NBR 14.653",
        }),
      });

      return {
        id: calculoId,
        tipo: "evolutivo",
        valor_terreno: input.valor_terreno,
        benfeitorias_depreciada: benfeitoriaDepreciada,
        fator_localizacao: input.fator_localizacao,
        valor_total: valorImovel,
      };
    }),

  listarPorAvaliacao: protectedProcedure
    .input(z.object({ avaliacao_id: z.string() }))
    .query(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(eq(avaliacoes.id, input.avaliacao_id))
        .limit(1);

      if (
        avaliacao.length === 0 ||
        avaliacao[0].avaliador_id !== ctx.user!.userId
      ) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      const result = await db
        .select()
        .from(calculos)
        .where(eq(calculos.avaliacao_id, input.avaliacao_id));

      return result.map((c) => ({
        ...c,
        valor_total: parseFloat(c.valor_total),
        valor_unitario: c.valor_unitario ? parseFloat(c.valor_unitario) : null,
        desvio_padrao: c.desvio_padrao ? parseFloat(c.desvio_padrao) : null,
      }));
    }),

  deletar: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const calculo = await db
        .select()
        .from(calculos)
        .where(eq(calculos.id, input.id))
        .limit(1);

      if (calculo.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Cálculo não encontrado",
        });
      }

      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(eq(avaliacoes.id, calculo[0].avaliacao_id))
        .limit(1);

      if (
        avaliacao.length === 0 ||
        avaliacao[0].avaliador_id !== ctx.user!.userId
      ) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      await db.delete(calculos).where(eq(calculos.id, input.id));

      return { success: true };
    }),
});
