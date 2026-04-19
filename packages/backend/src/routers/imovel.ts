import { z } from "zod";
import { router, protectedProcedure } from "../lib/trpc";
import { v4 as uuid } from "uuid";
import { TRPCError } from "@trpc/server";
import { eq, and } from "drizzle-orm";
import { imoveis, clientes } from "@avaliemob/db/schema";

export const imovelRouter = router({
  criar: protectedProcedure
    .input(
      z.object({
        cliente_id: z.string(),
        matricula: z.string().optional(),
        endereco: z.string().min(10),
        latitude: z.number().optional(),
        longitude: z.number().optional(),
        cidade: z.string().min(3),
        estado: z.string().length(2),
        cep: z.string().optional(),
        tipo: z.enum(["urbano", "rural", "misto"]).default("urbano"),
        area_total_m2: z.number().optional(),
        area_total_ha: z.number().optional(),
        descricao_fisica: z.string().optional(),
        topografia: z.string().optional(),
        acessibilidade: z.string().optional(),
        benfeitorias: z.string().optional(),
        estado_conservacao: z
          .enum(["otimo", "bom", "regular", "precario"])
          .optional(),
        fotos_urls: z.array(z.string().url()).optional(),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      // Verificar se cliente pertence ao usuário
      const cliente = await db
        .select()
        .from(clientes)
        .where(eq(clientes.id, input.cliente_id))
        .limit(1);

      if (cliente.length === 0 || cliente[0].user_id !== ctx.user!.userId) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Cliente não encontrado ou acesso negado",
        });
      }

      const imovelId = uuid();

      await db.insert(imoveis).values({
        id: imovelId,
        cliente_id: input.cliente_id,
        matricula: input.matricula,
        endereco: input.endereco,
        latitude: input.latitude
          ? input.latitude.toString()
          : null,
        longitude: input.longitude
          ? input.longitude.toString()
          : null,
        cidade: input.cidade,
        estado: input.estado,
        cep: input.cep,
        tipo: input.tipo,
        area_total_m2: input.area_total_m2
          ? input.area_total_m2.toString()
          : null,
        area_total_ha: input.area_total_ha
          ? input.area_total_ha.toString()
          : null,
        descricao_fisica: input.descricao_fisica,
        topografia: input.topografia,
        acessibilidade: input.acessibilidade,
        benfeitorias: input.benfeitorias,
        estado_conservacao: input.estado_conservacao,
        fotos_urls: input.fotos_urls
          ? JSON.stringify(input.fotos_urls)
          : null,
      });

      return { id: imovelId };
    }),

  listar: protectedProcedure
    .input(
      z.object({
        cliente_id: z.string().optional(),
        pagina: z.number().default(1),
        limite: z.number().default(20),
      })
    )
    .query(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      let query = db.select().from(imoveis);

      // Se cliente_id fornecido, validar se pertence ao usuário
      if (input.cliente_id) {
        const cliente = await db
          .select()
          .from(clientes)
          .where(eq(clientes.id, input.cliente_id))
          .limit(1);

        if (cliente.length === 0 || cliente[0].user_id !== ctx.user!.userId) {
          throw new TRPCError({
            code: "FORBIDDEN",
            message: "Acesso negado",
          });
        }

        query = query.where(eq(imoveis.cliente_id, input.cliente_id));
      } else {
        // Listar todos os imóveis do usuário (todos seus clientes)
        const meusClientes = await db
          .select({ id: clientes.id })
          .from(clientes)
          .where(eq(clientes.user_id, ctx.user!.userId));

        const clienteIds = meusClientes.map((c) => c.id);
        if (clienteIds.length === 0) {
          return { imoveis: [], total: 0 };
        }
      }

      const offset = (input.pagina - 1) * input.limite;

      const result = await query.limit(input.limite).offset(offset);

      // Total count
      const countResult = await db
        .select()
        .from(imoveis)
        .limit(1);

      return {
        imoveis: result,
        total: countResult.length,
        pagina: input.pagina,
        limite: input.limite,
      };
    }),

  obter: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const imovel = await db
        .select()
        .from(imoveis)
        .where(eq(imoveis.id, input.id))
        .limit(1);

      if (imovel.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Imóvel não encontrado",
        });
      }

      // Verificar se pertence a um cliente do usuário
      const cliente = await db
        .select()
        .from(clientes)
        .where(eq(clientes.id, imovel[0].cliente_id))
        .limit(1);

      if (cliente.length === 0 || cliente[0].user_id !== ctx.user!.userId) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      return {
        ...imovel[0],
        fotos_urls: imovel[0].fotos_urls
          ? JSON.parse(imovel[0].fotos_urls)
          : [],
      };
    }),

  atualizar: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        endereco: z.string().optional(),
        latitude: z.number().optional(),
        longitude: z.number().optional(),
        cidade: z.string().optional(),
        estado: z.string().optional(),
        cep: z.string().optional(),
        tipo: z.enum(["urbano", "rural", "misto"]).optional(),
        area_total_m2: z.number().optional(),
        area_total_ha: z.number().optional(),
        descricao_fisica: z.string().optional(),
        topografia: z.string().optional(),
        acessibilidade: z.string().optional(),
        benfeitorias: z.string().optional(),
        estado_conservacao: z.enum(["otimo", "bom", "regular", "precario"])
          .optional(),
        fotos_urls: z.array(z.string().url()).optional(),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const imovel = await db
        .select()
        .from(imoveis)
        .where(eq(imoveis.id, input.id))
        .limit(1);

      if (imovel.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Imóvel não encontrado",
        });
      }

      const cliente = await db
        .select()
        .from(clientes)
        .where(eq(clientes.id, imovel[0].cliente_id))
        .limit(1);

      if (cliente.length === 0 || cliente[0].user_id !== ctx.user!.userId) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      await db
        .update(imoveis)
        .set({
          endereco: input.endereco ?? imovel[0].endereco,
          latitude: input.latitude ? input.latitude.toString() : imovel[0].latitude,
          longitude: input.longitude ? input.longitude.toString() : imovel[0].longitude,
          cidade: input.cidade ?? imovel[0].cidade,
          estado: input.estado ?? imovel[0].estado,
          cep: input.cep ?? imovel[0].cep,
          tipo: input.tipo ?? imovel[0].tipo,
          area_total_m2: input.area_total_m2
            ? input.area_total_m2.toString()
            : imovel[0].area_total_m2,
          area_total_ha: input.area_total_ha
            ? input.area_total_ha.toString()
            : imovel[0].area_total_ha,
          descricao_fisica: input.descricao_fisica ?? imovel[0].descricao_fisica,
          topografia: input.topografia ?? imovel[0].topografia,
          acessibilidade: input.acessibilidade ?? imovel[0].acessibilidade,
          benfeitorias: input.benfeitorias ?? imovel[0].benfeitorias,
          estado_conservacao:
            input.estado_conservacao ?? imovel[0].estado_conservacao,
          fotos_urls: input.fotos_urls
            ? JSON.stringify(input.fotos_urls)
            : imovel[0].fotos_urls,
        })
        .where(eq(imoveis.id, input.id));

      return { success: true };
    }),

  deletar: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const imovel = await db
        .select()
        .from(imoveis)
        .where(eq(imoveis.id, input.id))
        .limit(1);

      if (imovel.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Imóvel não encontrado",
        });
      }

      const cliente = await db
        .select()
        .from(clientes)
        .where(eq(clientes.id, imovel[0].cliente_id))
        .limit(1);

      if (cliente.length === 0 || cliente[0].user_id !== ctx.user!.userId) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      await db.delete(imoveis).where(eq(imoveis.id, input.id));

      return { success: true };
    }),
});
