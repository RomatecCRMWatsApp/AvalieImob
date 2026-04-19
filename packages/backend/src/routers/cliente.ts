import { z } from "zod";
import { router, protectedProcedure } from "../lib/trpc";
import { v4 as uuid } from "uuid";
import { TRPCError } from "@trpc/server";
import { eq } from "drizzle-orm";
import { clientes } from "@avaliemob/db/schema";

export const clienteRouter = router({
  criar: protectedProcedure
    .input(
      z.object({
        razao_social: z.string().min(3),
        cnpj_cpf: z.string().optional(),
        telefone: z.string().optional(),
        email: z.string().email().optional(),
        endereco: z.string().optional(),
        cidade: z.string().optional(),
        estado: z.string().optional(),
        cep: z.string().optional(),
        contato: z.string().optional(),
        obs: z.string().optional(),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const clienteId = uuid();

      await db.insert(clientes).values({
        id: clienteId,
        user_id: ctx.user!.userId,
        razao_social: input.razao_social,
        cnpj_cpf: input.cnpj_cpf,
        telefone: input.telefone,
        email: input.email,
        endereco: input.endereco,
        cidade: input.cidade,
        estado: input.estado,
        cep: input.cep,
        contato: input.contato,
        obs: input.obs,
      });

      return { id: clienteId };
    }),

  listar: protectedProcedure.query(async ({ ctx }) => {
    const db = ctx.req.app.locals.db;

    const meusClientes = await db
      .select()
      .from(clientes)
      .where(eq(clientes.user_id, ctx.user!.userId));

    return meusClientes;
  }),

  obter: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const cliente = await db
        .select()
        .from(clientes)
        .where(eq(clientes.id, input.id))
        .limit(1);

      if (cliente.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Cliente não encontrado",
        });
      }

      if (cliente[0].user_id !== ctx.user!.userId) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      return cliente[0];
    }),

  atualizar: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        razao_social: z.string().min(3).optional(),
        cnpj_cpf: z.string().optional(),
        telefone: z.string().optional(),
        email: z.string().email().optional(),
        endereco: z.string().optional(),
        cidade: z.string().optional(),
        estado: z.string().optional(),
        cep: z.string().optional(),
        contato: z.string().optional(),
        obs: z.string().optional(),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const cliente = await db
        .select()
        .from(clientes)
        .where(eq(clientes.id, input.id))
        .limit(1);

      if (cliente.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Cliente não encontrado",
        });
      }

      if (cliente[0].user_id !== ctx.user!.userId) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      await db
        .update(clientes)
        .set({
          razao_social: input.razao_social ?? cliente[0].razao_social,
          cnpj_cpf: input.cnpj_cpf ?? cliente[0].cnpj_cpf,
          telefone: input.telefone ?? cliente[0].telefone,
          email: input.email ?? cliente[0].email,
          endereco: input.endereco ?? cliente[0].endereco,
          cidade: input.cidade ?? cliente[0].cidade,
          estado: input.estado ?? cliente[0].estado,
          cep: input.cep ?? cliente[0].cep,
          contato: input.contato ?? cliente[0].contato,
          obs: input.obs ?? cliente[0].obs,
        })
        .where(eq(clientes.id, input.id));

      return { success: true };
    }),

  deletar: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const cliente = await db
        .select()
        .from(clientes)
        .where(eq(clientes.id, input.id))
        .limit(1);

      if (cliente.length === 0) {
        throw new TRPCError({
          code: "NOT_FOUND",
          message: "Cliente não encontrado",
        });
      }

      if (cliente[0].user_id !== ctx.user!.userId) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "Acesso negado",
        });
      }

      await db.delete(clientes).where(eq(clientes.id, input.id));

      return { success: true };
    }),
});
