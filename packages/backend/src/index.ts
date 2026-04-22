import express from "express";
import cors from "cors";
import { createExpressMiddleware } from "@trpc/server/adapters/express";
import { createContext } from "./lib/trpc";
import { appRouter } from "./routers";
import dotenv from "dotenv";
import mysql from "mysql2/promise";
import { drizzle } from "drizzle-orm/mysql2";
import { join } from "path";
import { existsSync } from "fs";

dotenv.config();

const PORT = process.env.PORT || 3001;
console.log(`Starting on PORT=${PORT}`);

const app = express();

app.use(cors({ origin: "*" }));
app.use(express.json({ limit: "50mb" }));

app.use("/api/trpc", createExpressMiddleware({ router: appRouter, createContext }));

app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

const frontendDist = "/app/packages/frontend/dist";
if (existsSync(frontendDist)) {
  app.use(express.static(frontendDist));
}

app.get("*", (_req, res) => {
  const indexPath = join(frontendDist, "index.html");
  if (existsSync(indexPath)) {
    res.sendFile(indexPath);
  } else {
    res.json({ message: "AvalieImob API v1.0.0" });
  }
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`✅ Server listening on ${PORT}`);
});

setImmediate(async () => {
  try {
    const pool = await mysql.createPool({
      host: process.env.DATABASE_HOST || "mainline.proxy.rlwy.net",
      port: parseInt(process.env.DATABASE_PORT || "56439"),
      user: process.env.DATABASE_USER || "root",
      password: process.env.DATABASE_PASSWORD || "",
      database: process.env.DATABASE_NAME || "avaliacoes_db",
      waitForConnections: true,
      connectionLimit: 10,
      queueLimit: 0,
    });
    app.locals.db = drizzle(pool);
    console.log("✓ DB connected");
  } catch (error) {
    console.error("✗ DB error (server still running):", error);
  }
});

process.on("uncaughtException", (error) => {
  console.error("Uncaught exception:", error);
});

process.on("unhandledRejection", (reason) => {
  console.error("Unhandled rejection:", reason);
});
