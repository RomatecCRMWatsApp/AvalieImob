import { z } from "zod";
import { router, protectedProcedure } from "../lib/trpc";
import { v4 as uuid } from "uuid";
import { TRPCError } from "@trpc/server";
import { eq, and } from "drizzle-orm";
import { avaliacoes, imoveis } from "@avaliemob/db/schema";

export const avaliacaoRouter = router({
  criar: protectedProcedure
    .input(
      z.object({
        imovel_id: z.string(),
        titulo: z.string().min(5),
        finalidade: z.string().optional(),
        metodologia: z
          .enum(["comparativo", "evolutivo", "misto"])
          .default("comparativo"),
        notas_tecnicas: z.string().optional(),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      // Verificar se imóvel existe
      const imovel = await db
        .select()
        .from(imoveis)
        .where(eq(imoveis.id, input.imovel_id))
        .limit(1);

      if (imovel.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Imóvel não encontrado",
        });
      }

      const avaliacaoId = uuid();
      const numeroPtam = `PTAM-${Date.now()}-${Math.random().toString(36).substr(2, 5).toUpperCase()}`;

      await db.insert(avaliacoes).values({
        id: avaliacaoId,
        imovel_id: input.imovel_id,
        avaliador_id: ctx.user!.userId,
        numero_ptam: numeroPtam,
        titulo: input.titulo,
        finalidade: input.finalidade,
        metodologia: input.metodologia,
        status: "rascunho",
        notas_tecnicas: input.notas_tecnicas,
      });

      return { id: avaliacaoId, numero_ptam: numeroPtam };
    }),

  listar: protectedProcedure
    .input(
      z.object({
        status: z.enum(["rascunho", "em_andamento", "pronto", "emitido"]).optional(),
        pagina: z.number().default(1),
        limite: z.number().default(20),
      })
    )
    .query(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      let query = db.select().from(avaliacoes).where(
        eq(avaliacoes.avaliador_id, ctx.user!.userId)
      );

      if (input.status) {
        query = query.where(eq(avaliacoes.status, input.status));
      }

      const offset = (input.pagina - 1) * input.limite;
      const result = await query.limit(input.limite).offset(offset);

      return {
        avaliacoes: result,
        pagina: input.pagina,
        limite: input.limite,
      };
    }),

  obter: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(
          and(
            eq(avaliacoes.id, input.id),
            eq(avaliacoes.avaliador_id, ctx.user!.userId)
          )
        )
        .limit(1);

      if (avaliacao.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Avaliação não encontrada",
        });
      }

      return avaliacao[0];
    }),

  atualizar: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        titulo: z.string().optional(),
        finalidade: z.string().optional(),
        metodologia: z
          .enum(["comparativo", "evolutivo", "misto"])
          .optional(),
        status: z
          .enum(["rascunho", "em_andamento", "pronto", "emitido"])
          .optional(),
        notas_tecnicas: z.string().optional(),
        data_vistoria: z.date().optional(),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(
          and(
            eq(avaliacoes.id, input.id),
            eq(avaliacoes.avaliador_id, ctx.user!.userId)
          )
        )
        .limit(1);

      if (avaliacao.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Avaliação não encontrada",
        });
      }

      await db
        .update(avaliacoes)
        .set({
          titulo: input.titulo ?? avaliacao[0].titulo,
          finalidade: input.finalidade ?? avaliacao[0].finalidade,
          metodologia: input.metodologia ?? avaliacao[0].metodologia,
          status: input.status ?? avaliacao[0].status,
          notas_tecnicas: input.notas_tecnicas ?? avaliacao[0].notas_tecnicas,
          data_vistoria: input.data_vistoria
            ? new Date(input.data_vistoria)
            : avaliacao[0].data_vistoria,
        })
        .where(eq(avaliacoes.id, input.id));

      return { success: true };
    }),

  deletar: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const avaliacao = await db
        .select()
        .from(avaliacoes)
        .where(
          and(
            eq(avaliacoes.id, input.id),
            eq(avaliacoes.avaliador_id, ctx.user!.userId)
          )
        )
        .limit(1);

      if (avaliacao.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Avaliação não encontrada",
        });
      }

      // Impedir deleção de PTAMs emitidos
      if (avaliacao[0].status === "emitido") {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Não é possível deletar uma avaliação emitida",
        });
      }

      await db.delete(avaliacoes).where(eq(avaliacoes.id, input.id));

      return { success: true };
    }),
});
