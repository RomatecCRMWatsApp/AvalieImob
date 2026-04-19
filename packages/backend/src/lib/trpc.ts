import { initTRPC, TRPCError } from "@trpc/server";
import type { CreateExpressContextOptions } from "@trpc/server/adapters/express";
import jwt from "jsonwebtoken";

interface JWTPayload {
  userId: string;
  email: string;
  role: "admin" | "avaliador" | "cliente";
}

export async function createContext({
  req,
  res,
}: CreateExpressContextOptions) {
  let user: JWTPayload | null = null;

  const token = req.headers.authorization?.replace("Bearer ", "");
  if (token) {
    try {
      user = jwt.verify(
        token,
        process.env.JWT_SECRET || "dev-secret"
      ) as JWTPayload;
    } catch (err) {
      // Token inválido, user fica null
    }
  }

  return { user, req, res };
}

type Context = Awaited<ReturnType<typeof createContext>>;

export const t = initTRPC.context<Context>().create();

export const router = t.router;
export const publicProcedure = t.procedure;

// Procedimento protegido (requer autenticação)
export const protectedProcedure = t.procedure.use(async (opts) => {
  if (!opts.ctx.user) {
    throw new TRPCError({ code: "UNAUTHORIZED" });
  }
  return opts.next({
    ctx: { ...opts.ctx, user: opts.ctx.user },
  });
});

// Procedimento admin
export const adminProcedure = protectedProcedure.use(async (opts) => {
  if (opts.ctx.user?.role !== "admin") {
    throw new TRPCError({ code: "FORBIDDEN" });
  }
  return opts.next();
});
