import { TRPCError } from "@trpc/server";
import type { CreateExpressContextOptions } from "@trpc/server/adapters/express";

export function getDb(req: CreateExpressContextOptions["req"]) {
  const db = req.app?.locals?.db;
  if (!db) {
    throw new TRPCError({
      code: "INTERNAL_SERVER_ERROR",
      message: "Database not initialized",
    });
  }
  return db;
}
