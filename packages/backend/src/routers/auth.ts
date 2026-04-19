import { z } from "zod";
import { router, publicProcedure } from "../lib/trpc";
import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import { v4 as uuid } from "uuid";
import { TRPCError } from "@trpc/server";
import { eq } from "drizzle-orm";
import { users } from "@avaliemob/db/schema";

const JWT_SECRET = process.env.JWT_SECRET || "dev-secret";

export const authRouter = router({
  registro: publicProcedure
    .input(
      z.object({
        email: z.string().email(),
        senha: z.string().min(8),
        nome: z.string().min(3),
        cpf: z.string().optional(),
        role: z.enum(["avaliador", "cliente"]).default("cliente"),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      // Verificar se email já existe
      const existing = await db
        .select()
        .from(users)
        .where(eq(users.email, input.email))
        .limit(1);

      if (existing.length > 0) {
        throw new TRPCError({
          code: "CONFLICT",
          message: "Email já cadastrado",
        });
      }

      const hashedPassword = await bcrypt.hash(input.senha, 12);
      const userId = uuid();

      await db.insert(users).values({
        id: userId,
        email: input.email,
        password_hash: hashedPassword,
        nome: input.nome,
        cpf: input.cpf,
        role: input.role,
      });

      const token = jwt.sign(
        { userId, email: input.email, role: input.role },
        JWT_SECRET,
        { expiresIn: "30d" }
      );

      return { token, userId, email: input.email };
    }),

  login: publicProcedure
    .input(
      z.object({
        email: z.string().email(),
        senha: z.string(),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const db = ctx.req.app.locals.db;

      const user = await db
        .select()
        .from(users)
        .where(eq(users.email, input.email))
        .limit(1);

      if (user.length === 0) {
        throw new TRPCError({
          code: "UNAUTHORIZED",
          message: "Email ou senha inválidos",
        });
      }

      const senhaValida = await bcrypt.compare(
        input.senha,
        user[0].password_hash
      );

      if (!senhaValida) {
        throw new TRPCError({
          code: "UNAUTHORIZED",
          message: "Email ou senha inválidos",
        });
      }

      const token = jwt.sign(
        { userId: user[0].id, email: user[0].email, role: user[0].role },
        JWT_SECRET,
        { expiresIn: "30d" }
      );

      return {
        token,
        userId: user[0].id,
        email: user[0].email,
        nome: user[0].nome,
        role: user[0].role,
      };
    }),

  me: publicProcedure.query(async ({ ctx }) => {
    if (!ctx.user) {
      return null;
    }

    const db = ctx.req.app.locals.db;
    const user = await db
      .select()
      .from(users)
      .where(eq(users.id, ctx.user.userId))
      .limit(1);

    if (user.length === 0) return null;

    return {
      id: user[0].id,
      email: user[0].email,
      nome: user[0].nome,
      role: user[0].role,
      crea: user[0].crea,
      incra: user[0].incra,
    };
  }),
});
