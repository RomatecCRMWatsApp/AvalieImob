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
const app = express();

app.use(cors({ origin: process.env.CORS_ORIGIN || "*", credentials: true }));
app.use(express.json({ limit: "50mb" }));

async function initializeDatabase() {
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
    const db = drizzle(pool);
    app.locals.db = db;
    console.log("✓ Database conectado");
    return db;
  } catch (error) {
    console.error("✗ Erro ao conectar database:", error);
    throw error;
  }
}

// tRPC
app.use(
  "/api/trpc",
  createExpressMiddleware({ router: appRouter, createContext })
);

// Health check
app.get("/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// Serve React frontend (production)
// __dirname is packages/backend/ when bundled with esbuild --format=cjs
const frontendDist = join(__dirname, "../frontend/dist");
if (existsSync(frontendDist)) {
  app.use(express.static(frontendDist));
  app.get("*", (_req, res) => {
    res.sendFile(join(frontendDist, "index.html"));
  });
} else {
  app.get("/", (_req, res) => {
    res.json({ message: "AvalieImob API v1.0.0" });
  });
}

async function start() {
  app.listen(PORT, () => {
    console.log(`✅ Servidor rodando em http://localhost:${PORT}`);
    console.log(`📡 tRPC: http://localhost:${PORT}/api/trpc`);
  });

  try {
    await initializeDatabase();
  } catch (error) {
    console.error("✗ Erro ao conectar database:", error);
  }
}

start();
