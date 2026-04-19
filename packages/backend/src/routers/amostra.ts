import { z } from "zod";
import { router, protectedProcedure } from "../lib/trpc";
import { v4 as uuid } from "uuid";
import { TRPCError } from "@trpc/server";
import { eq } from "drizzle-orm";
import { amostras, avaliacoes } from "@avaliemob/db/schema";

export const amostraRouter = router({
  criar: protectedProcedure
    .input(
      z.object({
        avaliacao_id: z.string(),
        descricao: z.string().min(5),
        endereco: z.string().optional(),
        cidade: z.string().optional(),
        estado: z.string().optional(),
        tipo: z.enum(["urbano", "rural"]).default("urbano"),
        area_m2: z.number().optional(),
        area_ha: z.number().optional(),
        valor_total: z.number(),
        valor_unitario_m2: z.number().optional(),
        valor_unitario_ha: z.number().optional(),
        data_oferta: z.date().optional(),
        data_venda: z.date().optional(),
        fonte: z.string().optional(),
        situacao: z
          .enum(["oferta", "vendido", "aluguel"])
          .default("oferta"),
        obs: z.string().optional(),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      // Verificar se avaliação pertence ao usuário
      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(eq(avaliacoes.id, input.avaliacao_id))
        .limit(1);

      if (avaliacao.length === 0 || avaliacao[0].avaliador_id !== ctx.user!.userId) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Avaliação não encontrada ou acesso negado",
        });
      }

      const amostraId = uuid();

      await db.insert(amostras).values({
        id: amostraId,
        avaliacao_id: input.avaliacao_id,
        descricao: input.descricao,
        endereco: input.endereco,
        cidade: input.cidade,
        estado: input.estado,
        tipo: input.tipo,
        area_m2: input.area_m2 ? input.area_m2.toString() : null,
        area_ha: input.area_ha ? input.area_ha.toString() : null,
        valor_total: input.valor_total.toString(),
        valor_unitario_m2: input.valor_unitario_m2
          ? input.valor_unitario_m2.toString()
          : null,
        valor_unitario_ha: input.valor_unitario_ha
          ? input.valor_unitario_ha.toString()
          : null,
        data_oferta: input.data_oferta
          ? new Date(input.data_oferta)
          : null,
        data_venda: input.data_venda ? new Date(input.data_venda) : null,
        fonte: input.fonte,
        situacao: input.situacao,
        obs: input.obs,
      });

      return { id: amostraId };
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

      if (avaliacao.length === 0 || avaliacao[0].avaliador_id !== ctx.user!.userId) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      const result = await db
        .select()
        .from(amostras)
        .where(eq(amostras.avaliacao_id, input.avaliacao_id));

      return result.map((amostra) => ({
        ...amostra,
        area_m2: amostra.area_m2 ? parseFloat(amostra.area_m2) : null,
        area_ha: amostra.area_ha ? parseFloat(amostra.area_ha) : null,
        valor_total: parseFloat(amostra.valor_total),
        valor_unitario_m2: amostra.valor_unitario_m2
          ? parseFloat(amostra.valor_unitario_m2)
          : null,
        valor_unitario_ha: amostra.valor_unitario_ha
          ? parseFloat(amostra.valor_unitario_ha)
          : null,
      }));
    }),

  atualizar: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        descricao: z.string().optional(),
        endereco: z.string().optional(),
        cidade: z.string().optional(),
        estado: z.string().optional(),
        tipo: z.enum(["urbano", "rural"]).optional(),
        area_m2: z.number().optional(),
        area_ha: z.number().optional(),
        valor_total: z.number().optional(),
        valor_unitario_m2: z.number().optional(),
        valor_unitario_ha: z.number().optional(),
        data_oferta: z.date().optional(),
        data_venda: z.date().optional(),
        fonte: z.string().optional(),
        situacao: z.enum(["oferta", "vendido", "aluguel"]).optional(),
        obs: z.string().optional(),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const amostra = await db
        .select()
        .from(amostras)
        .where(eq(amostras.id, input.id))
        .limit(1);

      if (amostra.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Amostra não encontrada",
        });
      }

      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(eq(avaliacoes.id, amostra[0].avaliacao_id!))
        .limit(1);

      if (avaliacao.length === 0 || avaliacao[0].avaliador_id !== ctx.user!.userId) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      await db
        .update(amostras)
        .set({
          descricao: input.descricao ?? amostra[0].descricao,
          endereco: input.endereco ?? amostra[0].endereco,
          cidade: input.cidade ?? amostra[0].cidade,
          estado: input.estado ?? amostra[0].estado,
          tipo: input.tipo ?? amostra[0].tipo,
          area_m2: input.area_m2 ? input.area_m2.toString() : amostra[0].area_m2,
          area_ha: input.area_ha ? input.area_ha.toString() : amostra[0].area_ha,
          valor_total: input.valor_total
            ? input.valor_total.toString()
            : amostra[0].valor_total,
          valor_unitario_m2: input.valor_unitario_m2
            ? input.valor_unitario_m2.toString()
            : amostra[0].valor_unitario_m2,
          valor_unitario_ha: input.valor_unitario_ha
            ? input.valor_unitario_ha.toString()
            : amostra[0].valor_unitario_ha,
          data_oferta: input.data_oferta
            ? new Date(input.data_oferta)
            : amostra[0].data_oferta,
          data_venda: input.data_venda
            ? new Date(input.data_venda)
            : amostra[0].data_venda,
          fonte: input.fonte ?? amostra[0].fonte,
          situacao: input.situacao ?? amostra[0].situacao,
          obs: input.obs ?? amostra[0].obs,
        })
        .where(eq(amostras.id, input.id));

      return { success: true };
    }),

  deletar: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const amostra = await db
        .select()
        .from(amostras)
        .where(eq(amostras.id, input.id))
        .limit(1);

      if (amostra.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Amostra não encontrada",
        });
      }

      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(eq(avaliacoes.id, amostra[0].avaliacao_id!))
        .limit(1);

      if (avaliacao.length === 0 || avaliacao[0].avaliador_id !== ctx.user!.userId) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      await db.delete(amostras).where(eq(amostras.id, input.id));

      return { success: true };
    }),
});
